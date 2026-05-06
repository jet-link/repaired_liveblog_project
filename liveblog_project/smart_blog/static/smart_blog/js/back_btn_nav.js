/**
 * back_btn_nav.js
 * 1. Save current URL before navigating to tag / category / topic / comment-thread pages
 * 2. Handle back-btn click: navigate to saved URL or fallback
 */
function getCommentThreadReturnUrl() {
    try {
        var url = sessionStorage.getItem('comment_thread_return_url');
        if (url && typeof url === 'string' && url.charAt(0) === '/' && url.indexOf('//') < 0) {
            return url;
        }
    } catch (err) { }
    return '';
}
window.getCommentThreadReturnUrl = getCommentThreadReturnUrl;

function isCommentThreadPath(pathname) {
    try {
        var p = pathname.replace(/\/+$/, '') || '/';
        return /\/comment\/\d+\/thread$/.test(p);
    } catch (err) {
        return false;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    function showBrainPreloader() {
        if (window.__brainPreloader && typeof window.__brainPreloader.show === 'function') {
            window.__brainPreloader.show();
        }
    }

    // Save current page when user clicks a tag link (capture phase — before navigation)
    document.addEventListener('click', function (e) {
        var a = e.target.closest('a[href*="/tag/"], a[href*="/blog/tag/"]');
        if (a && a.href) {
            try {
                sessionStorage.setItem('tag_return_url', location.pathname + location.search);
            } catch (err) { }
        }
        var cat = e.target.closest('a[href*="/blog/brainews/category/"]');
        if (cat && cat.href) {
            try {
                sessionStorage.setItem('category_return_url', location.pathname + location.search);
            } catch (err) { }
        }
        var topic = e.target.closest('a[href*="/topics/"], a[href*="/blog/topics/"]');
        if (topic && topic.href) {
            try {
                var p = new URL(topic.href, window.location.origin).pathname.replace(/\/+$/, '') || '/';
                var isTopicHub = p.indexOf('/topics/') === 0 || p.indexOf('/blog/topics/') === 0;
                if (isTopicHub) {
                    sessionStorage.setItem('category_return_url', location.pathname + location.search);
                }
            } catch (err) { }
        }
        var threadA = e.target.closest('a[href*="/thread/"]');
        if (threadA && threadA.href) {
            try {
                var tp = new URL(threadA.href, window.location.origin).pathname || '';
                if (isCommentThreadPath(tp)) {
                    sessionStorage.setItem('comment_thread_return_url', location.pathname + location.search);
                }
            } catch (err) { }
        }
    }, true);

    // Back-btn click handler
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.back-btn');
        if (!btn) return;
        e.preventDefault();
        var key = btn.getAttribute('data-return-key');
        var fallback = btn.getAttribute('data-fallback') || '/brainews/';
        if (!key) {
            showBrainPreloader();
            window.location.href = fallback;
            return;
        }
        try {
            var url = sessionStorage.getItem(key);
            if (url && typeof url === 'string' && url.charAt(0) === '/' && url.indexOf('//') < 0) {
                showBrainPreloader();
                window.location.href = url;
            } else {
                showBrainPreloader();
                window.location.href = fallback;
            }
        } catch (err) {
            showBrainPreloader();
            window.location.href = fallback;
        }
    });
});
