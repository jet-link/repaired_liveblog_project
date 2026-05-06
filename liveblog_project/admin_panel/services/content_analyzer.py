"""
Content moderation analyzer: Banned words + Regex + Abuse patterns + OpenAI.
Uses full text for words/regex/abuse checks; only the OpenAI step truncates input.
"""
import re
import unicodedata
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags
from django.db import IntegrityError
from django.db.models import Q

from admin_panel.services.openai_moderator import (
    openai_moderate,
    openai_classify,
    batch_moderate,
    _truncate_for_ai,
)

logger = logging.getLogger(__name__)


def _normalize_text(text):
    """Lowercase, strip, NFKC-normalize. Handles long text and unicode evasion."""
    if not text:
        return ''
    s = str(text).strip()
    s = unicodedata.normalize('NFKC', s)
    return s.lower()


def check_banned_words(text, forbidden_words):
    """
    Check text against forbidden word list.
    Returns (found, word, reason) or (False, None, None).
    """
    if not text or not forbidden_words:
        return False, None, None
    normalized = _normalize_text(text)
    for fw in forbidden_words:
        if not fw.is_active:
            continue
        # Whole word or as substring
        if fw.word.lower() in normalized:
            return True, fw.word, fw.reason
    return False, None, None


def check_regex_patterns(text, forbidden_patterns):
    """
    Check text against regex patterns.
    Returns (found, match, reason) or (False, None, None).
    """
    if not text or not forbidden_patterns:
        return False, None, None
    for fp in forbidden_patterns:
        if not fp.is_active:
            continue
        try:
            m = re.search(fp.pattern, text, re.IGNORECASE)
            if m:
                return True, m.group(0)[:255], fp.reason
        except re.error:
            logger.warning('Invalid regex pattern: %s', fp.pattern[:50])
            continue
    return False, None, None


# Regex patterns for violence/abuse (checked before Detoxify for speed)
ABUSE_PATTERNS = [
    (r'\bhit\s+(women|men|kids?|children|people)\b', 'abuse'),
    (r'\b(kill|hurt|beat)\s+(women|men|kids?|children|people|them|us)\b', 'abuse'),
    (r'\b(women|men|people)\s+(need|must|should)\s+(hit|kill|hurt|beat)\b', 'abuse'),
    (r'\b(need|must|gotta|got\s+to|need\s+to)\s+(hit|kill|hurt|beat)\s+\w+', 'abuse'),
    (r'\b(punch|stab|attack)\s+(women|men|kids?|people)\b', 'abuse'),
    (r'\bviolence\s+against\s+(women|men|children)\b', 'abuse'),
]


def check_abuse_patterns(text):
    """
    Check for violence/abuse phrases that Detoxify may miss.
    Returns (found, match, reason) or (False, None, None).
    """
    if not text:
        return False, None, None
    for pattern, reason in ABUSE_PATTERNS:
        try:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return True, m.group(0)[:255], reason
        except re.error:
            continue
    return False, None, None


