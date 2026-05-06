(function () {
    'use strict';

    function init() {
        var profileCard  = document.getElementById('profileCard');
        var passwordCard = document.getElementById('passwordCard');
        var showBtn      = document.getElementById('showPasswordBtn');
        var closeBtn     = document.getElementById('closePasswordBtn');

        if (!profileCard || !passwordCard) return;
        if (showBtn && showBtn.__pwSwitcherBound) return;

        function showPasswordCard() {
            profileCard.classList.remove('is-visible');
            profileCard.classList.add('is-hidden');
            passwordCard.classList.remove('is-hidden');
            requestAnimationFrame(function () { passwordCard.classList.add('is-visible'); });
            var input = passwordCard.querySelector('input, textarea, select');
            if (input) setTimeout(function () { input.focus(); }, 260);
            document.addEventListener('keydown', escHandler);
        }

        function hidePasswordCard() {
            passwordCard.classList.remove('is-visible');
            setTimeout(function () { passwordCard.classList.add('is-hidden'); }, 420);
            profileCard.classList.remove('is-hidden');
            requestAnimationFrame(function () { profileCard.classList.add('is-visible'); });
            var btn = profileCard.querySelector('[type="submit"], button');
            if (btn) setTimeout(function () { btn.focus(); }, 260);
            document.removeEventListener('keydown', escHandler);
        }

        function escHandler(e) {
            if (e.key === 'Escape' || e.key === 'Esc') hidePasswordCard();
        }

        if (showBtn) {
            showBtn.__pwSwitcherBound = true;
            showBtn.addEventListener('click', function (e) { e.preventDefault(); showPasswordCard(); });
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', function (e) { e.preventDefault(); hidePasswordCard(); });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    document.documentElement.addEventListener('turbo:load', init);
})();
