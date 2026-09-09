// Example page script: three sine waves on a canvas. Starts when visible,
// pauses when scrolled away, stays static under prefers-reduced-motion.
(function () {
  var c = document.getElementById('wave');
  if (!c) return;
  var ctx = c.getContext('2d'), t = 0, raf = null;
  function frame() {
    var w = c.width, h = c.height;
    ctx.clearRect(0, 0, w, h);
    ctx.lineWidth = 2;
    ['--s1', '--s2', '--s3'].forEach(function (v, k) {
      ctx.strokeStyle = folio.css(v, c.parentNode) || ['#2a78d6', '#1baf7a', '#d98c00'][k];
      ctx.beginPath();
      for (var x = 0; x <= w; x += 2) {
        var y = h / 2 + Math.sin(x / (40 + 20 * k) + t * (1 + k / 2)) * (h / 3 - 12 * k);
        x ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    });
    t += 0.03;
    if (!folio.reducedMotion) raf = requestAnimationFrame(frame);
  }
  // .viz doesn't define --s*, so borrow the chart palette by tagging the container
  c.parentNode.classList.add('viz-root');
  folio.onVisible(c, function () { if (!raf) frame(); }, {
    repeat: true, leave: function () { cancelAnimationFrame(raf); raf = null; }
  });
})();
