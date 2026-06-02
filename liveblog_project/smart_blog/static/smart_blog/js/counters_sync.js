// counters_sync.js — keep card stats and item_detail stats in sync with the server.
// On every listing/detail load (and after filter card swaps) we ask the server for
// live counters of the visible posts and write them into the DOM, so the numbers
// on cards always match the post page.
(function () {
    'use strict';

    const body = document.body;
    const BULK_URL = body?.dataset?.countersBulkUrl || '';
    if (!BULK_URL) return;

    /* Mirror Python smart_blog.utils.count_convert exactly (truncates, not rounds). */
    function humanCount(n) {
        n = Number(n);
        if (!isFinite(n) || n < 0) return '0';
        n = Math.floor(n);
        if (n < 1000) return String(n);
        const units = [[1e9, 'B'], [1e6, 'M'], [1e3, 'K']];
        for (let i = 0; i < units.length; i++) {
            const value = units[i][0];
            const suffix = units[i][1];
            if (n >= value) {
                const res = n / value;
                if (res >= 10) return String(Math.floor(res)) + suffix;
                const truncated = Math.floor(res * 10) / 10;
                return truncated.toFixed(1).replace(/\.0$/, '') + suffix;
            }
        }
        return String(n);
    }

    function collectVisibleItemIds() {
        const ids = new Set();
        document.querySelectorAll('[id^="views-count-"]').forEach((el) => {
            const id = el.id.replace('views-count-', '');
            if (/^\d+$/.test(id)) ids.add(id);
        });
        document.querySelectorAll('.item_block[data-item-id]').forEach((el) => {
            const id = el.dataset.itemId;
            if (id && /^\d+$/.test(id)) ids.add(id);
        });
        if (body.classList.contains('page-item-detail')) {
            const id = body.dataset.itemId;
            if (id && /^\d+$/.test(id)) ids.add(id);
        }
        return Array.from(ids);
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function persistToListingChanges(map) {
        try {
            const key = 'listing_changes';
            const changes = JSON.parse(sessionStorage.getItem(key) || '{}');
            Object.entries(map).forEach(([itemId, c]) => {
                changes[itemId] = changes[itemId] || {};
                if (c.views != null) changes[itemId].views_count = c.views;
                if (c.likes != null) changes[itemId].likes_count = c.likes;
                if (c.comments != null) changes[itemId].comments_count = c.comments;
                if (c.bookmarks != null) changes[itemId].bookmarks_count = c.bookmarks;
                if (c.reposts != null) changes[itemId].reposts_count = c.reposts;
            });
            sessionStorage.setItem(key, JSON.stringify(changes));
        } catch { /* ignore */ }
    }

    function applyCounters(map) {
        const detailId = body.classList.contains('page-item-detail')
            ? String(body.dataset.itemId || '')
            : '';

        Object.entries(map).forEach(([itemId, c]) => {
            if (c.views != null) setText('views-count-' + itemId, humanCount(c.views));
            if (c.likes != null) setText('likes-count-' + itemId, humanCount(c.likes));
            if (c.comments != null) setText('comments-count-' + itemId, humanCount(c.comments));
            if (c.bookmarks != null) setText('bookmarks-count-' + itemId, humanCount(c.bookmarks));
            if (c.reposts != null) setText('reposts-count-' + itemId, humanCount(c.reposts));

            if (detailId && itemId === detailId) {
                if (c.views != null) setText('viewsCount', humanCount(c.views));
                if (c.likes != null) setText('likesCount', humanCount(c.likes));
                if (c.bookmarks != null) setText('bookmarksCount', humanCount(c.bookmarks));
                if (c.reposts != null) setText('repostCount', humanCount(c.reposts));
                if (c.comments != null) {
                    const txt = humanCount(c.comments);
                    setText('commentsCount', txt);
                    document.querySelectorAll('.js-item-detail-comments-count').forEach((node) => {
                        node.textContent = txt;
                    });
                }
            }
        });

        persistToListingChanges(map);
    }

    async function fetchChunk(ids) {
        const url = BULK_URL + (BULK_URL.includes('?') ? '&' : '?') + 'ids=' + ids.join(',');
        const resp = await fetch(url, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            cache: 'no-store',
        });
        if (!resp.ok) return null;
        const data = await resp.json().catch(() => null);
        return data && data.counters ? data.counters : null;
    }

    let syncInFlight = false;

    async function syncCounters() {
        if (syncInFlight) return;
        const ids = collectVisibleItemIds();
        if (!ids.length) return;
        syncInFlight = true;
        try {
            for (let i = 0; i < ids.length; i += 100) {
                const chunk = ids.slice(i, i + 100);
                const counters = await fetchChunk(chunk);
                if (counters) applyCounters(counters);
            }
        } catch { /* ignore */ } finally {
            syncInFlight = false;
        }
    }

    let scheduled = null;
    function scheduleSync(delay) {
        clearTimeout(scheduled);
        scheduled = setTimeout(syncCounters, delay || 0);
    }

    document.addEventListener('DOMContentLoaded', () => scheduleSync(0));
    window.addEventListener('pageshow', () => scheduleSync(0));
    document.addEventListener('brainewsFilterCardsReady', () => scheduleSync(80));

    window.syncPostCounters = syncCounters;
})();
