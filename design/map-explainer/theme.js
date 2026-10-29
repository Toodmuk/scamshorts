// ทันท่วงที — "map explainer" theme (light street-map stage + presenter mascot).
// Draws in logical 1080x1920. Pure functions of their inputs.
'use strict';
const W = 1080, HH = 1920;
const C = {
  sea: '#a8d4f2', land: '#f6f3ec', near: '#e9e5dc', urban: '#ece5d8', border: '#cfc6b6', provLine: '#dcd4c4',
  road: '#ffffff', roadEdge: '#d8cfbf', rail: '#b9b1a3', river: '#93c9ee',
  navy: '#1c2b4b', red: '#e0262b', redSoft: 'rgba(224,38,43,0.16)', yellow: '#ffc700', blue: '#2f6fe4',
  white: '#ffffff', muted: '#6b7280', card: '#ffffff', skin: '#f3c9a1', hair: '#1f1a17', pants: '#24345e',
};

// ---------------- camera / projection
const K = Math.cos(13 * Math.PI / 180);
const project = (cam) => ([lon, lat]) => [W / 2 + (lon * K - cam.lon * K) * cam.s, cam.cy - (lat - cam.lat) * cam.s];
const camFit = (lon0, lat0, lon1, lat1, top = 260, bottom = 1500) => {
  const s = Math.min((W - 80) / ((lon1 - lon0) * K), (bottom - top) / (lat1 - lat0));
  return { lon: (lon0 + lon1) / 2, lat: (lat0 + lat1) / 2, s, cy: (top + bottom) / 2 };
};
const camLerp = (a, b, t) => ({ lon: a.lon + (b.lon - a.lon) * t, lat: a.lat + (b.lat - a.lat) * t,
  s: Math.exp(Math.log(a.s) + (Math.log(b.s) - Math.log(a.s)) * t), cy: a.cy + (b.cy - a.cy) * t });

function path(c, P, ring) { ring.forEach((p, i) => { const [x, y] = P(p); i ? c.lineTo(x, y) : c.moveTo(x, y); }); }

// ---------------- base map
function drawMap(c, M, cam, opts = {}) {
  const P = project(cam);
  c.fillStyle = C.sea; c.fillRect(0, 0, W, HH);
  for (const L of M.land) { if (L.c === 'THA') continue; c.fillStyle = C.near;
    for (const r of L.p) { c.beginPath(); path(c, P, r); c.closePath(); c.fill(); } }
  c.fillStyle = C.land; for (const rings of Object.values(M.prov)) for (const r of rings) { c.beginPath(); path(c, P, r); c.closePath(); c.fill(); }
  c.fillStyle = C.urban; for (const r of M.urban) { c.beginPath(); path(c, P, r); c.closePath(); c.fill(); }
  // provinces
  c.lineWidth = Math.min(3.5, Math.max(1.6, cam.s / 200)); c.strokeStyle = C.border;
  for (const [name, rings] of Object.entries(M.prov)) for (const r of rings) {
    c.beginPath(); path(c, P, r); c.closePath();
    if (opts.hot === name) { c.fillStyle = C.redSoft; c.fill(); }
    c.stroke();
  }
  // water
  c.fillStyle = C.river; for (const r of M.lakes) { c.beginPath(); path(c, P, r); c.closePath(); c.fill(); }
  c.strokeStyle = C.river; c.lineCap = 'round'; c.lineJoin = 'round';
  for (const rv of M.rivers) { c.lineWidth = Math.max(1.5, (10 - rv.r) * cam.s / 900); c.beginPath(); path(c, P, rv.c); c.stroke(); }
  // rail
  c.strokeStyle = C.rail; c.lineWidth = Math.max(1.2, cam.s / 500); c.setLineDash([6, 6]);
  for (const l of M.rail) { c.beginPath(); path(c, P, l); c.stroke(); } c.setLineDash([]);
  // roads (edge then fill)
  const wv = (r) => (r === 1 ? 1 : 0.6) * Math.max(3, Math.min(16, cam.s / 38));
  for (const pass of [0, 1]) for (const rd of M.roads) {
    if (pass === 0) { c.strokeStyle = rd.r === 1 ? '#e2b052' : '#cbbfa9'; c.lineWidth = wv(rd.r) + 3; }
    else { c.strokeStyle = rd.r === 1 ? '#ffd47e' : C.road; c.lineWidth = wv(rd.r); }
    c.beginPath(); path(c, P, rd.c); c.stroke();
  }
  if (cam.s > 260) {        // province names when zoomed in
    c.textAlign = 'center'; c.font = '700 34px "Kanit"';
    for (const [name, rings] of Object.entries(M.prov)) {
      let x = 0, y = 0, n = 0; for (const r of rings) for (const [a, b] of r) { x += a; y += b; n++; }
      const [px, py] = P([x / n, y / n]); if (px < 60 || px > W - 60 || py < 240 || py > 1500 || name === opts.hot) continue;
      if (M.towns.some((t) => t.th === name)) continue;        // the town label already says it
      c.lineWidth = 7; c.strokeStyle = 'rgba(246,243,236,0.9)'; c.strokeText(name, px, py + 50); c.fillStyle = '#9a8f7c'; c.fillText(name, px, py + 50);
    }
    c.textAlign = 'left';
  }
  // hot province outline
  if (opts.hot && M.prov[opts.hot]) {
    c.strokeStyle = C.red; c.lineWidth = 5; c.setLineDash([16, 10]);
    for (const r of M.prov[opts.hot]) { c.beginPath(); path(c, P, r); c.closePath(); c.stroke(); }
    c.setLineDash([]);
  }
  // towns
  if (opts.towns !== false) {
    c.textAlign = 'center';
    const lim = cam.s > 300 ? 10 : cam.s > 140 ? 6 : 3;
    for (const t of M.towns) {
      if ((t.r || 9) > lim) continue;
      const [x, y] = P([t.x, t.y]); if (x < 30 || x > W - 30 || y < 220 || y > 1560) continue;
      c.fillStyle = C.white; c.strokeStyle = C.muted; c.lineWidth = 3; c.beginPath(); c.arc(x, y, 7, 0, 7); c.fill(); c.stroke();
      c.font = '500 30px "Kanit"'; c.lineWidth = 6; c.strokeStyle = 'rgba(255,255,255,0.9)'; c.strokeText(t.th, x, y - 16);
      c.fillStyle = '#4b5563'; c.fillText(t.th, x, y - 16);
    }
    c.textAlign = 'left';
  }
  return P;
}
function provinceCenter(M, name) {
  let x = 0, y = 0, n = 0; for (const r of M.prov[name]) for (const [a, b] of r) { x += a; y += b; n++; } return [x / n, y / n];
}
function provinceBox(M, name) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const r of M.prov[name]) for (const [a, b] of r) { x0 = Math.min(x0, a); x1 = Math.max(x1, a); y0 = Math.min(y0, b); y1 = Math.max(y1, b); }
  return [x0, y0, x1, y1];
}

