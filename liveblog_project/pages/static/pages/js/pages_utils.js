// pages/static/pages/js/hero_overlay.js
(function () {
    'use strict';

    // Настройки — подстрой под вкус:
    const START_DELAY_MS = 140;   // задержка перед началом анимации (даёт "задумчивость")
    const SLIDE_DURATION_MS = 900; // должна совпадать с transition в CSS .closing
    const TOTAL_MS = START_DELAY_MS + SLIDE_DURATION_MS + 30;

    let overlay, hint;
    let locked = false;      // предотвращает повторные запуски
    let touchStartY = null;

    function scheduleClose() {
        if (locked) return;
        locked = true;

        // 1) give a tiny visual pause: mark preparing (optional)
        overlay.classList.add('preparing');

        // 2) after short delay, start closing animation (add 'closing')
        setTimeout(() => {
            // remove preparing if present
            overlay.classList.remove('preparing');

            // start slide-up animation
            overlay.classList.add('closing');

            // keep body locked until animation finishes
            // remove overlay from flow after animation complete
            setTimeout(() => {
                // mark hidden (will set display:none via CSS)
                overlay.classList.add('hidden');

                // allow page scroll now
                document.body.classList.remove('no-scroll');
                if (typeof unlockScroll === 'function') unlockScroll();

                // cleanup listeners
                detachListeners();
            }, SLIDE_DURATION_MS + 10);
        }, START_DELAY_MS);
    }

    // Wheel detection: only react to a clear downward scroll intent
    function onWheel(e) {
        // prefer larger delta to avoid accidental triggers
        if (e.deltaY > 8) {
            e.preventDefault && e.preventDefault();
            scheduleClose();
        }
    }

    // Touch detection for mobile: detect swipe up
    function onTouchStart(e) {
        if (!e.touches || e.touches.length === 0) return;
        touchStartY = e.touches[0].clientY;
    }
    function onTouchMove(e) {
        if (touchStartY === null) return;
        const cur = (e.touches && e.touches[0] && e.touches[0].clientY) || 0;
        const dy = touchStartY - cur;
        // threshold to ensure deliberate swipe
        if (dy > 26) {
            e.preventDefault && e.preventDefault();
            scheduleClose();
            touchStartY = null;
        }
    }

    // keyboard
    function onKeyDown(e) {
        if (e.key === 'ArrowDown' || e.key === 'PageDown') {
            scheduleClose();
        }
    }

    function onHintClick(ev) {
        ev && ev.preventDefault && ev.preventDefault();
        scheduleClose();
    }

    function attachListeners() {
        window.addEventListener('wheel', onWheel, { passive: false });
        window.addEventListener('touchstart', onTouchStart, { passive: true });
        window.addEventListener('touchmove', onTouchMove, { passive: false });
        window.addEventListener('keydown', onKeyDown, { passive: true });

        if (hint) hint.addEventListener('click', onHintClick);
    }
    function detachListeners() {
        window.removeEventListener('wheel', onWheel);
        window.removeEventListener('touchstart', onTouchStart);
        window.removeEventListener('touchmove', onTouchMove);
        window.removeEventListener('keydown', onKeyDown);

        if (hint) hint.removeEventListener('click', onHintClick);
    }

    function init() {
        overlay = document.getElementById('heroOverlay');
        hint = document.querySelector('.hero-scroll-hint');

        if (!overlay) return;

        // 1) show overlay and block body scroll
        overlay.classList.remove('hidden', 'closing', 'preparing');
        overlay.style.display = 'flex';           // ensure visible
        document.body.classList.add('no-scroll');
        if (typeof lockScroll === 'function') lockScroll();

        // small rAF to let CSS settle before attaching listeners
        requestAnimationFrame(() => {
            // overlay visible now; attach listeners for the "first scroll" gesture
            attachListeners();
        });
    }

    // DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }

})();




