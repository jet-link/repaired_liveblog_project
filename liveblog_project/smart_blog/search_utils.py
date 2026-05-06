"""
PostgreSQL Full-Text Search and filter utilities.
- Pure FTS on search_vector (title A, text B, tags C). No OR/icontains/DISTINCT.
- Popular: uses denormalized likes_count + DB expression.
- Liked/Bookmarked: use Exists in views.
- Prefix matching: "universe" matches "universal" etc.
"""
import re
from functools import reduce
from operator import or_

from django.db import connection, transaction
from django.db.models import Q


def is_postgresql():
    return connection.vendor == 'postgresql'


def refresh_item_search_vector(item_id):
    """Update search_vector for Item (PostgreSQL FTS). Call after create/edit to ensure search works."""
    if connection.vendor != 'postgresql':
        return
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE smart_blog_item SET search_vector = (
                setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(regexp_replace(text, '<[^>]+>', ' ', 'g'), '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(
                    (SELECT string_agg(t.tag_name, ' ') FROM smart_blog_item_tags it
                     JOIN smart_blog_tag t ON t.id = it.tag_id
                     WHERE it.item_id = smart_blog_item.id),
                    ''
                )), 'C')
            ) WHERE id = %s
        """, [item_id])


def _flush_pending_search_vectors():
    """Run after transaction commit; see schedule_search_vector_refresh."""
    conn = transaction.get_connection()
    pending = getattr(conn, "_search_vector_pending", None)
    if not pending:
        return
    conn._search_vector_pending = set()
    for pk in sorted(pending):
        refresh_item_search_vector(pk)


def schedule_search_vector_refresh(item_id):
    """
    Queue search_vector refresh after commit. Multiple calls in the same transaction
    coalesce into one flush (first on_commit drains the whole pending set).
    Outside of atomic(), runs immediately.
    """
    if connection.vendor != "postgresql" or not item_id:
        return
    pk = int(item_id)
    conn = transaction.get_connection()
    if not conn.in_atomic_block:
        refresh_item_search_vector(pk)
        return
    if not hasattr(conn, "_search_vector_pending"):
        conn._search_vector_pending = set()
    conn._search_vector_pending.add(pk)
    transaction.on_commit(_flush_pending_search_vectors)


def _build_fts_query_with_prefix(q):
    """
    Build tsquery that matches exact words OR word prefixes (universe -> universal).
    Words 5+ chars get prefix variant for fuzzy-like matching.
    Strips special chars to avoid tsquery syntax errors.
    """
    safe_q = re.sub(r'[^\w\s]', ' ', q)
    words = [w.strip() for w in safe_q.split() if w.strip()]
    if not words:
        return q
    parts = []
    for w in words:
        if len(w) >= 5:
            prefix = w[:5] + ':*'
            parts.append('( ' + w + ' | ' + prefix + ' )')
        else:
            parts.append(w)
    return ' & '.join(parts)


def build_search_filter(qs, q, by_title, by_text, by_tags):
    """
    PostgreSQL FTS with field filtering: by_title, by_text, by_tags.
    Always computes tsvector from selected fields (title, text, tags) so search
    works for new posts even before search_vector is backfilled.
    Adds prefix matching so "universe" matches "universal" etc.
    """
    if not q or not (by_title or by_text or by_tags):
        return qs

    if is_postgresql():
        raw_query = _build_fts_query_with_prefix(q)
        table = qs.model._meta.db_table

        # Build tsvector from selected fields (always compute — works even when search_vector is NULL)
        vector_parts = []
        if by_title:
            vector_parts.append(
                "setweight(to_tsvector('simple', coalesce({0}.title, '')), 'A')"
                .format(table)
            )
        if by_text:
            vector_parts.append(
                "setweight(to_tsvector('simple', coalesce(regexp_replace({0}.text, '<[^>]+>', ' ', 'g'), '')), 'B')"
                .format(table)
            )
        if by_tags:
            vector_parts.append(
                "setweight(to_tsvector('simple', coalesce("
                "(SELECT string_agg(t.tag_name, ' ') FROM smart_blog_item_tags it "
                "JOIN smart_blog_tag t ON t.id = it.tag_id "
                "WHERE it.item_id = {0}.id), '')), 'C')"
                .format(table)
            )
        if not vector_parts:
            return qs
        vector_sql = ' || '.join(vector_parts)
        try:
            qs = qs.extra(
                where=["({0}) @@ to_tsquery('simple', %s)".format(vector_sql)],
                select={'rank': "ts_rank(({0}), to_tsquery('simple', %s))".format(vector_sql)},
                params=[raw_query, raw_query],
            )
            qs = qs.order_by('-rank', '-published_date', '-pk')
        except Exception:
            qs = _search_icontains(qs, q, by_title, by_text, by_tags)
    else:
        qs = _search_icontains(qs, q, by_title, by_text, by_tags)

    return qs


def _search_icontains(qs, q, by_title, by_text, by_tags):
    """SQLite fallback. Adds prefix match (universe -> universal) for queries 5+ chars."""
    queries = []
    if by_title:
        queries.append(Q(title__icontains=q))
        if len(q) >= 5:
            queries.append(Q(title__icontains=q[:5]))
    if by_text:
        queries.append(Q(text__icontains=q))
        if len(q) >= 5:
            queries.append(Q(text__icontains=q[:5]))
    if by_tags:
        queries.append(Q(tags__tag_name__icontains=q))
        if len(q) >= 5:
            queries.append(Q(tags__tag_name__icontains=q[:5]))
    if not queries:
        return qs
    # distinct() + M2M joins can clear default Meta.ordering; Paginator needs a deterministic order
    return qs.filter(reduce(or_, queries)).distinct().order_by('-published_date', '-pk')


def get_popularity_queryset(qs, min_likes=None):
    """
    Order by time-decayed popularity:
    (views*0.1 + likes + comments*3 + bookmarks*4 + reposts*5) / (age_hours + 2)^1.5
    """
    if is_postgresql():
        qs = qs.extra(
            select={
                'popularity_score': """
                    (
                        COALESCE(smart_blog_item.views_count, 0) * 0.1 +
                        COALESCE(smart_blog_item.likes_count, 0) +
                        (SELECT COUNT(*) FROM smart_blog_comment c 
                         WHERE c.item_id = smart_blog_item.id AND c.parent_id IS NULL) * 3 +
                        COALESCE(smart_blog_item.bookmarks_count, 0) * 4 +
                        COALESCE(smart_blog_item.reposts_count, 0) * 5
                    )
                    / NULLIF(
                        POWER(
                            GREATEST(0, EXTRACT(EPOCH FROM (now() - smart_blog_item.published_date)) / 3600.0) + 2,
                            1.5
                        ),
                        0
                    )
                """
            },
        ).order_by('-popularity_score')
    else:
        qs = qs.order_by('-likes_count', '-published_date')
    if min_likes is not None:
        qs = qs.filter(likes_count__gte=min_likes)
    return qs


def apply_popular_filter(qs):
    """Popular filter: time-decayed ranking, at least 6 likes."""
    return get_popularity_queryset(qs, min_likes=6)
