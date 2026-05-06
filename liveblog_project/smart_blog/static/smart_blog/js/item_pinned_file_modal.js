/**
 * Pinned PDF modal — PDF.js-powered viewer that lives in the parent document
 * so Escape always closes the modal.
 *
 * Goals of this rewrite:
 *  - Stable page label tracking (no flicker on scroll). We pick the page whose
 *    top is closest to the viewport top inside a single rAF tick.
 *  - Lazy rendering: pages are placeholders until they enter (or are near) the
 *    viewport. Off-screen pages release their canvas to keep memory bounded.
 *  - Zoom updates re-layout placeholders via cached intrinsic page sizes so we
 *    don't have to fetch pages again, and only re-render visible ones.
 *  - Mobile close button works via Bootstrap dismiss; we also wire it
 *    explicitly for safety.
 */
(function () {
    'use strict';

    var PDF_WORKER_SRC =
        'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js';

    var MIN_SCALE = 0.5;
    var MAX_SCALE = 3;
    var ZOOM_FACTOR = 1.15;
    var PRELOAD_PX = 600; // distance from viewport edge to start rendering pages

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    function debounce(fn, ms) {
        var t;
        return function () {
            clearTimeout(t);
            var self = this;
            var args = arguments;
            t = setTimeout(function () {
                fn.apply(self, args);
            }, ms);
        };
    }

    function bindModalEscape() {
        var modal = document.getElementById('itemPinnedFileModal');
        if (!modal || modal.dataset.itemPinnedEscapeBound === '1') {
            return;
        }
        modal.dataset.itemPinnedEscapeBound = '1';
        document.addEventListener(
            'keydown',
            function (e) {
                if (e.key !== 'Escape') {
                    return;
                }
                if (!modal.classList.contains('show')) {
                    return;
                }
                if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
                    return;
                }
                var inst = bootstrap.Modal.getInstance(modal);
                if (inst) {
                    inst.hide();
                }
            },
            true
        );
    }

    function bindCloseButton() {
        var modal = document.getElementById('itemPinnedFileModal');
        var btn = document.querySelector('[data-pdf-close]');
        if (!modal || !btn || btn.dataset.itemPinnedCloseBound === '1') {
            return;
        }
        btn.dataset.itemPinnedCloseBound = '1';
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                var inst = bootstrap.Modal.getOrCreateInstance(modal);
                if (inst) {
                    inst.hide();
                }
            }
        });
    }

    function createPdfController(host, pdf) {
        var scrollEl = host.querySelector('[data-pdf-scroll]');
        var inner = host.querySelector('[data-pdf-pages]');
        var pageLabelEl = host.querySelector('[data-pdf-page-label]');
        var zoomEl = host.querySelector('[data-pdf-zoom-pct]');
        var prevBtn = host.querySelector('[data-pdf-prev]');
        var nextBtn = host.querySelector('[data-pdf-next]');
        var zoomInBtn = host.querySelector('[data-pdf-zoom-in]');
        var zoomOutBtn = host.querySelector('[data-pdf-zoom-out]');

        // pageEntries[i] = { wrap, baseW, baseH, cssW, cssH, rendered, rendering, page, lastRenderScale }
        var pageEntries = [];
        var userScale = 1;
        var currentIndex = 0;
        var totalPages = pdf.numPages;
        var labelDirty = false;
        var pendingFrame = 0;

        function updateLabel(force) {
            if (!pageLabelEl) {
                return;
            }
            if (!force && !labelDirty) {
                return;
            }
            labelDirty = false;
            pageLabelEl.textContent = (currentIndex + 1) + ' / ' + totalPages;
        }

        function setCurrentIndex(i) {
            var next = clamp(i, 0, pageEntries.length - 1);
            if (next === currentIndex) {
                return;
            }
            currentIndex = next;
            labelDirty = true;
        }

        function getAvailableWidth() {
            var pad = 16; // matches CSS .item-pinned-pdfjs__pages-inner padding
            return Math.max(220, scrollEl.clientWidth - pad * 2);
        }

        function layoutPages() {
            var available = getAvailableWidth();
            for (var i = 0; i < pageEntries.length; i++) {
                var e = pageEntries[i];
                var fit = available / e.baseW;
                var cssScale = fit * userScale;
                e.cssW = Math.floor(e.baseW * cssScale);
                e.cssH = Math.floor(e.baseH * cssScale);
                e.wrap.style.width = e.cssW + 'px';
                e.wrap.style.height = e.cssH + 'px';
                // any previously rendered canvas is now stale — drop it
                if (e.rendered) {
                    e.rendered = false;
                    e.lastRenderScale = 0;
                    while (e.wrap.firstChild) {
                        e.wrap.removeChild(e.wrap.firstChild);
                    }
                }
            }
        }

        function renderPageEntry(entry) {
            if (entry.rendered || entry.rendering) {
                return;
            }
            entry.rendering = true;

            var dpr = clamp(window.devicePixelRatio || 1, 1, 3);
            var available = getAvailableWidth();
            var fit = available / entry.baseW;
            var cssScale = fit * userScale;
            var scale = cssScale * dpr;

            (entry.page
                ? Promise.resolve(entry.page)
                : pdf.getPage(entry.index + 1).then(function (p) {
                    entry.page = p;
                    return p;
                })
            ).then(function (page) {
                var viewport = page.getViewport({ scale: scale });
                var canvas = document.createElement('canvas');
                canvas.width = Math.floor(viewport.width);
                canvas.height = Math.floor(viewport.height);
                canvas.style.width = entry.cssW + 'px';
                canvas.style.height = entry.cssH + 'px';
                canvas.style.display = 'block';
                canvas.style.background = '#fff';
                var ctx = canvas.getContext('2d', { alpha: false });
                return page
                    .render({ canvasContext: ctx, viewport: viewport })
                    .promise.then(function () {
                        return canvas;
                    });
            }).then(function (canvas) {
                while (entry.wrap.firstChild) {
                    entry.wrap.removeChild(entry.wrap.firstChild);
                }
                entry.wrap.appendChild(canvas);
                entry.rendered = true;
                entry.rendering = false;
                entry.lastRenderScale = userScale;
            }).catch(function (err) {
                entry.rendering = false;
                console.error('PDF page render error', err);
            });
        }

        function releasePageEntry(entry) {
            if (!entry.rendered) {
                return;
            }
            while (entry.wrap.firstChild) {
                entry.wrap.removeChild(entry.wrap.firstChild);
            }
            entry.rendered = false;
            entry.lastRenderScale = 0;
        }

        function updateVisible() {
            if (!pageEntries.length) {
                return;
            }
            var scrollTop = scrollEl.scrollTop;
            var viewportH = scrollEl.clientHeight;
            var viewTop = scrollTop - PRELOAD_PX;
            var viewBottom = scrollTop + viewportH + PRELOAD_PX;

            var bestIdx = 0;
            var bestDist = Infinity;
            // pages-inner has top padding — we account for offsetTop from inner container
            for (var i = 0; i < pageEntries.length; i++) {
                var e = pageEntries[i];
                var top = e.wrap.offsetTop;
                var bottom = top + e.wrap.offsetHeight;

                var visible = bottom >= viewTop && top <= viewBottom;
                if (visible) {
                    renderPageEntry(e);
                } else {
                    releasePageEntry(e);
                }

                // pick page whose top is closest to viewport top (with slight bias)
                var dist = Math.abs(top - scrollTop - 8);
                if (dist < bestDist) {
                    bestDist = dist;
                    bestIdx = i;
                }
            }

            setCurrentIndex(bestIdx);
            updateLabel();
        }

        function scheduleUpdateVisible() {
            if (pendingFrame) {
                return;
            }
            pendingFrame = window.requestAnimationFrame(function () {
                pendingFrame = 0;
                updateVisible();
            });
        }

        function scrollToPage(index) {
            var clamped = clamp(index, 0, pageEntries.length - 1);
            var entry = pageEntries[clamped];
            if (!entry) {
                return;
            }
            // Position page top near container top (with small inset).
            scrollEl.scrollTo({
                top: Math.max(0, entry.wrap.offsetTop - 8),
                behavior: 'smooth',
            });
            // Predict label change immediately for snappier UX.
            currentIndex = clamped;
            labelDirty = true;
            updateLabel();
        }

        function setZoom(newScale) {
            var prev = userScale;
            userScale = clamp(newScale, MIN_SCALE, MAX_SCALE);
            if (userScale === prev) {
                return;
            }
            // Preserve scroll anchor: which page is currently top, and offset within it.
            var anchorIdx = currentIndex;
            var anchorEntry = pageEntries[anchorIdx];
            var anchorOffset = 0;
            if (anchorEntry) {
                anchorOffset = scrollEl.scrollTop - anchorEntry.wrap.offsetTop;
            }
            layoutPages();
            // After layout, re-measure offsets and re-position the scroll.
            if (anchorEntry) {
                scrollEl.scrollTop = Math.max(0, anchorEntry.wrap.offsetTop + anchorOffset);
            }
            if (zoomEl) {
                zoomEl.textContent = Math.round(userScale * 100) + '%';
            }
            scheduleUpdateVisible();
        }

        function onPrev() {
            scrollToPage(currentIndex - 1);
        }
        function onNext() {
            scrollToPage(currentIndex + 1);
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', onPrev);
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', onNext);
        }
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', function () {
                setZoom(userScale * ZOOM_FACTOR);
            });
        }
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', function () {
                setZoom(userScale / ZOOM_FACTOR);
            });
        }

        // Keyboard navigation when the scroll container has focus or when
        // the user simply has the modal open.
        function onKey(e) {
            if (!host.isConnected) {
                return;
            }
            var target = e.target;
            // ignore typing inside inputs / contenteditable
            if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
                return;
            }
            if (e.key === 'PageDown' || e.key === 'ArrowRight') {
                e.preventDefault();
                onNext();
            } else if (e.key === 'PageUp' || e.key === 'ArrowLeft') {
                e.preventDefault();
                onPrev();
            } else if (e.key === 'Home') {
                e.preventDefault();
                scrollToPage(0);
            } else if (e.key === 'End') {
                e.preventDefault();
                scrollToPage(pageEntries.length - 1);
            }
        }

        var modal = document.getElementById('itemPinnedFileModal');
        if (modal) {
            modal.addEventListener('keydown', onKey);
        }

        scrollEl.addEventListener('scroll', scheduleUpdateVisible, { passive: true });

        var onResize = debounce(function () {
            layoutPages();
            scheduleUpdateVisible();
        }, 150);
        window.addEventListener('resize', onResize);

        async function build() {
            inner.innerHTML = '';
            pageEntries.length = 0;

            // Create placeholders for all pages — fetch only base viewport once.
            for (var p = 1; p <= totalPages; p++) {
                var page = await pdf.getPage(p);
                var baseVp = page.getViewport({ scale: 1 });
                var wrap = document.createElement('div');
                wrap.className = 'item-pinned-pdfjs__page';
                inner.appendChild(wrap);
                pageEntries.push({
                    index: p - 1,
                    wrap: wrap,
                    baseW: baseVp.width,
                    baseH: baseVp.height,
                    cssW: 0,
                    cssH: 0,
                    rendered: false,
                    rendering: false,
                    page: page,
                    lastRenderScale: 0,
                });
            }

            layoutPages();
            currentIndex = 0;
            labelDirty = true;
            if (zoomEl) {
                zoomEl.textContent = Math.round(userScale * 100) + '%';
            }
            updateLabel(true);
            scheduleUpdateVisible();
        }

        return { build: build };
    }

    async function bootPdf(host) {
        var url = host.getAttribute('data-pdf-url');
        if (!url) {
            return;
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = PDF_WORKER_SRC;
        var task = pdfjsLib.getDocument({ url: url, withCredentials: true });
        var pdf = await task.promise;
        var controller = createPdfController(host, pdf);
        await controller.build();
    }

    function showError(host, msg) {
        var inner = host.querySelector('[data-pdf-pages]');
        if (inner) {
            inner.innerHTML =
                '<p class="text-danger p-3 mb-0 small item-pinned-pdfjs__err">' + msg + '</p>';
        }
    }

    bindModalEscape();
    bindCloseButton();

    var modal = document.getElementById('itemPinnedFileModal');
    var host = document.querySelector('.item-pinned-pdfjs');
    if (modal && host) {
        var started = false;
        modal.addEventListener('shown.bs.modal', function () {
            if (started) {
                return;
            }
            started = true;
            if (typeof pdfjsLib === 'undefined') {
                showError(host, 'PDF viewer failed to load.');
                return;
            }
            bootPdf(host).catch(function (err) {
                console.error(err);
                showError(host, 'PDF could not be displayed.');
            });
        });
    }
})();
