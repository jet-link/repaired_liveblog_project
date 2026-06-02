// brainews_filter.js – Liked / Bookmarked filter for BraiNews, Search, Tag
(function () {
    'use strict';

    const FILTER_KEY = 'brainews_filter_active';
    const FILTER_STORAGE_KEY_PREFIX = 'brainews_original_cards_';
    const FILTER_PAGINATION_KEY_PREFIX = 'brainews_original_pagination_';
    let latestFilterRequestId = 0;

    function notifyBrainewsListingCardsReady() {
        try {
            document.dispatchEvent(new CustomEvent('brainewsFilterCardsReady', { bubbles: true }));
        } catch { /* ignore */ }
    }

    function getFilterBaseUrl() {
        const block = document.querySelector('.filter-block[data-filter-url]');
        if (block?.dataset?.filterUrl) return block.dataset.filterUrl;
        const a = document.createElement('a');
        a.href = '/filter/';
        return a.href;
    }

    function isFilterablePage() {
        const path = location.pathname.replace(/\/$/, '') || '/';
        // brainstorm.news home now lives at "/" (former /brainews/).
        if (path === '' || path === '/') return true;
        if (path === '/filter' || path.startsWith('/filter/')) return true;
        // Legacy /brainews/... and /blog/brainews/... paths still recognized (301-redirected server-side).
        if (path === '/brainews' || path === '/blog/brainews' || path.endsWith('/brainews')) return true;
        if (path.startsWith('/brainews/filter') || path.startsWith('/blog/brainews/filter')) return true;
        if (path === '/search' || path.startsWith('/search/')) return true;
        if (path.startsWith('/tag/') || path.includes('/blog/tag/')) return true;
        return false;
    }

    function getPageContextKey() {
        return location.pathname + location.search;
    }

    /** Merge search/tag context into filter API URL (Liked/Bookmarked on Search or Tag page). */
    function mergeFilterContextParams(u) {
        try {
            const cur = new URL(location.href);
            ['q', 'by_title', 'by_text', 'by_tags'].forEach(function (k) {
                const v = cur.searchParams.get(k);
                if (v != null && v !== '') u.searchParams.set(k, v);
            });
            const wrapper = document.getElementById('filterCardsWrapper');
            if (wrapper && wrapper.dataset && wrapper.dataset.tagSlug) {
                u.searchParams.set('tag_slug', wrapper.dataset.tagSlug);
            }
        } catch { /* ignore */ }
    }

    function getFilterUrl(filter, page) {
        const base = getFilterBaseUrl();
        try {
            const u = new URL(base, location.origin);
            u.searchParams.set('filter', filter);
            mergeFilterContextParams(u);
            if (page != null && page > 1) {
                u.searchParams.set('page', String(page));
            } else {
                u.searchParams.delete('page');
            }
            return u.toString();
        } catch {
            let qs = 'filter=' + encodeURIComponent(filter);
            if (page != null && page > 1) qs += '&page=' + encodeURIComponent(String(page));
            return base + (base.includes('?') ? '&' : '?') + qs;
        }
    }

    function setItem(k, v) { try { sessionStorage.setItem(k, v); } catch { } }
    function getItem(k) { try { return sessionStorage.getItem(k); } catch { return null; } }
    function removeItem(k) { try { sessionStorage.removeItem(k); } catch { } }
    const REFRESH_FLAG = 'brainews_filter_refresh_needed';
    function getRefreshFlag() { try { return localStorage.getItem(REFRESH_FLAG); } catch { return null; } }
    function clearRefreshFlag() { try { localStorage.removeItem(REFRESH_FLAG); } catch { } }

    function getFilterButtons() {
        return Array.from(document.querySelectorAll('.filter-block .filter-reason-btn'));
    }

    function getActiveFilter() {
        const btn = getFilterButtons().find(b => b.classList.contains('is-selected'));
        if (!btn) return null;
        const v = btn.dataset.filter;
        return v === 'all' ? null : v;
    }

    const FILTER_TITLES = {
        liked: 'Liked',
        bookmarked: 'Marked',
        posted: 'Posted',
        for_you: 'For you',
    };

    const FOR_YOU_FILTER_HINT = 'Recommended for you — based on your activity';

    /**
     * Delegates to global scrollFilterSegmentSelectedIntoView (filter_segment_scroll.js):
     * all .filter-segment-scroll rows on the page, comfortable padding + center when possible.
     */
    function scrollSelectedFilterChipIntoView() {
        if (typeof window.scrollFilterSegmentSelectedIntoView === 'function') {
            window.scrollFilterSegmentSelectedIntoView();
        }
    }

    function scheduleScrollSelectedFilterChip() {
        requestAnimationFrame(function () {
            requestAnimationFrame(scrollSelectedFilterChipIntoView);
        });
    }

    function setActiveFilter(value) {
        const showAll = !value || value === 'all';
        getFilterButtons().forEach(b => {
            const f = b.dataset.filter;
            const sel = showAll ? f === 'all' : f === value;
            b.classList.toggle('is-selected', sel);
        });
        const forYouHint = document.getElementById('filterSegmentForYouHint');
        if (forYouHint) {
            if (value === 'for_you') {
                forYouHint.textContent = FOR_YOU_FILTER_HINT;
                forYouHint.classList.remove('d-none');
                forYouHint.setAttribute('aria-hidden', 'false');
            } else {
                forYouHint.classList.add('d-none');
                forYouHint.setAttribute('aria-hidden', 'true');
            }
        }
        const titleEl = document.getElementById('brainewsListingTitle');
        if (titleEl) {
            titleEl.classList.add('d-none');
            titleEl.setAttribute('aria-hidden', 'true');
        }
        scheduleScrollSelectedFilterChip();
    }

    function showPagination(show) {
        document.querySelectorAll('#itemsListPaginationBar, #itemsListPagination, #showMoreWrapper').forEach(el => {
            if (el) el.style.display = show ? '' : 'none';
        });
        const ctxBlock = document.getElementById('filterPageContextBlock');
        const titleEl = document.getElementById('brainewsListingTitle');
        if (ctxBlock) {
            if (show) {
                ctxBlock.style.display = '';
                requestAnimationFrame(function () {
                    ctxBlock.classList.remove('filter-context-hidden');
                });
                if (titleEl) {
                    titleEl.classList.add('d-none');
                    titleEl.setAttribute('aria-hidden', 'true');
                }
            } else {
                ctxBlock.classList.add('filter-context-hidden');
                setTimeout(function () { ctxBlock.style.display = 'none'; }, 350);
            }
        }
    }

    function showEmptyHint(msg) {
        const hint = document.getElementById('filterEmptyHint');
        if (!hint) return;
        if (msg) {
            hint.textContent = msg;
            hint.classList.remove('hidden');
        } else {
            hint.textContent = '';
            hint.classList.add('hidden');
        }
    }

    async function fetchFiltered(filter, page) {
        const url = getFilterUrl(filter, page);
        const resp = await fetch(url, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            cache: 'no-store'
        });
        if (!resp.ok) throw new Error('Filter fetch failed');
        return resp.text();
    }

    function applyFilterResponse(html) {
        const wrapper = document.getElementById('filterCardsWrapper');
        if (!wrapper) return;

        const doc = new DOMParser().parseFromString(html, 'text/html');
        const cardsRoot = doc.querySelector('.filter-cards-wrapper');
        const pagBlock = doc.querySelector('[data-filter-pagination]');
        const pagHost = document.getElementById('itemsListPagination');

        const FADE_MS = 200;
        wrapper.classList.add('filter-cards-fade-out');
        setTimeout(function () {
            if (cardsRoot) {
                const pagInside = cardsRoot.querySelector('[data-filter-pagination]');
                if (pagInside) pagInside.remove();
                wrapper.innerHTML = cardsRoot.outerHTML;
            } else {
                wrapper.innerHTML = html;
            }
            if (pagHost) {
                pagHost.innerHTML = pagBlock ? pagBlock.innerHTML : '';
            }
            showPagination(!!pagBlock);

            wrapper.classList.add('filter-cards-fade-in');
            wrapper.offsetHeight;
            requestAnimationFrame(function () {
                wrapper.classList.remove('filter-cards-fade-out');
                wrapper.classList.remove('filter-cards-fade-in');
            });
            if (window.initFilterCardsPagination) window.initFilterCardsPagination();
            if (typeof window.__gallery_adjustLastRow === 'function') {
                setTimeout(window.__gallery_adjustLastRow, 60);
            }
            setTimeout(notifyBrainewsListingCardsReady, 120);
        }, FADE_MS);
    }

    function saveOriginalContent() {
        const wrapper = document.getElementById('filterCardsWrapper');
        if (!wrapper || wrapper.dataset.brainewsOriginalSaved === '1') return;
        try {
            const ctxKey = getPageContextKey();
            sessionStorage.setItem(FILTER_STORAGE_KEY_PREFIX + ctxKey, wrapper.innerHTML);
            const pagHost = document.getElementById('itemsListPagination');
            if (pagHost) {
                sessionStorage.setItem(FILTER_PAGINATION_KEY_PREFIX + ctxKey, pagHost.innerHTML);
            }
            wrapper.dataset.brainewsOriginalSaved = '1';
        } catch { }
    }

    function restoreOriginalContent() {
        const wrapper = document.getElementById('filterCardsWrapper');
        const ctxKey = getPageContextKey();
        const key = FILTER_STORAGE_KEY_PREFIX + ctxKey;
        const pagKey = FILTER_PAGINATION_KEY_PREFIX + ctxKey;
        const saved = sessionStorage.getItem(key);
        const savedPag = sessionStorage.getItem(pagKey);
        if (!wrapper) return;
        if (!saved) {
            removeItem(key);
            removeItem(pagKey);
            if (wrapper.dataset) wrapper.dataset.brainewsOriginalSaved = '';
            showPagination(true);
            notifyBrainewsListingCardsReady();
            return;
        }
        wrapper.classList.add('filter-cards-fade-out');
        const transitionMs = 200;
        requestAnimationFrame(function () {
            setTimeout(function () {
                wrapper.innerHTML = saved;
                const pagHost = document.getElementById('itemsListPagination');
                if (pagHost && savedPag != null) {
                    pagHost.innerHTML = savedPag;
                }
                removeItem(key);
                removeItem(pagKey);
                if (wrapper.dataset) wrapper.dataset.brainewsOriginalSaved = '';
                wrapper.classList.remove('filter-cards-fade-out');
                wrapper.classList.add('filter-cards-fade-in');
                wrapper.offsetHeight;
                wrapper.classList.remove('filter-cards-fade-in');
                showPagination(true);
                if (window.applyListingChanges) window.applyListingChanges();
                if (window.initFilterCardsPagination) window.initFilterCardsPagination();
                if (typeof window.__gallery_adjustLastRow === 'function') {
                    setTimeout(window.__gallery_adjustLastRow, 60);
                }
                notifyBrainewsListingCardsReady();
            }, transitionMs + 120);
        });
    }

    function applyFilter(filter) {
        if (!filter || filter === 'all') {
            latestFilterRequestId++;
            clearRefreshFlag();
            const hadStored = getItem(FILTER_KEY);
            let hadSnapshot = false;
            try {
                hadSnapshot = !!sessionStorage.getItem(FILTER_STORAGE_KEY_PREFIX + getPageContextKey());
            } catch { /* ignore */ }
            removeItem(FILTER_KEY);
            setActiveFilter(null);
            if (!isFilterablePage()) return;
            if (!hadStored && !hadSnapshot) {
                showPagination(true);
                showEmptyHint('');
                notifyBrainewsListingCardsReady();
                return;
            }
            restoreOriginalContent();
            showEmptyHint('');
            return;
        }
        latestFilterRequestId++;
        const myReqId = latestFilterRequestId;
        saveOriginalContent();
        setActiveFilter(filter);
        setItem(FILTER_KEY, filter);

        fetchFiltered(filter, 1).then(html => {
            if (myReqId !== latestFilterRequestId) return;
            applyFilterResponse(html);
            const emptyEl = document.querySelector('.filter-empty-message');
            if (emptyEl) {
                showEmptyHint(emptyEl.textContent);
            } else {
                showEmptyHint('');
            }
            if (window.applyListingChanges) window.applyListingChanges();
        }).catch(() => {
            if (myReqId !== latestFilterRequestId) return;
            showEmptyHint('Failed to load filter');
        });
    }

    function removeInvalidFilterCards() {
        if (!isFilterablePage()) return;
        const active = getItem(FILTER_KEY);
        if (!active || (active !== 'liked' && active !== 'bookmarked')) return;

        let changes = {};
        try {
            changes = JSON.parse(sessionStorage.getItem('listing_changes') || '{}');
        } catch { return }

        document.querySelectorAll('.filter-cards-wrapper .item_block[data-item-id], #filterCardsWrapper .item_block[data-item-id]').forEach(card => {
            const itemId = card.dataset.itemId;
            if (!itemId || !changes[itemId]) return;
            const state = changes[itemId];
            const col = card.closest('.item-card');
            if (!col) return;

            if (active === 'liked' && state.liked === false) {
                col.remove();
            }
            if (active === 'bookmarked' && state.bookmarked === false) {
                col.remove();
            }
        });
    }

    function onFilterChange(e) {
        const btn = e.target.closest('.filter-block .filter-reason-btn');
        if (!btn) return;
        if (!isFilterablePage()) return;
        if (btn.classList.contains('is-selected')) return;

        if (typeof window.scrollPageToTopForListingFilter === 'function') {
            window.scrollPageToTopForListingFilter();
        }

        const value = btn.dataset.filter;
        if (value === 'all') {
            applyFilter(null);
        } else {
            applyFilter(value);
        }
    }

    document.addEventListener('click', onFilterChange);
    document.addEventListener('click', function (e) {
        const a = e.target.closest('a[href]');
        if (!a) return;
        /* Breadcrumbs: keep Liked/Bookmarked etc. when returning to listings via trail links. */
        if (a.closest('.breadcrumb-trail')) return;
        try {
            const u = new URL(a.getAttribute('href') || '', location.origin);
            const path = u.pathname.replace(/\/$/, '') || '/';
            const targetPath = path + (u.search || '');
            const currentPath = getPageContextKey();
            if (targetPath !== currentPath && !u.searchParams.get('filter')) {
                /* Keep filter when drilling into item detail — return should restore Liked/etc. */
                const isPostDetailNav = u.pathname.includes('/post/') && !u.pathname.includes('/edit/');
                if (isPostDetailNav) {
                    return;
                }
                removeItem(FILTER_KEY);
            }
        } catch { }
    }, { passive: true });

    function restoreFilterOnReturnForPage() {
        const active = getItem(FILTER_KEY);
        if (!active) return;
        latestFilterRequestId++;
        const myReqId = latestFilterRequestId;
        clearRefreshFlag();
        saveOriginalContent();
        setActiveFilter(active);
        fetchFiltered(active, 1).then(html => {
            if (myReqId !== latestFilterRequestId) return;
            applyFilterResponse(html);
            const emptyEl = document.querySelector('.filter-empty-message');
            if (emptyEl) {
                showEmptyHint(emptyEl.textContent);
            } else {
                showEmptyHint('');
            }
            if (window.applyListingChanges) window.applyListingChanges();
        }).catch(() => {
            if (myReqId !== latestFilterRequestId) return;
            applyFilter(null);
        });
    }

    function initFilterBlockFromStorage() {
        const block = document.querySelector('.filter-block');
        if (!block) return;
        if (!isFilterablePage()) {
            block.style.display = 'none';
            return;
        }
        const active = getItem(FILTER_KEY);
        if (active) {
            restoreFilterOnReturnForPage();
        } else {
            requestAnimationFrame(function () {
                requestAnimationFrame(notifyBrainewsListingCardsReady);
            });
        }
    }

    document.addEventListener('DOMContentLoaded', initFilterBlockFromStorage);
    (document.documentElement || document).addEventListener('turbo:load', initFilterBlockFromStorage);

    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) {
            if (isFilterablePage()) {
                const active = getItem(FILTER_KEY);
                if (active) restoreFilterOnReturnForPage();
                else removeInvalidFilterCards();
            }
            return;
        }
        if (isFilterablePage()) {
            refreshFilterIfNeeded();
            removeInvalidFilterCards();
        }
    });

    window.addEventListener('pageshow', function () {
        if (isFilterablePage()) removeInvalidFilterCards();
    });

    document.addEventListener('DOMContentLoaded', removeInvalidFilterCards);

    function refreshFilterIfNeeded() {
        if (!isFilterablePage()) return;
        const active = getItem(FILTER_KEY);
        if (active !== 'liked' && active !== 'bookmarked') return;
        if (getRefreshFlag() !== '1') return;
        clearRefreshFlag();
        latestFilterRequestId++;
        const myReqId = latestFilterRequestId;
        setActiveFilter(active);
        fetchFiltered(active, 1).then(html => {
            if (myReqId !== latestFilterRequestId) return;
            applyFilterResponse(html);
            const emptyEl = document.querySelector('.filter-empty-message');
            if (emptyEl) {
                showEmptyHint(emptyEl.textContent);
            } else {
                showEmptyHint('');
            }
            if (window.applyListingChanges) window.applyListingChanges();
        }).catch(() => {});
    }

    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') {
            refreshFilterIfNeeded();
        }
    });

    window.addEventListener('focus', refreshFilterIfNeeded);

    window.addEventListener('storage', function (e) {
        if (e.key === REFRESH_FLAG && e.newValue === '1') {
            refreshFilterIfNeeded();
        }
    });

    document.addEventListener('brainews-filter-refresh', function () {
        removeInvalidFilterCards();
        refreshFilterIfNeeded();
    });

    /* Filter tabs: Prev / page numbers / Next (same paginator as All, via AJAX) */
    document.addEventListener('click', function (e) {
        const link = e.target.closest(
            '#itemsListPagination a.paginator-btn, #itemsListPagination a.paginator-page'
        );
        if (!link || !document.body.contains(link)) return;
        const active = getActiveFilter();
        if (!active) return;

        e.preventDefault();
        let page = 1;
        try {
            const u = new URL(link.getAttribute('href') || '', location.origin);
            page = parseInt(u.searchParams.get('page') || '1', 10);
        } catch { return; }
        if (Number.isNaN(page) || page < 1) page = 1;

        if (typeof window.scrollPageToTopForListingFilter === 'function') {
            window.scrollPageToTopForListingFilter();
        }

        latestFilterRequestId++;
        const myReqId = latestFilterRequestId;
        fetchFiltered(active, page).then(function (html) {
            if (myReqId !== latestFilterRequestId) return;
            applyFilterResponse(html);
            if (window.applyListingChanges) window.applyListingChanges();
        }).catch(function () {
            if (myReqId !== latestFilterRequestId) return;
            showEmptyHint('Failed to load page');
        });
    });

})();
