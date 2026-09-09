// Progressive enhancement for the inline-SVG trend charts (adoption-index).
// Reads the JSON payload embedded in each .viz-root figure and adds:
//   1. crosshair + tooltip: hover anywhere on the plot, read every visible
//      series' value for the nearest week;
//   2. legend toggling: click a legend item to hide/show a series, the y-axis
//      rescales to the remaining lines.
// Without JS the server-rendered SVG stays fully readable (static fallback).
(function () {
  function fmt(n) {
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1e3) return Math.round(n / 1e3) + 'K';
    return String(Math.round(n));
  }
  document.querySelectorAll('.viz-root').forEach(function (fig) {
    var dataEl = fig.querySelector('.viz-data');
    var svg = fig.querySelector('svg');
    if (!dataEl || !svg) return;
    var P = JSON.parse(dataEl.textContent);
    var plotW = P.W - P.ml - P.mr, plotH = P.H - P.mt - P.mb;
    var hidden = {};
    fig.classList.add('js');

    var tip = document.createElement('div');
    tip.className = 'viz-tip';
    fig.appendChild(tip);
    var xh = svg.querySelector('.xh');

    function xAt(i) { return P.ml + plotW * i / Math.max(1, P.weeks.length - 1); }
    function visible() { return P.series.filter(function (s) { return !hidden[s.key]; }); }

    function redraw() {
      var vis = visible();
      var ymax = Math.max.apply(null, vis.map(function (s) {
        return Math.max.apply(null, s.vals.filter(function (v) { return v != null; }));
      })) * 1.06;
      function Y(v) { return P.mt + plotH * (1 - v / ymax); }
      svg.querySelectorAll('.y-tick').forEach(function (t) {
        var v = ymax * parseFloat(t.dataset.frac);
        t.textContent = P.indexed ? '×' + Math.round(v / 100) : fmt(v);
      });
      var ends = [];
      P.series.forEach(function (s) {
        var line = svg.querySelector('polyline[data-key="' + CSS.escape(s.key) + '"]');
        var dot = svg.querySelector('circle[data-key="' + CSS.escape(s.key) + '"]');
        var lbl = svg.querySelector('text.lbl[data-key="' + CSS.escape(s.key) + '"]');
        var off = !!hidden[s.key];
        [line, dot, lbl].forEach(function (el) { if (el) el.style.display = off ? 'none' : ''; });
        if (off) return;
        var pts = [], li = -1;
        s.vals.forEach(function (v, i) { if (v != null) { pts.push(xAt(i).toFixed(1) + ',' + Y(v).toFixed(1)); li = i; } });
        if (line) line.setAttribute('points', pts.join(' '));
        if (dot && li >= 0) { dot.setAttribute('cx', xAt(li).toFixed(1)); dot.setAttribute('cy', Y(s.vals[li]).toFixed(1)); }
        if (lbl && li >= 0) ends.push({ el: lbl, y: Y(s.vals[li]) });
      });
      ends.sort(function (a, b) { return a.y - b.y; });
      for (var i = 1; i < ends.length; i++)
        if (ends[i].y - ends[i - 1].y < 14) ends[i].y = ends[i - 1].y + 14;
      ends.forEach(function (e) { e.el.setAttribute('y', (e.y + 4).toFixed(1)); });
    }

    fig.querySelectorAll('.li[data-key]').forEach(function (li) {
      li.addEventListener('click', function () {
        var k = li.dataset.key;
        if (!hidden[k] && visible().length <= 1) return;   // keep at least one line
        hidden[k] = !hidden[k];
        li.classList.toggle('off', !!hidden[k]);
        tip.style.display = 'none'; if (xh) xh.style.display = 'none';
        redraw();
      });
    });

    svg.addEventListener('pointermove', function (e) {
      var r = svg.getBoundingClientRect();
      var sx = r.width / P.W;
      var mx = (e.clientX - r.left) / sx;
      if (mx < P.ml - 8 || mx > P.W - P.mr + 8) { tip.style.display = 'none'; if (xh) xh.style.display = 'none'; return; }
      var idx = Math.round((mx - P.ml) / plotW * (P.weeks.length - 1));
      idx = Math.max(0, Math.min(P.weeks.length - 1, idx));
      var xp = xAt(idx);
      if (xh) { xh.setAttribute('x1', xp); xh.setAttribute('x2', xp); xh.style.display = ''; }
      var rows = visible().map(function (s) {
        var v = s.vals[idx];
        if (v == null) return null;
        var txt = P.indexed
          ? (s.raw[idx] != null ? s.raw[idx].toLocaleString() : '—') + '/周（×' + (v / 100).toFixed(1) + '）'
          : Math.round(v).toLocaleString() + '/周';
        return { v: v, html: '<span class="d" style="background:var(--' + s.var + ')"></span>' + s.short + ' ' + txt };
      }).filter(Boolean).sort(function (a, b) { return b.v - a.v; });
      if (!rows.length) { tip.style.display = 'none'; return; }
      tip.innerHTML = '<strong>' + P.weeks[idx] + ' 当周</strong><br>' + rows.map(function (r) { return r.html; }).join('<br>');
      tip.style.display = 'block';
      var fr = fig.getBoundingClientRect();
      var left = (r.left - fr.left) + xp * sx + 14;
      if (left + tip.offsetWidth > fr.width - 8) left = (r.left - fr.left) + xp * sx - tip.offsetWidth - 14;
      tip.style.left = Math.max(4, left) + 'px';
      tip.style.top = (e.clientY - fr.top + 14) + 'px';
    });
    svg.addEventListener('pointerleave', function () {
      tip.style.display = 'none'; if (xh) xh.style.display = 'none';
    });
  });
})();

// Scatter charts (quality vs cost): a styled hover tooltip over each marker.
// Data lives in the SVG's data-* attributes, so no JSON payload is needed and
// the server-rendered SVG stays fully readable without JS.
(function () {
  document.querySelectorAll('.viz-root.scatter').forEach(function (fig) {
    var svg = fig.querySelector('svg');
    if (!svg) return;
    fig.classList.add('js');
    var tip = document.createElement('div');
    tip.className = 'viz-tip';
    fig.appendChild(tip);
    var pts = svg.querySelectorAll('[data-pt]');

    function show(el, clientX, clientY) {
      var d = el.dataset;
      var lat = parseFloat(d.l);
      tip.innerHTML =
        '<b><span class="d" style="background:var(--' + d.c + ')"></span>' + d.name + '</b><br>' +
        '质量 ' + d.q + '%　·　$' + parseFloat(d.cost).toFixed(5).replace(/0+$/, '').replace(/\.$/, '') + '/任务　·　p50 ' + lat + 's' +
        (d.budget ? '<br><span style="color:var(--muted)">▲ 预算内不可用（reasoning 爆 token）</span>' : '');
      tip.style.display = 'block';
      var fr = fig.getBoundingClientRect();
      var left = clientX - fr.left + 14;
      if (left + tip.offsetWidth > fr.width - 8) left = clientX - fr.left - tip.offsetWidth - 14;
      tip.style.left = Math.max(4, left) + 'px';
      tip.style.top = (clientY - fr.top + 16) + 'px';
    }
    pts.forEach(function (el) {
      el.addEventListener('pointerenter', function (e) { el.classList.add('hot'); show(el, e.clientX, e.clientY); });
      el.addEventListener('pointermove', function (e) { show(el, e.clientX, e.clientY); });
      el.addEventListener('pointerleave', function () { el.classList.remove('hot'); tip.style.display = 'none'; });
    });
  });
})();