def analyze_content(text, forbidden_words, forbidden_patterns, use_ai=True, ai_stats=None):
    """
    Run full pipeline: banned words -> regex -> abuse patterns -> OpenAI moderation -> OpenAI classifier.
    Returns (is_violation, reason, detected_word).

    ``ai_stats`` is an optional dict updated with counters
    ``{'moderated': int, 'classified': int, 'errors': int, 'ai_hits': int}``
    so the calling pipeline can summarise OpenAI usage in AnalysisRun.log_lines.
    """
    # 1. Banned words
    found, word, reason = check_banned_words(text, forbidden_words)
    if found:
        return True, reason, word

    # 2. Regex
    found, match, reason = check_regex_patterns(text, forbidden_patterns)
    if found:
        return True, reason, match[:255] if match else 'regex_match'

    # 3. Violence/abuse patterns (before OpenAI)
    found, match, reason = check_abuse_patterns(text)
    if found:
        return True, reason, match[:255] if match else 'abuse'

    # 4. OpenAI moderation (free, fixed taxonomy) — catches harassment/sexual/violence/self-harm
    if use_ai:
        ai_text = _truncate_for_ai(text)
        if ai_stats is not None:
            ai_stats['moderated'] = ai_stats.get('moderated', 0) + 1
        try:
            found, reason, detected = openai_moderate(ai_text)
        except Exception as exc:
            logger.warning('openai_moderate raised: %s', exc)
            if ai_stats is not None:
                ai_stats['errors'] = ai_stats.get('errors', 0) + 1
            found = False
        if found:
            if ai_stats is not None:
                ai_stats['ai_hits'] = ai_stats.get('ai_hits', 0) + 1
            return True, reason, detected or 'AI:moderation'

        # 5. OpenAI Chat classifier with custom blocklist (catches site-specific rules)
        if ai_stats is not None:
            ai_stats['classified'] = ai_stats.get('classified', 0) + 1
        try:
            found, reason, detected = openai_classify(ai_text, forbidden_words, forbidden_patterns)
        except Exception as exc:
            logger.warning('openai_classify raised: %s', exc)
            if ai_stats is not None:
                ai_stats['errors'] = ai_stats.get('errors', 0) + 1
            found = False
        if found:
            if ai_stats is not None:
                ai_stats['ai_hits'] = ai_stats.get('ai_hits', 0) + 1
            return True, reason, detected or 'AI:gpt'

    return False, None, None


def _deterministic_check(text, forbidden_words, forbidden_patterns):
    """Run only words / regex / abuse-pattern checks (no AI). Internal helper."""
    found, word, reason = check_banned_words(text, forbidden_words)
    if found:
        return True, reason, word
    found, match, reason = check_regex_patterns(text, forbidden_patterns)
    if found:
        return True, reason, match[:255] if match else 'regex_match'
    found, match, reason = check_abuse_patterns(text)
    if found:
        return True, reason, match[:255] if match else 'abuse'
    return False, None, None


def analyze_batch(texts, forbidden_words, forbidden_patterns, *, use_ai=True, ai_stats=None):
    """
    Bulk moderation pipeline: deterministic checks per text, then a single
    Moderation API request for all remaining texts (chunked), then a parallel
    GPT classifier for items still pending (only when a custom blocklist is
    configured and ``OPENAI_USE_CLASSIFIER`` is on).

    Returns a list of ``(found, reason, detected)`` tuples aligned to ``texts``.
    """
    n = len(texts)
    out = [(False, None, None)] * n
    if n == 0:
        return out

    # Stage 1-3: deterministic
    pending_idx = []
    pending_texts = []
    for i, t in enumerate(texts):
        text = t or ''
        if not text:
            continue
        found, reason, detected = _deterministic_check(text, forbidden_words, forbidden_patterns)
        if found:
            out[i] = (True, reason, detected)
        elif use_ai:
            pending_idx.append(i)
            pending_texts.append(_truncate_for_ai(text))

    if not use_ai or not pending_idx:
        return out

    # Stage 4: batched Moderation API
    if ai_stats is not None:
        ai_stats['moderated'] = ai_stats.get('moderated', 0) + len(pending_texts)
    try:
        mod_results = batch_moderate(pending_texts)
    except Exception as exc:
        logger.warning('batch_moderate failed: %s', exc)
        if ai_stats is not None:
            ai_stats['errors'] = ai_stats.get('errors', 0) + 1
        mod_results = [(False, None, None)] * len(pending_texts)

    next_idx = []
    next_texts = []
    for j, idx in enumerate(pending_idx):
        try:
            found, reason, detected = mod_results[j]
        except IndexError:
            found = False
            reason = detected = None
        if found:
            out[idx] = (True, reason, detected or 'AI:moderation')
            if ai_stats is not None:
                ai_stats['ai_hits'] = ai_stats.get('ai_hits', 0) + 1
        else:
            next_idx.append(idx)
            next_texts.append(pending_texts[j])

    # Stage 5: parallel GPT classifier (optional, slow, opt-in)
    use_classifier = bool(getattr(settings, 'OPENAI_USE_CLASSIFIER', True))
    has_blocklist = bool(forbidden_words) or bool(forbidden_patterns)
    if not (use_classifier and has_blocklist and next_texts):
        return out

    parallelism = max(1, int(getattr(settings, 'OPENAI_PARALLELISM', 8) or 8))
    if ai_stats is not None:
        ai_stats['classified'] = ai_stats.get('classified', 0) + len(next_texts)

    def _run_classify(text):
        try:
            return openai_classify(text, forbidden_words, forbidden_patterns)
        except Exception as exc:
            logger.warning('openai_classify failed: %s', exc)
            return None

    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        futures = {
            executor.submit(_run_classify, text): k
            for k, text in enumerate(next_texts)
        }
        for future in as_completed(futures):
            k = futures[future]
            idx = next_idx[k]
            result = future.result()
            if result is None:
                if ai_stats is not None:
                    ai_stats['errors'] = ai_stats.get('errors', 0) + 1
                continue
            found, reason, detected = result
            if found:
                out[idx] = (True, reason, detected or 'AI:gpt')
                if ai_stats is not None:
                    ai_stats['ai_hits'] = ai_stats.get('ai_hits', 0) + 1

    return out


