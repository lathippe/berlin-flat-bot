// Example flat: Uhlandstraße, Wilmersdorf. Sketched from the room sizes, not from a real plan.
// Engine: plan3d.html?f=uhland. Coordinates are plan pixels, 1 px = 1 cm (S: 100).
(window.PLAN3D = window.PLAN3D || {}).uhland = {
  title: "Uhlandstraße (example)",
  sub: "Wilmersdorf · 86 m² · three rooms, separate study, lift",
  legend: "<b>An example plan.</b> Living room and bedroom face the street to the east, kitchen, bath and study face the courtyard to the west. Press Furniture to see a possible layout.",
  foot: "Altbau ceilings at 3.20 m.",
  S: 100, OX: 480, OZ: 460, H: 3.2,
  north: 270,
  lat: 52.4972, lon: 13.3245,
  facades: [
    { plan: 0, label: "Living room and bedroom (street, east)", now: "morning sun in the living room and bedroom" },
    { plan: 180, label: "Kitchen and study (courtyard, west)", now: "afternoon sun in the kitchen and study" },
  ],
  sims: { pos: [6.5, 11, 10], target: [0, 0, 0], min: 3, max: 22 },
  span: 7,
  eye: { from: [80, 510], to: [900, 510] },
  clamp: { x: [-5.5, 5.5], z: [-5, 5] },
  build({ THREE, M, mat, canvasTex, rnd, tiles, flatFloor, wall, box, named, tagAt, area, fixed }) {
    const parquet = canvasTex(1024, (g, n) => {
      const q = n / 8, f = q / 5;
      for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) {
        const turn = (i + j) % 2;
        for (let k = 0; k < 5; k++) {
          g.fillStyle = `hsl(${rnd(32, 38)}, ${rnd(48, 60)}%, ${rnd(56, 66)}%)`;
          if (turn) g.fillRect(i * q + k * f, j * q, f, q); else g.fillRect(i * q, j * q + k * f, q, f);
          g.strokeStyle = "rgba(110,70,30,.25)"; g.lineWidth = 1;
          if (turn) g.strokeRect(i * q + k * f, j * q, f, q); else g.strokeRect(i * q, j * q + k * f, q, f);
        }
      }
    }, [1 / 1.2, 1 / 1.2]);
    const tile = tiles(6, 6, [200, 6, 90], "#9aa3a8", 2); tile.repeat.set(1 / 1.2, 1 / 1.2);
    Object.assign(M, {
      parquet: new THREE.MeshStandardMaterial({ map: parquet, roughness: .4 }),
      tile: new THREE.MeshStandardMaterial({ map: tile, roughness: .3 }),
      kitchen: mat(0xeef0ee, { roughness: .2 }), counter: mat(0x2f3133, { roughness: .5 }),
    });

    const LIVING = [[0, 0], [560, 0], [560, 440], [0, 440]];
    const BED = [[560, 0], [960, 0], [960, 440], [560, 440]];
    const HALL = [[0, 440], [960, 440], [960, 580], [0, 580]];
    const KITCHEN = [[0, 580], [340, 580], [340, 920], [0, 920]];
    const BATH = [[340, 580], [560, 580], [560, 920], [340, 920]];
    const STUDY = [[560, 580], [960, 580], [960, 920], [560, 920]];
    for (const r of [LIVING, BED, HALL, STUDY]) flatFloor(r, M.parquet, 0);
    flatFloor(KITCHEN, M.tile, .003); flatFloor(BATH, M.tile, .003);

    // Outside walls
    wall([0, 0], [960, 0], { ext: true, openings: [[.8, 2.2, "window", .7, 2.6, 2], [3.2, 4.6, "window", .7, 2.6, 2], [6.8, 8.4, "window", .7, 2.6, 2]] });
    wall([0, 920], [960, 920], { ext: true, openings: [[1.0, 2.4, "window", .9, 2.6, 2], [4.0, 4.8, "window", 1.2, 2.4, 1], [6.5, 8.3, "window", .7, 2.6, 2]] });
    wall([0, 0], [0, 920], { ext: true, openings: [[4.5, 5.5, "door"]] });
    wall([960, 0], [960, 920], { ext: true });
    // Inside walls
    wall([560, 0], [560, 440], { t: .15 });
    wall([0, 440], [960, 440], { t: .15, openings: [[2.4, 3.3, "door"], [6.6, 7.5, "door"]] });
    wall([0, 580], [960, 580], { t: .15, openings: [[2.2, 3.0, "door"], [3.7, 4.5, "door"], [6.4, 7.3, "door"]] });
    wall([340, 580], [340, 920], { t: .12 });
    wall([560, 580], [560, 920], { t: .15 });

    // What comes with the flat
    named("fitted kitchen, included", box(5, 860, 335, 915, .9, M.kitchen, { group: fixed }), box(3, 858, 337, 915, .04, M.counter, { y: .9, group: fixed }),
      box(5, 590, 65, 850, .9, M.kitchen, { group: fixed }), box(3, 588, 67, 850, .04, M.counter, { y: .9, group: fixed }));
    named("bathtub", box(350, 590, 550, 665, .58, M.porcelain, { group: fixed }));
    named("toilet", box(490, 850, 550, 910, .4, M.porcelain, { group: fixed }));
    named("washbasin", box(350, 860, 430, 912, .18, M.porcelain, { y: .8, group: fixed }));
    named("radiators under the windows", box(80, 8, 220, 16, .55, M.white, { y: .2, group: fixed }), box(680, 8, 840, 16, .55, M.white, { y: .2, group: fixed }), box(650, 904, 830, 912, .55, M.white, { y: .2, group: fixed }));

    // A possible layout, hidden until Furniture
    box(680, 180, 840, 380, .5, M.bed, { label: "bed 160 × 200" });
    box(580, 20, 640, 260, 2.2, M.wood, { label: "wardrobe" });
    box(40, 300, 280, 400, .85, M.sofa, { label: "sofa" });
    box(330, 120, 520, 260, .75, M.wood, { label: "dining table" });
    box(80, 120, 280, 260, .01, M.rug, { label: "rug" });
    box(780, 760, 950, 900, .75, M.wood, { label: "desk by the window" });
    box(580, 600, 640, 900, 2.0, M.white, { label: "bookshelf" });

    tagAt(`Living room <i>≈${area(LIVING).toFixed(0)} m²</i>`, 280, 220);
    tagAt(`Bedroom <i>≈${area(BED).toFixed(0)} m²</i>`, 760, 220);
    tagAt(`Hall <i>≈${area(HALL).toFixed(0)} m²</i>`, 480, 510);
    tagAt(`Kitchen <i>≈${area(KITCHEN).toFixed(0)} m²</i>`, 170, 750);
    tagAt(`Bath <i>≈${area(BATH).toFixed(0)} m²</i>`, 450, 750);
    tagAt(`Study <i>≈${area(STUDY).toFixed(0)} m²</i>`, 760, 750);
    tagAt("Uhlandstraße · east", 480, -60, "street");
    tagAt("entrance", 40, 510, "", .3);
  },
};
