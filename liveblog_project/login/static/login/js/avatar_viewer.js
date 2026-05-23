
// static/js/avatar-viewer.js
(function () {
    'use strict';

    const SELECTOR = '.personal_avatar .avatar-wrapper';
    const THUMB_SELECTOR = '.profile-mobile-avatar-thumb';

    const __avatarPrevOverflow = {
        html: '',
        body: '',
        paddingRight: ''
    };

    function init() {
        document.addEventListener('click', function (e) {
            const thumbBtn = e.target.closest(THUMB_SELECTOR);
            if (thumbBtn) {
                const img = thumbBtn.querySelector('img');
                if (!img) return;
                if (img.classList.contains('avatar-load-failed') || img.src.includes('no_avatar') || img.src.includes('no_image')) return;
                e.preventDefault();
                openLightbox(img.dataset.full || img.src, img.alt || 'Avatar');
                return;
            }

            const wrapper = e.target.closest(SELECTOR);
            if (!wrapper) return;

            if (e.target.closest('.avatar-remove-overlay')) return;

            const img = wrapper.querySelector('img');
            if (!img) return;

            if (img.classList.contains('avatar-load-failed') || img.src.includes('no_avatar') || img.src.includes('no_image')) return;

            e.preventDefault();

            openLightbox(
                img.dataset.full || img.src,
                img.alt || 'Avatar'
            );
        });
    }

    function createLightbox() {
        const overlay = document.createElement('div');
        overlay.id = 'avatarLightboxOverlay';
        overlay.className = 'avatar-lightbox-overlay';

        const container = document.createElement('div');
        container.className = 'avatar-lightbox-container';

        const img = document.createElement('img');
        img.className = 'avatar-lightbox-img';

        container.appendChild(img);
        overlay.appendChild(container);
        document.body.appendChild(overlay);

        bindEvents({ overlay, img });
        return { overlay, img };
    }

    function openLightbox(src, alt) {
        if (!window.__avatarLB__ || !document.body.contains(window.__avatarLB__.overlay)) {
            window.__avatarLB__ = createLightbox();
        }

        const lb = window.__avatarLB__;

        lb.img.src = src;
        lb.img.alt = alt;
        lb.overlay.style.display = 'flex';

        lockScroll();
    }

    function healAvatarScrollLock() {
        try {
            if (typeof window.LB !== 'undefined' && typeof LB.resetScrollLockAfterTurboNavigation === 'function') {
                LB.resetScrollLockAfterTurboNavigation();
            }
        } catch (e) { /* ignore */ }
    }

    function closeLightbox() {
        const lb = window.__avatarLB__;
        if (!lb) {
            healAvatarScrollLock();
            return;
        }

        try {
            lb.overlay.style.display = 'none';
        } catch (e) { /* detached node */ }
        try {
            lb.img.src = '';
        } catch (e) { /* ignore */ }

        if (typeof unlockScroll === 'function') {
            unlockScroll();
        }
        healAvatarScrollLock();
    }

    function bindEvents(lb) {
        lb.overlay.addEventListener('click', e => {
            if (e.target === lb.img) return;
            closeLightbox();
        });

        if (!window.__avatarLBKeydownBound) {
            window.__avatarLBKeydownBound = true;
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape') closeLightbox();
            });
        }
    }

    document.readyState === 'loading'
        ? document.addEventListener('DOMContentLoaded', init)
        : init();

    (document.documentElement || document).addEventListener('turbo:before-visit', function () {
        closeLightbox();
    });
})();




