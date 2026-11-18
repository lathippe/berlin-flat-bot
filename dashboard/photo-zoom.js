// Photo zoom in the lightbox, like a phone gallery.
// Pinch zooms to the point between the fingers, double tap zooms 2.5x or back,
// a finger pans while zoomed. Unzoomed, swipe sideways for the next photo, down to close.
// On a computer: double click zooms, the wheel zooms to the cursor.
window.photoZoom = function (box, img, { prev, next, close }) {
  let s = 1, x = 0, y = 0, pinch = null, pan = null, start = null, lastTap = 0, lastTouch = 0;
  box.style.touchAction = "none";
  img.style.transformOrigin = "0 0";
  img.style.willChange = "transform";
  const apply = (anim) => {
    img.style.transition = anim ? "transform .22s ease" : "none";
    img.style.transform = `translate(${x}px,${y}px) scale(${s})`;
  };
  // keep the photo in frame while zoomed
  const clamp = () => {
    if (s <= 1) { s = 1; x = 0; y = 0; return; }
    const bw = img.offsetWidth * s, bh = img.offsetHeight * s, ox = img.offsetLeft, oy = img.offsetTop;
    x = bw <= innerWidth ? (innerWidth - bw) / 2 - ox : Math.min(-ox, Math.max(innerWidth - bw - ox, x));
    y = bh <= innerHeight ? (innerHeight - bh) / 2 - oy : Math.min(-oy, Math.max(innerHeight - bh - oy, y));
  };
  // zoom to screen point (cx, cy) at scale ns
  const zoomTo = (ns, cx, cy) => {
    ns = Math.max(1, Math.min(5, ns));
    const ox = img.offsetLeft, oy = img.offsetTop;
    const px = (cx - ox - x) / s, py = (cy - oy - y) / s;   // point in photo coordinates
    s = ns; x = cx - ox - px * s; y = cy - oy - py * s;
  };
  const reset = () => { s = 1; x = 0; y = 0; apply(false); };
  img.addEventListener("load", reset);
  const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
  const mid = (t) => [(t[0].clientX + t[1].clientX) / 2, (t[0].clientY + t[1].clientY) / 2];

  box.addEventListener("touchstart", (e) => {
    lastTouch = performance.now();
    if (e.target.closest("button")) return;
    if (e.touches.length === 2) {
      pinch = { d: dist(e.touches), m: mid(e.touches) }; pan = null; start = null; return;
    }
    if (e.touches.length !== 1) return;
    const t = e.touches[0];
    pan = { x: t.clientX, y: t.clientY };
    start = { x: t.clientX, y: t.clientY, t: performance.now() };
  }, { passive: true });

  box.addEventListener("touchmove", (e) => {
    if (pinch && e.touches.length === 2) {
      const d = dist(e.touches), m = mid(e.touches);
      zoomTo(s * d / pinch.d, m[0], m[1]);
      x += m[0] - pinch.m[0]; y += m[1] - pinch.m[1];
      pinch = { d, m }; apply(false); e.preventDefault(); return;
    }
    if (pan && e.touches.length === 1) {
      const t = e.touches[0];
      if (s > 1) { x += t.clientX - pan.x; y += t.clientY - pan.y; apply(false); }
      else if (start) {   // unzoomed, the photo follows the finger a little
        const dx = t.clientX - start.x, dy = t.clientY - start.y;
        img.style.transition = "none";
        img.style.transform = Math.abs(dy) > Math.abs(dx) && dy > 0
          ? `translateY(${dy}px)` : `translateX(${dx}px)`;
        img.style.opacity = Math.abs(dy) > Math.abs(dx) && dy > 0 ? String(Math.max(0.3, 1 - dy / 400)) : "1";
      }
      pan = { x: t.clientX, y: t.clientY }; e.preventDefault();
    }
  }, { passive: false });

  box.addEventListener("touchend", (e) => {
    if (pinch && e.touches.length < 2) {
      pinch = null; clamp(); apply(true);
      if (e.touches.length === 1) { const t = e.touches[0]; pan = { x: t.clientX, y: t.clientY }; }
      start = null; return;
    }
    if (e.touches.length) return;
    const t = e.changedTouches[0];
    img.style.opacity = "1";
    if (start && s === 1) {
      const dx = t.clientX - start.x, dy = t.clientY - start.y;
      if (dy > 110 && Math.abs(dy) > Math.abs(dx)) { reset(); close(); start = null; pan = null; return; }
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) { reset(); (dx < 0 ? next : prev)(); start = null; pan = null; return; }
    }
    // double tap
    const moved = start ? Math.hypot(t.clientX - start.x, t.clientY - start.y) : 99;
    if (moved < 10) {
      const now = performance.now();
      if (now - lastTap < 300) { if (s > 1) { s = 1; x = 0; y = 0; } else zoomTo(2.5, t.clientX, t.clientY); clamp(); apply(true); lastTap = 0; }
      else lastTap = now;
    }
    if (s > 1) { clamp(); apply(true); } else if (moved >= 10) apply(true);
    start = null; pan = null;
  });

  img.addEventListener("dblclick", (e) => {
    if (performance.now() - lastTouch < 1000) return;   // on a phone the double tap is handled above
    if (s > 1) { s = 1; x = 0; y = 0; } else zoomTo(2.5, e.clientX, e.clientY);
    clamp(); apply(true);
  });
  box.addEventListener("wheel", (e) => {
    e.preventDefault();
    zoomTo(s * Math.exp(-e.deltaY * 0.004), e.clientX, e.clientY); clamp(); apply(false);
  }, { passive: false });
  return { reset, zoomed: () => s > 1 };
};
