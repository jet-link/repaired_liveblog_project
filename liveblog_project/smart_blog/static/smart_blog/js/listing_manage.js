// static/js/listing-manager.js
// listing-memory + listing-apply-changes + breadcrumb-back
// ✅ browser back === breadcrumb
// ✅ no extra fetch
// ✅ no double views
// ✅ correct scroll + highlight

(function () {
    'use strict';

    if (location.pathname.includes('/edit/')) {
        return;
    }

    /* ================= CONFIG ================= */
    const ALLOWED_PATTERNS = ['brainews', 'blog', '/profile', '/search', '/tag', 'smart_blog', '/mindset'];

    function isAllowedPath(pathname) {
        try {
            const p = (pathname || location.pathname || '').toLowerCase();
            // brainstorm.news home now lives at "/" — treat root as an allowed listing surface.
            if (p === '' || p === '/') return true;
            if (p.includes('/topics')) return true;
            return ALLOWED_PATTERNS.some(t => p.includes(t));
        } catch {
            return false;
        }
    }

    /** Mindset: URL keyed in listing_url — must match return target after hashtag filter (# ×). */
    function getMindsetListRestoreUrl() {
        try {
            const pathname = location.pathname || '/';
            const search = window.location.search || '';
            const pathTrim = pathname.replace(/\/+$/, '') || '/';

            if (/^\/profile\/[^/]+\/themes$/i.test(pathTrim)) {
                return pathname.replace(/\/+$/, '') + '/' + search;
            }
            if (pathTrim.startsWith('/mindset/tag')) {
                return '/mindset/';
            }
            if (pathTrim.startsWith('/mindset/theme')) {
                return '/mindset/';
            }
            if (pathTrim === '/mindset') {
                return '/mindset/' + (search === '?' ? '' : search);
            }
        } catch { }
        return '';
    }

    /** Same-origin hashtag filter exit (# ×) → back to profile themes or Mindset hub. */
    function patchMindsetTagExitHref() {
        try {
            if (!location.pathname.includes('/mindset/tag')) return;
            const a = document.querySelector('.mindset-active-tag a.mindset-hashtag[href]');
            if (!a) return;
            const ret = getItem('listing_url');
            if (!ret || ret.indexOf('/mindset/tag/') !== -1) return;
            const u = new URL(ret, location.origin);
            if (u.origin !== location.origin) return;
            const p = u.pathname.replace(/\/+$/, '') || '/';
            const ok = /^\/profile\/[^/]+\/themes$/i.test(p) || /^\/mindset$/i.test(p) || u.pathname.startsWith('/mindset/');
            if (!ok || u.pathname.includes('/mindset/tag/')) return;
            a.setAttribute('href', u.pathname + (u.search || ''));
        } catch { }
    }

    const BRAIN_FILTER_KEY = 'brainews_filter_active';
    /** Set for one nested restoreListingPosition() call triggered by BraiNews after filtered cards hit the DOM. */
    const LISTING_FROM_BRAIN_EVENT = 'listing_from_brainews_cards_ready';

    function isBrainewsFilterableFeedPage() {
        try {
            const path = (location.pathname || '').replace(/\/+$/, '') || '/';
            if (path === '' || path === '/') return true;
            if (path === '/filter' || path.startsWith('/filter/')) return true;
            if (path.endsWith('/brainews') || path === '/brainews' || path === '/blog/brainews') return true;
            if (path.startsWith('/brainews/filter') || path.startsWith('/blog/brainews/filter')) return true;
            if (path === '/search' || path.startsWith('/search/')) return true;
            if (path.startsWith('/tag/') || path.includes('/blog/tag/')) return true;
        } catch { }
        return false;
    }

    function getMindsetAnchorIdFromElement(innerEl) {
        const reply = innerEl?.closest?.('[data-mindset-reply]');
        if (reply) {
            let id = reply.id;
            if (!id || !id.startsWith('mindset-reply-')) {
                const pid = reply.getAttribute('data-mindset-reply');
                if (pid) id = 'mindset-reply-' + pid;
            }
            if (id && id.startsWith('mindset-reply-')) return id;
        }
        const theme = innerEl?.closest?.('[data-mindset-theme]');
        if (theme) {
            let id = theme.id;
            if (!id || !id.startsWith('mindset-theme-')) {
                const tid = theme.getAttribute('data-mindset-theme');
                if (tid) id = 'mindset-theme-' + tid;
            }
            if (id && id.startsWith('mindset-theme-')) return id;
        }
        return null;
    }


    /* ================= Storage helpers ================= */
    function setItem(k, v) { try { sessionStorage.setItem(k, v); } catch { } }
    function getItem(k) { try { return sessionStorage.getItem(k); } catch { return null; } }
    function removeItem(k) { try { sessionStorage.removeItem(k); } catch { } }

    function clearListing() {
        removeItem('listing_url');
        removeItem('listing_scroll');
        removeItem('listing_anchor');
        removeItem('listing_changes');
        removeItem('listing_instant');
        removeItem('listing_section_anchor');
        removeItem('listing_label');
        removeItem('profile_active_tab');
        removeItem('profile_back_url');
        removeItem('profile_back_anchor');
        removeItem('profile_from_detail');
    }

    function clearProfileListingState() {
        removeItem('listing_url');
        removeItem('listing_scroll');
        removeItem('listing_anchor');
        removeItem('listing_instant');
        removeItem('listing_section_anchor');
        removeItem('listing_label');
        removeItem('profile_active_tab');
        removeItem('profile_back_url');
        removeItem('profile_back_anchor');
        removeItem('profile_from_detail');
        try {
            Object.keys(sessionStorage).forEach((key) => {
                if (key.startsWith('section_scroll_index_')) {
                    sessionStorage.removeItem(key);
                }
            });
        } catch { }
    }
    window.clearProfileListingState = clearProfileListingState;

    function isProfilePage() {
        return location.pathname.includes('/profile/');
    }

    function isProfileSectionPage() {
        try {
            const parts = (location.pathname || '').split('/').filter(Boolean);
            return parts.length >= 3 && parts[0] === 'profile';
        } catch {
            return false;
        }
    }

    function getProfileSectionIdFromPath() {
        try {
            const parts = (location.pathname || '').split('/').filter(Boolean);
            if (parts.length >= 3 && parts[0] === 'profile') {
                return 'profile-section-' + parts[2];
            }
        } catch { }
        return null;
    }

    function isItemDetailHref(href) {
        try {
            const u = new URL(href, location.origin);
            if (!u.pathname.includes('/post/')) return false;
            return !u.pathname.includes('/edit/');
        } catch {
            return false;
        }
    }

    function getCurrentTab() {
        try {
            return new URL(location.href).searchParams.get('tab') || 'all';
        } catch {
            return 'all';
        }
    }

    function getCurrentPage() {
        try {
            const p = parseInt(new URL(location.href).searchParams.get('page') || '1', 10);
            return Number.isNaN(p) ? 1 : p;
        } catch {
            return 1;
        }
    }

    /* =====================================================
       Save views_count to listing_changes when on post_detail
       (user just viewed → count increased → cards will show it on return)
    ===================================================== */
    function saveItemDetailViewsToListingChanges() {
        const itemId = document.body.dataset?.itemId;
        const viewsCount = document.body.dataset?.viewsCount;
        if (!itemId || viewsCount === undefined || viewsCount === '') return;
        try {
            const key = 'listing_changes';
            const changes = JSON.parse(sessionStorage.getItem(key) || '{}');
            changes[itemId] = changes[itemId] || {};
            changes[itemId].views_count = viewsCount;
            sessionStorage.setItem(key, JSON.stringify(changes));
        } catch { }
    }

    let profileRefreshInProgress = false;

    async function refreshProfileListing() {
        const section = getItem('profile_refresh_section');
        try {
            const resp = await fetch(location.href, {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                cache: 'no-store'
            });
            if (!resp.ok) return;

            const html = await resp.text();
            const doc = new DOMParser().parseFromString(html, 'text/html');

            if (isProfileSectionPage()) {
                const fresh = doc.querySelector('.profile-section-page');
                const current = document.querySelector('.profile-section-page');
                if (fresh && current) {
                    current.innerHTML = fresh.innerHTML;
                    if (typeof window.__gallery_adjustLastRow === 'function') {
                        setTimeout(window.__gallery_adjustLastRow, 60);
                    }
                }
                return;
            }

            if (!section) return;
            const currentSection = document.getElementById('profile-section-' + section);
            const freshSection = doc.getElementById('profile-section-' + section);
            if (!currentSection || !freshSection) return;

            const currentContainer = currentSection.querySelector('[data-scroll-container]');
            const freshContainer = freshSection.querySelector('[data-scroll-container]');
            if (currentContainer && freshContainer) {
                const currentRow = currentContainer.querySelector('.row') || currentContainer.querySelector('.feed-cards-masonry');
                const freshRow = freshContainer.querySelector('.row') || freshContainer.querySelector('.feed-cards-masonry');
                if (currentRow && freshRow) {
                    currentRow.innerHTML = freshRow.innerHTML;
                    if (typeof window.__gallery_adjustLastRow === 'function') {
                        setTimeout(window.__gallery_adjustLastRow, 60);
                    }
                }
            }

            if (freshSection.dataset?.count) {
                currentSection.dataset.count = freshSection.dataset.count;
            }
            currentSection.__updateControls?.();
        } catch { }
    }

    function maybeRefreshProfileListing() {
        if (!isProfilePage()) return false;
        const needsRefresh = getItem('profile_refresh_needed') === '1';
        const refreshDone = getItem('profile_refresh_done') === '1';

        if (needsRefresh && !refreshDone) {
            if (profileRefreshInProgress) return true;
            profileRefreshInProgress = true;
            setItem('profile_refresh_done', '1');
            refreshProfileListing().finally(() => {
                profileRefreshInProgress = false;
            });
            return true;
        }

        if (needsRefresh && refreshDone) {
            if (profileRefreshInProgress) return true;
            removeItem('profile_refresh_needed');
            removeItem('profile_refresh_done');
            removeItem('profile_refresh_section');
        }
        return false;
    }

    function updateTabCount(tab, delta) {
        const badge = document.querySelector('.custom_badge_danger[data-tab="' + tab + '"]');
        if (badge) {
            const n = parseInt(badge.textContent || '0', 10);
            if (!Number.isNaN(n)) badge.textContent = Math.max(0, n + delta);
        }

        const tabBadge = document.querySelector('.tab-count-badge[data-tab-count="' + tab + '"]');
        if (tabBadge) {
            const n = parseInt(tabBadge.textContent || '0', 10);
            if (!Number.isNaN(n)) tabBadge.textContent = Math.max(0, n + delta);
        }
    }

    function markProfileRemoval(itemId, tab) {
        try {
            const key = 'profile_removed';
            const removed = JSON.parse(sessionStorage.getItem(key) || '{}');
            removed[itemId] = removed[itemId] || {};
            removed[itemId][tab] = true;
            sessionStorage.setItem(key, JSON.stringify(removed));
        } catch { }
    }

    function wasProfileRemoved(itemId, tab) {
        try {
            const key = 'profile_removed';
            const removed = JSON.parse(sessionStorage.getItem(key) || '{}');
            return !!removed[itemId]?.[tab];
        } catch {
            return false;
        }
    }

    function ensureProfilePagination(tab) {
        if (!isProfilePage()) return;
        const cards = document.querySelectorAll('.item_block[data-item-id]');
        if (cards.length > 0) return;

        const currentPage = getCurrentPage();
        if (currentPage <= 1) return;

        const url = new URL(location.href);
        url.searchParams.set('tab', tab || 'all');
        url.searchParams.set('page', String(currentPage - 1));

        if (window.profileTabs && typeof window.profileTabs.fetchAndReplace === 'function') {
            window.profileTabs.fetchAndReplace(url.toString());
        } else {
            location.href = url.toString();
        }
    }

    function scrollToProfileTabs() {
        const tabs = document.querySelector('.tabs_block');
        if (tabs) {
            tabs.scrollIntoView({ behavior: 'auto', block: 'start' });
        }
    }

    /* =====================================================
       0) SAVE VIEWS_COUNT ON ITEM DETAIL LOAD (for instant card updates on back)
    ===================================================== */
    function saveItemDetailViewsToListingChanges() {
        const itemId = document.body.dataset?.itemId;
        const viewsCount = document.body.dataset?.viewsCount;
        if (!itemId || viewsCount == null || viewsCount === '') return;
        try {
            const key = 'listing_changes';
            const changes = JSON.parse(sessionStorage.getItem(key) || '{}');
            changes[itemId] = changes[itemId] || {};
            changes[itemId].views_count = parseInt(viewsCount, 10);
            if (!Number.isNaN(changes[itemId].views_count)) {
                sessionStorage.setItem(key, JSON.stringify(changes));
            }
        } catch { }
    }
    document.addEventListener('DOMContentLoaded', saveItemDetailViewsToListingChanges);

    /* =====================================================
       1) SAVE LISTING STATE ON CARD CLICK
    ===================================================== */
    document.addEventListener('click', function (e) {
        if (!location.pathname.includes('/post/') || location.pathname.includes('/edit/')) return;

        const a = e.target.closest?.('a[href]');
        if (!a) return;

        // Triggers smooth scroll+glow when leaving detail back to a listing surface:
        // breadcrumb link, header brand link, or any other internal link pointing
        // at an allowed listing path that matches our saved listing_url.
        const isBreadcrumb = !!a.closest?.('.breadcrumb-trail');
        const isBrand = a.classList?.contains('brand-minimal');
        const isMindsetBack = a.classList?.contains('mindset-back-link__link');
        let isMindsetHeaderHub = false;
        try {
            const hu = new URL(a.getAttribute('href') || '', location.origin);
            const pth = hu.pathname.replace(/\/+$/, '') || '/';
            isMindsetHeaderHub = !!a.classList?.contains('header-menu-item')
                && hu.origin === location.origin
                && pth === '/mindset';
        } catch { }

        let targetMatchesSavedListing = false;
        try {
            const targetUrl = new URL(a.getAttribute('href') || '', location.origin);
            if (targetUrl.origin === location.origin && !targetUrl.pathname.includes('/post/')) {
                const targetPath = targetUrl.pathname + targetUrl.search;
                if (isAllowedPath(targetPath)) {
                    const savedListing = getItem('listing_url');
                    if (savedListing && savedListing === targetPath) {
                        targetMatchesSavedListing = true;
                    }
                }
            }
        } catch { }

        if (!isBreadcrumb && !isBrand && !targetMatchesSavedListing && !isMindsetBack && !isMindsetHeaderHub) return;

        try {
            setItem('listing_instant', '1');
            setItem('profile_from_detail', '1');
        } catch { }
    }, { passive: true });

    /* Mindset: save scroll + card anchor when opening tag filter; restore on "×" exit. */
    document.addEventListener('click', function (e) {
        const a = e.target.closest?.('.mindset-active-tag a.mindset-hashtag[href]');
        if (!a) return;
        let u;
        try {
            u = new URL(a.getAttribute('href') || '', location.origin);
        } catch {
            return;
        }
        const p = u.pathname.replace(/\/+$/, '') || '/';
        if (p !== '/mindset') return;
        try {
            setItem('listing_instant', '1');
            setItem('profile_from_detail', '1');
        } catch { }
    }, { passive: true });

    document.addEventListener('click', function (e) {
        const a = e.target.closest?.('a.mindset-hashtag[href]');
        if (!a || a.closest('.mindset-active-tag')) return;
        let u;
        try {
            u = new URL(a.getAttribute('href') || '', location.origin);
        } catch {
            return;
        }
        if (!u.pathname.includes('/mindset/tag/')) return;
        const listUrl = getMindsetListRestoreUrl();
        if (!listUrl) return;
        setItem('listing_url', listUrl);
        setItem('listing_scroll', String(window.scrollY || 0));
        const anchor = getMindsetAnchorIdFromElement(a);
        if (anchor) setItem('listing_anchor', anchor);
        removeItem('listing_section_anchor');
    }, { passive: true });

    document.addEventListener('click', function (e) {
        if (!isAllowedPath(location.pathname + location.search)) return;

        let link = e.target.closest?.('a.item-link');
        if (!link) {
            const generic = e.target.closest?.('a[href]');
            if (generic && isItemDetailHref(generic.getAttribute('href') || '')) {
                link = generic;
            }
        }
        if (!link) return;

        if (/^\/mindset(\/|$)/.test(location.pathname || '')) {
            try {
                const uh = new URL(link.href, location.origin);
                if (
                    uh.origin === location.origin
                    && isItemDetailHref(link.getAttribute('href') || '')
                    && uh.pathname.includes('/post/')
                    && !uh.searchParams.has('from')
                ) {
                    uh.searchParams.set('from', 'mindset');
                    uh.searchParams.set(
                        'source_url',
                        location.pathname + (location.search || ''),
                    );
                    link.href = uh.toString();
                }
            } catch { }
        }

        setItem('listing_url', location.pathname + location.search);
        setItem('listing_scroll', String(window.scrollY || 0));
        // Ensure slider restore is instant when returning from detail
        setItem('section_scroll_instant', '1');

        const itemId = link.dataset?.itemId;
        if (itemId) setItem('listing_anchor', 'item-' + itemId);

        const section = link.closest?.('[data-anchor]');
        if (section) {
            setItem('listing_section_anchor', section.dataset.anchor);
        }

        const activeTab = document.querySelector('.profile-section-tab.success_');
        if (activeTab?.dataset?.sectionTarget) {
            setItem('profile_active_tab', activeTab.dataset.sectionTarget);
        }

        try {
            setItem('profile_from_detail', '1');
            /* Smooth scroll + pulse on return (including browser back) from listing → post. */
            setItem('listing_instant', '1');
        } catch { }

        try {
            const sectionId = section?.dataset?.anchor;
            const container = section?.matches?.('[data-scroll-container]')
                ? section
                : section?.querySelector?.('[data-scroll-container]');
            if (sectionId && container) {
                const row = container.querySelector('.row') || container.querySelector('.feed-cards-masonry');
                const card = container.querySelector('.item-card');
                if (card) {
                    const styles = row ? window.getComputedStyle(row) : null;
                    const gap = styles ? parseFloat(styles.columnGap || styles.gap || '0') : 0;
                    const perView = window.matchMedia('(max-width: 768px)').matches ? 1 : 2;
                    const step = (card.getBoundingClientRect().width + (Number.isNaN(gap) ? 0 : gap)) * perView;
                    const index = step ? Math.round(container.scrollLeft / step) : 0;
                    setItem('section_scroll_index_' + sectionId, String(index));
                }
            }
        } catch { }
    }, { passive: true });

    /* =====================================================
       2) RESTORE SCROLL + HIGHLIGHT ON BACK
    ===================================================== */
    function getCardsForShowMore() {
        const container = document.getElementById('filterCardsWrapper');
        return container
            ? Array.from(container.querySelectorAll('.item-card'))
            : Array.from(document.querySelectorAll('.item-card'));
    }

    function getShownCount() {
        const items = getCardsForShowMore();
        if (!items.length) return 0;
        return items.filter(i => !i.classList.contains('listing-hidden')).length;
    }

    function saveShownCount() {
        const wrapper = document.getElementById('showMoreWrapper');
        if (!wrapper) return;
        const shown = getShownCount();
        if (!shown) return;
        setItem('listing_shown_count', String(shown));
        setItem('listing_shown_url', location.pathname + location.search);
    }

    function restoreShownCount() {
        const wrapper = document.getElementById('showMoreWrapper');
        if (!wrapper) return;

        const savedUrl = getItem('listing_shown_url');
        if (!savedUrl || savedUrl !== location.pathname + location.search) return;

        const raw = getItem('listing_shown_count');
        const shown = parseInt(raw || '0', 10);
        if (!shown) return;

        const items = getCardsForShowMore();
        if (!items.length) return;

        items.forEach((item, index) => {
            if (index < shown) {
                item.classList.remove('listing-hidden');
            } else {
                item.classList.add('listing-hidden');
            }
            item.classList.remove('listing-animate');
        });

        const total = items.length;
        const counter = document.getElementById('shownCounter');
        if (counter) counter.textContent = `${Math.min(shown, total)} / ${total}`;
        const btn = document.getElementById('showMoreBtn');
        if (btn) btn.style.display = shown >= total ? 'none' : '';
    }

    function ensureListingCardVisible(el) {
        const wrapper = document.getElementById('showMoreWrapper');
        if (!wrapper || !el) return;

        const card = el.closest?.('.item-card');
        if (!card) return;

        const items = getCardsForShowMore();
        if (!items.length) return;

        const idx = items.indexOf(card);
        if (idx < 0) return;

        for (let i = 0; i <= idx; i += 1) {
            items[i].classList.remove('listing-hidden');
        }

        const total = items.length;
        const shown = items.filter(i => !i.classList.contains('listing-hidden')).length;
        const counter = document.getElementById('shownCounter');
        if (counter) {
            counter.textContent = `${shown} / ${total}`;
        }
        const btn = document.getElementById('showMoreBtn');
        if (btn) {
            btn.style.display = shown >= total ? 'none' : '';
        }
    }

    function smoothScrollToCard(cardEl) {
        if (!cardEl) return false;
        const headerEl = document.querySelector('.header-wrapper');
        const headerH = headerEl ? Math.round(headerEl.getBoundingClientRect().height) : 64;
        const offset = headerH + 24;
        const rect = cardEl.getBoundingClientRect();
        const targetY = Math.max(0, Math.round(rect.top + window.pageYOffset - offset));
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        try {
            window.scrollTo({ top: targetY, behavior: reduce ? 'auto' : 'smooth' });
        } catch {
            window.scrollTo(0, targetY);
        }
        return true;
    }

    function smoothScrollToY(y) {
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        try {
            window.scrollTo({ top: y, behavior: reduce ? 'auto' : 'smooth' });
        } catch {
            window.scrollTo(0, y);
        }
    }

    function restoreListingPosition() {
        if (maybeRefreshProfileListing()) return;
        // Non-listing surfaces (e.g. /post/<slug>/): just bail out. Do NOT clearListing()
        // here — that would wipe state right after a card click on the way to the detail
        // page, breaking the smooth-scroll/glow return flow.
        if (!isAllowedPath(location.pathname + location.search)) return;

        const savedUrl = getItem('listing_url');
        if (!savedUrl || savedUrl !== location.pathname + location.search) return;

        const anchorId = getItem('listing_anchor');
        const sectionAnchor = getItem('listing_section_anchor');
        const targetId = anchorId || sectionAnchor;
        const instant = getItem('listing_instant') === '1';
        const savedTab = getItem('profile_active_tab');

        const fromDetail = getItem('profile_from_detail') === '1';
        const instantSection = getItem('section_scroll_instant') === '1';
        if (savedTab && window.profileSectionsActivate && fromDetail) {
            try { window.profileSectionsActivate(savedTab, instantSection); } catch { }
            if (instantSection) {
                removeItem('section_scroll_instant');
            }
        }

        restoreShownCount();

        const el = targetId ? document.getElementById(targetId) : null;
        if (el) {
            ensureListingCardVisible(el);

            const section = el.closest?.('.profile-section');
            if (section && window.profileSectionsActivate) {
                try { window.profileSectionsActivate(section.id); } catch { }
            }
        }

        const fromBrainCardsReady = getItem(LISTING_FROM_BRAIN_EVENT) === '1';
        /* BraiNews filter replaces cards asynchronously; skip first scroll attempt until filtered HTML is painted. */
        const deferBrainewsScroll = !!(instant && fromDetail && getItem(BRAIN_FILTER_KEY)
            && isBrainewsFilterableFeedPage() && !fromBrainCardsReady);

        if (!deferBrainewsScroll && instant && fromDetail) {
            let cardForScroll = null;
            if (el) {
                if (el.classList?.contains('mindset-theme') || el.classList?.contains('mindset-reply')) {
                    cardForScroll = el;
                } else {
                    cardForScroll = el.closest?.('.item-card') || el;
                }
            }
            requestAnimationFrame(() => {
                if (cardForScroll) {
                    smoothScrollToCard(cardForScroll);
                } else {
                    const savedScroll = parseInt(getItem('listing_scroll') || '0', 10);
                    if (!Number.isNaN(savedScroll)) {
                        smoothScrollToY(savedScroll);
                    }
                }
            });
            removeItem('listing_instant');
        }

        if (deferBrainewsScroll || !targetId || !fromDetail || !el) return;

        const isBlogItem = anchorId && String(anchorId).startsWith('item-');
        const isMindsetCard = anchorId && (
            String(anchorId).startsWith('mindset-theme-')
            || String(anchorId).startsWith('mindset-reply-')
        );
        if (isBlogItem || isMindsetCard) {
            let cardEl = el;
            if (isBlogItem) {
                cardEl = el.closest?.('.item-card') || el;
            }
            cardEl.classList.remove('back-highlight');
            setTimeout(() => {
                void cardEl.offsetWidth;
                cardEl.classList.add('back-highlight');
                setTimeout(() => cardEl.classList.remove('back-highlight'), 1900);
            }, 250);
        }
    }

    document.addEventListener('brainewsFilterCardsReady', function () {
        try {
            setItem(LISTING_FROM_BRAIN_EVENT, '1');
            restoreListingPosition();
        } finally {
            removeItem(LISTING_FROM_BRAIN_EVENT);
        }
    });

    window.addEventListener('pageshow', restoreListingPosition);
    document.addEventListener('DOMContentLoaded', restoreListingPosition);
    document.addEventListener('DOMContentLoaded', patchMindsetTagExitHref);
    window.addEventListener('pageshow', patchMindsetTagExitHref);
    window.addEventListener('pageshow', () => { maybeRefreshProfileListing(); });
    document.addEventListener('DOMContentLoaded', () => { maybeRefreshProfileListing(); });

    if (isProfileSectionPage()) {
        const sectionId = getProfileSectionIdFromPath();
        if (sectionId) {
            setItem('profile_active_tab', sectionId);
            setItem('profile_from_detail', '1');
        }
    }

    /* humanCount: match Python count_convert (1K, 100K, 1.5M, etc.) */
    function humanCount(n) {
        n = Number(n);
        if (isNaN(n) || n < 0) return '0';
        if (n < 1000) return String(n);
        if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + 'B';
        if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
        if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
        return String(n);
    }

    /* =====================================================
       3) APPLY listing_changes (likes / bookmarks / views / comments)
    ===================================================== */
    function applyListingChanges() {
        let changes = {};
        try {
            changes = JSON.parse(sessionStorage.getItem('listing_changes') || '{}');
        } catch { }

        if (!changes || Object.keys(changes).length === 0) return;

        const currentUserId = (document.body.dataset.userId || '').toString();

        Object.entries(changes).forEach(([itemId, data]) => {
            const dataUserId = data.user_id != null ? String(data.user_id) : null;
            const isSameUser = dataUserId !== null && dataUserId === currentUserId;

            if (data.likes_count != null) {
                const n = document.getElementById('likes-count-' + itemId);
                if (n) n.textContent = humanCount(data.likes_count);
            }

            if (data.comments_count != null) {
                const n = document.getElementById('comments-count-' + itemId);
                if (n) n.textContent = humanCount(data.comments_count);
            }

            if (data.views_count != null) {
                const n = document.getElementById('views-count-' + itemId);
                if (n) n.textContent = humanCount(data.views_count);
            }

            if (data.reposts_count != null) {
                const n = document.getElementById('reposts-count-' + itemId);
                if (n) n.textContent = humanCount(data.reposts_count);
            }

            if (data.bookmarked != null && isSameUser) {
                const icon = document.getElementById('bookmark-icon-' + itemId);
                if (icon) {
                    icon.classList.toggle('fa-bookmark', data.bookmarked);
                    icon.classList.toggle('fa-bookmark-o', !data.bookmarked);
                }
                const cardRb = document.getElementById('reading-badge-' + itemId);
                if (cardRb) cardRb.hidden = !data.bookmarked;
                const bodyId = document.body.dataset.itemId;
                if (bodyId != null && String(bodyId) === String(itemId)) {
                    const detailRb = document.getElementById('itemReadingBadge');
                    if (detailRb) detailRb.hidden = !data.bookmarked;
                }
            }

            if (data.liked != null && isSameUser) {
                const icon = document.getElementById('like-icon-' + itemId);
                if (icon) {
                    icon.classList.toggle('fa-heart', data.liked);
                    icon.classList.toggle('fa-heart-o', !data.liked);
                }
            }
        });
    }

    window.applyListingChanges = applyListingChanges;
    window.addEventListener('pageshow', applyListingChanges);
    document.addEventListener('DOMContentLoaded', applyListingChanges);

    /* =====================================================
       4.1) PASS REDIRECT URL ON DELETE
    ===================================================== */
    document.addEventListener('submit', function (e) {
        const form = e.target;
        if (!form || !form.matches || !form.matches('form[data-delete-post]')) return;

        const redirectInput = form.querySelector('input.delete-redirect[name="redirect_to"]');
        if (!redirectInput) return;

        const listingUrl = getItem('listing_url');
        if (listingUrl) {
            redirectInput.value = listingUrl;
        }
    });

    /* =====================================================
       5) CLEAR LISTING WHEN LEAVING ALLOWED PAGES
    ===================================================== */
    document.addEventListener('click', function (e) {
        const a = e.target.closest?.('a[href]');
        if (!a) return;

        if (a.classList?.contains('item-link')) {
            return;
        }

        const href = a.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:')
            || href.startsWith('mailto:') || href.startsWith('tel:')) return;

        let target;
        try {
            target = new URL(href, location.origin);
        } catch {
            return;
        }

        if (target.origin === location.origin) {
            if (target.pathname.includes('/post/')) {
                return;
            }
            if (target.pathname.includes('/post/') && target.pathname.includes('/edit/')) {
                return;
            }
            if (isProfilePage() && !target.pathname.includes('/profile/')) {
                clearProfileListingState();
            }
            if (!isAllowedPath(target.pathname + target.search)) {
                clearListing();
            }
        } else {
            clearListing();
        }
    }, { passive: true });

    document.addEventListener('click', function (e) {
        const showMoreBtn = e.target.closest?.('#showMoreBtn');
        if (showMoreBtn) {
            setTimeout(saveShownCount, 0);
            return;
        }

        const link = e.target.closest?.('a.item-link');
        if (link) {
            saveShownCount();
        }
    }, { passive: true });


    /* =====================================================
       6) REMOVE INVALID CARDS ON BFCache RESTORE (KEY FIX)
    ===================================================== */
    function removeInvalidProfileCards() {
        if (!isProfilePage()) return;

        const url = new URL(location.href);
        const tab = url.searchParams.get('tab');

        let sectionFromPath = null;
        if (isProfileSectionPage()) {
            try {
                const parts = (location.pathname || '').split('/').filter(Boolean);
                if (parts.length >= 3 && parts[0] === 'profile') {
                    sectionFromPath = parts[2];
                }
            } catch { }
        }

        let changes = {};
        try {
            changes = JSON.parse(sessionStorage.getItem('listing_changes') || '{}');
        } catch {
            return;
        }

        const skipRemovedCheck = isProfileSectionPage();

        function removeCard(col, sectionEl, contextKey) {
            if (!skipRemovedCheck && contextKey
                && wasProfileRemoved(col.querySelector('.item_block')?.dataset?.itemId, contextKey)) {
                return false;
            }
            col.remove();
            if (sectionEl) {
                const n = parseInt(sectionEl.dataset.count || '0', 10);
                if (!Number.isNaN(n)) {
                    sectionEl.dataset.count = String(Math.max(0, n - 1));
                }
                sectionEl.__updateControls?.();
            }
            return true;
        }

        let removedCount = 0;
        document.querySelectorAll('.item_block[data-item-id]').forEach(card => {
            const itemId = card.dataset.itemId;
            if (!itemId || !changes[itemId]) return;

            const state = changes[itemId];
            const col = card.closest('.item-card');
            if (!col) return;

            const sectionEl = col.closest('.profile-section');
            const context = tab || sectionFromPath || sectionEl?.dataset?.section || null;

            if (context === 'liked' && state.liked === false) {
                if (removeCard(col, sectionEl, 'liked')) {
                    removedCount += 1;
                    if (!skipRemovedCheck) markProfileRemoval(itemId, 'liked');
                }
            }

            if (context === 'bookmarked' && state.bookmarked === false) {
                if (removeCard(col, sectionEl, 'bookmarked')) {
                    removedCount += 1;
                    if (!skipRemovedCheck) markProfileRemoval(itemId, 'bookmarked');
                }
            }
        });

        if (removedCount > 0 && tab) {
            updateTabCount(tab, -removedCount);
            ensureProfilePagination(tab);
            scrollToProfileTabs();
        }
    }

    window.addEventListener('pageshow', function (event) {
        if (!event.persisted) return;
        removeInvalidProfileCards();
    });

    document.addEventListener('DOMContentLoaded', removeInvalidProfileCards);
    window.addEventListener('profileTabContentReplaced', removeInvalidProfileCards);

    /* =====================================================
    7) REMOVE ITEM FROM PROFILE LISTS WITH SMOOTH ANIMATION
    ===================================================== */
    document.addEventListener('click', function (e) {
        const likeBtn = e.target.closest('#likeBtn');
        const bookmarkBtn = e.target.closest('#bookmarkLink');

        if (!likeBtn && !bookmarkBtn) return;

        // работаем ТОЛЬКО на странице профиля
        if (!location.pathname.includes('/profile/')) return;

        const article = e.target.closest('.item_block');
        if (!article) return;

        const card = article.closest('.item-card');
        if (!card) return;

        const tab = new URL(location.href).searchParams.get('tab');

        // ─────────────────────────────
        // helper: плавное удаление
        // ─────────────────────────────
        function smoothRemove(node) {
            const height = node.offsetHeight;

            // фиксируем высоту
            node.style.height = height + 'px';
            node.style.overflow = 'hidden';

            // следующий кадр — анимация
            requestAnimationFrame(() => {
                node.classList.add('fade-collapse');
                node.style.height = '0px';
                node.style.opacity = '0';
            });

            // удаляем после анимации
            setTimeout(() => {
                node.remove();
            }, 300);
        }

        // ─────────────────────────────
        // ЛОГИКА ТАБОВ
        // ─────────────────────────────
        if (tab === 'liked' && likeBtn) {
            // убрали лайк → публикация больше не должна быть в liked
            setTimeout(() => {
                smoothRemove(card);
                updateTabCount('liked', -1);
                const itemId = article.dataset.itemId;
                if (itemId) markProfileRemoval(itemId, 'liked');
                setTimeout(() => ensureProfilePagination(tab), 350);
                scrollToProfileTabs();
            }, 150);
        }

        if (tab === 'bookmarked' && bookmarkBtn) {
            // убрали bookmark → публикация больше не должна быть в bookmarked
            setTimeout(() => {
                smoothRemove(card);
                updateTabCount('bookmarked', -1);
                const itemId = article.dataset.itemId;
                if (itemId) markProfileRemoval(itemId, 'bookmarked');
                setTimeout(() => ensureProfilePagination(tab), 350);
                scrollToProfileTabs();
            }, 150);
        }
    });

})();


// static/js/item_views_sync.js
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        const body = document.body;

        const itemId = body.dataset.itemId;
        const views = parseInt(body.dataset.viewsCount, 10);

        if (!itemId || Number.isNaN(views)) return;

        try {
            const key = 'listing_changes';
            const changes = JSON.parse(sessionStorage.getItem(key) || '{}');

            // СОХРАНЯЕМ АКТУАЛЬНОЕ ЗНАЧЕНИЕ С СЕРВЕРА
            changes[itemId] = changes[itemId] || {};
            changes[itemId].views_count = views;

            sessionStorage.setItem(key, JSON.stringify(changes));
        } catch { }
    });
})();