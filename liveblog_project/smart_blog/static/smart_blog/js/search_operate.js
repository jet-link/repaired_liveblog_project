// Fullscreen search overlay: history, FTS suggestions, Enter → /search/
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    var __searchOverlayOpen = false;
    var OVERLAY_HISTORY_MAX = 25;
    var SEARCH_MAX_CHARS = 150;
    var SEARCH_MAX_WORDS = 15;
    var SEARCH_MIN_CHARS = 2;
    var SUGGEST_DEBOUNCE_MS = 280;

    function $$(sel, ctx) {
        try { return Array.from((ctx || document).querySelectorAll(sel)); } catch (e) { return []; }
    }

    function showBrainPreloader() {
        if (window.__brainPreloader && typeof window.__brainPreloader.show === 'function') {
            window.__brainPreloader.show();
        }
    }

    function getSearchReturnUrl() {
        var path = location.pathname;
        var parts = path.split('/').filter(function (s) { return s.length; });
        var i;

        i = parts.lastIndexOf('edit');
        if (i >= 2 && parts[i - 1] && parts[i - 2] === 'post') {
            return '/' + parts.slice(0, i).join('/') + '/';
        }

        i = parts.indexOf('edit');
        if (i === 1 && parts[0] === 'profile' && parts[2]) {
            return '/profile/' + parts[2] + '/';
        }

        return path + location.search;
    }

    var GUEST_STORAGE_KEY = 'brainews_search_history';
    var GUEST_MAX_ITEMS = 10;
    var GUEST_TTL_MS = 24 * 60 * 60 * 1000;

    function isGuestItemExpired(item) {
        try {
            var ts = item && item.created_at ? new Date(item.created_at).getTime() : 0;
            return !ts || (Date.now() - ts > GUEST_TTL_MS);
        } catch (e) { return true; }
    }

    function getGuestHistory(maxItems) {
        try {
            var raw = localStorage.getItem(GUEST_STORAGE_KEY);
            if (!raw) return [];
            var arr = JSON.parse(raw);
            if (!Array.isArray(arr)) return [];
            var valid = arr.filter(function (it) { return !isGuestItemExpired(it); });
            if (valid.length < arr.length) {
                localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(valid));
            }
            var limit = (maxItems != null && maxItems > 0) ? maxItems : GUEST_MAX_ITEMS;
            return valid.slice(0, limit).map(function (it, i) {
                return {
                    id: 'local-' + i,
                    search_query: it.search_query,
                    search_filters: it.search_filters || {},
                    created_at: it.created_at,
                    results_count: it.results_count
                };
            });
        } catch (e) { return []; }
    }
    window.getGuestSearchHistory = function (max) { return getGuestHistory(max); };

    function saveGuestSearchHistory(query, filters) {
        if (!query || typeof query !== 'string' || (window.USER_AUTHENTICATED === true)) return;
        try {
            var q = query.trim();
            if (!q) return;
            var f = filters || { by_title: true, by_text: true, by_tags: true };
            var arr = [];
            try {
                var raw = localStorage.getItem(GUEST_STORAGE_KEY);
                if (raw) arr = JSON.parse(raw);
                if (!Array.isArray(arr)) arr = [];
            } catch (e) { arr = []; }
            arr = arr.filter(function (it) { return !isGuestItemExpired(it); });
            var now = new Date().toISOString();
            var dupIdx = arr.findIndex(function (it) {
                return (it.search_query || '').toLowerCase() === q.toLowerCase() &&
                    JSON.stringify(it.search_filters || {}) === JSON.stringify(f);
            });
            if (dupIdx >= 0) arr.splice(dupIdx, 1);
            arr.unshift({ search_query: q, search_filters: f, created_at: now });
            if (arr.length > GUEST_MAX_ITEMS) arr.length = GUEST_MAX_ITEMS;
            localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(arr));
        } catch (e) { }
    }
    window.saveGuestSearchHistory = saveGuestSearchHistory;

    function bumpGuestSearchToTop(query, filters) {
        if (!query || (window.USER_AUTHENTICATED === true)) return;
        try {
            var q = String(query).trim();
            if (!q) return;
            var f = filters || { by_title: true, by_text: true, by_tags: true };
            var arr = [];
            try {
                var raw = localStorage.getItem(GUEST_STORAGE_KEY);
                if (raw) arr = JSON.parse(raw);
                if (!Array.isArray(arr)) arr = [];
            } catch (e) { arr = []; }
            arr = arr.filter(function (it) { return !isGuestItemExpired(it); });
            var dupIdx = arr.findIndex(function (it) {
                return (it.search_query || '').toLowerCase() === q.toLowerCase() &&
                    JSON.stringify(it.search_filters || {}) === JSON.stringify(f);
            });
            if (dupIdx >= 0) {
                var it = arr.splice(dupIdx, 1)[0];
                arr.unshift(it);
                localStorage.setItem(GUEST_STORAGE_KEY, JSON.stringify(arr));
            }
        } catch (e) { }
    }
    window.bumpGuestSearchToTop = bumpGuestSearchToTop;

    function normalizeSearchQuery(raw) {
        if (!raw || typeof raw !== 'string') return { ok: false, reason: 'too_short' };
        var s = raw.trim();
        if (!s) return { ok: false, reason: 'too_short' };
        s = s.replace(/\s+/g, ' ');
        s = s.replace(/[^\p{L}\p{N}\s\-'",.!?]/gu, ' ').replace(/\s+/g, ' ').trim();
        s = s.replace(/\b(site|filetype|intitle|inurl):\s*[\S]+/gi, '').replace(/\s+/g, ' ').trim();
        s = s.replace(/\b(AND|OR|NOT)\b/gi, ' ').replace(/\s+/g, ' ').trim();
        if (s.length > SEARCH_MAX_CHARS) s = s.slice(0, SEARCH_MAX_CHARS).trim();
        var words = s.split(/\s+/).filter(Boolean);
        if (words.length > SEARCH_MAX_WORDS) words = words.slice(0, SEARCH_MAX_WORDS);
        s = words.join(' ');
        if (s.length < SEARCH_MIN_CHARS) return { ok: false, reason: 'too_short' };
        return { ok: true, query: s };
    }

    function bodyAttr(name) {
        return (document.body && document.body.getAttribute(name)) || '';
    }

    var isAuth = String(bodyAttr('data-user-authenticated')).trim() === '1';
    var listUrl = bodyAttr('data-search-history-url');
    var clickedPattern = bodyAttr('data-search-history-clicked-pattern');
    var deletePattern = bodyAttr('data-search-history-delete-pattern');
    var clearUrl = bodyAttr('data-search-history-clear-url');
    var suggestUrl = bodyAttr('data-search-suggest-url');

    var overlayRoot = document.getElementById('overlaySearchRoot');
    var overlayBackdrop = document.getElementById('overlaySearchBackdrop');
    var overlayCloseToolbar = document.getElementById('overlaySearchCloseToolbar');
    var overlayInput = document.getElementById('overlaySearchInput');
    var suggestionsSection = document.getElementById('overlaySearchSuggestionsSection');
    var suggestionsEl = document.getElementById('overlaySearchSuggestions');
    var historySection = document.getElementById('overlaySearchHistorySection');
    var historyEl = document.getElementById('overlaySearchHistory');

    if (!overlayRoot || !overlayInput || !historyEl || !suggestionsEl || !suggestionsSection) {
        return;
    }

    var overlaySearchBody = overlayRoot.querySelector('.overlay-search-body');
    if (!overlaySearchBody) {
        return;
    }

    var cachedHistory = [];
    var historyFetchSeq = 0;
    var suggestTimer = null;
    var suggestSeq = 0;
    var suggestAbort = null;
    var __searchOverlayTouchBlock = null;
    var __searchOverlayWheelBlock = null;

    /** Block scroll gestures on the page behind the overlay (iOS still scrolls fixed body sometimes). */
    function attachSearchOverlayScrollGuards() {
        if (__searchOverlayTouchBlock) return;
        __searchOverlayTouchBlock = function (e) {
            if (!__searchOverlayOpen || !overlayRoot) return;
            if (overlayRoot.contains(e.target)) return;
            if (e.cancelable) e.preventDefault();
        };
        __searchOverlayWheelBlock = function (e) {
            if (!__searchOverlayOpen || !overlayRoot) return;
            if (overlayRoot.contains(e.target)) return;
            if (e.cancelable) e.preventDefault();
        };
        document.addEventListener('touchmove', __searchOverlayTouchBlock, { passive: false });
        document.addEventListener('wheel', __searchOverlayWheelBlock, { passive: false });
    }

    function detachSearchOverlayScrollGuards() {
        if (__searchOverlayTouchBlock) {
            document.removeEventListener('touchmove', __searchOverlayTouchBlock);
            __searchOverlayTouchBlock = null;
        }
        if (__searchOverlayWheelBlock) {
            document.removeEventListener('wheel', __searchOverlayWheelBlock);
            __searchOverlayWheelBlock = null;
        }
    }

    var __overlayBodyScrollRO = null;
    var __overlayBodyScrollVv = null;

    function scheduleSyncOverlayBodyScrollability() {
        if (!__searchOverlayOpen) return;
        requestAnimationFrame(function () {
            requestAnimationFrame(syncOverlayBodyScrollability);
        });
    }

    function syncOverlayBodyScrollability() {
        /* Scroll is now always enabled via CSS (overflow-y: auto) — no class toggling needed. */
    }

    function attachOverlayBodyScrollWatch() {
        if (__overlayBodyScrollVv) return;
        var onResize = function () {
            scheduleSyncOverlayBodyScrollability();
        };
        if (typeof ResizeObserver !== 'undefined') {
            __overlayBodyScrollRO = new ResizeObserver(onResize);
            __overlayBodyScrollRO.observe(overlaySearchBody);
            var content = overlaySearchBody.closest('.overlay-search-content');
            if (content) __overlayBodyScrollRO.observe(content);
        }
        __overlayBodyScrollVv = onResize;
        var vv = window.visualViewport;
        if (vv) {
            vv.addEventListener('resize', __overlayBodyScrollVv);
            vv.addEventListener('scroll', __overlayBodyScrollVv);
        }
        window.addEventListener('resize', __overlayBodyScrollVv);
        window.addEventListener('orientationchange', __overlayBodyScrollVv);
    }

    function detachOverlayBodyScrollWatch() {
        if (__overlayBodyScrollRO) {
            __overlayBodyScrollRO.disconnect();
            __overlayBodyScrollRO = null;
        }
        if (__overlayBodyScrollVv) {
            var vv = window.visualViewport;
            if (vv) {
                vv.removeEventListener('resize', __overlayBodyScrollVv);
                vv.removeEventListener('scroll', __overlayBodyScrollVv);
            }
            window.removeEventListener('resize', __overlayBodyScrollVv);
            window.removeEventListener('orientationchange', __overlayBodyScrollVv);
            __overlayBodyScrollVv = null;
        }
        overlaySearchBody.scrollTop = 0;
    }

    function getCSRF() {
        var m = document.cookie.match(/(^|;\s*)csrftoken=([^;]+)/);
        return m ? m[2] : '';
    }

    function escapeHtml(s) {
        if (!s) return '';
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function buildSearchUrl(item) {
        var params = new URLSearchParams();
        params.set('q', item.search_query);
        var f = item.search_filters || {};
        if (f.by_title) params.set('by_title', '1');
        if (f.by_text) params.set('by_text', '1');
        if (f.by_tags) params.set('by_tags', '1');
        if (!f.by_title && !f.by_text && !f.by_tags) {
            params.set('by_title', '1'); params.set('by_text', '1'); params.set('by_tags', '1');
        }
        return (window.SEARCH_URL || '/search/') + '?' + params.toString();
    }

    function filterHistoryItems(items, text) {
        if (!text || !text.trim()) return items;
        var lower = text.trim().toLowerCase();
        return items.filter(function (it) {
            return (it.search_query || '').toLowerCase().indexOf(lower) >= 0;
        });
    }

    function formatMeta(item) {
        /* Hidden for now: result count + search date in recent list (restore when uncommenting metaHtml below)
        var parts = [];
        if (item.results_count != null) parts.push(item.results_count + ' found');
        if (item.created_at) {
            var d = new Date(item.created_at);
            var now = new Date();
            var diff = Math.floor((now - d) / 86400000);
            if (diff === 0) parts.push('Today');
            else if (diff === 1) parts.push('Yesterday');
            else if (diff <= 5) parts.push(diff + ' days ago');
            else parts.push(d.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }));
        }
        return parts.join(' · ');
        */
        return '';
    }

    function renderOverlayHistory() {
        try {
            var val = (overlayInput.value || '').trim();
            var items = val ? filterHistoryItems(cachedHistory, val) : cachedHistory.slice(0, OVERLAY_HISTORY_MAX);
            historyEl.innerHTML = '';
            historySection.hidden = false;

            if (!items.length) {
                historyEl.innerHTML = '<div class="overlay-search-empty">' +
                    (val ? 'No matching searches in your history.' : 'No recent searches yet.') + '</div>';
                return;
            }

            var headerRow = document.createElement('div');
            headerRow.className = 'search-history-header-row';
            headerRow.innerHTML = '<span class="search-history-header">Recent</span>';
            if (isAuth && clearUrl) {
                var clearBtn = document.createElement('button');
                clearBtn.type = 'button';
                clearBtn.className = 'search-history-clear-btn';
                clearBtn.textContent = 'Clear history';
                clearBtn.setAttribute('aria-label', 'Clear search history');
                headerRow.appendChild(clearBtn);
            }
            historyEl.appendChild(headerRow);

            items.forEach(function (item, idx) {
                var row = document.createElement('div');
                row.className = 'search-history-item overlay-search-history-row';
                row.dataset.id = item.id;
                row.dataset.url = buildSearchUrl(item);
                row.dataset.searchQuery = item.search_query || '';
                row.dataset.searchFilters = JSON.stringify(item.search_filters || {});
                row.dataset.isGuest = isAuth ? '0' : '1';
                /* var metaHtml = isAuth ? '<span class="search-history-item-meta">' + escapeHtml(formatMeta(item)) + '</span>' : ''; */
                var metaHtml = '';
                var removeHtml = isAuth && deletePattern
                    ? '<button type="button" class="search-history-item-remove" data-id="' + escapeHtml(String(item.id)) + '" aria-label="Remove from history">×</button>'
                    : '';
                row.innerHTML = '<span class="search-history-item-icon"><i class="fa fa-clock-o" aria-hidden="true"></i></span>' +
                    '<span class="search-history-item-text">' + escapeHtml(item.search_query || '') + '</span>' +
                    metaHtml + removeHtml;
                historyEl.appendChild(row);
            });
        } finally {
            scheduleSyncOverlayBodyScrollability();
        }
    }

    function fetchHistory(callback) {
        var seq = ++historyFetchSeq;
        if (isAuth && listUrl) {
            fetch(listUrl, { credentials: 'same-origin' })
                .then(function (r) {
                    return r.json().then(function (data) {
                        return { ok: r.ok, data: data || {} };
                    }).catch(function () {
                        return { ok: r.ok, data: {} };
                    });
                })
                .then(function (res) {
                    if (seq !== historyFetchSeq) return;
                    if (res.ok && res.data && Array.isArray(res.data.items)) {
                        cachedHistory = res.data.items;
                    } else {
                        cachedHistory = [];
                    }
                    renderOverlayHistory();
                    if (callback) callback();
                })
                .catch(function () {
                    if (seq !== historyFetchSeq) return;
                    cachedHistory = [];
                    renderOverlayHistory();
                    if (callback) callback();
                });
        } else {
            cachedHistory = getGuestHistory(OVERLAY_HISTORY_MAX);
            renderOverlayHistory();
            if (callback) callback();
        }
    }

    function appendFromHistory(url) {
        var sep = url.indexOf('?') >= 0 ? '&' : '?';
        return url + sep + 'from_history=1';
    }

    function runSuggest() {
        var raw = (overlayInput.value || '').trim();
        var norm = normalizeSearchQuery(raw);
        if (!norm.ok || !suggestUrl) {
            suggestionsSection.hidden = true;
            suggestionsEl.innerHTML = '';
            scheduleSyncOverlayBodyScrollability();
            return;
        }

        if (suggestAbort) suggestAbort.abort();
        suggestAbort = new AbortController();
        var seq = ++suggestSeq;
        var url = suggestUrl + (suggestUrl.indexOf('?') >= 0 ? '&' : '?') + 'q=' + encodeURIComponent(norm.query);

        fetch(url, { credentials: 'same-origin', signal: suggestAbort.signal })
            .then(function (r) {
                return r.json().then(function (data) {
                    return { ok: r.ok, data: data || {} };
                }).catch(function () {
                    return { ok: r.ok, data: {} };
                });
            })
            .then(function (res) {
                if (seq !== suggestSeq) return;
                suggestionsEl.innerHTML = '';
                var items = (res.data && res.data.items) || [];
                if (!Array.isArray(items) || !items.length) {
                    suggestionsSection.hidden = true;
                    return;
                }
                suggestionsSection.hidden = false;
                items.forEach(function (it) {
                    var a = document.createElement('a');
                    a.href = it.url || '#';
                    a.className = 'overlay-search-suggestion-item';
                    a.setAttribute('role', 'option');
                    a.textContent = it.title || '';
                    suggestionsEl.appendChild(a);
                });
            })
            .catch(function () {
                if (seq !== suggestSeq) return;
                suggestionsSection.hidden = true;
                suggestionsEl.innerHTML = '';
            })
            .finally(function () {
                if (seq === suggestSeq) {
                    scheduleSyncOverlayBodyScrollability();
                }
            });
    }

    function onOverlayInput() {
        clearTimeout(suggestTimer);
        renderOverlayHistory();
        var raw = (overlayInput.value || '').trim();
        var norm = normalizeSearchQuery(raw);
        if (!norm.ok) {
            if (suggestAbort) suggestAbort.abort();
            suggestionsSection.hidden = true;
            suggestionsEl.innerHTML = '';
            scheduleSyncOverlayBodyScrollability();
            return;
        }
        suggestTimer = setTimeout(runSuggest, SUGGEST_DEBOUNCE_MS);
    }

    function submitOverlaySearch() {
        var raw = (overlayInput.value || '').trim();
        if (!raw) return;
        var norm = normalizeSearchQuery(raw);
        if (!norm.ok) return;
        var q = norm.query;
        var params = new URLSearchParams();
        params.set('q', q);
        params.set('by_title', '1');
        params.set('by_text', '1');
        params.set('by_tags', '1');
        try {
            sessionStorage.removeItem('brainews_filter_active');
            sessionStorage.setItem('search_return_url', getSearchReturnUrl());
        } catch (err) { }
        if (typeof window.saveGuestSearchHistory === 'function') {
            window.saveGuestSearchHistory(q, { by_title: true, by_text: true, by_tags: true });
        }
        closeOverlay(function () {
            showBrainPreloader();
            window.location.href = '/search/?' + params.toString();
        }, { skipAnimation: true });
    }

    function openOverlay() {
        if (__searchOverlayOpen) return;
        __searchOverlayOpen = true;

        overlayRoot.classList.remove('hidden');
        overlayRoot.removeAttribute('inert');
        overlayRoot.setAttribute('aria-hidden', 'false');

        overlayRoot.style.removeProperty('top');
        overlayRoot.style.removeProperty('left');
        overlayRoot.style.removeProperty('width');
        overlayRoot.style.removeProperty('height');
        overlayRoot.style.removeProperty('max-height');

        if (typeof lockScroll === 'function') lockScroll();
        document.documentElement.classList.add('search-overlay-open');
        attachSearchOverlayScrollGuards();
        attachOverlayBodyScrollWatch();

        fetchHistory(function () {
            onOverlayInput();
        });

        scheduleSyncOverlayBodyScrollability();

        try {
            overlayInput.focus({ preventScroll: true });
        } catch (err) {
            try { overlayInput.focus(); } catch (err2) { }
        }
    }

    function closeOverlay(onAfterAnimation, options) {
        if (!__searchOverlayOpen) return;

        __searchOverlayOpen = false;
        clearTimeout(suggestTimer);
        if (suggestAbort) suggestAbort.abort();

        try {
            var ae = document.activeElement;
            if (ae && overlayRoot.contains(ae)) ae.blur();
        } catch (e) { /* ignore */ }

        overlayRoot.setAttribute('inert', '');
        overlayInput.value = '';
        var clr = document.getElementById('overlaySearchClear');
        if (clr) clr.classList.add('hidden');

        requestAnimationFrame(function () {
            overlayRoot.classList.add('hidden');
            overlayRoot.setAttribute('aria-hidden', 'true');
            overlayRoot.removeAttribute('inert');
            document.documentElement.classList.remove('search-overlay-open');
            detachSearchOverlayScrollGuards();
            detachOverlayBodyScrollWatch();
            suggestionsSection.hidden = true;
            suggestionsEl.innerHTML = '';
            historyEl.innerHTML = '';
            if (typeof unlockScroll === 'function') unlockScroll();
            if (typeof onAfterAnimation === 'function') onAfterAnimation();
        });
    }

    window.openSearchOverlay = openOverlay;
    document.addEventListener('openSearchOverlay', openOverlay);

    if (overlayCloseToolbar) overlayCloseToolbar.addEventListener('click', function () { closeOverlay(); });
    if (overlayBackdrop) {
        overlayBackdrop.addEventListener('click', function () { closeOverlay(); });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && __searchOverlayOpen) {
            e.preventDefault();
            closeOverlay();
        }
    });

    overlayInput.addEventListener('input', onOverlayInput);
    overlayInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            var active = document.activeElement;
            if (active && active.classList && active.classList.contains('overlay-search-suggestion-item')) {
                return;
            }
            submitOverlaySearch();
        }
    });

    suggestionsEl.addEventListener('click', function (e) {
        var a = e.target.closest('.overlay-search-suggestion-item');
        if (!a || !a.href) return;
        e.preventDefault();
        var href = a.href;
        closeOverlay(function () {
            showBrainPreloader();
            window.location.href = href;
        }, { skipAnimation: true });
    });

    historyEl.addEventListener('click', function (e) {
        var removeBtn = e.target.closest('.search-history-item-remove');
        if (removeBtn && isAuth && deletePattern) {
            e.preventDefault();
            e.stopPropagation();
            var row = removeBtn.closest('.search-history-item');
            var id = removeBtn.getAttribute('data-id') || (row && row.dataset.id);
            if (!id) return;
            var deleteU = deletePattern.replace('999999', id);
            fetch(deleteU, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCSRF(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then(function () {
                if (row) row.remove();
                cachedHistory = cachedHistory.filter(function (it) { return String(it.id) !== String(id); });
                if (!historyEl.querySelector('.search-history-item')) {
                    renderOverlayHistory();
                } else {
                    scheduleSyncOverlayBodyScrollability();
                }
            }).catch(function () { });
            return;
        }
        var clearBtn = e.target.closest('.search-history-clear-btn');
        if (clearBtn && isAuth && clearUrl) {
            e.preventDefault();
            e.stopPropagation();
            fetch(clearUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCSRF(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then(function () {
                cachedHistory = [];
                renderOverlayHistory();
            }).catch(function () { });
            return;
        }
        var historyRow = e.target.closest('.search-history-item');
        if (!historyRow) return;
        e.preventDefault();
        var historyId = historyRow.dataset && historyRow.dataset.id;
        var historyBaseUrl = historyRow.dataset && historyRow.dataset.url;
        if (!historyBaseUrl) return;
        if (!isAuth) {
            var q = historyRow.dataset && historyRow.dataset.searchQuery;
            var fStr = historyRow.dataset && historyRow.dataset.searchFilters;
            if (q && typeof window.bumpGuestSearchToTop === 'function') {
                try {
                    var f = {};
                    if (fStr) try { f = JSON.parse(fStr); } catch (err2) { }
                    window.bumpGuestSearchToTop(q, f);
                } catch (err) { }
            }
        }
        var url = appendFromHistory(historyBaseUrl);
        try {
            sessionStorage.setItem('search_clear_next', '1');
            sessionStorage.removeItem('brainews_filter_active');
            sessionStorage.setItem('search_return_url', getSearchReturnUrl());
        } catch (err) { }
        if (isAuth && clickedPattern && historyId && String(historyId).indexOf('local-') !== 0) {
            var clickedU = clickedPattern.replace('999999', historyId);
            fetch(clickedU, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': getCSRF(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            }).catch(function () { });
        }
        closeOverlay(function () {
            showBrainPreloader();
            window.location.href = url;
        }, { skipAnimation: true });
    });

    function attachClearButtons(container) {
        var btns = container ? $$('.field-clear', container) : $$('.field-clear');
        btns.forEach(function (btn) {
            if (btn.__clearBound) return;
            btn.__clearBound = true;
            var dataTarget = btn.getAttribute('data-target');
            var target = dataTarget ? document.querySelector(dataTarget) : null;
            if (!target && container) {
                var parent = btn.closest('.header-search-row, form, .input-group, .form-floating');
                if (parent) target = parent.querySelector('input, textarea');
            }
            if (!target) return;

            function updateVisibility() {
                var v = (target.value || '').trim();
                if (v.length) btn.classList.remove('hidden'); else btn.classList.add('hidden');
            }
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                target.value = '';
                target.focus();
                try { target.dispatchEvent(new Event('input', { bubbles: true })); } catch (err) { }
                updateVisibility();
            });
            target.addEventListener('input', updateVisibility);
            updateVisibility();
        });
    }
    attachClearButtons(document);

    document.addEventListener('focus', function (ev) {
        if (!overlayRoot || overlayRoot.classList.contains('hidden')) return;
        if (!overlayRoot.contains(ev.target)) {
            var focusable = overlayRoot.querySelector('input,button,select,textarea,a[href]');
            if (focusable) focusable.focus();
        }
    }, true);

    document.documentElement.addEventListener('turbo:before-visit', function () {
        if (__searchOverlayOpen) closeOverlay();
    });
});
