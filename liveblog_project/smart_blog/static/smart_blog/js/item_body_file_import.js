/**
 * Create/Edit post: pinned PDF/DOCX — clear via body_pin_clear on save (same flow as mark-delete for images).
 */
(function () {
    'use strict';

    function queryPinWrap() {
        return document.getElementById('itemBodyPinRow');
    }

    function queryPinFileInput(wrap) {
        if (!wrap) {
            return null;
        }
        return wrap.querySelector('input[type="file"][name="body_pin_file"]');
    }

    function queryPinClearHidden(wrap) {
        if (!wrap) {
            return null;
        }
        return wrap.querySelector('input[name="body_pin_clear"]');
    }

    function isClearRequested(clearHidden) {
        if (!clearHidden) {
            return false;
        }
        var v = String(clearHidden.value || clearHidden.getAttribute('value') || '')
            .trim()
            .toLowerCase();
        return v === 'on' || v === '1' || v === 'true' || v === 'yes';
    }

    function updatePinMarkUi(wrap) {
        var clearHidden = queryPinClearHidden(wrap);
        var existing = document.getElementById('itemBodyPinExistingName');
        var btn = document.getElementById('itemBodyPinFileClear');
        var marked = isClearRequested(clearHidden);
        if (existing) {
            existing.classList.toggle('marked-for-delete', marked);
        }
        if (btn) {
            if (marked) {
                btn.innerHTML = '<i class="fa fa-undo" aria-hidden="true"></i>';
                btn.setAttribute('aria-pressed', 'true');
                var un = btn.getAttribute('data-title-unmark');
                if (un) {
                    btn.title = un;
                }
            } else {
                btn.innerHTML = '<i class="fa fa-times" aria-hidden="true"></i>';
                btn.setAttribute('aria-pressed', 'false');
                var mk = btn.getAttribute('data-title-mark');
                if (mk) {
                    btn.title = mk;
                }
            }
        }
    }

    function sync(wrap) {
        var inp = queryPinFileInput(wrap);
        var clearHidden = queryPinClearHidden(wrap);
        var existingName = document.getElementById('itemBodyPinExistingName');
        var headingSep = document.getElementById('itemBodyPinHeadingSep');
        if (!inp) {
            updatePinMarkUi(wrap);
            return;
        }
        if (!existingName) {
            return;
        }
        var hasLocal = !!(inp.files && inp.files.length);
        var hidePinnedRow = !!hasLocal;
        existingName.hidden = hidePinnedRow;
        if (hidePinnedRow) {
            existingName.classList.add('d-none');
        } else {
            existingName.classList.remove('d-none');
        }
        if (headingSep) {
            headingSep.hidden = hidePinnedRow;
            if (hidePinnedRow) {
                headingSep.classList.add('d-none');
            } else {
                headingSep.classList.remove('d-none');
            }
        }
        if (hidePinnedRow && clearHidden) {
            clearHidden.value = '';
            clearHidden.removeAttribute('value');
        }
        updatePinMarkUi(wrap);
    }

    function togglePinMark(wrap) {
        var clearHidden = queryPinClearHidden(wrap);
        if (!clearHidden) {
            return;
        }
        var marked = isClearRequested(clearHidden);
        if (!marked) {
            clearHidden.value = 'on';
            clearHidden.setAttribute('value', 'on');
        } else {
            clearHidden.value = '';
            clearHidden.removeAttribute('value');
        }
        updatePinMarkUi(wrap);
    }

    function boot() {
        var wrap = queryPinWrap();
        if (!wrap) {
            return;
        }
        var inp = queryPinFileInput(wrap);
        var btn = document.getElementById('itemBodyPinFileClear');
        if (!inp && !btn) {
            return;
        }

        if (inp) {
            inp.addEventListener('change', function () {
                var clearHidden = queryPinClearHidden(wrap);
                if (clearHidden) {
                    clearHidden.value = '';
                    clearHidden.removeAttribute('value');
                }
                sync(wrap);
            });
        }

        if (btn) {
            btn.addEventListener('click', function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                togglePinMark(wrap);
            });
        }

        sync(wrap);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
