// Gallery progress indicator: bar + fade dots (opacity by distance from bar).
(function (global) {
    'use strict';

    var DEFAULT_DURATION_MS = 7000;
    var MAX_DOTS = 4;
    var MIN_DOT_OPACITY = 0.22;

    function prefersReducedMotion() {
        return global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    /**
     * Opacity: nearest to bar = 1, farther = lower; beyond window = hidden.
     * @param {number} distance 1 = adjacent to bar
     * @param {number} maxOnSide
     */
    function opacityForDistance(distance, maxOnSide) {
        if (distance < 1) return 1;
        if (maxOnSide < 1) return 1;
        if (distance > maxOnSide) return 0;
        var t = (distance - 1) / maxOnSide;
        return MIN_DOT_OPACITY + (1 - MIN_DOT_OPACITY) * (1 - t);
    }

    /**
     * @param {number} currentIndex
     * @param {number} total
     * @returns {{ type: string, slideIndex: number, distance: number, opacity: number }[]}
     */
    function computeFadeSlots(currentIndex, total) {
        if (total <= 0) return [];
        if (total === 1) {
            return [{ type: 'bar', slideIndex: 0, distance: 0, opacity: 1 }];
        }

        var leftCount = 0;
        var rightCount = 0;

        if (currentIndex === 0) {
            rightCount = Math.min(total - 1, MAX_DOTS);
        } else if (currentIndex === total - 1) {
            leftCount = Math.min(currentIndex, MAX_DOTS);
        } else {
            leftCount = Math.min(currentIndex, MAX_DOTS);
            rightCount = Math.min(total - currentIndex - 1, MAX_DOTS);
            while (leftCount + 1 + rightCount > MAX_DOTS + 1) {
                if (rightCount > leftCount) rightCount -= 1;
                else if (leftCount > 0) leftCount -= 1;
                else rightCount -= 1;
            }
        }

        var slots = [];
        var l;
        var r;

        for (l = leftCount; l >= 1; l--) {
            slots.push({
                type: 'viewed',
                slideIndex: currentIndex - l,
                distance: l,
                opacity: opacityForDistance(l, leftCount)
            });
        }

        slots.push({
            type: 'bar',
            slideIndex: currentIndex,
            distance: 0,
            opacity: 1
        });

        for (r = 1; r <= rightCount; r++) {
            slots.push({
                type: 'next',
                slideIndex: currentIndex + r,
                distance: r,
                opacity: opacityForDistance(r, rightCount)
            });
        }

        return slots;
    }

    function GalleryProgressIndicator(hostEl) {
        this.hostEl = hostEl;
        this.rootEl = null;
        this.trackEl = null;
        this.fillEl = null;
        this.index = 0;
        this.total = 0;
        this.durationMs = DEFAULT_DURATION_MS;
        this.autoNextCb = null;
        this.seekCb = null;
        this.timerId = null;
        this._autoNextFired = false;
        this._progressGen = 0;
        this._slotSignature = '';
        this._lastSlotCount = 0;
    }

    GalleryProgressIndicator.prototype._cancelProgress = function () {
        this._progressGen += 1;
        this._clearTimer();
        this._autoNextFired = false;
    };

    GalleryProgressIndicator.prototype._resetFillVisual = function () {
        if (!this.fillEl) return;
        var barWrap = this.fillEl.closest('.gallery-progress__slot--bar');
        if (barWrap) barWrap.setAttribute('aria-valuenow', '0');
        this.fillEl.classList.remove('is-animating', 'is-full');
        this.fillEl.style.transition = 'none';
        this.fillEl.style.transform = 'scaleX(0)';
        void this.fillEl.offsetWidth;
    };

    GalleryProgressIndicator.prototype.mount = function () {
        if (!this.hostEl) return;
        this.hostEl.innerHTML = '';
        this.rootEl = document.createElement('div');
        this.rootEl.className = 'gallery-progress';
        this.rootEl.setAttribute('role', 'group');
        this.trackEl = document.createElement('div');
        this.trackEl.className = 'gallery-progress__track';
        this.rootEl.appendChild(this.trackEl);
        this.hostEl.appendChild(this.rootEl);

        var self = this;
        this.trackEl.addEventListener('click', function (e) {
            var btn = e.target.closest('.gallery-progress__slot:not([disabled])');
            if (!btn || !self.trackEl.contains(btn)) return;
            if (Number(btn.dataset.hidden) === 1) return;
            e.preventDefault();
            e.stopPropagation();
            var target = Number(btn.dataset.slideIndex);
            if (isNaN(target) || target === self.index || !self.seekCb) return;
            var dir = target > self.index ? 1 : -1;
            if (self.total > 1) {
                var fwd = (target - self.index + self.total) % self.total;
                var back = (self.index - target + self.total) % self.total;
                dir = fwd <= back ? 1 : -1;
            }
            self.seekCb(target, dir);
        });
    };

    GalleryProgressIndicator.prototype._clearTimer = function () {
        if (this.timerId) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }
    };

    GalleryProgressIndicator.prototype.cancelProgress = function () {
        this._cancelProgress();
    };

    GalleryProgressIndicator.prototype.stop = function () {
        this._cancelProgress();
        this._resetFillVisual();
    };

    GalleryProgressIndicator.prototype.onAutoNext = function (cb) {
        this.autoNextCb = typeof cb === 'function' ? cb : null;
    };

    GalleryProgressIndicator.prototype.onSeek = function (cb) {
        this.seekCb = typeof cb === 'function' ? cb : null;
    };

    GalleryProgressIndicator.prototype._slotSignatureFrom = function (slots) {
        return slots.map(function (s) {
            return s.type + ':' + s.slideIndex + ':' + s.opacity.toFixed(2);
        }).join('|');
    };

    GalleryProgressIndicator.prototype._buildSlotVisual = function () {
        var visual = document.createElement('span');
        visual.className = 'gallery-progress__slot-visual';
        visual.setAttribute('aria-hidden', 'true');

        var dot = document.createElement('span');
        dot.className = 'gallery-progress__dot-mark';

        var track = document.createElement('span');
        track.className = 'gallery-progress__bar-track';
        var fill = document.createElement('span');
        fill.className = 'gallery-progress__bar-fill';
        track.appendChild(fill);

        visual.appendChild(dot);
        visual.appendChild(track);
        return visual;
    };

    GalleryProgressIndicator.prototype._ensureSlotVisual = function (btn) {
        if (!btn.querySelector('.gallery-progress__slot-visual')) {
            btn.appendChild(this._buildSlotVisual());
        }
    };

    GalleryProgressIndicator.prototype._setSlotType = function (btn, type) {
        btn.classList.remove(
            'gallery-progress__slot--viewed',
            'gallery-progress__slot--next',
            'gallery-progress__slot--bar'
        );
        btn.classList.add('gallery-progress__slot--' + type);
    };

    GalleryProgressIndicator.prototype._applySlotPresentation = function (btn, slot) {
        var opacity = slot.opacity;
        var hidden = opacity < 0.12;
        btn.style.setProperty('--slot-fade', String(opacity));
        btn.style.pointerEvents = hidden ? 'none' : '';
        btn.dataset.hidden = hidden ? '1' : '0';
        btn.dataset.distance = String(slot.distance);
        btn.classList.toggle('gallery-progress__slot--faded', opacity < 0.55 && opacity >= 0.12);
        btn.classList.toggle('gallery-progress__slot--ghost', hidden);
        btn.classList.toggle('gallery-progress__slot--near', slot.distance === 1);
        btn.classList.toggle('gallery-progress__slot--far', slot.distance >= 3);
    };

    GalleryProgressIndicator.prototype._createSlotButton = function (slot) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'gallery-progress__slot gallery-progress__slot--' + slot.type;
        btn.dataset.slideIndex = String(slot.slideIndex);
        if (slot.type === 'bar') {
            btn.setAttribute('aria-current', 'true');
            btn.setAttribute('aria-label', 'Current slide ' + (slot.slideIndex + 1));
            btn.disabled = true;
        } else {
            btn.setAttribute('aria-label', 'Go to slide ' + (slot.slideIndex + 1));
        }
        btn.appendChild(this._buildSlotVisual());
        this._applySlotPresentation(btn, slot);
        return btn;
    };

    GalleryProgressIndicator.prototype._renderSlots = function (slots) {
        this.trackEl.innerHTML = '';
        var frag = document.createDocumentFragment();
        slots.forEach(function (slot) {
            frag.appendChild(this._createSlotButton(slot));
        }, this);
        this.trackEl.appendChild(frag);
    };

    GalleryProgressIndicator.prototype._patchSlots = function (slots) {
        var buttons = this.trackEl.querySelectorAll('.gallery-progress__slot');
        slots.forEach(function (slot, i) {
            var btn = buttons[i];
            if (!btn) return;
            var isBar = slot.type === 'bar';
            this._ensureSlotVisual(btn);
            this._setSlotType(btn, slot.type);
            btn.dataset.slideIndex = String(slot.slideIndex);
            if (isBar) {
                btn.setAttribute('aria-current', 'true');
                btn.setAttribute('aria-label', 'Current slide ' + (slot.slideIndex + 1));
                btn.disabled = true;
            } else {
                btn.removeAttribute('aria-current');
                btn.setAttribute('aria-label', 'Go to slide ' + (slot.slideIndex + 1));
                btn.disabled = false;
            }
            this._applySlotPresentation(btn, slot);
        }, this);
    };

    GalleryProgressIndicator.prototype.update = function (opts) {
        opts = opts || {};
        var prevIndex = this.index;
        var direction = opts.direction || 0;
        if (direction === 0 && typeof prevIndex === 'number' && opts.index !== prevIndex) {
            if (this.total > 1) {
                var fwd = (Number(opts.index) - prevIndex + this.total) % this.total;
                var back = (prevIndex - Number(opts.index) + this.total) % this.total;
                direction = fwd <= back ? 1 : -1;
            } else {
                direction = Number(opts.index) > prevIndex ? 1 : -1;
            }
        }

        this.index = Math.max(0, Number(opts.index) || 0);
        this.total = Math.max(0, Number(opts.total) || 0);

        if (!this.rootEl) this.mount();
        if (!this.rootEl || !this.trackEl) return;

        if (this.total <= 1) {
            this.stop();
            if (this.hostEl) {
                this.hostEl.hidden = true;
                this.hostEl.setAttribute('aria-hidden', 'true');
            }
            return;
        }

        if (this.hostEl) {
            this.hostEl.hidden = false;
            this.hostEl.removeAttribute('aria-hidden');
        }

        var slots = computeFadeSlots(this.index, this.total);
        var signature = this._slotSignatureFrom(slots);
        var slideNum = this.index + 1;

        this.rootEl.setAttribute(
            'aria-label',
            'Gallery progress, slide ' + slideNum + ' of ' + this.total
        );

        var canPatch = this._lastSlotCount === slots.length &&
            this.trackEl.children.length === slots.length;

        if (canPatch) {
            this._patchSlots(slots);
        } else {
            this._renderSlots(slots);
        }
        this._slotSignature = signature;
        this._lastSlotCount = slots.length;

        this.fillEl = this.trackEl.querySelector(
            '.gallery-progress__slot--bar .gallery-progress__bar-fill'
        );
    };

    GalleryProgressIndicator.prototype.startProgress = function (durationMs) {
        var self = this;
        this._cancelProgress();
        var gen = this._progressGen;

        if (!this.fillEl || this.total <= 1) return;

        this.durationMs = durationMs || DEFAULT_DURATION_MS;
        var reduced = prefersReducedMotion();
        var barRole = this.fillEl.closest('.gallery-progress__slot--bar');
        if (barRole) {
            barRole.setAttribute('role', 'progressbar');
            barRole.setAttribute('aria-valuemin', '0');
            barRole.setAttribute('aria-valuemax', '100');
            barRole.setAttribute('aria-valuenow', '0');
        }

        this.fillEl.classList.remove('is-animating', 'is-full');
        this.fillEl.style.transition = 'none';
        this.fillEl.style.transform = 'scaleX(0)';

        if (reduced) {
            this.timerId = setTimeout(function () {
                if (self._progressGen !== gen) return;
                self._fireAutoNext(gen);
            }, this.durationMs);
            return;
        }

        this.rootEl.style.setProperty('--indicator-duration', this.durationMs + 'ms');

        var beginFill = function () {
            if (self._progressGen !== gen || !self.fillEl) return;
            self.fillEl.style.transition = 'transform ' + self.durationMs + 'ms linear';
            self.fillEl.classList.add('is-animating');
            self.fillEl.style.transform = 'scaleX(1)';
            if (barRole) barRole.setAttribute('aria-valuenow', '100');
        };

        requestAnimationFrame(function () {
            requestAnimationFrame(beginFill);
        });

        this.timerId = setTimeout(function () {
            if (self._progressGen !== gen) return;
            self._fireAutoNext(gen);
        }, this.durationMs + 32);
    };

    GalleryProgressIndicator.prototype._fireAutoNext = function (gen) {
        if (this._autoNextFired) return;
        if (typeof gen === 'number' && gen !== this._progressGen) return;
        this._autoNextFired = true;
        this._clearTimer();
        if (this.autoNextCb && this.total > 1) {
            this.autoNextCb();
        }
    };

    GalleryProgressIndicator.create = function (hostEl) {
        var indicator = new GalleryProgressIndicator(hostEl);
        indicator.mount();
        return indicator;
    };

    global.GalleryProgressIndicator = GalleryProgressIndicator;
    global.GALLERY_SLIDE_MS = DEFAULT_DURATION_MS;
})(typeof window !== 'undefined' ? window : this);
