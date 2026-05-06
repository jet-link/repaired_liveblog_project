// static/js/image_manage.js
(function () {
    'use strict';

    // tiny helpers
    function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
    function qsa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

    function getCookie(name) {
        const v = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith(name + '='));
        return v ? decodeURIComponent(v.split('=')[1]) : null;
    }

    function humanFileSize(size) {
        if (size < 1024) return size + ' B';
        if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
        return (size / (1024 * 1024)).toFixed(1) + ' MB';
    }

    document.addEventListener('DOMContentLoaded', function () {
        const mainInput = qs('#id_images') || qs('input[name="images"]');
        const preview = qs('#preview');
        const existingContainer = qs('#existingImages');
        const infoNode = qs('#imagesHelp');
        const addMoreBtn = qs('#btnAddMoreImages');
        const itemForms = [qs('#itemForm'), qs('#itemEditForm')].filter(Boolean);

        const MAX = 10;
        const MAX_POST_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB total post weight
        // Keep in sync with smart_blog.image_utils.ALLOWED_MIME_TYPES (server rejects others)
        const ALLOWED = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp'];

        if (!mainInput || (!preview && !existingContainer)) {
            // nothing to do on pages without the file UI
            return;
        }

        const fileTrigger = document.querySelector('.item-images-file-trigger');
        if (fileTrigger && mainInput) {
            fileTrigger.addEventListener('click', function () {
                mainInput.click();
            });
        }

        // ----- helpers -----
        function setInfo(text, isWarning) {
            if (!infoNode) return;
            infoNode.textContent = text;
            if (isWarning) infoNode.classList.add('text-danger'); else infoNode.classList.remove('text-danger');
        }

        function countThumbnails() {
            const previewCount = preview ? preview.querySelectorAll('.image-preview-item').length : 0;
            const existingCount = existingContainer ? existingContainer.querySelectorAll('.existing-image').length : 0;
            const filesCount = (mainInput.files && mainInput.files.length) ? mainInput.files.length : 0;
            return { previewCount, existingCount, filesCount, total: previewCount + existingCount + filesCount };
        }

        // count existing images (DOM) that are currently present (not necessarily actual DB count)
        function countExistingDOM() {
            return existingContainer ? existingContainer.querySelectorAll('.existing-image').length : 0;
        }

        // count how many existing images user has marked for deletion (we attach hidden inputs named delete_images)
        function countMarkedForDelete() {
            const inputs = document.querySelectorAll('input[name="delete_images"]');
            return inputs ? inputs.length : 0;
        }

        // compute resulting images count after apply delete marks + new files selected
        function computeResultingImagesCount() {
            const existingCount = countExistingDOM();
            const markedDelete = countMarkedForDelete();
            const remainingExisting = Math.max(0, existingCount - markedDelete);
            const newFiles = (mainInput.files && mainInput.files.length) ? mainInput.files.length : 0;
            return remainingExisting + newFiles;
        }

        function refreshAddMoreVisibility() {
            if (!addMoreBtn) return;
            const cnt = countThumbnails();
            // show button only if there is at least one thumbnail OR at least one selected file
            if (cnt.total > 0) addMoreBtn.style.display = 'inline-flex';
            // if (cnt.total > 0) addMoreBtn.style.display = 'flex';
            else addMoreBtn.style.display = 'none';
        }

        // create preview DOM block (used for client previews)
        function makePreviewBlock(srcOrFileName, sizeText, idOrTempId) {
            const wrap = document.createElement('div');
            wrap.className = 'image-preview-item existing-image position-relative text-center';
            wrap.style.width = '150px';

            const img = document.createElement('img');
            img.style.width = '150px';
            img.style.height = '130px';
            img.style.objectFit = 'cover';
            img.style.borderRadius = '4px';
            img.style.display = 'block';
            if (srcOrFileName && typeof srcOrFileName === 'string') img.src = srcOrFileName;

            const meta = document.createElement('div');
            meta.style.marginTop = '10px';
            const nameNode = document.createElement('small');
            nameNode.textContent = idOrTempId || (srcOrFileName && srcOrFileName.name ? srcOrFileName.name : srcOrFileName);
            nameNode.style.display = 'block';

            const sizeNode = document.createElement('small');
            sizeNode.className = 'text-muted d-block';
            sizeNode.textContent = sizeText || '';

            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm btn-danger btn-delete-image position-absolute';
            btn.style.right = '5px';
            btn.style.top = '5px';
            btn.style.fontSize = '.7rem';
            btn.innerHTML = '<i class="fa fa-times"></i>';

            wrap.appendChild(img);
            meta.appendChild(nameNode);
            meta.appendChild(sizeNode);
            wrap.appendChild(meta);
            wrap.appendChild(btn);

            return wrap;
        }

        // render mainInput.files -> preview container
        function renderFilesFromInput() {
            if (!preview) return;
            preview.innerHTML = '';
            const files = Array.from(mainInput.files || []);
            files.forEach(f => {
                const node = makePreviewBlock('', humanFileSize(f.size), f.name);
                const img = node.querySelector('img');
                const reader = new FileReader();
                reader.onload = function (e) { img.src = e.target.result; };
                reader.readAsDataURL(f);

                // mark remove action for this node (client-only)
                const btn = node.querySelector('.btn-delete-image');
                btn.dataset.action = 'remove-temp';
                preview.appendChild(node);
            });
            updateInfo();
            refreshAddMoreVisibility();
        }

        function updateInfo() {
            const count = (mainInput.files && mainInput.files.length) || 0;
            const cntObj = countThumbnails();
            setInfo(
                `You can upload up to ${MAX} images per post · selected ${count} new file(s).`,
                (cntObj.total > MAX),
            );
            checkPostSizeWarning();
        }

        function computeTotalPostSize() {
            var total = 0;
            var imgFiles = Array.from(mainInput.files || []);
            imgFiles.forEach(function (f) { total += f.size; });
            _videoQueue.forEach(function (v) { total += v.file.size; });
            return total;
        }

        function checkPostSizeWarning() {
            var warn = document.getElementById('postSizeWarning');
            if (!warn) return;
            var total = computeTotalPostSize();
            if (total > MAX_POST_SIZE_BYTES) {
                var mb = (total / (1024 * 1024)).toFixed(1);
                warn.textContent = 'Total file size is ' + mb + ' MB. Posts over 50 MB may cause errors. Remove some files.';
                warn.hidden = false;
            } else {
                warn.hidden = true;
            }
        }
        _checkPostSizeWarning = checkPostSizeWarning;

        function mergeFilesToMainInput(newFiles) {
            const current = Array.from(mainInput.files || []);
            const filteredNew = newFiles.filter(f => ALLOWED.includes(f.type));
            const merged = current.concat(filteredNew);

            if (merged.length > MAX) {
                const kept = merged.slice(0, MAX);
                const dt = new DataTransfer();
                kept.forEach(f => dt.items.add(f));
                mainInput.files = dt.files;
                renderFilesFromInput();
                setInfo(`You can upload up to ${MAX} images per post. Extra files were not added.`, true);
                refreshAddMoreVisibility();
                return;
            }

            const dt = new DataTransfer();
            merged.forEach(f => dt.items.add(f));
            mainInput.files = dt.files;
            renderFilesFromInput();
            refreshAddMoreVisibility();
        }

        // transient temporary input for "add more"
        let tmpInput = null;
        if (addMoreBtn) {
            try { addMoreBtn.style.display = 'none'; } catch (e) { }
            addMoreBtn.addEventListener('click', function (e) {
                e.preventDefault();
                if (!tmpInput) {
                    tmpInput = document.createElement('input');
                    tmpInput.type = 'file';
                    tmpInput.accept = 'image/*';
                    tmpInput.multiple = true;
                    tmpInput.style.display = 'none';
                    document.body.appendChild(tmpInput);

                    tmpInput.addEventListener('change', function () {
                        const files = Array.from(tmpInput.files || []);
                        if (!files.length) return;
                        const currentCount = (mainInput.files && mainInput.files.length) || 0;
                        if (currentCount + files.length > MAX) {
                            const allowedCount = Math.max(0, MAX - currentCount);
                            if (allowedCount === 0) {
                                setInfo(`You can upload up to ${MAX} images per post. Remove some first to add more.`, true);
                                tmpInput.value = '';
                                return;
                            }
                            const toAdd = files.slice(0, allowedCount);
                            mergeFilesToMainInput(toAdd);
                            setInfo(`Only ${allowedCount} files were added to reach the maximum ${MAX}.`, true);
                        } else {
                            mergeFilesToMainInput(files);
                        }
                        tmpInput.value = '';
                    });
                }
                tmpInput.click();
            });
        }

        // main input change (user selected files)
        mainInput.addEventListener('change', function () {
            let files = Array.from(mainInput.files || []);
            if (files.length > MAX) {
                files = files.slice(0, MAX);
                const dt = new DataTransfer();
                files.forEach(f => dt.items.add(f));
                mainInput.files = dt.files;
                setInfo(`You can upload up to ${MAX} images per post. Extra files were removed.`, true);
            }

            const bad = files.filter(f => !ALLOWED.includes(f.type));
            if (bad.length) {
                files = files.filter(f => ALLOWED.includes(f.type));
                const dt = new DataTransfer();
                files.forEach(f => dt.items.add(f));
                mainInput.files = dt.files;
                setInfo(`Removed unsupported types (${bad.map(b => b.name).join(', ')})`, true);
            }

            renderFilesFromInput();
        });

        // GLOBAL click listener: handles both client-side removal and AJAX delete for existing images
        document.addEventListener('click', function (ev) {
            const btn = ev.target.closest && ev.target.closest('button.btn-delete-image');
            if (!btn) return;

            ev.preventDefault();

            // Case: AJAX delete existing image (button must have data-delete-url)
            const deleteUrl = btn.dataset.deleteUrl;
            const imageId = btn.dataset.imageId;
            if (deleteUrl) {
                btn.disabled = true;
                btn.classList.add('opacity-75');
                (async function () {
                    try {
                        const resp = await fetch(deleteUrl, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': getCookie('csrftoken'),
                                'X-Requested-With': 'XMLHttpRequest',
                                'Accept': 'application/json'
                            },
                            credentials: 'same-origin'
                        });
                        const data = await resp.json().catch(() => null);
                        if (resp.ok && data && data.success) {
                            const node = document.getElementById('image-' + data.image_id) || btn.closest('.existing-image');
                            if (node) {
                                node.style.transition = 'opacity .15s ease, transform .15s ease';
                                node.style.opacity = '0';
                                node.style.transform = 'scale(.98)';
                                setTimeout(function () {
                                    node.remove();
                                    updateInfo();
                                    refreshAddMoreVisibility();
                                }, 160);
                            } else {
                                updateInfo();
                                refreshAddMoreVisibility();
                            }
                        } else {
                            console.warn('Delete failed', data && data.error);
                            btn.disabled = false;
                            btn.classList.remove('opacity-75');
                        }
                    } catch (err) {
                        console.error('Image delete error', err);
                        btn.disabled = false;
                        btn.classList.remove('opacity-75');
                    }
                })();
                return;
            }

            // Case: client-side removal of file selected in input (button dataset.action === 'remove-temp' OR it's inside preview)
            const item = btn.closest('.image-preview-item');
            if (!item) return;
            const filenameNode = item.querySelector('small');
            const filename = filenameNode ? filenameNode.textContent : null;
            const cur = Array.from(mainInput.files || []);
            const dt = new DataTransfer();
            let removed = false;
            for (let f of cur) {
                if (!removed && filename && f.name === filename) {
                    removed = true;
                    continue;
                }
                dt.items.add(f);
            }
            if (!removed) {
                // fallback by index
                const previews = qsa('.image-preview-item', preview);
                const idx = previews.indexOf(item);
                Array.from(mainInput.files || []).forEach((f, i) => { if (i !== idx) dt.items.add(f); });
            }
            mainInput.files = dt.files;

            // animate and remove DOM
            item.style.transition = 'opacity .15s ease, transform .15s ease';
            item.style.opacity = '0';
            item.style.transform = 'scale(.98)';
            setTimeout(function () {
                item.remove();
                updateInfo();
                refreshAddMoreVisibility();
            }, 160);
        });

        // initial render (bfcache or page load)
        renderFilesFromInput();
        refreshAddMoreVisibility();

    });

    // Shared references (accessible across DOMContentLoaded blocks)
    var _videoQueue = [];
    var _checkPostSizeWarning = function () {};

    // Video upload handling — all videos go through chunked upload
    document.addEventListener('DOMContentLoaded', function () {
        var videoInput = document.getElementById('id_videos');
        var addVideoBtn = document.getElementById('btnAddVideo');
        var videoPreview = document.getElementById('videoPreview');
        var MAX_VIDEOS = 1;
        var ALLOWED_VIDEO = ['video/mp4', 'video/webm', 'video/quicktime'];
        var CHUNK_SIZE = 2 * 1024 * 1024; // 2 MB per chunk

        var videoQueue = _videoQueue;
        var uploading = false;

        if (addVideoBtn && videoInput) {
            addVideoBtn.addEventListener('click', function () {
                videoInput.click();
            });
        }

        if (videoInput) {
            videoInput.addEventListener('change', function () {
                var files = Array.from(videoInput.files || []);
                files.forEach(function (f) {
                    if (videoQueue.length >= MAX_VIDEOS) return;
                    if (ALLOWED_VIDEO.indexOf(f.type) === -1) return;
                    videoQueue.push({
                        file: f,
                        id: generateUploadId(),
                        status: 'pending',
                        progress: 0,
                        uploadId: null
                    });
                });
                // Clear the file input — videos will go through chunked upload only
                videoInput.value = '';
                var dt = new DataTransfer();
                videoInput.files = dt.files;

                renderVideoPreview();
                _checkPostSizeWarning();
                processUploadQueue();
            });
        }

        function generateUploadId() {
            return 'vu-' + Date.now() + '-' + Math.random().toString(36).substring(2, 10);
        }

        function getVideoThumbnail(file, callback) {
            var video = document.createElement('video');
            video.preload = 'metadata';
            video.muted = true;
            video.playsInline = true;
            var url = URL.createObjectURL(file);
            video.src = url;
            video.onloadeddata = function () {
                video.currentTime = 0.1;
            };
            video.onseeked = function () {
                try {
                    var canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth || 320;
                    canvas.height = video.videoHeight || 240;
                    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                    callback(canvas.toDataURL('image/jpeg', 0.7));
                } catch (e) {
                    callback(null);
                }
                URL.revokeObjectURL(url);
            };
            video.onerror = function () {
                callback(null);
                URL.revokeObjectURL(url);
            };
        }

        function processUploadQueue() {
            if (uploading) return;
            var next = null;
            for (var k = 0; k < videoQueue.length; k++) {
                if (videoQueue[k].status === 'pending') { next = videoQueue[k]; break; }
            }
            if (!next) return;

            uploading = true;
            next.status = 'uploading';
            renderVideoPreview();

            uploadChunked(next.file, next.id,
                function (pct) {
                    next.progress = pct;
                    updateVideoItemUI(next);
                },
                function (resp) {
                    next.status = 'done';
                    next.progress = 100;
                    next.uploadId = resp.upload_id;
                    uploading = false;
                    updateVideoItemUI(next);
                    processUploadQueue();
                },
                function (err) {
                    next.status = 'error';
                    uploading = false;
                    updateVideoItemUI(next);
                    processUploadQueue();
                }
            );
        }

        function uploadChunked(file, uploadId, progressCb, doneCb, errCb) {
            var totalChunks = Math.ceil(file.size / CHUNK_SIZE);
            var csrfToken = getCookie('csrftoken');
            var chunkIndex = 0;
            var uploadUrl = '/blog/api/video-chunk-upload/';

            function sendNext() {
                if (chunkIndex >= totalChunks) return;
                var start = chunkIndex * CHUNK_SIZE;
                var end = Math.min(start + CHUNK_SIZE, file.size);
                var blob = file.slice(start, end);

                var fd = new FormData();
                fd.append('chunk', blob, 'chunk');
                fd.append('upload_id', uploadId);
                fd.append('chunk_index', chunkIndex);
                fd.append('total_chunks', totalChunks);
                fd.append('filename', file.name);

                var xhr = new XMLHttpRequest();
                xhr.open('POST', uploadUrl, true);
                xhr.setRequestHeader('X-CSRFToken', csrfToken);
                xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

                xhr.onload = function () {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        var resp;
                        try { resp = JSON.parse(xhr.responseText); } catch (e) { resp = {}; }
                        chunkIndex++;
                        var pct = Math.round((chunkIndex / totalChunks) * 100);
                        if (progressCb) progressCb(pct);
                        if (resp.status === 'complete') {
                            if (doneCb) doneCb(resp);
                        } else {
                            sendNext();
                        }
                    } else {
                        if (errCb) errCb(xhr.responseText);
                    }
                };
                xhr.onerror = function () { if (errCb) errCb('Network error'); };
                xhr.send(fd);
            }

            sendNext();
        }

        function removeFromQueue(idx) {
            var removed = videoQueue.splice(idx, 1);
            if (removed[0] && removed[0]._dom && removed[0]._dom.wrap.parentNode) {
                removed[0]._dom.wrap.remove();
            }
            renderVideoPreview();
            _checkPostSizeWarning();
        }

        function updateVideoItemUI(entry) {
            if (!entry._dom) return;
            var bar = entry._dom.progressBar;
            var status = entry._dom.statusEl;
            var barColor = entry.status === 'done' ? '#27ae60' : entry.status === 'error' ? '#e74c3c' : 'var(--btn-primary-bg,#273c75)';
            bar.style.width = entry.progress + '%';
            bar.style.background = barColor;
            if (entry.status === 'pending') status.textContent = 'Waiting...';
            else if (entry.status === 'uploading') status.textContent = entry.progress + '%';
            else if (entry.status === 'done') status.textContent = 'Ready';
            else if (entry.status === 'error') status.textContent = 'Upload failed';

            // Add or remove hidden input
            var existing = entry._dom.wrap.querySelector('input[name="chunked_video_ids"]');
            if (entry.status === 'done' && entry.uploadId && !existing) {
                var hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'chunked_video_ids';
                hidden.value = entry.uploadId;
                entry._dom.wrap.appendChild(hidden);
            }
        }

        function renderVideoPreview() {
            if (!videoPreview) return;
            videoPreview.innerHTML = '';

            videoQueue.forEach(function (entry, i) {
                // If DOM already built, re-append and update
                if (entry._dom) {
                    videoPreview.appendChild(entry._dom.wrap);
                    updateVideoItemUI(entry);
                    return;
                }

                var f = entry.file;
                var wrap = document.createElement('div');
                wrap.className = 'video-preview-item existing-video position-relative text-center';
                wrap.style.width = '150px';

                var thumb = document.createElement('div');
                thumb.className = 'existing-video__thumb';
                thumb.innerHTML = '<i class="fa fa-video-camera"></i><small class="d-block text-muted mt-1">' + f.name.substring(0, 20) + '</small><small class="text-muted d-block">' + (f.size / (1024 * 1024)).toFixed(1) + ' MB</small>';
                wrap.appendChild(thumb);

                var progressWrap = document.createElement('div');
                progressWrap.className = 'video-upload-progress mt-1';
                progressWrap.style.cssText = 'width:100%;height:6px;background:var(--bg-muted,#eee);border-radius:3px;overflow:hidden;';
                var progressBar = document.createElement('div');
                progressBar.className = 'video-upload-progress__bar';
                progressBar.style.cssText = 'width:0%;height:100%;transition:width .15s ease;border-radius:3px;';
                progressWrap.appendChild(progressBar);
                wrap.appendChild(progressWrap);

                var statusEl = document.createElement('small');
                statusEl.className = 'video-upload-status text-muted d-block mt-1';
                statusEl.style.fontSize = '.65rem';
                wrap.appendChild(statusEl);

                entry._dom = { wrap: wrap, progressBar: progressBar, statusEl: statusEl };
                updateVideoItemUI(entry);

                getVideoThumbnail(f, function (dataUrl) {
                    if (dataUrl && thumb.parentNode) {
                        thumb.innerHTML = '';
                        var img = document.createElement('img');
                        img.src = dataUrl;
                        img.style.cssText = 'width:150px;height:100px;object-fit:cover;border-radius:4px;display:block;';
                        img.alt = 'Video preview';
                        thumb.appendChild(img);
                        var meta = document.createElement('div');
                        meta.innerHTML = '<small class="d-block text-muted mt-1">' + f.name.substring(0, 20) + '</small><small class="text-muted d-block">' + (f.size / (1024 * 1024)).toFixed(1) + ' MB</small>';
                        thumb.appendChild(meta);
                    }
                });

                var btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-sm btn-danger btn-delete-video position-absolute';
                btn.style.right = '5px';
                btn.style.top = '5px';
                btn.style.fontSize = '.7rem';
                btn.innerHTML = '<i class="fa fa-times"></i>';
                (function (idx) {
                    btn.addEventListener('click', function () { removeFromQueue(idx); });
                })(i);
                wrap.appendChild(btn);

                videoPreview.appendChild(wrap);
            });
        }

        // Block form submission while any video is still uploading.
        // Use capture phase so this fires before forms_handler.js (which sends AJAX).
        var itemForm = document.getElementById('itemForm') || document.getElementById('itemEditForm');
        if (itemForm) {
            itemForm.addEventListener('submit', function (e) {
                var hasPending = videoQueue.some(function (v) {
                    return v.status === 'pending' || v.status === 'uploading';
                });
                if (hasPending) {
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    alert('Please wait for all video uploads to finish before submitting.');
                    return false;
                }
                // Ensure the file input is empty so the AJAX handler
                // doesn't try to send raw video bytes
                if (videoInput) {
                    try {
                        var dt = new DataTransfer();
                        videoInput.files = dt.files;
                    } catch (ex) { videoInput.value = ''; }
                }
            }, true);
        }
    });

    // Generate poster thumbnails for existing videos on edit page
    document.addEventListener('DOMContentLoaded', function () {
        var thumbs = document.querySelectorAll('.existing-video__thumb--poster[data-video-src]');
        if (!thumbs.length) return;

        thumbs.forEach(function (thumbEl) {
            var src = thumbEl.getAttribute('data-video-src');
            if (!src) return;
            var video = document.createElement('video');
            video.preload = 'metadata';
            video.muted = true;
            video.playsInline = true;
            video.crossOrigin = 'anonymous';
            video.src = src;
            video.onloadeddata = function () { video.currentTime = 0.1; };
            video.onseeked = function () {
                try {
                    var canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth || 320;
                    canvas.height = video.videoHeight || 240;
                    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                    var dataUrl = canvas.toDataURL('image/jpeg', 0.7);
                    if (dataUrl) {
                        var label = thumbEl.querySelector('small');
                        var labelText = label ? label.textContent : '';
                        thumbEl.innerHTML = '';
                        var img = document.createElement('img');
                        img.src = dataUrl;
                        img.alt = 'Video poster';
                        img.style.cssText = 'width:150px;height:100px;object-fit:cover;border-radius:4px;display:block;';
                        thumbEl.appendChild(img);
                        if (labelText) {
                            var sm = document.createElement('small');
                            sm.className = 'd-block text-muted mt-1';
                            sm.textContent = labelText;
                            thumbEl.appendChild(sm);
                        }
                    }
                } catch (e) { /* cross-origin or other error — keep icon fallback */ }
            };
            video.onerror = function () { /* keep icon fallback */ };
        });
    });

    // Video mark-for-delete on edit page
    document.addEventListener('DOMContentLoaded', function () {
        var existingVideos = document.getElementById('existingVideos');
        if (!existingVideos) return;

        var deleteVideoContainer = document.getElementById('deleteVideoInputs') || (function () {
            var d = document.createElement('div');
            d.id = 'deleteVideoInputs';
            existingVideos.insertAdjacentElement('afterend', d);
            return d;
        })();

        existingVideos.addEventListener('click', function (ev) {
            var btn = ev.target.closest && ev.target.closest('button.btn-mark-delete-video');
            if (!btn) return;
            ev.preventDefault();
            var videoId = btn.dataset.videoId;
            if (!videoId) return;
            var wrapper = btn.closest('.existing-video');
            if (!wrapper) return;
            var isMarked = btn.getAttribute('aria-pressed') === 'true';
            if (!isMarked) {
                wrapper.classList.add('marked-for-delete');
                btn.innerHTML = '<i class="fa fa-undo" aria-hidden="true"></i>';
                btn.setAttribute('aria-pressed', 'true');
                btn.title = 'Unmark deletion';
                var hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'delete_videos';
                hidden.value = videoId;
                hidden.id = 'delete-video-input-' + videoId;
                deleteVideoContainer.appendChild(hidden);
            } else {
                wrapper.classList.remove('marked-for-delete');
                btn.innerHTML = '<i class="fa fa-times"></i>';
                btn.setAttribute('aria-pressed', 'false');
                btn.title = 'Mark for deletion';
                var hid = document.getElementById('delete-video-input-' + videoId);
                if (hid) hid.remove();
            }
        });
    });

    // second DOMContentLoaded block remains, for existingContainer mark/unmark logic
    document.addEventListener('DOMContentLoaded', function () {
        const existingContainer = document.getElementById('existingImages');
        if (!existingContainer) return;

        const deleteInputsContainer = document.getElementById('deleteInputs') || (function () {
            const d = document.createElement('div');
            d.id = 'deleteInputs';
            existingContainer.insertAdjacentElement('afterend', d);
            return d;
        })();

        // toggle mark
        existingContainer.addEventListener('click', function (ev) {
            const btn = ev.target.closest && ev.target.closest('button.btn-mark-delete');
            if (!btn) return;
            ev.preventDefault();

            const imageId = btn.dataset.imageId;
            if (!imageId) return;

            const wrapper = btn.closest('.existing-image');
            if (!wrapper) return;

            const isMarked = btn.getAttribute('aria-pressed') === 'true';

            if (!isMarked) {
                // mark visually (dimming via CSS on img / .existing-video__thumb only)
                wrapper.classList.add('marked-for-delete');
                btn.innerHTML = '<i class="fa fa-undo" aria-hidden="true"></i>';
                btn.setAttribute('aria-pressed', 'true');
                btn.title = 'Unmark deletion';

                // create hidden input to be submitted with the form
                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.name = 'delete_images';
                hidden.value = imageId;
                hidden.id = 'delete-input-' + imageId;
                deleteInputsContainer.appendChild(hidden);
            } else {
                // unmark
                wrapper.classList.remove('marked-for-delete');
                btn.innerHTML = '<i class="fa fa-times"></i>';
                btn.setAttribute('aria-pressed', 'false');
                btn.title = 'Mark for deletion';

                // remove hidden input
                const hid = document.getElementById('delete-input-' + imageId);
                if (hid) hid.remove();
            }
        });
    });
})();