// Shared by the board (index.html) and the map (map.html): your flats, your profile, the score.
//
// Flats come from flats.js plus whatever you added in the browser (localStorage). A flat you
// add or edit here wins over the file entry with the same id. Deleting a file entry hides it.
//
// The profile is the profile.json that intake/interview.py writes. Load it with the Profile
// button, or serve the repo root (python3 -m http.server from the repo) and it is read from
// ../profile.json automatically. Without one, neutral defaults apply and the page says so.
(function () {
  const CENTRE = { lat: 52.52, lng: 13.405 };
  const K_FLATS = "flatboard.flats.v1", K_HIDDEN = "flatboard.hidden.v1", K_PROFILE = "flatboard.profile.v1";

  // The nine factors the bot's interview rates from 0 to 5.
  const DIMS = [
    ["transit", "Station at the door"],
    ["area", "A neighbourhood you like"],
    ["anchors", "Short trip to the office"],
    ["centre", "Close to the centre"],
    ["rent", "The rent itself"],
    ["price_per_sqm", "Value per m²"],
    ["size", "Size"],
    ["rooms", "Number of rooms"],
    ["nearby", "What you need nearby"],
  ];
  const DEFAULT_PROFILE = {
    _default: true,
    weights: { _ratings: { transit: 3, area: 3, anchors: 4, centre: 2, rent: 4, price_per_sqm: 2, size: 3, rooms: 3, nearby: 2 } },
    budget: { max_warm: 1800, target_warm: 1500 },
    home: { min_size_sqm: 55, min_rooms: 2, max_floor_no_lift: 4, wants: ["balcony"], deal_breakers: [] },
    areas: { favourite: [], never: [] },
    anchors: [{ id: "office", label: "office", max_minutes: 40 }],
  };

  const get = (k, d) => { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } };
  const put = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } };

  function profile() { return get(K_PROFILE, null) || DEFAULT_PROFILE; }
  function setProfile(p) { put(K_PROFILE, p); }
  // The office is the first anchor in your profile that has coordinates. Until you load one,
  // the board uses Alexanderplatz as a stand-in so the example routes have somewhere to go.
  const EXAMPLE_OFFICE = { id: "office", name: "Office", note: "Alexanderplatz (example, set yours in profile.json)", short: "Alexanderplatz", lat: 52.5219, lng: 13.4132 };
  const OFFICE = (() => { const a = (profile().anchors || []).find((x) => x.lat != null && x.lng != null);
    return a ? { id: "office", name: a.label || "Office", note: a.label || "Office", short: a.label || "Office", lat: +a.lat, lng: +a.lng } : EXAMPLE_OFFICE; })();
  // When the page is served from the repo, the bot's own profile sits one folder up.
  async function repoProfile() {
    if (get(K_PROFILE, null) || !/^https?:/.test(location.protocol)) return false;
    try {
      const r = await fetch("../profile.json", { cache: "no-store" });
      if (!r.ok) return false;
      const p = await r.json(); p._source = "profile.json from the repo"; setProfile(p); return true;
    } catch (e) { return false; }
  }

  function ratings(p) {
    const w = p.weights || {};
    if (w._ratings) return Object.fromEntries(DIMS.map(([k]) => [k, +w._ratings[k] || 0]));
    const mx = Math.max(...DIMS.map(([k]) => +w[k] || 0)) || 1;
    return Object.fromEntries(DIMS.map(([k]) => [k, Math.round((+w[k] || 0) / mx * 5)]));
  }
  function weights(p) {
    const r = ratings(p), tot = DIMS.reduce((s, [k]) => s + r[k], 0) || 1;
    return Object.fromEntries(DIMS.map(([k]) => [k, r[k] / tot * 100]));
  }
  const limits = (p) => {
    const off = (p.anchors || []).find((a) => /office|work|büro/i.test((a.label || "") + (a.id || ""))) || (p.anchors || [])[0] || {};
    return {
      max: +p.budget?.max_warm || 1800, target: +p.budget?.target_warm || +p.budget?.max_warm || 1500,
      size: +p.home?.min_size_sqm || 0, rooms: +p.home?.min_rooms || 0, noLift: p.home?.max_floor_no_lift ?? 4,
      commute: +off.max_minutes || 40, wants: p.home?.wants || [], breakers: p.home?.deal_breakers || [],
      fav: p.areas?.favourite || [], never: p.areas?.never || [],
    };
  };

  function flats() {
    const hidden = new Set(get(K_HIDDEN, [])), local = get(K_FLATS, []);
    const ids = new Set(local.map((f) => f.id));
    return [...(window.FLATS_FILE || []).filter((f) => !hidden.has(f.id) && !ids.has(f.id)), ...local].map((f) => ({ photos: [], pros: [], cons: [], ...f }));
  }
  function saveFlat(f) { const local = get(K_FLATS, []).filter((x) => x.id !== f.id); local.push(f); return put(K_FLATS, local); }
  function deleteFlat(id) {
    put(K_FLATS, get(K_FLATS, []).filter((x) => x.id !== id));
    if ((window.FLATS_FILE || []).some((f) => f.id === id)) put(K_HIDDEN, [...new Set([...get(K_HIDDEN, []), id])]);
  }
  function removeExamples() { flats().filter((f) => f.example).forEach((f) => deleteFlat(f.id)); }
  function exportAll() { return { flats: flats(), profile: get(K_PROFILE, null) }; }
  function importAll(d) {
    const list = Array.isArray(d) ? d : d.flats; if (!Array.isArray(list)) throw new Error("no flats");
    list.forEach((f) => { if (f && f.name) saveFlat({ ...f, id: f.id || "f" + Math.random().toString(36).slice(2, 9) }); });
    if (d.profile) setProfile(d.profile);
    return list.length;
  }

  // ---- Reading a flat
  const km = (a, b) => { const R = 6371, r = Math.PI / 180, dA = (b.lat - a.lat) * r, dO = (b.lng - a.lng) * r;
    const h = Math.sin(dA / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dO / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(h)); };
  const clamp01 = (v) => Math.max(0, Math.min(1, v));
  const lin = (v, good, bad) => clamp01((v - bad) / (good - bad));
  const eur = (n) => n == null ? "—" : Math.round(n).toLocaleString("en-US") + " €";
  const floorNo = (f) => { const m = String(f.floor || "").match(/(-?\d+)/); return /ground/i.test(f.floor || "") ? 0 : m ? +m[1] : null; };
  const stationWalk = (f) => { if (f.route?.walk0 != null) return f.route.walk0; const m = String(f.transit || "").match(/(\d+)\s*min/); return m ? +m[1] : null; };
  const has = {
    balcony: (f) => !!f.balcony, lift: (f) => !!f.lift, kitchen: (f) => !!f.kitchen, bathtub: (f) => !!f.bathtub,
    pets: (f) => /^(yes|allowed|ok)/i.test(f.pets || ""), anmeldung: (f) => /^yes/i.test(f.anmeldung || ""),
    permanent: (f) => /permanent|unbefrist|unlimited/i.test(f.term || ""),
  };
  const PRO_TEXT = { balcony: "Balcony", lift: "Lift", kitchen: "Fitted kitchen", bathtub: "Bathtub", pets: "Pets allowed", anmeldung: "Anmeldung possible", permanent: "Permanent contract" };
  const WANT_NAME = { balcony: "balcony", lift: "lift", kitchen: "fitted kitchen", bathtub: "bathtub", pets: "pets allowed", anmeldung: "Anmeldung", permanent: "permanent contract" };
  function wantKey(w) { const t = String(w).toLowerCase();
    if (/balcon|terrace|loggia/.test(t)) return "balcony"; if (/lift|elevator|aufzug/.test(t)) return "lift";
    if (/kitchen|ebk|küche/.test(t)) return "kitchen"; if (/tub|wanne/.test(t)) return "bathtub";
    if (/pet|dog|cat|hund|tier/.test(t)) return "pets"; if (/permanent|unbefrist|unlimited/.test(t)) return "permanent";
    if (/anmeld|register/.test(t)) return "anmeldung"; return null; }

  // The score out of 10: each factor the profile rates above 0, measured 0..1, weighted by
  // the profile. A factor the flat has no data for is left out rather than counted as bad.
  function evaluate(f, p = profile()) {
    const L = limits(p), W = weights(p), dims = {}, pros = [], cons = [];
    const ppm = f.warm && f.size ? f.warm / f.size : null;
    const area = String(f.name || "") + " " + String(f.area || "");
    const never = L.never.find((n) => n && area.toLowerCase().includes(String(n).toLowerCase()));
    const fav = L.fav.find((n) => n && area.toLowerCase().includes(String(n).toLowerCase()));
    const dist = f.lat != null ? km(f, CENTRE) : null, walk = stationWalk(f), fl = floorNo(f);
    const add = (k, v, pro, con) => { dims[k] = v; if (v == null || !W[k]) return; if (v >= 0.7 && pro) pros.push(pro); if (v <= 0.35 && con) cons.push(con); };
    const station = String(f.transit || "").split(" · ")[0] || "the station";
    add("transit", walk == null ? null : lin(walk, 4, 15), `${station}, ${walk} min on foot`, `${walk} min on foot to ${station}`);
    let a = f.areaRate == null ? null : (f.areaRate - 1) / 4;
    if (never) a = 0; else if (fav) a = Math.max(a ?? 0, 0.9);
    add("area", a, fav ? `${fav} is on your list` : `You rated the area ${f.areaRate} of 5`, never ? `${never} is ruled out in your profile` : `You rated the area ${f.areaRate} of 5`);
    const changes = f.route?.changes;
    add("anchors", f.office == null ? null : lin(f.office, L.commute * 0.6, L.commute * 1.25),
      `${f.office} min to the office${changes != null ? (changes ? `, ${changes} change${changes > 1 ? "s" : ""}` : ", no changes") : ""}`,
      `${f.office} min to the office, your limit is ${L.commute}`);
    add("centre", dist == null ? null : lin(dist, 3, 12), `${dist?.toFixed(1)} km from the centre`, `${dist?.toFixed(1)} km from the centre`);
    let rent = null;
    if (f.warm) rent = f.warm <= L.target ? 1 : f.warm >= L.max ? 0 : 1 - (f.warm - L.target) / Math.max(1, L.max - L.target) * 0.85;
    add("rent", rent, `${eur(f.warm)} warm, within your comfortable ${eur(L.target)}`, f.warm > L.max ? `${eur(f.warm)} warm, over your ${eur(L.max)} max` : `${eur(f.warm)} warm, close to your ${eur(L.max)} max`);
    add("price_per_sqm", ppm == null ? null : lin(ppm, 14, 26), `${ppm?.toFixed(1)} € per m² warm`, `${ppm?.toFixed(1)} € per m² warm`);
    add("size", !f.size || !L.size ? null : lin(f.size, L.size * 1.45, L.size * 0.9), `${f.size} m², well over your ${L.size}`, `${f.size} m², your minimum is ${L.size}`);
    add("rooms", !f.rooms || !L.rooms ? null : f.rooms >= L.rooms + 1 ? 1 : f.rooms >= L.rooms ? 0.6 : 0, `${f.rooms} rooms, one more than you need`, `${f.rooms} rooms, you want ${L.rooms}`);
    add("nearby", f.nearRate == null ? null : (f.nearRate - 1) / 4, `You rated what is nearby ${f.nearRate} of 5`, `You rated what is nearby ${f.nearRate} of 5`);
    for (const w of L.wants) { const k = wantKey(w); if (!k) continue;
      if (has[k](f)) pros.push(PRO_TEXT[k]);
      else if (k === "lift" && fl != null && fl >= 3) cons.push(`No lift, ${fl}${fl === 3 ? "rd" : "th"} floor`);
      else cons.push(`No ${WANT_NAME[k]}`); }
    if (!has.lift(f) && fl != null && fl > L.noLift) cons.push(`Floor ${fl} without a lift, your limit is ${L.noLift}`);
    let sum = 0, ws = 0;
    for (const [k] of DIMS) if (dims[k] != null && W[k]) { sum += dims[k] * W[k]; ws += W[k]; }
    const score = ws ? Math.round(sum / ws * 100) / 10 : null;
    return { score, dims, W, pros, cons, ppm, dist };
  }

  window.FB = { OFFICE, CENTRE, DIMS, DEFAULT_PROFILE, profile, setProfile, repoProfile, ratings, weights, limits,
    flats, saveFlat, deleteFlat, removeExamples, exportAll, importAll, evaluate, eur, floorNo, stationWalk, has };
})();
