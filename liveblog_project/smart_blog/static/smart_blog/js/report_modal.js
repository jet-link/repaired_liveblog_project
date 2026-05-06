(function () {
  'use strict';

  const modalEl = document.getElementById('reportModal');
  if (!modalEl) return;

  const reasonList = document.getElementById('reportReasonList');
  const details = document.getElementById('reportDetails');
  const submitBtn = document.getElementById('reportSubmitBtn');
  const feedback = document.getElementById('reportFeedback');
  const formView = document.getElementById('reportFormView');
  const existsView = document.getElementById('reportExistsView');
  const reportExistsReasonsWrap = document.getElementById('reportExistsReasonsWrap');
  const reportExistsReasonsList = document.getElementById('reportExistsReasonsList');
  const reportExistsDetailsWrap = document.getElementById('reportExistsDetailsWrap');
  const reportExistsDetailsBlock = document.getElementById('reportExistsDetailsBlock');
  const reportExistsTime = document.getElementById('reportExistsTime');
  const updateBtn = document.getElementById('reportUpdateBtn');
  const cancelBtn = document.getElementById('reportCancelBtn');

  const MIN_OTHER_CHARS = 2;
  const MAX_OTHER_CHARS = 300;
  const REASON_LABELS = { spam: 'Spam', abuse: 'Abuse', harassment: 'Harassment', copyright: 'Copyright', other: 'Other' };

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const m = (document.cookie || '').match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  function buildUrl(template, id) {
    return template.replace(/\/0\//, '/' + id + '/');
  }

  function validateOtherDetails() {
    const text = (details?.value || '').trim();
    if (text.length < MIN_OTHER_CHARS) return { valid: false, msg: 'Minimum 2 characters' };
    if (text.length > MAX_OTHER_CHARS) return { valid: false, msg: 'Maximum 300 characters' };
    return { valid: true };
  }

  function toggleDetailsEnabled() {
    const isOther = selectedReasons.includes('other');
    if (details) {
      details.disabled = !isOther;
      if (!isOther) details.value = '';
    }
    if (!isOther) setFeedback('');
  }

  let targetType = null;
  let targetId = null;
  let selectedReasons = [];
  let existingReport = null;

  function setFeedback(text, isError = false, isSuccess = false) {
    if (!feedback) return;
    feedback.textContent = text || '';
    feedback.classList.toggle('text-danger', !!isError);
    feedback.classList.toggle('text-muted', !isError && !isSuccess);
    feedback.classList.toggle('report-feedback-success', !!isSuccess);
  }

  function resetForm() {
    selectedReasons = [];
    existingReport = null;
    if (details) details.value = '';
    setFeedback('');
    reasonList?.querySelectorAll('.report-reason-btn').forEach(btn => btn.classList.remove('is-selected'));
    toggleDetailsEnabled();
    showFormView();
  }

  function showFormView() {
    if (formView) formView.classList.remove('d-none');
    if (existsView) existsView.classList.add('d-none');
    if (submitBtn) {
      submitBtn.textContent = existingReport ? 'Update report' : 'Report';
      submitBtn.style.display = '';
    }
  }

  function showExistsView(report) {
    if (formView) formView.classList.add('d-none');
    if (existsView) existsView.classList.remove('d-none');
    if (submitBtn) submitBtn.style.display = 'none';

    const reasons = Array.isArray(report.reasons) ? report.reasons : (report.reason ? [report.reason] : []);
    const isOther = reasons.includes('other') || (report.reason || '') === 'other';
    const detailsText = (report.details || '').trim();

    if (reportExistsReasonsWrap && reportExistsReasonsList) {
      if (reasons.length > 0) {
        reportExistsReasonsWrap.classList.remove('d-none');
        reportExistsReasonsList.innerHTML = '';
        reasons.forEach(r => {
          if (r) {
            const li = document.createElement('li');
            li.textContent = REASON_LABELS[r] || r;
            reportExistsReasonsList.appendChild(li);
          }
        });
      } else {
        reportExistsReasonsWrap.classList.add('d-none');
      }
    }

    if (reportExistsDetailsWrap && reportExistsDetailsBlock) {
      if (isOther && detailsText) {
        reportExistsDetailsWrap.classList.remove('d-none');
        reportExistsDetailsBlock.textContent = detailsText;
      } else {
        reportExistsDetailsWrap.classList.add('d-none');
      }
    }

    if (reportExistsTime) {
      const d = new Date(report.created_at);
      const now = new Date();
      const diffMs = now - d;
      const diffM = Math.floor(diffMs / 60000);
      const diffH = Math.floor(diffMs / 3600000);
      reportExistsTime.textContent = diffMs < 60000 ? 'just now' : diffM < 60 ? diffM + ' min ago...' : diffH < 24 ? diffH + ' hours ago' : Math.floor(diffH / 24) + ' days ago';
    }
  }

  function openReportModal(type, id) {
    targetType = type;
    targetId = String(id);
    resetForm();
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();

    const apiUrl = type === 'post'
      ? buildUrl(modalEl.dataset.apiPostUrl || '', targetId)
      : buildUrl(modalEl.dataset.apiCommentUrl || '', targetId);

    fetch(apiUrl, {
      method: 'GET',
      headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
    })
      .then(r => {
        if (!r.ok) {
          setFeedback('Could not load report status.', true);
          showFormView();
          return;
        }
        return r.json();
      })
      .then(data => {
        if (data && data.exists && data.report) {
          existingReport = data.report;
          showExistsView(data.report);
        } else {
          showFormView();
        }
      })
      .catch(() => {
        setFeedback('Could not load report status.', true);
        showFormView();
      });
  }

  function markTargetReported(type, id) {
    if (type === 'post') {
      const el = document.getElementById('post-reported-label');
      if (el) el.classList.remove('d-none');
    }
  }

  function unmarkTargetReported(type, id) {
    if (type === 'post') {
      const el = document.getElementById('post-reported-label');
      if (el) el.classList.add('d-none');
    }
  }

  reasonList?.addEventListener('click', (e) => {
    const btn = e.target.closest('.report-reason-btn');
    if (!btn) return;
    const reason = btn.dataset.reason;
    if (!reason) return;
    if (reason === 'other') {
      if (selectedReasons.includes('other')) {
        selectedReasons = [];
        btn.classList.remove('is-selected');
      } else {
        selectedReasons = ['other'];
        reasonList.querySelectorAll('.report-reason-btn').forEach(b => b.classList.remove('is-selected'));
        btn.classList.add('is-selected');
      }
    } else {
      if (selectedReasons.includes('other')) {
        selectedReasons = selectedReasons.filter(r => r !== 'other');
        reasonList.querySelector('.report-reason-btn[data-reason="other"]')?.classList.remove('is-selected');
      }
      if (selectedReasons.includes(reason)) {
        selectedReasons = selectedReasons.filter(r => r !== reason);
        btn.classList.remove('is-selected');
      } else {
        selectedReasons.push(reason);
        btn.classList.add('is-selected');
      }
    }
    toggleDetailsEnabled();
    if (!selectedReasons.includes('other')) setFeedback('');
  });

  updateBtn?.addEventListener('click', () => {
    if (!existingReport) return;
    const report = existingReport;
    existingReport = null;
    selectedReasons = Array.isArray(report.reasons) && report.reasons.length > 0
      ? [...report.reasons]
      : [report.reason || 'spam'];
    if (details) details.value = report.details || '';
    reasonList?.querySelectorAll('.report-reason-btn').forEach(b => {
      b.classList.toggle('is-selected', selectedReasons.includes(b.dataset.reason));
    });
    toggleDetailsEnabled();
    showFormView();
    if (submitBtn) submitBtn.textContent = 'Update report';
  });

  cancelBtn?.addEventListener('click', async () => {
    if (!existingReport || !existingReport.id) return;
    const url = buildUrl(modalEl.dataset.cancelUrl || '', existingReport.id);
    try {
      const r = await fetch(url, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
        },
        credentials: 'same-origin',
      });
      const data = await r.json().catch(() => ({}));
      if (r.ok && data.success) {
        unmarkTargetReported(targetType, targetId);
        bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      } else {
        setFeedback(data.error || 'Could not cancel report.', true);
      }
    } catch (err) {
      setFeedback('Network error.', true);
    }
  });

  submitBtn?.addEventListener('click', async () => {
    if (!selectedReasons.length) {
      setFeedback('Please select a reason.', true);
      return;
    }
    if (selectedReasons.includes('other')) {
      const result = validateOtherDetails();
      if (!result.valid) {
        setFeedback(result.msg, true);
        return;
      }
    }
    if (!targetType || !targetId) {
      setFeedback('Report target error.', true);
      return;
    }
    const reportUrl = targetType === 'post'
      ? buildUrl(modalEl.dataset.reportPostUrl || '', targetId)
      : buildUrl(modalEl.dataset.reportCommentUrl || '', targetId);
    const reasons = [...selectedReasons];

    setFeedback('Sending...');
    submitBtn.disabled = true;
    try {
      const resp = await fetch(reportUrl, {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reasons, details: (details?.value || '').trim() }),
      });
      const data = await resp.json().catch(() => null);
      if (!resp.ok || !data?.success) {
        setFeedback(data?.error || 'Report failed.', true);
        return;
      }
      setFeedback(existingReport ? 'Report updated.' : 'Report sent. Thank you', false, true);
      existingReport = { id: data.report_id, reasons, reason: reasons[0], details: (details?.value || '').trim(), created_at: new Date().toISOString() };
      markTargetReported(targetType, targetId);
      setTimeout(() => {
        bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      }, 500);
    } catch (err) {
      setFeedback('Network error.', true);
    } finally {
      submitBtn.disabled = false;
    }
  });

  document.addEventListener('click', (e) => {
    const postBtn = e.target.closest('.post_report_btn');
    if (postBtn) {
      e.preventDefault();
      const id = postBtn.dataset.itemId || postBtn.dataset.itemPk || postBtn.dataset.targetId || postBtn.dataset.postId || postBtn.dataset.post || document.getElementById('postIdForReport')?.value;
      if (id) openReportModal('post', id);
      return;
    }
  });

  window.addEventListener('comment-report', (e) => {
    const commentId = e?.detail?.commentId;
    if (commentId) openReportModal('comment', commentId);
  });

  window.addEventListener('post-report', (e) => {
    const postId = e?.detail?.postId ?? e?.detail?.itemId;
    if (postId) openReportModal('post', String(postId));
  });
})();
