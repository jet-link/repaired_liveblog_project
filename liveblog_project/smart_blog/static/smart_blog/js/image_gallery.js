// Post media: editorial grid + shared fullscreen viewer with swipe navigation.
(function () {
    'use strict';
    function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
    function qsa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

    document.addEventListener('DOMContentLoaded', function () {
        qsa('.js-gallery').forEach(initGallery);
    });

    function parsePostMediaSlides(galleryRoot) {
        const sid = galleryRoot.dataset.jsonScriptId;
        if (!sid) return null;
        const el = document.getElementById(sid);
        if (!el || el.type !== 'application/json') return null;
        try {
            const raw = JSON.parse(el.textContent || '[]');
            return Array.isArray(raw) ? raw : null;
        } catch (e) {
            return null;
        }
    }

    function initGallery(galleryRoot) {
        const slidesJson = parsePostMediaSlides(galleryRoot);
        if (slidesJson && slidesJson.length) {
            galleryRoot._pmSlides = slidesJson;
        }
        const imgs = qsa('.gallery-img', galleryRoot);
        ensureOverlay();

        setupThumbLazyObserver(imgs);

        imgs.forEach((img, i) => {
            if (!img.dataset.index) img.dataset.index = String(i);
            img.addEventListener('click', function (e) {
                e.preventDefault();
                const idx = Number(img.dataset.index || 0);
                openOverlayAt(idx, galleryRoot);
            });
            img.style.cursor = 'pointer';
            img.fetchPriority = i === 0 ? 'high' : 'low';
        });

    }

    function setupThumbLazyObserver(imgNodes) {
        if (!('IntersectionObserver' in window)) return;
        const io = new IntersectionObserver((entries, obs) => {
            entries.forEach(ent => {
                if (ent.isIntersecting) {
                    const img = ent.target;
                    const src = img.dataset.src || img.src;
                    if (src && img.src !== src) {
                        img.src = src;
                    }
                    obs.unobserve(img);
                }
            });
        }, { rootMargin: '200px 0px', threshold: 0.01 });

        imgNodes.forEach(img => {
            if (img.src && img.complete && img.naturalWidth) return;
            io.observe(img);
        });
    }

    function ensureOverlay() {
        if (qs('.gallery-overlay')) return;

        const overlay = document.createElement('div');
        overlay.className = 'gallery-overlay';
        overlay.innerHTML = `
      <button type="button" class="gallery-close-btn" aria-label="Close">
        <span class="gallery-close-btn__line"></span>
        <span class="gallery-close-btn__line"></span>
      </button>
      <div class="gallery-overlay-inner" role="dialog" aria-modal="true" aria-label="Image viewer">
        <img src="" alt="" class="gallery-overlay-img gallery-overlay-img--contain" loading="lazy" decoding="async" />
        <p class="gcaption"></p>
      </div>
      <span class="gallery-overlay-title" aria-hidden="true">Photos</span>
      <span class="gcount" aria-live="polite"></span>
    `;
        document.body.appendChild(overlay);

        const imgEl = qs('.gallery-overlay-img', overlay);
        const captionEl = qs('.gcaption', overlay);
        const countEl = qs('.gcount', overlay);
        const inner = qs('.gallery-overlay-inner', overlay);
        const closeBtn = qs('.gallery-close-btn', overlay);

        closeBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            hideOverlay();
        });

        let curIndex = 0;
        /** @type {{src:string, alt:string, caption:string}[]} */
        let currentSlides = [];

        function preloadAdjacent() {
            const n = currentSlides.length;
            if (!n) return;
            const prevIdx = (curIndex - 1 + n) % n;
            const nextIdx = (curIndex + 1) % n;
            const prevSrc = currentSlides[prevIdx] && currentSlides[prevIdx].src;
            const nextSrc = currentSlides[nextIdx] && currentSlides[nextIdx].src;
            if (prevSrc) { var i = new Image(); i.src = prevSrc; }
            if (nextSrc && nextIdx !== prevIdx) { var j = new Image(); j.src = nextSrc; }
        }

        function showCurrent(direction) {
            const s = currentSlides[curIndex];
            if (!s || !s.src) return;

            if (direction) {
                var cls = direction === 'left' ? 'gallery-slide-out-left' : 'gallery-slide-out-right';
                imgEl.classList.add(cls);
                setTimeout(function () {
                    imgEl.classList.remove(cls);
                    applySlide(s);
                    var inCls = direction === 'left' ? 'gallery-slide-in-right' : 'gallery-slide-in-left';
                    imgEl.classList.add(inCls);
                    setTimeout(function () { imgEl.classList.remove(inCls); }, 280);
                }, 180);
            } else {
                applySlide(s);
            }
        }

        function applySlide(s) {
            imgEl.classList.add('gallery-overlay-loading');
            imgEl.onload = function () {
                imgEl.classList.remove('gallery-overlay-loading');
            };
            imgEl.onerror = function () {
                imgEl.classList.remove('gallery-overlay-loading');
            };
            imgEl.alt = s.alt || '';
            captionEl.textContent = s.caption || '';
            countEl.textContent = (curIndex + 1) + ' / ' + currentSlides.length;
            requestAnimationFrame(function () {
                imgEl.src = s.src;
                if (imgEl.complete && imgEl.naturalWidth) {
                    imgEl.classList.remove('gallery-overlay-loading');
                }
                preloadAdjacent();
            });
        }

        function nav(dir) {
            if (!currentSlides.length) return;
            curIndex = (curIndex + dir + currentSlides.length) % currentSlides.length;
            showCurrent(dir < 0 ? 'right' : 'left');
        }

        function hideOverlay() {
            overlay.classList.remove('is-visible');
            unlockScroll();
            imgEl.src = '';
            imgEl.alt = '';
            captionEl.textContent = '';
            countEl.textContent = '';
            currentSlides = [];
        }

        document.addEventListener('keydown', function (e) {
            if (!overlay.classList.contains('is-visible')) return;
            if (e.key === 'Escape') {
                e.preventDefault();
                hideOverlay();
                return;
            }
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                nav(-1);
                return;
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                nav(1);
                return;
            }
        });

        // Swipe handling with drag animation
        var touchStartX = 0;
        var touchStartY = 0;
        var touchCurrentX = 0;
        var isDragging = false;
        var isVerticalScroll = false;

        inner.addEventListener('touchstart', function (e) {
            if (!e.changedTouches || !e.changedTouches.length) return;
            touchStartX = e.changedTouches[0].clientX;
            touchStartY = e.changedTouches[0].clientY;
            touchCurrentX = touchStartX;
            isDragging = true;
            isVerticalScroll = false;
            imgEl.style.transition = 'none';
        }, { passive: true });

        inner.addEventListener('touchmove', function (e) {
            if (!isDragging || !e.changedTouches || !e.changedTouches.length) return;
            var dx = e.changedTouches[0].clientX - touchStartX;
            var dy = e.changedTouches[0].clientY - touchStartY;

            if (!isVerticalScroll && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) {
                isVerticalScroll = true;
            }
            if (isVerticalScroll) return;

            touchCurrentX = e.changedTouches[0].clientX;
            imgEl.style.transform = 'translateX(' + dx + 'px)';
            imgEl.style.opacity = Math.max(0.5, 1 - Math.abs(dx) / 600);
        }, { passive: true });

        inner.addEventListener('touchend', function (e) {
            if (!isDragging) return;
            isDragging = false;
            if (isVerticalScroll) {
                imgEl.style.transform = '';
                imgEl.style.opacity = '';
                imgEl.style.transition = '';
                return;
            }
            var dx = (e.changedTouches && e.changedTouches.length) ? e.changedTouches[0].clientX - touchStartX : touchCurrentX - touchStartX;

            imgEl.style.transition = 'transform 0.28s cubic-bezier(.4,0,.2,1), opacity 0.28s ease';

            if (Math.abs(dx) > 50 && currentSlides.length > 1) {
                var direction = dx < 0 ? 1 : -1;
                var exitX = dx < 0 ? -window.innerWidth : window.innerWidth;
                imgEl.style.transform = 'translateX(' + exitX + 'px)';
                imgEl.style.opacity = '0';
                setTimeout(function () {
                    imgEl.style.transition = 'none';
                    curIndex = (curIndex + direction + currentSlides.length) % currentSlides.length;
                    imgEl.style.transform = 'translateX(' + (-exitX) + 'px)';
                    imgEl.style.opacity = '0';
                    requestAnimationFrame(function () {
                        applySlide(currentSlides[curIndex]);
                        requestAnimationFrame(function () {
                            imgEl.style.transition = 'transform 0.28s cubic-bezier(.4,0,.2,1), opacity 0.28s ease';
                            imgEl.style.transform = 'translateX(0)';
                            imgEl.style.opacity = '1';
                            setTimeout(function () {
                                imgEl.style.transition = '';
                                imgEl.style.transform = '';
                                imgEl.style.opacity = '';
                            }, 300);
                        });
                    });
                }, 200);
            } else {
                imgEl.style.transform = 'translateX(0)';
                imgEl.style.opacity = '1';
                setTimeout(function () {
                    imgEl.style.transition = '';
                    imgEl.style.transform = '';
                    imgEl.style.opacity = '';
                }, 300);
            }
        }, { passive: true });

        window.__gallery_openAt = function (index, slidesInput) {
            var list = Array.isArray(slidesInput) ? slidesInput : [];
            currentSlides = list.map(function (item) {
                if (typeof item === 'string') {
                    return { src: item, alt: '', caption: '' };
                }
                return {
                    src: item.src || item.full || '',
                    alt: item.alt || '',
                    caption: item.caption || '',
                };
            }).filter(function (s) { return Boolean(s.src); });

            if (!currentSlides.length) return;
            curIndex = Math.max(0, Math.min(Number(index) || 0, currentSlides.length - 1));
            overlay.classList.add('is-visible');
            lockScroll();
            showCurrent();
        };

        window.__gallery_close = hideOverlay;
    }

    function openOverlayAt(index, galleryRoot) {
        const raw = galleryRoot._pmSlides;
        let slides;
        if (Array.isArray(raw) && raw.length) {
            slides = raw.map(function (s) {
                return {
                    src: s.full,
                    alt: s.alt || '',
                    caption: s.caption || '',
                };
            });
        } else {
            const nodes = Array.from(
                galleryRoot.querySelectorAll('.gallery-img, .gallery-slide-img, .gallery-slide[data-src]')
            );
            slides = nodes.map(function (n) {
                return {
                    src: n.dataset.full || n.dataset.src || n.src,
                    alt: n.alt || '',
                    caption: '',
                };
            });
        }

        const seen = new Set();
        slides = slides.filter(function (s) {
            if (!s.src || seen.has(s.src)) return false;
            seen.add(s.src);
            return true;
        });

        if (typeof window.__gallery_openAt === 'function') {
            window.__gallery_openAt(index || 0, slides);
        }
    }
})();