// ---------------- UI pieces
function shadowed(c, fn, blur = 24, oy = 10, a = 0.18) { c.save(); c.shadowColor = `rgba(20,30,60,${a})`; c.shadowBlur = blur; c.shadowOffsetY = oy; fn(); c.restore(); }
function rrect(c, x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }
function pill(c, txt, x, y, opts = {}) {     // white label pill centred on x
  const size = opts.size || 38; c.font = `${opts.weight || 700} ${size}px "Kanit"`;
  const w = c.measureText(txt).width + (opts.dot ? 70 : 44), h = size * 1.6;
  shadowed(c, () => { c.fillStyle = opts.bg || C.white; rrect(c, x - w / 2, y - h / 2, w, h, h / 2); c.fill(); }, 16, 6, 0.2);
  if (opts.border) { c.strokeStyle = opts.border; c.lineWidth = 4; rrect(c, x - w / 2, y - h / 2, w, h, h / 2); c.stroke(); }
  if (opts.dot) { c.fillStyle = opts.dot; c.beginPath(); c.arc(x - w / 2 + 30, y, 10, 0, 7); c.fill(); }
  c.fillStyle = opts.fg || C.navy; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillText(txt, x + (opts.dot ? 14 : 0), y + 2); c.textAlign = 'left'; c.textBaseline = 'alphabetic';
  return w;
}
function pin(c, x, y, s = 1, col = C.red) {
  c.save(); c.translate(x, y); c.scale(s, s);
  shadowed(c, () => { c.fillStyle = col; c.beginPath(); c.moveTo(0, 0); c.bezierCurveTo(-34, -40, -40, -62, -40, -78);
    c.arc(0, -78, 40, Math.PI, 0); c.bezierCurveTo(40, -62, 34, -40, 0, 0); c.fill(); }, 14, 6, 0.3);
  c.fillStyle = C.white; c.beginPath(); c.arc(0, -78, 16, 0, 7); c.fill(); c.restore();
}
function zone(c, x, y, r, pulse = 0) {
  c.fillStyle = 'rgba(224,38,43,0.14)'; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill();
  c.strokeStyle = 'rgba(224,38,43,0.85)'; c.lineWidth = 5; c.beginPath(); c.arc(x, y, r, 0, 7); c.stroke();
  if (pulse > 0) { c.strokeStyle = `rgba(224,38,43,${0.5 * (1 - pulse)})`; c.lineWidth = 4; c.beginPath(); c.arc(x, y, r * (1 + 0.35 * pulse), 0, 7); c.stroke(); }
}
// captions: navy with red key words and a white halo, centred
function caption(c, lines, y, opts = {}) {
  const size = opts.size || 60; c.textAlign = 'left'; c.lineJoin = 'round';
  lines.forEach((parts, i) => {
    c.font = `${opts.weight || 800} ${size}px "Kanit"`;
    const segs = Array.isArray(parts) ? parts : [[parts, false]];
    const total = segs.reduce((s, [t]) => s + c.measureText(t).width, 0);
    let x = W / 2 - total / 2; const yy = y + i * size * 1.3;
    for (const [t, hi] of segs) {
      c.lineWidth = size * 0.28; c.strokeStyle = 'rgba(255,255,255,0.96)'; c.strokeText(t, x, yy);
      c.fillStyle = hi ? C.red : C.navy; c.fillText(t, x, yy); x += c.measureText(t).width;
    }
  });
}
function chip(c, txt, x, y) {                 // small top-left channel chip
  c.font = '700 34px "Kanit"'; const w = c.measureText(txt).width + 40;
  shadowed(c, () => { c.fillStyle = C.navy; rrect(c, x, y, w, 56, 28); c.fill(); }, 10, 4, 0.2);
  c.fillStyle = C.yellow; c.fillText(txt, x + 20, y + 40);
}
function card(c, x, y, w, h, r = 30) { shadowed(c, () => { c.fillStyle = C.card; rrect(c, x, y, w, h, r); c.fill(); }); }
function fitFont(c, txt, weight, size, maxW, fam = 'Kanit') { let s = size; c.font = `${weight} ${s}px "${fam}"`; while (c.measureText(txt).width > maxW && s > 24) { s -= 2; c.font = `${weight} ${s}px "${fam}"`; } return s; }

