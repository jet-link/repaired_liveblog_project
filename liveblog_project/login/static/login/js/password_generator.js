// Password generator modal for register / change-password forms.
// Runs on DOMContentLoaded + turbo:load so it works after Turbo soft navigations.
(function () {
    'use strict';

    var modalId     = 'genPassModal';
    var genBtnId    = 'genPassBtn';
    var generatedId = 'generatedPassword';
    var copyBtnId   = 'copyPassBtn';
    var useBtnId    = 'usePassBtn';

    function findPassFields() {
        var ids = ['id_password1','id_password2','id_new_password1','id_new_password2','password1','password2'];
        var found = {};
        ids.forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            if (id.toLowerCase().indexOf('1') !== -1) found.p1 = found.p1 || el;
            if (id.toLowerCase().indexOf('2') !== -1) found.p2 = found.p2 || el;
        });
        if (!found.p1) found.p1 = document.querySelector('input[name="password1"], input[name="new_password1"]') || null;
        if (!found.p2) found.p2 = document.querySelector('input[name="password2"], input[name="new_password2"]') || null;
        return found;
    }

    function randomPassword(n) {
        var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*()-_=+';
        var s = '';
        for (var i = 0; i < (n || 12); i++) s += chars.charAt(Math.floor(Math.random() * chars.length));
        return s;
    }

    function getModalInstance(el) {
        if (!el || typeof bootstrap === 'undefined') return null;
        try { return bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el); } catch (e) { return null; }
    }

    function init() {
        var modalEl     = document.getElementById(modalId);
        var genBtn      = document.getElementById(genBtnId);
        var generatedEl = document.getElementById(generatedId);
        var copyBtn     = document.getElementById(copyBtnId);
        var useBtn      = document.getElementById(useBtnId);

        if (!genBtn || !generatedEl || !modalEl) return;
        if (genBtn.__pwGenBound) return;
        genBtn.__pwGenBound = true;

        if (modalEl.parentNode !== document.body) document.body.appendChild(modalEl);

        var initFields = findPassFields();

        genBtn.addEventListener('click', function (e) {
            e.preventDefault();
            generatedEl.textContent = randomPassword(12);
            var inst = getModalInstance(modalEl);
            if (inst) inst.show();
            setTimeout(function () { var u = document.getElementById(useBtnId); if (u) u.focus(); }, 200);
        });

        if (copyBtn) {
            copyBtn.addEventListener('click', function (e) {
                e.preventDefault();
                var txt = (generatedEl.textContent || '').trim();
                if (!txt) return;
                try {
                    navigator.clipboard.writeText(txt).then(function () {
                        var old = copyBtn.textContent;
                        copyBtn.textContent = 'Copied!';
                        copyBtn.classList.replace('btn-success', 'btn-secondary');
                        setTimeout(function () { copyBtn.textContent = old; copyBtn.classList.replace('btn-secondary', 'btn-success'); }, 1200);
                    });
                } catch (_) {}
            });
        }

        if (useBtn) {
            useBtn.addEventListener('click', function (e) {
                e.preventDefault();
                var txt = (generatedEl.textContent || '').trim();
                if (!txt) return;
                var f = findPassFields();
                var t1 = f.p1 || initFields.p1;
                var t2 = f.p2 || initFields.p2;
                if (t1) { t1.value = txt; t1.dispatchEvent(new Event('input', { bubbles: true })); t1.dispatchEvent(new Event('change', { bubbles: true })); }
                if (t2) { t2.value = txt; t2.dispatchEvent(new Event('input', { bubbles: true })); t2.dispatchEvent(new Event('change', { bubbles: true })); }
                var inst = getModalInstance(modalEl);
                try { if (inst) inst.hide(); } catch (_) {}
                setTimeout(function () { var sb = document.querySelector('form [type="submit"]'); if (sb) sb.focus(); }, 180);
            });
        }

        modalEl.addEventListener('hidden.bs.modal', function () {
            try {
                if (document.activeElement && modalEl.contains(document.activeElement)) {
                    var fb = document.getElementById(genBtnId) || document.querySelector('form [type="submit"]');
                    if (fb) fb.focus(); else document.body.focus();
                }
            } catch (_) {}
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    document.documentElement.addEventListener('turbo:load', init);
})();