// Grid last-row span helper (feed thumbs + legacy .gallery-grid only).
(function () {
    'use strict';

    function debounce(fn, wait) {
        let t = null;
        return function () {
            const args = arguments;
            clearTimeout(t);
            t = setTimeout(() => fn.apply(this, args), wait);
        };
    }

    function getGridColumnCount(grid) {
        const cs = window.getComputedStyle(grid);
        const cols = cs.getPropertyValue('grid-template-columns') || '';
        if (!cols.trim()) return 1;
        const parts = cols.trim().replace(/\s+/g, ' ').split(' ');
        return parts.length;
    }

    function distributeSpans(cols, lastRowCount) {
        const base = Math.floor(cols / lastRowCount);
        let rem = cols - base * lastRowCount;
        const spans = [];
        for (let i = 0; i < lastRowCount; i++) {
            const extra = (rem > 0) ? 1 : 0;
            spans.push(base + extra);
            if (rem > 0) rem--;
        }
        return spans;
    }

    function gridItemsForAdjust(grid) {
        if (grid.classList.contains('item-feed-card__thumb-grid')) {
            return Array.from(grid.querySelectorAll('.item-feed-card__thumb-slot'));
        }
        return Array.from(grid.querySelectorAll('.gallery-cell'));
    }

    function adjustLastRowSpan(grid) {
        if (!grid) return;
        if (grid.classList.contains('post-media-gallery__grid')) return;

        const items = gridItemsForAdjust(grid);
        if (!items.length) return;

        items.forEach(it => {
            it.style.gridColumn = '';
        });

        const isFeedThumb = grid.classList.contains('item-feed-card__thumb-grid');
        if (!isFeedThumb && items.length === 2) {
            grid.classList.add('gallery-two-cols');
        } else if (!isFeedThumb) {
            grid.classList.remove('gallery-two-cols');
        }

        const cols = getGridColumnCount(grid) || 1;
        if (cols <= 1) return;

        const lastRowCount = items.length % cols === 0 ? cols : items.length % cols;
        if (lastRowCount === cols) return;

        const startIndex = items.length - lastRowCount;
        const spans = distributeSpans(cols, lastRowCount);

        for (let i = 0; i < lastRowCount; i++) {
            const it = items[startIndex + i];
            const span = Math.max(1, spans[i] || 1);
            if (span === 1) it.style.gridColumn = '';
            else it.style.gridColumn = 'span ' + span;
        }
    }

    function adjustAllGrids() {
        const grids = Array.from(document.querySelectorAll('.gallery-grid, .item-feed-card__thumb-grid'));
        grids.forEach(grid => {
            try {
                adjustLastRowSpan(grid);
            } catch (err) {
                console.error('adjustLastRowSpan error', err);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(adjustAllGrids, 60);
    });

    window.addEventListener('resize', debounce(function () {
        adjustAllGrids();
    }, 120));

    window.__gallery_adjustLastRow = adjustAllGrids;
})();
