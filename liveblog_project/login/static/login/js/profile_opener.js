(function () {
    const menu = document.getElementById('userMenu');
    if (!menu) return;

    const avatar = menu.querySelector('.user-avatar-btn');
    const tooltip = menu.querySelector('.user-tooltip');

    function isMobile() {
        return window.matchMedia('(max-width: 768px)').matches;
    }

    function updateTooltipCaret() {
        if (!tooltip || !avatar || !menu.classList.contains('open')) return;
        const ar = avatar.getBoundingClientRect();
        const tr = tooltip.getBoundingClientRect();
        const x = ar.left + ar.width / 2 - tr.left;
        tooltip.style.setProperty('--user-tooltip-caret-x', x + 'px');
    }

    avatar.addEventListener('click', (e) => {
        if (isMobile()) {
            // 📱 MOBILE → обычный переход по ссылке
            return;
        }

        // 🖥 DESKTOP → tooltip
        e.preventDefault();
        e.stopPropagation();
        menu.classList.toggle('open');
        if (menu.classList.contains('open')) {
            requestAnimationFrame(() => requestAnimationFrame(updateTooltipCaret));
        }
    });

    // закрытие по клику вне (в т.ч. по другим кнопкам — search, theme, burger)
    // capture: true — чтобы сработать до stopPropagation в обработчиках кнопок
    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target)) {
            menu.classList.remove('open');
        }
    }, true);

    // закрытие по ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            menu.classList.remove('open');
        }
    });

    // закрытие при скролле
    window.addEventListener('scroll', () => {
        menu.classList.remove('open');
    }, { passive: true });

    window.addEventListener('resize', () => {
        updateTooltipCaret();
    }, { passive: true });
})();