def recheck_and_clear_violation_if_clean(item=None, comment=None):
    """
    After edit: if content no longer has violations, remove the ContentViolation.
    Call with item=... or comment=... (exactly one).
    """
    from admin_panel.models import ContentViolation, ForbiddenWord, ForbiddenPattern

    if item:
        if not ContentViolation.objects.filter(item=item).exists():
            return
        try:
            tag_names = ' '.join(t.name for t in item.tags.all())
        except Exception:
            tag_names = ''
        parts = [
            str(item.title or ''),
            strip_tags(str(item.text or '')),
            (item.category.name if item.category else ''),
            str(item.slug or ''),
            tag_names,
        ]
        text = ' '.join(p for p in parts if p)
    elif comment:
        if not ContentViolation.objects.filter(comment=comment).exists():
            return
        text = strip_tags(str(comment.text or ''))
    else:
        return

    forbidden_words = list(ForbiddenWord.objects.filter(is_active=True))
    forbidden_patterns = list(ForbiddenPattern.objects.filter(is_active=True))
    is_violation, _, _ = analyze_content(text, forbidden_words, forbidden_patterns, use_ai=True)
    if not is_violation:
        author = (item.author if item else None) or (comment.author if comment else None)
        if item:
            ContentViolation.objects.filter(item=item).delete()
        else:
            ContentViolation.objects.filter(comment=comment).delete()
        logger.info('Cleared ContentViolation: content edited and no longer violates.')
        if author:
            from django.db import transaction
            from admin_panel.services.trust_score_service import update_user_trust_score
            def _recalc():
                try:
                    update_user_trust_score(author)
                except Exception:
                    pass
            transaction.on_commit(_recalc)


