/* Marci.RMT — analytics
 *
 * Privacy-first, cookieless page and event tracking via Umami Cloud.
 * No cookies are set and no personal data is collected, so the site does
 * not need a cookie consent banner.
 *
 * ─────────────────────────────────────────────────────────────────────
 * SETUP: paste the Website ID from Umami Cloud between the quotes below.
 * Until it is filled in, this file does nothing at all.
 * ─────────────────────────────────────────────────────────────────────
 */
(function () {
  'use strict';

  var WEBSITE_ID = '0d22651f-283e-46f3-b9dc-b98b0a3e1e42';
  var SCRIPT_SRC = 'https://cloud.umami.is/script.js';

  if (!WEBSITE_ID) return;

  var tag = document.createElement('script');
  tag.defer = true;
  tag.src = SCRIPT_SRC;
  tag.setAttribute('data-website-id', WEBSITE_ID);
  (document.head || document.documentElement).appendChild(tag);

  function track(name, data) {
    if (window.umami && typeof window.umami.track === 'function') {
      window.umami.track(name, data);
    }
  }

  /* Where on the page the CTA sits, so we can tell which placements earn
     their keep. Order matters: the sticky pill and nav are checked first
     because they also sit inside broader containers. */
  function placement(el) {
    if (el.closest('.mobile-book')) return 'mobile-sticky';
    if (el.closest('.site-header')) return 'nav';
    if (el.closest('footer')) return 'footer';
    if (el.closest('.hero, .page-hero')) return 'hero';
    return 'page-cta';
  }

  function bookingType(href) {
    if (href.indexOf('#book-event') !== -1) return 'event';
    if (href.indexOf('#book-home') !== -1) return 'in-home';
    return 'general';
  }

  document.addEventListener('click', function (e) {
    var el = e.target;
    if (!el || typeof el.closest !== 'function') return;

    var link = el.closest('a[href]');
    if (!link) return;

    var href = link.getAttribute('href') || '';

    /* Book CTAs. Matches #book, #book-home and #book-event, and
       deliberately not in-page anchors like #booking on the FAQ. */
    if (/#book(-home|-event)?$/.test(href)) {
      track('Book Click', {
        placement: placement(link),
        type: bookingType(href),
        page: location.pathname
      });
      return;
    }

    /* Outbound links, including the Jane booking link once it is wired up.
       Query strings and fragments are dropped rather than recorded. */
    var url;
    try {
      url = new URL(link.href, location.href);
    } catch (err) {
      return;
    }

    if (/^https?:$/.test(url.protocol) && url.hostname !== location.hostname) {
      track('Outbound Link', {
        domain: url.hostname,
        url: url.hostname + url.pathname,
        page: location.pathname
      });
    }
  }, true);
})();
