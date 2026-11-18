// Example flat: Boxhagener Straße, Friedrichshain. Sketched from the room sizes, not from a real plan.
// Engine: plan3d.html?f=boxhagener. Coordinates are plan pixels, 1 px = 1 cm (S: 100).
// x runs right, z runs down the plan. Openings are [from, to, kind, sill, head, panes] in metres along the wall.
(window.PLAN3D = window.PLAN3D || {}).boxhagener = {
  title: "Boxhagener Straße (example)",
  sub: "Friedrichshain · 62 m² · two rooms, balcony to the courtyard",
  legend: "<b>An example plan.</b> Living room and bedroom face the courtyard to the south, the kitchen has no window. Press Furniture to see a possible layout.",
  foot: "Replace this file with your own flat: copy it, change the rooms and the walls, and set plan3d in flats.js.",
  S: 100, OX: 440, OZ: 360, H: 2.85,
  north: 180,
  lat: 52.5114, lon: 13.4624,
  facades: [
    { plan: 0, label: "Living room and bedroom (courtyard)", now: "sun in the living room and bedroom" },
    { plan: 270, label: "Living room side window (street)", now: "sun in the side window" },
  ],
  sunNote: "The courtyard side faces south, so winter sun reaches the living room around midday.",
  sims: { pos: [6, 10, 9], target: [0, 0, 0], min: 3, max: 20 },
  span: 6,
  eye: { from: [460, 600], to: [250, 120] },
  clamp: { x: [-5, 5], z: [-4.5, 4.5] },
  build({ THREE, M, mat, canvasTex, rnd, tiles, flatFloor, wall, box, named, tagAt, area, fixed }) {
    const boards = canvasTex(1024, (g, n) => {
      const pw = n / 7;
      for (let i = 0; i < 7; i++) {
        let y = -rnd(0, n);
        while (y < n) {
          const len = rnd(n * .6, n * 1.4);
          g.fillStyle = `hsl(${rnd(30, 36)}, ${rnd(35, 45)}%, ${rnd(58, 66)}%)`; g.fillRect(i * pw, y, pw, len);
          g.fillStyle = "rgba(80,45,15,.25)"; g.fillRect(i * pw, y, pw, 2); y += len;
        }
        g.fillStyle = "rgba(60,30,10,.25)"; g.fillRect(i * pw, 0, 2, n);
      }
    }, [1 / 1.4, 1 / 1.4]);
    const tile = tiles(4, 4, [30, 5, 88], "#8a8782", 2); tile.repeat.set(1 / 1.2, 1 / 1.2);
    Object.assign(M, {
      boards: new THREE.MeshStandardMaterial({ map: boards, roughness: .35 }),
      tile: new THREE.MeshStandardMaterial({ map: tile, roughness: .35 }),
      kitchen: mat(0xf8f7f2, { roughness: .2 }), counter: mat(0x3a2c26, { roughness: .5 }),
      balcony: mat(0xcfcac2, { roughness: .9 }), rail: mat(0x6d6a66, { roughness: .6 }),
    });

    const LIVING = [[0, 0], [500, 0], [500, 450], [0, 450]];
    const BED = [[500, 0], [880, 0], [880, 450], [500, 450]];
    const KITCHEN = [[0, 450], [320, 450], [320, 720], [0, 720]];
    const HALL = [[320, 450], [600, 450], [600, 720], [320, 720]];
    const BATH = [[600, 450], [880, 450], [880, 720], [600, 720]];
    const BALCONY = [[120, -150], [420, -150], [420, 0], [120, 0]];
    flatFloor(LIVING, M.boards, 0); flatFloor(BED, M.boards, 0); flatFloor(HALL, M.boards, 0);
    flatFloor(KITCHEN, M.tile, .003); flatFloor(BATH, M.tile, .003); flatFloor(BALCONY, M.balcony, -.02);

    // Outside walls
    wall([0, 0], [880, 0], { ext: true, openings: [[1.3, 2.3, "door"], [2.6, 4.4, "window", .85, 2.35, 2], [6.0, 7.6, "window", .85, 2.35, 2]] });
    wall([0, 0], [0, 720], { ext: true, openings: [[1.5, 2.9, "window", .85, 2.35, 2]] });
    wall([880, 0], [880, 720], { ext: true });
    wall([0, 720], [880, 720], { ext: true, openings: [[4.0, 5.0, "door"]] });
    // Inside walls
    wall([500, 0], [500, 450], { t: .12 });
    wall([0, 450], [880, 450], { t: .12, openings: [[3.6, 4.5, "door"], [5.2, 6.0, "door"]] });
    wall([320, 450], [320, 720], { t: .12, openings: [[.8, 1.7, "door"]] });
    wall([600, 450], [600, 720], { t: .12, openings: [[.9, 1.7, "door"]] });

    box(120, -150, 420, -144, 1.0, M.rail, { group: fixed }); box(120, -150, 126, 0, 1.0, M.rail, { group: fixed }); box(414, -150, 420, 0, 1.0, M.rail, { group: fixed });

    // What comes with the flat
    named("fitted kitchen with sink and hob", box(5, 455, 315, 515, .9, M.kitchen, { group: fixed }), box(3, 453, 317, 515, .04, M.counter, { y: .9, group: fixed }), box(5, 455, 315, 490, .7, M.kitchen, { y: 1.5, group: fixed }));
    named("shower", box(800, 640, 875, 715, .05, M.porcelain, { group: fixed }));
    named("toilet", box(820, 460, 870, 520, .4, M.porcelain, { group: fixed }));
    named("washbasin", box(640, 680, 720, 715, .18, M.porcelain, { y: .8, group: fixed }));
    named("radiators under the windows", box(270, 8, 430, 16, .55, M.white, { y: .2, group: fixed }), box(610, 8, 750, 16, .55, M.white, { y: .2, group: fixed }));

    // A possible layout, hidden until Furniture
    box(530, 120, 690, 320, .5, M.bed, { label: "bed 160 × 200" });
    box(780, 200, 870, 440, 2.2, M.wood, { label: "wardrobe" });
    box(40, 250, 260, 340, .85, M.sofa, { label: "sofa" });
    box(80, 100, 260, 200, .01, M.rug, { label: "rug" });
    box(330, 300, 470, 380, .75, M.wood, { label: "desk by the window" });
    box(40, 600, 160, 700, .75, M.wood, { label: "kitchen table" });
    box(160, -120, 220, -60, .7, M.plant, { label: "plants on the balcony" });

    tagAt(`Living room <i>≈${area(LIVING).toFixed(0)} m²</i>`, 250, 225);
    tagAt(`Bedroom <i>≈${area(BED).toFixed(0)} m²</i>`, 690, 225);
    tagAt(`Kitchen <i>≈${area(KITCHEN).toFixed(0)} m²</i>`, 160, 585);
    tagAt(`Hall <i>≈${area(HALL).toFixed(0)} m²</i>`, 460, 585);
    tagAt(`Bath <i>≈${area(BATH).toFixed(0)} m²</i>`, 740, 585);
    tagAt("balcony · courtyard, south", 270, -75);
    tagAt("entrance", 450, 700, "", .3);
  },
};
