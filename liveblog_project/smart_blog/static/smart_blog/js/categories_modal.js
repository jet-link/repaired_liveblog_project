// categories_modal.js — Categories dropdown-modal (delegation + fresh DOM on each open/close for Turbo)
(function () {
    'use strict';

    if (window.__categoriesModalInit) return;
    window.__categoriesModalInit = true;

    const TRIG_SEL = '.categories-modal-trigger';
    let isOpen = false;
    let lastTrigger = null;

    function root() {
        return document.getElementById('categoriesModalRoot');
    }
    function backdrop() {
        return document.getElementById('categoriesModalBackdrop');
    }
    function closeBtn() {
        return document.getElementById('categoriesModalClose');
    }
    function dialogEl() {
        return document.getElementById('categoriesModalDialog');
    }
    function chipsBtn() {
        return document.getElementById('categoriesModalChipsMoreBtn');
    }
    function chipsExtrasWrap() {
        return document.getElementById('categoriesModalChipsExtrasWrap');
    }

    function setExpandIcon(btn, up) {
        if (!btn) return;
        const i = btn.querySelector('i');
        if (!i) return;
        i.className = up ? 'fa fa-angle-up' : 'fa fa-angle-down';
    }

    function closeChipsExpand() {
        const cb = chipsBtn();
        const wrap = chipsExtrasWrap();
        if (!cb || !wrap) return;
        wrap.classList.remove('is-expanded');
        wrap.setAttribute('inert', '');
        wrap.setAttribute('aria-hidden', 'true');
        cb.setAttribute('aria-expanded', 'false');
        setExpandIcon(cb, false);
    }

    function toggleChipsExpand() {
        const cb = chipsBtn();
        const wrap = chipsExtrasWrap();
        if (!cb || !wrap) return;
        const willOpen = !wrap.classList.contains('is-expanded');
        wrap.classList.toggle('is-expanded', willOpen);
        if (willOpen) {
            wrap.removeAttribute('inert');
            wrap.setAttribute('aria-hidden', 'false');
        } else {
            wrap.setAttribute('inert', '');
            wrap.setAttribute('aria-hidden', 'true');
        }
        cb.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
        setExpandIcon(cb, willOpen);
    }

    function setTriggersExpanded(open) {
        document.querySelectorAll(TRIG_SEL).forEach(function (el) {
            el.setAttribute('aria-expanded', open ? 'true' : 'false');
            el.classList.toggle('active', open);
            el.querySelectorAll('.fa-angle-down').forEach(function (i) {
                i.classList.toggle('hidden', open);
            });
            el.querySelectorAll('.fa-angle-up').forEach(function (i) {
                i.classList.toggle('hidden', !open);
            });
        });
    }

    function openModal(triggerEl) {
        const r = root();
        if (!r || !backdrop() || !closeBtn() || !dialogEl() || isOpen) return;
        isOpen = true;
        lastTrigger = triggerEl && triggerEl.matches(TRIG_SEL) ? triggerEl : null;

        if (typeof lockScroll === 'function') {
            lockScroll();
        }

        r.classList.remove('hidden');
        r.setAttribute('aria-hidden', 'false');
        setTriggersExpanded(true);

        closeChipsExpand();

        const cb = closeBtn();
        if (cb) cb.focus();
    }

    function closeModal() {
        if (!isOpen) return;
        const r = root();
        isOpen = false;

        if (typeof unlockScroll === 'function') {
            unlockScroll();
        }

        if (r) {
            r.classList.add('hidden');
            r.setAttribute('aria-hidden', 'true');
        }
        setTriggersExpanded(false);

        const t = lastTrigger;
        lastTrigger = null;
        if (t && document.body.contains(t)) {
            try {
                t.focus({ preventScroll: true });
            } catch (e) {
                try {
                    t.focus();
                } catch (e2) {
                    /* ignore */
                }
            }
        }
    }

    document.addEventListener('click', function (e) {
        const chips = e.target && e.target.closest ? e.target.closest('#categoriesModalChipsMoreBtn') : null;
        if (chips) {
            e.preventDefault();
            toggleChipsExpand();
            return;
        }

        const closeEl = e.target && e.target.closest ? e.target.closest('#categoriesModalClose') : null;
        if (closeEl) {
            e.preventDefault();
            closeModal();
            return;
        }

        const bd = e.target && e.target.closest ? e.target.closest('#categoriesModalBackdrop') : null;
        if (bd) {
            closeModal();
            return;
        }

        const trigger = e.target && e.target.closest ? e.target.closest(TRIG_SEL) : null;
        if (!trigger) return;

        e.preventDefault();

        if (isOpen) {
            return;
        }

        openModal(trigger);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isOpen) {
            e.preventDefault();
            closeModal();
        }
    });

    var turboRoot = typeof document !== 'undefined' ? document.documentElement : null;
    if (turboRoot) {
        turboRoot.addEventListener('turbo:before-visit', function () {
            if (isOpen) {
                closeModal();
            }
        });
    }
})();
