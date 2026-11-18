// Top bar shared by the board and the map: weekday and date, the page name, actions, theme toggle.
// Sticky elements on the page are shifted down by the bar's height so they stand under it.
(function () {
  if (document.getElementById("site-header")) return;
  var H = 36;
  try {
    var saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {}
  function isDark() {
    var a = document.documentElement.getAttribute("data-theme");
    if (a === "dark" || a === "light") return a === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  if (!document.querySelector('link[href*="IBM+Plex+Mono"]')) {
    var fl = document.createElement("link");
    fl.rel = "stylesheet";
    fl.href = "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500&display=swap";
    document.head.appendChild(fl);
  }
  var css = [
    "#site-header{--sh-surface:#ffffff;--sh-fg:#121212;--sh-muted:#616161;--sh-muted-strong:#2e2e2e;--sh-border:#d3d1cb;--sh-border-strong:#b8b6b0;",
    "position:sticky;top:0;z-index:1000;box-sizing:border-box;width:auto;max-width:100vw;height:" + H + "px;background:var(--sh-surface);border-bottom:1px solid var(--sh-border-strong);",
    "box-shadow:0 6px 16px -14px color-mix(in srgb,var(--sh-fg) 55%,transparent);font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}",
    "#site-header.sh-dark{--sh-surface:#1c1917;--sh-fg:#e5e7eb;--sh-muted:#a8a29e;--sh-muted-strong:#d6d3d1;--sh-border:#292524;--sh-border-strong:#44403c}",
    "#site-header .sh-in{max-width:1400px;margin:0 auto;height:100%;padding:0 16px;display:flex;align-items:center;gap:8px;min-width:0}",
    "@media (min-width:640px){#site-header .sh-in{padding:0 24px;gap:12px}}",
    "#site-header .sh-l{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:11px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;line-height:1;white-space:nowrap}",
    "#site-header .sh-day{color:var(--sh-muted-strong)}#site-header .sh-date{color:var(--sh-muted)}",
    "@media (max-width:639px){#site-header .sh-date{display:none}}",
    "#site-header .sh-pill{height:28px;padding:0 10px;display:inline-flex;align-items:center;gap:6px;border-radius:999px;border:0;cursor:pointer;text-decoration:none;",
    "background:color-mix(in srgb,var(--sh-fg) 5%,transparent);color:var(--sh-muted-strong);transition:background .15s,color .15s}",
    "#site-header .sh-pill:hover,#site-header .sh-pill[aria-expanded=true]{background:color-mix(in srgb,var(--sh-fg) 10%,transparent);color:var(--sh-fg)}",
    "#site-header .sh-pill:focus-visible,#site-header .sh-theme:focus-visible,#site-header .sh-menu a:focus-visible{outline:2px solid var(--sh-muted);outline-offset:2px}",
    "#site-header .sh-sp{flex:1}",
    "#site-header .sh-home{display:inline-flex;align-items:center;gap:8px;text-decoration:none;height:28px;padding:0 8px;margin-left:-8px;border-radius:999px;transition:background .15s}",
    "#site-header .sh-home:hover{background:color-mix(in srgb,var(--sh-fg) 6%,transparent)}",
    "#site-header .sh-home:focus-visible{outline:2px solid var(--sh-muted);outline-offset:2px}",
    "#site-header .sh-theme{width:28px;height:28px;border:0;background:none;border-radius:999px;cursor:pointer;color:var(--sh-muted);font-size:15px}",
    "#site-header .sh-theme:hover{color:var(--sh-fg)}",
    "#site-header .sh-wrap{position:relative}",
    "#site-header .sh-menu{position:absolute;right:0;top:100%;margin-top:8px;width:min(340px,calc(100vw - 32px));max-height:calc(100vh - 80px);overflow-y:auto;padding:8px;border-radius:12px;display:grid;gap:8px;",
    "background:var(--sh-surface);border:1px solid var(--sh-border-strong);box-shadow:0 10px 30px -10px rgba(0,0,0,.35)}",
    "#site-header .sh-menu[hidden]{display:none}",
    "#site-header .sh-g{border-radius:10px;padding:6px;background:color-mix(in srgb,var(--t) 7%,transparent);border:1px solid color-mix(in srgb,var(--t) 18%,transparent)}",
    "#site-header .sh-gt{padding:4px 6px 6px;color:var(--t);display:flex;align-items:center;gap:6px}",
    "#site-header .sh-it{border-radius:8px}#site-header .sh-it:hover{background:var(--sh-surface)}",
    "#site-header .sh-menu a.sh-a{display:flex;align-items:center;gap:10px;padding:6px;border-radius:8px;text-decoration:none}",
    "#site-header .sh-menu a[aria-current=page]{background:color-mix(in srgb,var(--sh-fg) 8%,transparent)}",
    "#site-header .sh-ic{width:32px;height:32px;flex:none;border-radius:8px;display:grid;place-items:center;font-size:16px;line-height:1;background:color-mix(in srgb,var(--t) 16%,transparent)}",
    "#site-header .sh-tx{min-width:0;flex:1}",
    "#site-header .sh-lab{display:block;font-size:13.5px;line-height:1.25;color:var(--sh-fg);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
    "#site-header .sh-note{display:block;font-size:11.5px;line-height:1.25;margin-top:2px;color:var(--sh-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
    "#site-header .sh-chips{display:flex;flex-wrap:wrap;gap:4px;padding:0 6px 8px 48px;margin-top:-2px}",
    "#site-header .sh-chips a{font-size:11.5px;line-height:1;padding:5px 8px;border-radius:999px;text-decoration:none;color:var(--sh-fg);background:color-mix(in srgb,var(--t) 12%,transparent)}",
    "#site-header .sh-chips a:hover{background:color-mix(in srgb,var(--t) 22%,transparent)}",
    "@media (max-width:639px){#site-header .sh-word{display:none}}",
    "#site-header summary.sh-gt{cursor:pointer;list-style:none}#site-header summary.sh-gt::-webkit-details-marker{display:none}",
  ].join("");
  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  var now = new Date();
  var day = now.toLocaleDateString("en-US", { weekday: "long" });
  var date = now.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  var actions = document.body.getAttribute("data-actions") === "1";
  var bar = document.createElement("header");
  bar.id = "site-header";
  bar.innerHTML =
    '<div class="sh-in">' +
    '<a class="sh-home" href="index.html" title="Flat board"><span class="sh-l sh-day"></span><span class="sh-l sh-date"></span></a>' +
    '<span class="sh-l" style="opacity:.9">· Flat HQ</span>' +
    '<span class="sh-sp"></span>' +
    (actions ?
      '<button type="button" class="sh-pill sh-l" data-act="add" title="Add a flat"><span aria-hidden="true">+</span><span class="sh-word">add flat</span></button>' +
      '<button type="button" class="sh-pill sh-l" data-act="profile" title="Your profile and priorities"><span aria-hidden="true">◎</span><span class="sh-word">profile</span></button>' +
      '<button type="button" class="sh-pill sh-l" data-act="data" title="Back up or move your flats"><span aria-hidden="true">⇅</span><span class="sh-word">data</span></button>'
      : '<a class="sh-pill sh-l" href="index.html"><span aria-hidden="true">☰</span><span class="sh-word">board</span></a>') +
    '<button type="button" class="sh-theme" aria-label="Switch theme"></button>' +
    "</div>";
  bar.querySelector(".sh-day").textContent = day;
  bar.querySelector(".sh-date").textContent = date;
  document.body.insertBefore(bar, document.body.firstChild);
  var bs = getComputedStyle(document.body);
  bar.style.marginTop = "-" + bs.paddingTop;
  bar.style.marginLeft = "-" + bs.paddingLeft;
  bar.style.marginRight = "-" + bs.paddingRight;
  bar.style.marginBottom = bs.paddingTop;
  bar.querySelectorAll("[data-act]").forEach(function (b) {
    b.addEventListener("click", function () { window.dispatchEvent(new CustomEvent("fb-action", { detail: b.getAttribute("data-act") })); });
  });

  var themeBtn = bar.querySelector(".sh-theme");
  function paintTheme() {
    var d = isDark();
    bar.classList.toggle("sh-dark", d);
    themeBtn.textContent = d ? "☀" : "☾";
  }
  paintTheme();
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paintTheme);
  themeBtn.addEventListener("click", function () {
    var next = isDark() ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) {}
    paintTheme();
    window.dispatchEvent(new Event("themechange"));
  });

  function shift(rules) {
    for (var i = 0; i < rules.length; i++) {
      var r = rules[i];
      if (r.cssRules && r.media) { shift(r.cssRules); continue; }
      if (!r.style || r.style.position !== "sticky" || !r.selectorText) continue;
      if (r.selectorText.indexOf("#site-header") !== -1) continue;
      var top = r.style.top || "0px";
      r.style.setProperty("top", "calc(" + top + " + " + H + "px)", r.style.getPropertyPriority("top"));
    }
  }
  for (var s = 0; s < document.styleSheets.length; s++) {
    try { shift(document.styleSheets[s].cssRules || []); } catch (e) {}
  }
  document.documentElement.style.scrollPaddingTop = H + 8 + "px";
})();