// ---------------- the presenter mascot "น้องทัน" (original character)
// pose: wave | point | shock | phone | megaphone | thumb ; mouth 0..1 ; blink 0..1
function mascot(c, x, y, s, pose = 'wave', mouth = 0.3, blink = 0) {
  c.save(); c.translate(x, y); c.scale(s, s);
  c.lineCap = 'round'; c.lineJoin = 'round';
  // shadow on the ground
  c.fillStyle = 'rgba(20,30,60,0.18)'; c.beginPath(); c.ellipse(0, 6, 120, 22, 0, 0, 7); c.fill();
  // legs + shoes
  c.fillStyle = C.pants; rrect(c, -62, -190, 52, 190, 22); c.fill(); rrect(c, 10, -190, 52, 190, 22); c.fill();
  c.fillStyle = '#2b2b2b'; rrect(c, -78, -24, 74, 30, 14); c.fill(); rrect(c, 6, -24, 74, 30, 14); c.fill();
  // arms behind/in front depending on pose
  const arm = (sx, sy, ex, ey, hx, hy, holding) => {
    c.strokeStyle = C.yellow; c.lineWidth = 44; c.beginPath(); c.moveTo(sx, sy); c.quadraticCurveTo(ex, ey, hx, hy); c.stroke();
    c.strokeStyle = '#e6b400'; c.lineWidth = 6; c.beginPath(); c.moveTo(hx - 8, hy - 8); c.lineTo(hx + 8, hy + 8); c.stroke();
    c.fillStyle = C.skin; c.beginPath(); c.arc(hx, hy, 24, 0, 7); c.fill();
    if (holding === 'phone') { c.fillStyle = C.navy; rrect(c, hx - 22, hy - 62, 44, 78, 10); c.fill(); c.fillStyle = '#8fc3ff'; rrect(c, hx - 16, hy - 54, 32, 56, 6); c.fill(); c.fillStyle = C.skin; c.beginPath(); c.arc(hx, hy + 6, 22, 0, 7); c.fill(); }
    if (holding === 'mega') { c.fillStyle = C.red; c.beginPath(); c.moveTo(hx, hy - 20); c.lineTo(hx + 120, hy - 70); c.lineTo(hx + 120, hy + 40); c.lineTo(hx, hy + 14); c.closePath(); c.fill();
      c.fillStyle = '#b81d22'; c.beginPath(); c.ellipse(hx + 120, hy - 15, 16, 55, 0, 0, 7); c.fill(); c.fillStyle = C.skin; c.beginPath(); c.arc(hx, hy, 24, 0, 7); c.fill(); }
    if (holding === 'thumb') { c.fillStyle = C.skin; rrect(c, hx - 8, hy - 52, 18, 40, 9); c.fill(); }
  };
  const L = { wave: [-70, -330, -150, -420, -170, -520], point: [-70, -330, -150, -330, -230, -380], shock: [-70, -330, -140, -400, -110, -470],
    phone: [-70, -330, -120, -300, -60, -400], megaphone: [-70, -330, -110, -320, -40, -360], thumb: [-70, -330, -150, -340, -170, -420] }[pose];
  const R = pose === 'shock' ? [70, -330, 140, -400, 110, -470] : [70, -330, 110, -270, 92, -200];
  // body (hoodie)
  c.fillStyle = C.yellow; rrect(c, -95, -400, 190, 230, 60); c.fill();
  c.fillStyle = '#e6b400'; rrect(c, -55, -260, 110, 52, 18); c.fill();                 // pocket
  c.fillStyle = C.red; c.beginPath(); c.arc(42, -340, 24, 0, 7); c.fill();             // badge
  c.fillStyle = C.white; c.font = '900 34px "Kanit"'; c.textAlign = 'center'; c.fillText('!', 42, -328); c.textAlign = 'left';
  arm(R[0], R[1], R[2], R[3], R[4], R[5]);
  arm(L[0], L[1], L[2], L[3], L[4], L[5], pose === 'phone' ? 'phone' : pose === 'megaphone' ? 'mega' : pose === 'thumb' ? 'thumb' : null);
  // neck + head
  c.fillStyle = C.skin; rrect(c, -22, -430, 44, 40, 12); c.fill();
  c.beginPath(); c.ellipse(0, -520, 92, 100, 0, 0, 7); c.fill();
  c.beginPath(); c.ellipse(-90, -515, 16, 22, 0, 0, 7); c.ellipse(90, -515, 16, 22, 0, 0, 7); c.fill();   // ears
  // hair under the cap
  c.fillStyle = C.hair; c.beginPath(); c.ellipse(0, -585, 90, 46, 0, Math.PI, 0); c.fill();
  // cap (red) with yellow badge, brim to the side
  c.fillStyle = C.red; c.beginPath(); c.ellipse(0, -600, 96, 64, 0, Math.PI, 0); c.fill(); rrect(c, -96, -606, 192, 22, 8); c.fill();
  c.beginPath(); c.ellipse(70, -588, 74, 16, -0.08, 0, 7); c.fill();
  c.fillStyle = C.yellow; c.beginPath(); c.arc(0, -632, 18, 0, 7); c.fill();
  // face
  const ey = -520, eh = 22 * (1 - blink) + 2;
  c.fillStyle = C.hair; c.beginPath(); c.ellipse(-34, ey, 12, eh, 0, 0, 7); c.ellipse(34, ey, 12, eh, 0, 0, 7); c.fill();
  if (blink < 0.5) { c.fillStyle = C.white; c.beginPath(); c.arc(-30, ey - 7, 4, 0, 7); c.arc(38, ey - 7, 4, 0, 7); c.fill(); }
  c.strokeStyle = C.hair; c.lineWidth = 7;
  const lift = pose === 'shock' ? 14 : 0;
  c.beginPath(); c.arc(-34, -548 - lift, 22, Math.PI * 1.15, Math.PI * 1.85); c.stroke();
  c.beginPath(); c.arc(34, -548 - lift, 22, Math.PI * 1.15, Math.PI * 1.85); c.stroke();
  c.fillStyle = 'rgba(240,120,110,0.45)'; c.beginPath(); c.ellipse(-56, -484, 16, 10, 0, 0, 7); c.ellipse(56, -484, 16, 10, 0, 0, 7); c.fill();
  const mo = pose === 'shock' ? Math.max(0.8, mouth) : mouth;
  if (pose === 'shock') { c.fillStyle = '#7a2a2a'; c.beginPath(); c.ellipse(0, -466, 20, 10 + 18 * mo, 0, 0, 7); c.fill(); }
  else {   // smile; the jaw drops into an open smile while talking
    c.fillStyle = '#7a2a2a'; c.beginPath(); c.moveTo(-30, -478); c.quadraticCurveTo(0, -478 + 10 + 34 * mo, 30, -478);
    c.quadraticCurveTo(0, -478 + 4 + 8 * mo, -30, -478); c.fill();
    if (mo > 0.35) { c.fillStyle = '#e46a6a'; c.beginPath(); c.ellipse(0, -478 + 18 * mo, 12, 6 * mo, 0, 0, 7); c.fill(); }
    c.strokeStyle = '#7a2a2a'; c.lineWidth = 5; c.beginPath(); c.moveTo(-32, -479); c.quadraticCurveTo(0, -470 + 30 * mo, 32, -479); c.stroke();
  }
  c.restore();
}

module.exports = { W, HH, C, project, camFit, camLerp, drawMap, provinceCenter, provinceBox, pill, pin, zone, caption, chip, card, rrect, shadowed, fitFont, mascot };
