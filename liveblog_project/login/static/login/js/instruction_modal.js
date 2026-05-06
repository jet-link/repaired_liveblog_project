document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.instruction-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var modalEl = document.getElementById('instructionModal');
      if (modalEl && typeof bootstrap !== 'undefined') {
        var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
      }
    });
  });

  ['floatingUsername', 'floatingUsernameProfile'].forEach(function (id) {
    var input = document.getElementById(id);
    if (input) {
      input.addEventListener('input', function () {
        var wrap = this.closest('.form-floating');
        var err = wrap ? wrap.querySelector('.text-danger') : null;
        if (err) err.style.display = 'none';
      });
    }
  });
});
