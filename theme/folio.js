// folio.js — the one small script every page loads (~4 KB). Progressive
// enhancement only: without it, every page is complete and readable.
//   1. sortable tables: click a header cell (numeric-aware: , $ % K/M/B)
//   2. hover popups: [data-pop] elements show the <template> named by the attr
//      (link previews, [[glossary]] terms, footnotes) -- built at build time
//   3. active-section marker for a long page's contents minimap
//   4. mermaid bootstrap, theme-aware, re-renders when the OS theme flips
//   5. window.folio helpers for embedded animations
(function () {
  'use strict';
  var doc = document, dark = matchMedia('(prefers-color-scheme: dark)');
  var lang = (doc.documentElement.lang || 'en').slice(0, 2);
  var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- helpers for page scripts ------------------------------------------
  window.folio = {
    dark: function () { return dark.matches; },
    reducedMotion: reduced,
    // run fn(el) when el scrolls into view (once by default): start animations lazily
    onVisible: function (el, fn, opts) {
      opts = opts || {};
      if (!('IntersectionObserver' in window)) { fn(el); return; }
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (!e.isIntersecting) { if (opts.leave) opts.leave(el); return; }
          fn(el);
          if (!opts.repeat) io.unobserve(el);
        });
      }, { threshold: opts.threshold || 0.2 });
      io.observe(el);
    },
    onThemeChange: function (fn) { dark.addEventListener('change', function () { fn(dark.matches); }); },
    // read a CSS custom property off the page (e.g. folio.css('--fg'))
    css: function (name, el) { return getComputedStyle(el || doc.documentElement).getPropertyValue(name).trim(); }
  };

  // ---- 1. sortable tables ------------------------------------------------
  function num(s) {
    s = s.trim().replace(/[,$%]/g, '');
    var m = s.match(/^(-?\d+(?:\.\d+)?)\s*([KMB])?/i);
    if (!m) return null;
    var v = parseFloat(m[1]), suf = (m[2] || '').toUpperCase();
    return v * (suf === 'K' ? 1e3 : suf === 'M' ? 1e6 : suf === 'B' ? 1e9 : 1);
  }
  doc.querySelectorAll('article table').forEach(function (table) {
    var head = table.rows[0];
    if (!head || table.rows.length < 3) return;
    var body = table.tBodies[0] || table;
    Array.prototype.forEach.call(head.cells, function (th, col) {
      if (th.tagName !== 'TH') return;
      th.style.cursor = 'pointer';
      th.title = lang === 'zh' ? '点击排序' : 'click to sort';
      th.addEventListener('click', function () {
        var dir = th.getAttribute('aria-sort') === 'descending' ? 1 : -1;
        Array.prototype.forEach.call(head.cells, function (h) { h.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
        var rows = Array.prototype.slice.call(table.rows, 1).filter(function (r) { return r.parentNode !== table.tHead; });
        rows.sort(function (a, b) {
          var x = (a.cells[col] || {}).textContent || '', y = (b.cells[col] || {}).textContent || '';
          var nx = num(x), ny = num(y);
          if (nx !== null && ny !== null) return (nx - ny) * dir;
          if (nx !== null) return -1;
          if (ny !== null) return 1;
          return x.localeCompare(y, lang) * dir;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });

  // ---- 2. hover popups ---------------------------------------------------
  var pop = null, timer = null, anchor = null;
  function box() {
    if (pop) return pop;
    pop = doc.createElement('div');
    pop.className = 'pop';
    pop.setAttribute('role', 'tooltip');
    pop.addEventListener('mouseenter', function () { clearTimeout(timer); });
    pop.addEventListener('mouseleave', hideSoon);
    doc.body.appendChild(pop);
    return pop;
  }
  function show(a) {
    var t = doc.getElementById(a.getAttribute('data-pop'));
    if (!t || !t.content) return;
    var p = box();
    p.innerHTML = '';
    p.appendChild(t.content.cloneNode(true));
    p.style.display = 'block';
    anchor = a;
    var r = a.getBoundingClientRect(), w = p.offsetWidth, h = p.offsetHeight;
    var left = Math.max(8, Math.min(r.left + scrollX, doc.documentElement.clientWidth - w - 8));
    var top = r.bottom + scrollY + 6;
    if (r.bottom + h + 12 > innerHeight && r.top - h - 6 > 0) top = r.top + scrollY - h - 6;
    p.style.left = left + 'px';
    p.style.top = top + 'px';
  }
  function hide() { clearTimeout(timer); if (pop) pop.style.display = 'none'; anchor = null; }
  function hideSoon() { clearTimeout(timer); timer = setTimeout(hide, 220); }
  doc.querySelectorAll('[data-pop]').forEach(function (a) {
    a.removeAttribute('title');            // the popup replaces the native tooltip
    a.addEventListener('mouseenter', function () { clearTimeout(timer); timer = setTimeout(function () { show(a); }, 180); });
    a.addEventListener('mouseleave', hideSoon);
    a.addEventListener('focus', function () { show(a); });
    a.addEventListener('blur', hide);
  });
  doc.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
  doc.addEventListener('scroll', function () { if (anchor) hide(); }, { passive: true });

  // ---- 3. contents minimap ----------------------------------------------
  var toc = doc.querySelector('.toc');
  if (toc) {
    var tocLinks = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
    var tocHeads = tocLinks.map(function (a) {
      try { return doc.getElementById(decodeURIComponent(a.hash.slice(1))); }
      catch (_) { return null; }
    });
    var ticking = false;
    function markSection() {
      ticking = false;
      var active = -1;
      tocHeads.forEach(function (h, i) {
        if (h && h.getBoundingClientRect().top <= 96) active = i;
      });
      if (active < 0 && tocHeads.length) active = 0;
      tocLinks.forEach(function (a, i) {
        if (i === active) a.setAttribute('aria-current', 'location');
        else a.removeAttribute('aria-current');
      });
    }
    function requestMark() {
      if (!ticking) { ticking = true; requestAnimationFrame(markSection); }
    }
    doc.addEventListener('scroll', requestMark, { passive: true });
    markSection();
  }

  // ---- 4. mermaid --------------------------------------------------------
  var diagrams = doc.querySelectorAll('pre.mermaid');
  if (diagrams.length && window.mermaid) {
    diagrams.forEach(function (el) { el.dataset.src = el.textContent; });
    function draw() {
      mermaid.initialize({ startOnLoad: false, theme: dark.matches ? 'dark' : 'neutral', securityLevel: 'strict' });
      diagrams.forEach(function (el) { el.textContent = el.dataset.src; el.removeAttribute('data-processed'); });
      mermaid.run({ nodes: diagrams });
    }
    draw();
    dark.addEventListener('change', draw);
  }
})();