// pages/static/pages/js/secondary_parallax.js
(function () {
    'use strict';

    const section = document.querySelector('.cosmo_section');
    if (!section) return;

    const title = section.querySelector('.sec-title');
    const sub = section.querySelector('.sec-sub');
    const astros = Array.from(section.querySelectorAll('.sec-astro'));

    const TITLE_MAX = 48;
    const SUB_MAX = 28;
    const BASE_ASTRO_MAX = 480; // базовая дальность подъёма (px)

    // Пер-элемент state
    const elems = astros.map(img => {
        const speed = parseFloat(img.dataset.speed) || 0.16;
        const depth = parseFloat(img.dataset.depth) || 1.0;
        const scale = parseFloat(img.dataset.scale) || 1.0;
        const blur = parseFloat(img.dataset.blur) || 0;
        const z = parseInt(img.dataset.z || '3', 10);
        const left = img.dataset.left != null ? (parseFloat(img.dataset.left) + '%') : null;
        const bottom = img.dataset.bottom != null ? (isNaN(Number(img.dataset.bottom)) ? img.dataset.bottom : (parseFloat(img.dataset.bottom) + 'px')) : null;

        // apply initial left/bottom/scale/z/blur
        if (left) img.style.left = left;
        if (bottom) img.style.bottom = bottom;
        img.style.zIndex = String(z);
        img.style.transform = `translateX(-50%) translateY(0) scale(${scale})`;
        img.style.filter = `blur(${blur}px)`;

        return {
            el: img,
            cur: 0,
            tgt: 0,
            speed: speed,
            depth: depth,
            scale: scale,
            blur: blur,
            z: z
        };
    });

    let tCur = 0, tTgt = 0;
    let sCur = 0, sTgt = 0;
    let pCur = 0, pTgt = 0;
    let ticking = false;

    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    function updateTargets() {
        const rect = section.getBoundingClientRect();
        const h = rect.height || window.innerHeight;

        // progress 0..1
        const EARLY_START = window.innerHeight * 0.45;  // начать ≈ за 45% до входа секции
        let progress = clamp((EARLY_START - rect.top) / (h + EARLY_START), 0, 1);

        tTgt = -TITLE_MAX * progress;
        sTgt = -SUB_MAX * progress;
        pTgt = progress;

        elems.forEach(e => {
            // цель подъёма — базовая * depth * progress
            e.tgt = - (BASE_ASTRO_MAX * e.depth) * progress;
        });
    }

    function render() {
        // текст
        tCur += (tTgt - tCur) * 0.14;
        sCur += (sTgt - sCur) * 0.14;
        pCur += (pTgt - pCur) * 0.12;
        if (title) title.style.transform = `translateY(${tCur}px)`;
        if (sub) sub.style.transform = `translateY(${sCur}px)`;

        // astros
        elems.forEach(e => {
            // более дальние элементы: делаем скорость ниже и амплитуду горизонтального wobble меньше
            const speed = e.speed;
            e.cur += (e.tgt - e.cur) * speed;

            // горизонтальный лёгкий параллакс: дальние меньше двигаются
            const depthNorm = Math.max(0.3, Math.min(1.6, e.depth));
            const wobbleAmp = 1.4 + (depthNorm - 0.6) * 1.2;
            const wobble = Math.sin(e.cur * 0.02 + (e.z * 0.5)) * wobbleAmp;

            // применяем scale вместе с translateY
            const scaleShift = 1 + (depthNorm - 1) * 0.06 + (depthNorm - 1) * 0.03 * pCur;
            const scale = e.scale * scaleShift;
            e.el.style.transform = `translateX(-50%) translateY(${e.cur}px) translateX(${wobble}px) scale(${scale})`;

            // blur и z уже заданы в начале, но можно динамически чуть подкорректировать blur при подъёме (опционально)
            // e.el.style.filter = `blur(${e.blur}px)`;
        });

        ticking = false;
    }

    function onScroll() {
        updateTargets();
        if (!ticking) {
            ticking = true;
            requestAnimationFrame(render);
        }
    }

    // init
    updateTargets();
    render();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', function () {
        updateTargets();
        if (!ticking) {
            ticking = true;
            requestAnimationFrame(render);
        }
    }, { passive: true });
})();




(function () {
    const snap = document.querySelector('.hero-snap');
    if (!snap) return;

    const card = snap.querySelector('.hero-card');
    if (!card) return;

    const GAP = 32;
    const STEP = card.offsetWidth + GAP;
    const INTERVAL = 5000; // 5 секунд

    let autoTimer = null;
    let autoEnabled = true;

    function scrollNext() {
        if (!autoEnabled) return;

        // если дошли до конца — возвращаемся в начало БЕЗ рывка
        if (snap.scrollLeft + snap.clientWidth >= snap.scrollWidth - STEP) {
            snap.scrollTo({ left: 0, behavior: 'auto' });
        } else {
            snap.scrollBy({ left: STEP, behavior: 'auto' });
        }
    }

    function startAuto() {
        stopAuto();
        autoEnabled = true;
        autoTimer = setInterval(scrollNext, INTERVAL);
    }

    function stopAuto() {
        autoEnabled = false;
        if (autoTimer) {
            clearInterval(autoTimer);
            autoTimer = null;
        }
    }

    // любое вмешательство пользователя — стоп
    ['wheel', 'touchstart', 'mousedown'].forEach(ev =>
        snap.addEventListener(ev, stopAuto, { passive: true })
    );

    // управление стрелками ← →
    window.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;

        stopAuto();

        if (e.key === 'ArrowRight') {
            snap.scrollBy({ left: STEP, behavior: 'auto' });
        } else {
            snap.scrollBy({ left: -STEP, behavior: 'auto' });
        }
    });

    // старт
    startAuto();
})();