def run_content_analysis(schedule='now', analysis_run=None, log_callback=None, use_ai=None):
    """
    Run full content analysis: fetch items/comments, check each, create ContentViolation.
    analysis_run: AnalysisRun instance to update progress/logs.
    log_callback: optional callable(msg) for real-time logs.
    use_ai: tri-state. None = auto-detect from settings.OPENAI_API_KEY;
            True forces OpenAI checks (errors logged if no key); False disables them.
    """
    from admin_panel.models import (
        AnalysisRun, ContentViolation, ForbiddenWord, ForbiddenPattern,
    )
    from smart_blog.models import Item, Comment

    def log(msg):
        if log_callback:
            log_callback(msg)
        if analysis_run:
            lines = list(analysis_run.log_lines or [])
            lines.append(f'[{timezone.now().isoformat()}] {msg}')
            analysis_run.log_lines = lines
            analysis_run.save(update_fields=['log_lines'])

    # Resolve analysis_run
    if not analysis_run:
        analysis_run = AnalysisRun.objects.create(
            schedule=schedule,
            status=AnalysisRun.STATUS_RUNNING,
            progress=0,
        )

    ai_stats = {'moderated': 0, 'classified': 0, 'errors': 0, 'ai_hits': 0}

    try:
        if use_ai is None:
            ai_enabled = bool(getattr(settings, 'OPENAI_API_KEY', '') or '')
        else:
            ai_enabled = bool(use_ai)
        use_classifier = bool(getattr(settings, 'OPENAI_USE_CLASSIFIER', True))
        batch_size = max(1, int(getattr(settings, 'OPENAI_BATCH_SIZE', 32) or 32))

        log('Start Analysis!')
        forbidden_words = list(ForbiddenWord.objects.filter(is_active=True))
        forbidden_patterns = list(ForbiddenPattern.objects.filter(is_active=True))
        log(f'Loaded {len(forbidden_words)} forbidden words, {len(forbidden_patterns)} patterns')
        if ai_enabled:
            classifier_state = 'on' if use_classifier else 'off'
            log(
                f'OpenAI: enabled (Moderation API batched, batch={batch_size}; '
                f'GPT classifier {classifier_state})'
            )
        else:
            log('OpenAI moderation: disabled (OPENAI_API_KEY not set) — using deterministic checks only')
        if not forbidden_words and not forbidden_patterns and not ai_enabled:
            log('Warning: no active forbidden words/patterns and OpenAI is off; nothing will flag content.')

        # Content created since cutoff
        if schedule == 'hourly':
            cutoff = timezone.now() - timedelta(hours=1)
        elif schedule == 'daily':
            cutoff = timezone.now() - timedelta(days=1)
        else:
            cutoff = None  # Check all for 'now'

        # Skip items/comments that already have a ContentViolation row to avoid duplicates.
        existing_items = set(
            ContentViolation.objects.filter(
                item__isnull=False,
            ).values_list('item_id', flat=True)
        )
        existing_comments = set(
            ContentViolation.objects.filter(
                comment__isnull=False,
            ).values_list('comment_id', flat=True)
        )

        # Items
        item_qs = Item.objects.select_related('category').prefetch_related('tags').all()
        if cutoff:
            item_qs = item_qs.filter(created__gte=cutoff)
        items = list(item_qs.order_by('-created')[:5000])  # Limit batch
        total = len(items)

        # Comments
        comment_qs = Comment.objects.select_related('item').all()
        if cutoff:
            comment_qs = comment_qs.filter(created__gte=cutoff)
        comments = list(comment_qs.order_by('-created')[:5000])
        total += len(comments)

        if total == 0:
            log('No new content to analyze.')
            analysis_run.status = AnalysisRun.STATUS_COMPLETED
            analysis_run.progress = 100
            analysis_run.finished_at = timezone.now()
            analysis_run.save(update_fields=['status', 'progress', 'finished_at'])
            return analysis_run

        processed = 0
        violations_created = 0

        def _save_progress(force=False):
            """Throttle progress updates: at most one DB write per ~3% delta."""
            if not analysis_run or total <= 0:
                return
            new_progress = min(99, int(100 * processed / total))
            last = getattr(_save_progress, '_last', -1)
            if force or new_progress - last >= 3:
                analysis_run.progress = new_progress
                analysis_run.save(update_fields=['progress'])
                _save_progress._last = new_progress

        def _build_item_text(item):
            try:
                tag_names = ' '.join(t.name for t in item.tags.all())
            except Exception:
                tag_names = ''
            parts = [
                str(item.title or ''),
                strip_tags(str(item.text or '')),
                (item.category.name if item.category else ''),
                str(item.slug or ''),
                tag_names,
            ]
            return ' '.join(p for p in parts if p)

        def _persist_post_violation(item, reason, detected):
            severity = ContentViolation.get_severity_from_reason(reason)
            confidence = ContentViolation.get_confidence_from_detected(detected, reason)
            try:
                ContentViolation.objects.create(
                    content_type=ContentViolation.TYPE_POST,
                    item=item,
                    reason=reason,
                    severity=severity,
                    confidence=confidence,
                    detected_word=detected[:255],
                    status=ContentViolation.STATUS_PENDING,
                    analysis_run=analysis_run,
                )
            except IntegrityError:
                logger.warning(
                    'Skipped duplicate post violation (race or constraint): item_id=%s',
                    item.pk,
                )
                existing_items.add(item.pk)
                return False
            existing_items.add(item.pk)
            user = item.author
            if user:
                try:
                    from admin_panel.services.trust_score_service import update_user_trust_score
                    update_user_trust_score(user, set_last_violation=True)
                except Exception as e:
                    logger.exception('Trust score update failed for user %s: %s', user.pk, e)
            log(f'Violation: Post #{item.pk} ({reason}): {detected[:50]}...')
            return True

        def _persist_comment_violation(comment, reason, detected):
            severity = ContentViolation.get_severity_from_reason(reason)
            confidence = ContentViolation.get_confidence_from_detected(detected, reason)
            try:
                ContentViolation.objects.create(
                    content_type=ContentViolation.TYPE_COMMENT,
                    comment=comment,
                    reason=reason,
                    severity=severity,
                    confidence=confidence,
                    detected_word=detected[:255],
                    status=ContentViolation.STATUS_PENDING,
                    analysis_run=analysis_run,
                )
            except IntegrityError:
                logger.warning(
                    'Skipped duplicate comment violation (race or constraint): comment_id=%s',
                    comment.pk,
                )
                existing_comments.add(comment.pk)
                return False
            existing_comments.add(comment.pk)
            user = comment.author
            if user:
                try:
                    from admin_panel.services.trust_score_service import update_user_trust_score
                    update_user_trust_score(user, set_last_violation=True)
                except Exception as e:
                    logger.exception('Trust score update failed for user %s: %s', user.pk, e)
            log(f'Violation: Comment #{comment.pk} ({reason}): {detected[:50]}...')
            return True

        # ---- Items ----
        items_to_check = [i for i in items if i.pk not in existing_items]
        skipped_items = len(items) - len(items_to_check)
        processed += skipped_items
        for chunk_start in range(0, len(items_to_check), batch_size):
            chunk = items_to_check[chunk_start:chunk_start + batch_size]
            texts = [_build_item_text(it) for it in chunk]
            results = analyze_batch(
                texts, forbidden_words, forbidden_patterns,
                use_ai=ai_enabled, ai_stats=ai_stats,
            )
            for item, (is_violation, reason, detected) in zip(chunk, results):
                if is_violation and _persist_post_violation(item, reason, detected):
                    violations_created += 1
                processed += 1
            _save_progress()

        # ---- Comments ----
        comments_to_check = [c for c in comments if c.pk not in existing_comments]
        skipped_comments = len(comments) - len(comments_to_check)
        processed += skipped_comments
        for chunk_start in range(0, len(comments_to_check), batch_size):
            chunk = comments_to_check[chunk_start:chunk_start + batch_size]
            texts = [strip_tags(str(c.text or '')) for c in chunk]
            results = analyze_batch(
                texts, forbidden_words, forbidden_patterns,
                use_ai=ai_enabled, ai_stats=ai_stats,
            )
            for comment, (is_violation, reason, detected) in zip(chunk, results):
                if is_violation and _persist_comment_violation(comment, reason, detected):
                    violations_created += 1
                processed += 1
            _save_progress()

        _save_progress(force=True)

        if ai_enabled:
            log(
                f'OpenAI: moderated={ai_stats["moderated"]}, '
                f'classified={ai_stats["classified"]}, '
                f'ai_hits={ai_stats["ai_hits"]}, '
                f'errors={ai_stats["errors"]}'
            )
        log(f'Finish Analysis! Processed {processed} items. Found {violations_created} violations.')
        analysis_run.status = AnalysisRun.STATUS_COMPLETED
        analysis_run.progress = 100
        analysis_run.finished_at = timezone.now()
        analysis_run.save(update_fields=['status', 'progress', 'finished_at'])

    except Exception as e:
        logger.exception('Content analysis failed: %s', e)
        log(f'Error: {e}')
        analysis_run.status = AnalysisRun.STATUS_FAILED
        analysis_run.finished_at = timezone.now()
        analysis_run.save(update_fields=['status', 'finished_at'])

    return analysis_run