// avatar_preview.js — profile edit + register (forms with data-avatar-picker)
(function () {
    'use strict';

    const NOT_FOUND = '/static/img/image_not_found.webp';
    const ALLOWED_EXT = /\.(jpg|jpeg|png|gif|webp|svg)$/i;
    const REGISTER_AVATAR_DRAFT_KEY = 'brainstorm:registerAvatarDraft';

    function readRegisterAvatarDraft() {
        try {
            const raw = sessionStorage.getItem(REGISTER_AVATAR_DRAFT_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (_) {
            return null;
        }
    }

    function writeRegisterAvatarDraft(payload) {
        if (!payload || !payload.type) {
            try { sessionStorage.removeItem(REGISTER_AVATAR_DRAFT_KEY); } catch (_) { /* ignore */ }
            return;
        }
        try {
            sessionStorage.setItem(REGISTER_AVATAR_DRAFT_KEY, JSON.stringify(payload));
        } catch (_) { /* quota / private mode */ }
    }

    function currentRegisterUsername(formEl) {
        const input = formEl.querySelector('input[name="username"]');
        return input ? String(input.value || '').trim().toLowerCase() : '';
    }

    function registerAvatarDraftPayload(formEl, extra) {
        return Object.assign({ username: currentRegisterUsername(formEl) }, extra || {});
    }

    function dataUrlToFile(dataUrl, filename, mime) {
        const parts = String(dataUrl || '').split(',');
        if (parts.length < 2) return null;
        const match = parts[0].match(/:(.*?);/);
        const type = mime || (match && match[1]) || 'image/png';
        const bin = atob(parts[1]);
        const len = bin.length;
        const u8 = new Uint8Array(len);
        for (let i = 0; i < len; i++) u8[i] = bin.charCodeAt(i);
        return new File([u8], filename || 'avatar.png', { type: type });
    }

    function assignFileToInput(fileInput, file) {
        if (!fileInput || !file) return;
        try {
            const dt = new DataTransfer();
            dt.items.add(file);
            fileInput.files = dt.files;
        } catch (_) { /* ignore */ }
    }

    function initAvatarPicker(form) {
        const saveBtn = form.querySelector('button[type="submit"]');
        const urlInput = form.querySelector('input[name="avatar_url"]');
        const fileInput = form.querySelector('input[type="file"][name="avatar_file"]');
        const fileTrigger = form.querySelector('.avatar-file-trigger');

        const urlPreview = form.querySelector('#avatarUrlPreview');
        const filePreview = form.querySelector('#avatarFilePreview');

        const urlImg = urlPreview ? urlPreview.querySelector('img') : null;
        const fileImg = filePreview ? filePreview.querySelector('img') : null;
        const urlDeleteBtn = urlPreview ? urlPreview.querySelector('.avatar-preview-delete') : null;
        const fileDeleteBtn = filePreview ? filePreview.querySelector('.avatar-preview-delete') : null;

        const clearFlag = form.querySelector('#avatarClearFlag');

        if (!urlInput || !fileInput) return;

        function disableSave() {
            if (!saveBtn) return;
            if (!saveBtn.dataset.origText) {
                saveBtn.dataset.origText = saveBtn.textContent || '';
            }
            saveBtn.disabled = true;
            saveBtn.textContent = 'Blocked';
            saveBtn.classList.remove('custom-primary-btn');
            saveBtn.classList.add('custom-danger-btn');
        }

        function enableSave() {
            if (!saveBtn) return;
            saveBtn.disabled = false;
            if (saveBtn.dataset.origText) {
                saveBtn.textContent = saveBtn.dataset.origText;
            }
            saveBtn.classList.remove('custom-danger-btn');
            saveBtn.classList.add('custom-primary-btn');
        }

        function extractName(url) {
            return url ? url.split('/').pop().split('?')[0] : '';
        }

        function setClearFlag(val) {
            if (!clearFlag) return;
            clearFlag.value = val ? '1' : '0';
        }

        function clearAvatarSelection() {
            urlInput.value = '';
            fileInput.value = '';
            urlPreview?.classList.add('d-none');
            filePreview?.classList.add('d-none');
            urlInput.classList.remove('is-invalid');
            setClearFlag(true);
            if (urlDeleteBtn) urlDeleteBtn.classList.add('d-none');
            if (fileDeleteBtn) fileDeleteBtn.classList.add('d-none');
            if (form.id === 'registerForm') {
                writeRegisterAvatarDraft(null);
            }
            enableSave();
        }

        function showFile(src) {
            if (fileImg) fileImg.src = src;
            filePreview?.classList.remove('d-none');
            urlPreview?.classList.add('d-none');
            if (fileDeleteBtn) fileDeleteBtn.classList.remove('d-none');
            setClearFlag(false);
        }

        function showUrl(src) {
            if (urlImg) urlImg.src = src;
            urlPreview?.classList.remove('d-none');
            filePreview?.classList.add('d-none');
            if (urlDeleteBtn) urlDeleteBtn.classList.remove('d-none');
            setClearFlag(false);
        }

        function showInvalidUrl() {
            if (urlImg) urlImg.src = NOT_FOUND;
            urlPreview?.classList.remove('d-none');
            filePreview?.classList.add('d-none');
            urlInput.classList.add('is-invalid');
            if (urlDeleteBtn) urlDeleteBtn.classList.add('d-none');
            disableSave();
        }

        const initialAvatar = {
            type: null,
            value: null,
            name: null,
        };

        function restoreRegisterAvatarDraft() {
            const currentUser = currentRegisterUsername(form);
            let draft = readRegisterAvatarDraft();
            if (draft && draft.username && currentUser && draft.username !== currentUser) {
                writeRegisterAvatarDraft(null);
                draft = null;
            }
            if (draft && draft.type === 'file' && draft.dataUrl) {
                initialAvatar.type = 'file';
                initialAvatar.value = draft.dataUrl;
                initialAvatar.name = draft.name || 'avatar.png';
                showFile(draft.dataUrl);
                const file = dataUrlToFile(draft.dataUrl, draft.name, draft.mime);
                assignFileToInput(fileInput, file);
                return true;
            }
            if (draft && draft.type === 'url' && draft.url) {
                urlInput.value = draft.url;
                initialAvatar.type = 'url';
                initialAvatar.value = draft.url;
                initialAvatar.name = extractName(draft.url);
                showUrl(draft.url);
                return true;
            }
            const urlVal = (urlInput.value || '').trim();
            if (urlVal) {
                try { new URL(urlVal); } catch (_) { return false; }
                if (!ALLOWED_EXT.test(urlVal)) return false;
                initialAvatar.type = 'url';
                initialAvatar.value = urlVal;
                initialAvatar.name = extractName(urlVal);
                showUrl(urlVal);
                return true;
            }
            return false;
        }

        if (form.id === 'registerForm') {
            if (form.getAttribute('data-register-redisplay') === '1') {
                restoreRegisterAvatarDraft();
            } else {
                writeRegisterAvatarDraft(null);
            }
        } else if (window.CURRENT_AVATAR && window.CURRENT_AVATAR.file) {
            initialAvatar.type = 'file';
            initialAvatar.value = window.CURRENT_AVATAR.file;
            initialAvatar.name = extractName(window.CURRENT_AVATAR.file);
            showFile(initialAvatar.value);
        } else if (window.CURRENT_AVATAR && window.CURRENT_AVATAR.url) {
            initialAvatar.type = 'url';
            initialAvatar.value = window.CURRENT_AVATAR.url;
            initialAvatar.name = extractName(window.CURRENT_AVATAR.url);
            showUrl(initialAvatar.value);
        }

        function restoreInitialAvatar() {
            urlInput.classList.remove('is-invalid');
            urlPreview?.classList.add('d-none');

            if (!initialAvatar.type) {
                enableSave();
                return;
            }

            if (initialAvatar.type === 'file') {
                showFile(initialAvatar.value);
            } else {
                showUrl(initialAvatar.value);
            }

            enableSave();
        }

        let lastUrlValue = urlInput.value || '';
        urlInput.addEventListener('input', function () {
            const val = urlInput.value.trim();

            if (!val) {
                const hasFile = fileInput.files && fileInput.files.length;
                if (!hasFile && lastUrlValue) {
                    clearAvatarSelection();
                } else {
                    urlPreview?.classList.add('d-none');
                    setClearFlag(!hasFile);
                    urlInput.classList.remove('is-invalid');
                    enableSave();
                }
                lastUrlValue = val;
                if (initialAvatar.type) {
                    restoreInitialAvatar();
                }
                return;
            }

            try {
                new URL(val);
            } catch (e) {
                showInvalidUrl();
                return;
            }

            if (!ALLOWED_EXT.test(val)) {
                showInvalidUrl();
                return;
            }

            const img = new Image();
            img.onload = function () {
                urlInput.classList.remove('is-invalid');
                showUrl(val);
                enableSave();
                lastUrlValue = val;
                if (form.id === 'registerForm') {
                    writeRegisterAvatarDraft(registerAvatarDraftPayload(form, {
                        type: 'url',
                        url: val,
                        name: extractName(val),
                    }));
                }
            };
            img.onerror = showInvalidUrl;
            img.src = val;
        });

        if (fileTrigger && fileInput) {
            fileTrigger.addEventListener('click', function () {
                fileInput.click();
            });
        }

        fileInput.addEventListener('change', function () {
            const file = fileInput.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function (e) {
                initialAvatar.type = 'file';
                initialAvatar.value = e.target.result;
                initialAvatar.name = file.name;

                showFile(initialAvatar.value);
                urlInput.value = '';
                urlInput.classList.remove('is-invalid');
                enableSave();
                lastUrlValue = '';
                if (form.id === 'registerForm') {
                    writeRegisterAvatarDraft(registerAvatarDraftPayload(form, {
                        type: 'file',
                        dataUrl: e.target.result,
                        name: file.name,
                        mime: file.type || 'image/png',
                    }));
                }
            };
            reader.readAsDataURL(file);
        });

        form.querySelectorAll('.avatar-preview-delete').forEach(function (btn) {
            btn.addEventListener('click', function () {
                clearAvatarSelection();
            });
        });

        form.addEventListener('submit', function (e) {
            if (urlInput.classList.contains('is-invalid')) {
                e.preventDefault();
                disableSave();
                return;
            }
            if (form.id === 'registerForm') {
                const draft = readRegisterAvatarDraft();
                if (draft && draft.type) {
                    writeRegisterAvatarDraft(registerAvatarDraftPayload(form, draft));
                }
            }
        });
    }

    document.querySelectorAll('form[data-avatar-picker]').forEach(initAvatarPicker);

    try {
        if (new URLSearchParams(window.location.search).get('registered') === '1') {
            sessionStorage.removeItem(REGISTER_AVATAR_DRAFT_KEY);
        }
    } catch (_) { /* ignore */ }
})();



// avatar_remove.js
(function () {
    'use strict';

    const overlay = document.querySelector('.avatar-remove-overlay');
    if (!overlay) return;

    overlay.addEventListener('click', function () {
        fetch(this.dataset.url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(res => res.json())
            .then(data => {
                if (!data.success) return;

                const username = overlay.dataset.username || '';
                const safeUser = (window.CSS && CSS.escape)
                    ? CSS.escape(username)
                    : username.replace(/["\\]/g, '\\$&');

                const selector = username
                    ? '.user-avatar[data-username="' + safeUser + '"]'
                    : '.user-avatar';

                // 🔁 ОБНОВЛЯЕМ АВАТАРЫ ТОЛЬКО ЭТОГО ПОЛЬЗОВАТЕЛЯ
                document.querySelectorAll(selector).forEach(img => {
                    img.src = data.default_avatar;
                    img.classList.add('no_avatar');
                    img.removeAttribute('data-full');
                });

                // убираем сегмент удаления
                overlay.remove();

                var profileHdr = document.querySelector(
                    '.profile-page-header[data-profile-username="' + safeUser + '"]'
                );
                if (profileHdr) {
                    profileHdr.querySelectorAll('.profile-mobile-avatar-thumb').forEach(function (btn) {
                        btn.remove();
                    });
                }
            });
    });

    function getCookie(name) {
        return document.cookie
            .split('; ')
            .find(row => row.startsWith(name + '='))
            ?.split('=')[1];
    }
})();