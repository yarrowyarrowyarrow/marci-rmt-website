/* Marci.RMT — contact form submission via Formspree
 *
 * ─────────────────────────────────────────────────────────────────────
 * SETUP: paste your Formspree form ID between the quotes below. It is the
 * part after /f/ in your endpoint, e.g. for
 *   https://formspree.io/f/xnqelrbk   the ID is   xnqelrbk
 * All three forms share the one endpoint and are distinguished by the
 * hidden "enquiry_type" field, so a single Formspree form is enough.
 * ─────────────────────────────────────────────────────────────────────
 *
 * Note: keep clinical detail out of these forms. Health history and
 * consent belong in Jane, which is built to hold them securely.
 */
(function () {
  'use strict';

  var FORMSPREE_ID = '';

  var forms = document.querySelectorAll('form[data-enquiry]');
  if (!forms.length) return;

  function setStatus(form, message, isError) {
    var el = form.querySelector('.form-status');
    if (!el) {
      el = document.createElement('p');
      el.className = 'form-status';
      el.setAttribute('role', 'status');
      form.appendChild(el);
    }
    el.textContent = message;
    el.classList.toggle('is-error', !!isError);
    el.classList.add('is-visible');
  }

  Array.prototype.forEach.call(forms, function (form) {
    if (FORMSPREE_ID) {
      form.action = 'https://formspree.io/f/' + FORMSPREE_ID;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      if (!FORMSPREE_ID) {
        setStatus(form, 'This form is not connected yet. Please email marci.makarewicz@gmail.com in the meantime.', true);
        return;
      }

      if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;

      var button = form.querySelector('button[type="submit"]');
      var label = button && button.querySelector('span');
      var original = label ? label.textContent : '';
      if (button) button.disabled = true;
      if (label) label.textContent = 'Sending…';

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' }
      }).then(function (res) {
        if (!res.ok) throw new Error('Request failed');
        form.reset();
        setStatus(form, 'Thank you, that came through. I will reply within one business day.', false);
      }).catch(function () {
        setStatus(form, 'Something went wrong sending that. Please email marci.makarewicz@gmail.com and I will get right back to you.', true);
      }).then(function () {
        if (button) button.disabled = false;
        if (label) label.textContent = original;
      });
    });
  });
})();
