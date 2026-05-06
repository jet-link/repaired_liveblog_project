// Video gallery: Plyr-powered viewer with swipe navigation + quality selector.
(function () {
    'use strict';

    var isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

    var overlay = null;
    var plyrInstance = null;
    var currentSlides = [];
    var curIndex = 0;

    function qs(sel, ctx) { return (ctx || document).querySelector(sel); }

    function ensureOverlay() {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.className = 'video-gallery-overlay';
        overlay.innerHTML =
            '<button type="button" class="video-gallery-close-btn" aria-label="Close">' +
            '<span class="video-gallery-close-btn__line"></span>' +
            '<span class="video-gallery-close-btn__line"></span>' +
            '</button>' +
            '<div class="video-gallery-nav" role="group" aria-label="Video navigation">' +
            '<button type="button" class="video-gallery-nav-btn video-gallery-nav-btn--prev" aria-label="Previous video">' +
            '<svg class="video-gallery-nav-icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">' +
            '<path fill="currentColor" d="M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6 1.41-1.41z"/>' +
            '</svg></button>' +
            '<button type="button" class="video-gallery-nav-btn video-gallery-nav-btn--next" aria-label="Next video">' +
            '<svg class="video-gallery-nav-icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">' +
            '<path fill="currentColor" d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>' +
            '</svg></button>' +
            '</div>' +
            '<div class="video-gallery-overlay-inner" role="dialog" aria-modal="true" aria-label="Video viewer">' +
            '<div class="video-gallery-player-wrap"></div>' +
            '</div>';
        document.body.appendChild(overlay);

        var inner = qs('.video-gallery-overlay-inner', overlay);
        var closeBtn = qs('.video-gallery-close-btn', overlay);
        var prevNavBtn = qs('.video-gallery-nav-btn--prev', overlay);
        var nextNavBtn = qs('.video-gallery-nav-btn--next', overlay);

        closeBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            hideOverlay();
        });

        prevNavBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            nav(-1);
        });
        nextNavBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            nav(1);
        });

        document.addEventListener('keydown', function (e) {
            if (!overlay || !overlay.classList.contains('is-visible')) return;
            if (e.key === 'Escape') { e.preventDefault(); hideOverlay(); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); nav(-1); }
            if (e.key === 'ArrowRight') { e.preventDefault(); nav(1); }
            if (e.key === ' ' || e.code === 'Space') {
                e.preventDefault();
                if (plyrInstance) {
                    try { plyrInstance.togglePlay(); } catch (err) {}
                }
            }
        });

        // Swipe between videos: desktop/tablet only; mobile uses bottom nav arrows
        if (!isMobile) {
            var touchStartX = 0;
            var touchStartY = 0;
            var isDragging = false;
            var isVerticalScroll = false;

            inner.addEventListener('touchstart', function (e) {
                if (!e.changedTouches || !e.changedTouches.length) return;
                if (e.target.closest && e.target.closest('.plyr__controls')) return;
                touchStartX = e.changedTouches[0].clientX;
                touchStartY = e.changedTouches[0].clientY;
                isDragging = true;
                isVerticalScroll = false;
            }, { passive: true });

            inner.addEventListener('touchmove', function (e) {
                if (!isDragging || !e.changedTouches || !e.changedTouches.length) return;
                var dy = e.changedTouches[0].clientY - touchStartY;
                var dx = e.changedTouches[0].clientX - touchStartX;
                if (!isVerticalScroll && Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) {
                    isVerticalScroll = true;
                }
            }, { passive: true });

            inner.addEventListener('touchend', function (e) {
                if (!isDragging) return;
                isDragging = false;
                if (isVerticalScroll) return;
                if (!e.changedTouches || !e.changedTouches.length) return;
                var dx = e.changedTouches[0].clientX - touchStartX;
                if (Math.abs(dx) < 55) return;
                if (currentSlides.length <= 1) return;
                if (dx < 0) nav(1);
                else nav(-1);
            }, { passive: true });
        }
    }

    function syncVideoGalleryNav() {
        if (!overlay) return;
        var navEl = qs('.video-gallery-nav', overlay);
        var prevBtn = qs('.video-gallery-nav-btn--prev', overlay);
        var nextBtn = qs('.video-gallery-nav-btn--next', overlay);
        if (!navEl || !prevBtn || !nextBtn) return;
        var n = currentSlides.length;
        if (n <= 1) {
            navEl.hidden = true;
            return;
        }
        navEl.hidden = false;
        prevBtn.hidden = curIndex === 0;
        nextBtn.hidden = curIndex === n - 1;
    }

    function destroyPlyr() {
        if (plyrInstance) {
            try { plyrInstance.destroy(); } catch (e) {}
            plyrInstance = null;
        }
    }

    function buildVideoElement(slide) {
        var video = document.createElement('video');
        video.className = 'video-gallery-player';
        video.setAttribute('playsinline', '');
        video.setAttribute('preload', 'metadata');

        var qualities = slide.qualities || {};
        var qualityKeys = Object.keys(qualities).map(Number).sort(function (a, b) { return b - a; });

        if (qualityKeys.length) {
            qualityKeys.forEach(function (q) {
                var source = document.createElement('source');
                source.src = qualities[q];
                source.type = 'video/mp4';
                source.setAttribute('size', q);
                video.appendChild(source);
            });
        } else if (slide.src) {
            var source = document.createElement('source');
            source.src = slide.src;
            source.type = 'video/mp4';
            source.setAttribute('size', 720);
            video.appendChild(source);
        }

        return video;
    }

    function getAvailableQualities(slide) {
        var qualities = slide.qualities || {};
        var keys = Object.keys(qualities).map(Number).sort(function (a, b) { return b - a; });
        return keys.length ? keys : [720];
    }

    function createPlyr(videoEl, qualityOptions, hasMultipleQualities) {
        var defaultQuality = 720;
        if (qualityOptions.indexOf(720) === -1) {
            defaultQuality = qualityOptions[qualityOptions.length - 1];
        }

        var settingsList = ['speed'];
        if (hasMultipleQualities) {
            settingsList.unshift('quality');
        }

        try {
            plyrInstance = new Plyr(videoEl, {
                controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'settings', 'fullscreen'],
                settings: settingsList,
                quality: {
                    default: defaultQuality,
                    options: qualityOptions,
                    forced: true
                },
                speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] },
                blankVideo: '',
                resetOnEnd: true,
                clickToPlay: true,
                hideControls: true,
                tooltips: { controls: false, seek: true },
                i18n: {
                    qualityLabel: {
                        0: 'Auto',
                        360: '360p',
                        480: '480p',
                        720: '720p',
                        1080: '1080p HD'
                    }
                }
            });

            plyrInstance.on('enterfullscreen', function () {
                var btn = overlay && overlay.querySelector('.video-gallery-close-btn');
                if (btn) btn.style.display = 'none';
                initMobileFullscreenControls();
            });
            plyrInstance.on('exitfullscreen', function () {
                var btn = overlay && overlay.querySelector('.video-gallery-close-btn');
                if (btn) btn.style.display = '';
                cleanupMobileFullscreenControls();
            });
        } catch (err) {
            plyrInstance = null;
        }
    }

    function showCurrent() {
        var s = currentSlides[curIndex];
        if (!s) return;

        var inner = qs('.video-gallery-overlay-inner', overlay);
        var wrap = qs('.video-gallery-player-wrap', overlay);

        inner.style.opacity = '0';

        destroyPlyr();
        wrap.innerHTML = '';

        var videoEl = buildVideoElement(s);
        wrap.appendChild(videoEl);

        var qualityOptions = getAvailableQualities(s);
        var hasMultipleQualities = s.qualities && Object.keys(s.qualities).length > 1;

        videoEl.addEventListener('loadedmetadata', function () {
            inner.style.opacity = '';
        });

        createPlyr(videoEl, qualityOptions, hasMultipleQualities);
        syncVideoGalleryNav();
    }

    function nav(dir) {
        if (currentSlides.length <= 1) return;
        curIndex = (curIndex + dir + currentSlides.length) % currentSlides.length;
        showCurrent();
    }

    function hideOverlay() {
        if (!overlay) return;
        destroyPlyr();
        var wrap = qs('.video-gallery-player-wrap', overlay);
        if (wrap) wrap.innerHTML = '';
        overlay.classList.remove('is-visible');
        if (typeof window.unlockScroll === 'function') window.unlockScroll();
    }

    window.__videoGallery_openAt = function (index, slides) {
        ensureOverlay();
        currentSlides = (Array.isArray(slides) ? slides : []).map(function (s) {
            if (typeof s === 'string') return { src: s };
            return {
                src: s.src || s.url || '',
                qualities: s.qualities || null
            };
        }).filter(function (s) { return Boolean(s.src); });
        if (!currentSlides.length) return;
        curIndex = Math.max(0, Math.min(Number(index) || 0, currentSlides.length - 1));
        overlay.classList.add('is-visible');
        if (typeof window.lockScroll === 'function') window.lockScroll();
        showCurrent();
    };

    window.__videoGallery_close = hideOverlay;

    /* ── Mobile fullscreen: tap to show controls, double-tap to exit ── */
    var _mfsCleanups = [];

    function initMobileFullscreenControls() {
        if (!isMobile || !plyrInstance) return;
        cleanupMobileFullscreenControls();

        var container = plyrInstance.elements && plyrInstance.elements.container;
        if (!container) return;

        var lastTap = 0;
        var controlsVisible = true;
        var hideTimer = null;

        function showControls() {
            if (!plyrInstance) return;
            container.classList.remove('plyr--hide-controls');
            container.classList.add('plyr--mobile-fs-controls-visible');
            controlsVisible = true;
            clearTimeout(hideTimer);
            hideTimer = setTimeout(function () {
                if (!plyrInstance || !plyrInstance.fullscreen || !plyrInstance.fullscreen.active) return;
                container.classList.add('plyr--hide-controls');
                container.classList.remove('plyr--mobile-fs-controls-visible');
                controlsVisible = false;
            }, 4000);
        }

        function onTap(e) {
            if (!plyrInstance || !plyrInstance.fullscreen || !plyrInstance.fullscreen.active) return;
            if (e.target.closest('.plyr__controls') || e.target.closest('.plyr__menu') ||
                e.target.closest('button')) return;

            var now = Date.now();
            if (now - lastTap < 350) {
                clearTimeout(hideTimer);
                try { plyrInstance.fullscreen.exit(); } catch (err) {}
                lastTap = 0;
                return;
            }
            lastTap = now;

            if (controlsVisible) {
                clearTimeout(hideTimer);
                container.classList.add('plyr--hide-controls');
                container.classList.remove('plyr--mobile-fs-controls-visible');
                controlsVisible = false;
            } else {
                showControls();
            }
        }

        container.addEventListener('touchend', onTap);
        _mfsCleanups.push(function () {
            container.removeEventListener('touchend', onTap);
            clearTimeout(hideTimer);
            container.classList.remove('plyr--mobile-fs-controls-visible');
        });

        showControls();
    }

    function cleanupMobileFullscreenControls() {
        _mfsCleanups.forEach(function (fn) { try { fn(); } catch (e) {} });
        _mfsCleanups = [];
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (typeof Plyr === 'undefined') return;
        document.querySelectorAll('.js-plyr-inline').forEach(function (el) {
            var sources = el.querySelectorAll('source[size]');
            var hasQualities = sources.length > 1;
            var settingsList = ['speed'];
            if (hasQualities) settingsList.unshift('quality');

            var inlinePlayer = new Plyr(el, {
                controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'settings', 'fullscreen'],
                settings: settingsList,
                quality: { default: 720, options: [1080, 720, 480, 360], forced: true },
                speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] },
                blankVideo: '',
                resetOnEnd: true,
                hideControls: true,
                tooltips: { controls: false, seek: true },
            });

            if (isMobile) {
                inlinePlayer.on('enterfullscreen', function () {
                    initInlineMobileFS(inlinePlayer);
                });
                inlinePlayer.on('exitfullscreen', function () {
                    cleanupInlineMobileFS(inlinePlayer);
                });
            }
        });
    });

    /* Same tap/double-tap logic for inline players in fullscreen */
    function initInlineMobileFS(player) {
        var container = player.elements && player.elements.container;
        if (!container) return;

        var lastTap = 0;
        var controlsVisible = true;
        var hideTimer = null;

        function showControls() {
            container.classList.remove('plyr--hide-controls');
            container.classList.add('plyr--mobile-fs-controls-visible');
            controlsVisible = true;
            clearTimeout(hideTimer);
            hideTimer = setTimeout(function () {
                if (!player.fullscreen || !player.fullscreen.active) return;
                container.classList.add('plyr--hide-controls');
                container.classList.remove('plyr--mobile-fs-controls-visible');
                controlsVisible = false;
            }, 4000);
        }

        function onTap(e) {
            if (!player.fullscreen || !player.fullscreen.active) return;
            if (e.target.closest('.plyr__controls') || e.target.closest('.plyr__menu') ||
                e.target.closest('button')) return;

            var now = Date.now();
            if (now - lastTap < 350) {
                clearTimeout(hideTimer);
                try { player.fullscreen.exit(); } catch (err) {}
                lastTap = 0;
                return;
            }
            lastTap = now;

            if (controlsVisible) {
                clearTimeout(hideTimer);
                container.classList.add('plyr--hide-controls');
                container.classList.remove('plyr--mobile-fs-controls-visible');
                controlsVisible = false;
            } else {
                showControls();
            }
        }

        container.addEventListener('touchend', onTap);
        container._mfsCleanup = function () {
            container.removeEventListener('touchend', onTap);
            clearTimeout(hideTimer);
            container.classList.remove('plyr--mobile-fs-controls-visible');
        };

        showControls();
    }

    function cleanupInlineMobileFS(player) {
        var container = player.elements && player.elements.container;
        if (container && container._mfsCleanup) {
            container._mfsCleanup();
            delete container._mfsCleanup;
        }
    }
})();
