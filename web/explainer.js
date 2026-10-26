// ทันท่วงที — Constructivist Propaganda explainer engine.
// Turns the daily script (JSON) into a vertical 1080x1920 animated explainer in the style of the
// AI Style Atlas "Constructivist Propaganda" reference: litho paper, ink mottle, halftone photomontage,
// slogans slammed onto slanted bars on twos, heavy bar arrows, Lissitzky's red wedge between scenes.
// Every frame is a pure function of t (seeded randomness only). Needs window.H (harness.js) and
// window.SOUND (sound.js). Works in a browser and in Node (node-canvas + node-web-audio-api).
(function (root) {
  'use strict';
  const H = root.H;
  const W = 1080, HH = 1920, FPS = 15;
  const RED = '#c8281e', BLACK = '#1d1a17', CREAM = '#e9dcbc';
  const E = H.ease, cl = H.clamp;
  const P = (u, a, b) => cl((u - a) / (b - a), 0, 1);            // progress of u between a and b
  const HOOK_OUT = 1.9;                                             // scene 1 content starts entering here

  // ------------------------------------------------------------------ textures (reference functions)
  const fieldNoise = (w, h, seed, cell, oct, sx = 1, sy = 1) => {
    const nz = H.makeNoise(seed), gw = Math.ceil(w / cell) + 2, gh = Math.ceil(h / cell) + 2, g = new Float32Array(gw * gh);
    for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) g[j * gw + i] = nz.fbm2(i * 0.35 * sx, j * 0.35 * sy, oct);
    const out = new Float32Array(w * h);
    for (let y = 0; y < h; y++) {
      const fy = y / cell, j = fy | 0, ty = fy - j;
      for (let x = 0; x < w; x++) {
        const fx = x / cell, i = fx | 0, tx = fx - i, k = j * gw + i;
        const a = g[k] + (g[k + 1] - g[k]) * tx, b = g[k + gw] + (g[k + gw + 1] - g[k + gw]) * tx;
        out[y * w + x] = a + (b - a) * ty;
      }
    }
    return out;
  };
  const inkify = (layer, seed, mottle, speck) => {
    const c = layer.getContext('2d'), w = layer.width, h = layer.height, img = c.getImageData(0, 0, w, h), d = img.data;
    const n1 = fieldNoise(w, h, seed, 4, 3), n2 = fieldNoise(w, h, seed + 9, 36, 3), r = H.rng(seed + 3);
    for (let i = 0, p = 0; i < d.length; i += 4, p++) {
      if (!d[i + 3]) continue;
      let a = 1 - mottle * Math.max(0, n1[p] * 1.7 + n2[p] * 1.1);
      if (r() < speck * (0.3 + Math.max(0, n2[p]) * 4)) a *= 0.2;
      d[i + 3] *= H.clamp(a, 0, 1);
    }
    c.putImageData(img, 0, 0);
  };
  const CACHE = {}; const CF = (k, ...a) => CACHE[k] || (CACHE[k] = fieldNoise(...a));
  const exInk = (layer, seed, mottle, speck = 0) => {
    const c = layer.getContext('2d'), w = layer.width, h = layer.height, img = c.getImageData(0, 0, w, h), d = img.data;
    const n1 = CF('ei1' + w + 'x' + h, w, h, seed, 4, 3), n2 = CF('ei2' + w + 'x' + h, w, h, seed + 9, 36, 3);
    const key = 'rnd' + w + 'x' + h;
    const rnd = CACHE[key] || (CACHE[key] = (() => { const r = H.rng(seed + 3), a = new Float32Array(w * h); for (let i = 0; i < a.length; i++) a[i] = r(); return a; })());
    for (let i = 0, p = 0; i < d.length; i += 4, p++) {
      if (!d[i + 3]) continue;
      const m = n2[p] > 0 ? n2[p] : 0;
      let a = 1 - mottle * Math.max(0, n1[p] * 1.7 + n2[p] * 1.1);
      if (rnd[p] < speck * (0.3 + m * 4)) a *= 0.2;
      d[i + 3] *= a < 0 ? 0 : a > 1 ? 1 : a;
    }
    c.putImageData(img, 0, 0);
  };
  let PAPER = null;
  const paperC = () => PAPER || (PAPER = (() => {
    const cv = H.layer(W, HH), x = cv.getContext('2d'), img = x.createImageData(W, HH), pd = img.data;
    const lo = CF('lo', W, HH, 41, 22, 4), fib = CF('fib', W, HH, 42, 2, 2, 4, 0.5), r0 = H.rng(5), base = H.hex(CREAM), tan = H.hex('#b99a62');
    for (let y = 0, p = 0; y < HH; y++) for (let xx = 0; xx < W; xx++, p++) {
      const ex = Math.min(xx, W - xx) / W, ey = Math.min(y, HH - y) / HH;
      const edge = Math.pow(1 - H.clamp(Math.min(ex * 4, ey * 3) + lo[p] * 0.2, 0, 1), 3), k = 0.4 * edge + 0.16 * Math.max(0, lo[p]);
      const s = 1 + fib[p] * 0.04 + (r0() - 0.5) * 0.05, i = p * 4;
      pd[i] = (base[0] + (tan[0] - base[0]) * k) * s; pd[i + 1] = (base[1] + (tan[1] - base[1]) * k) * s; pd[i + 2] = (base[2] + (tan[2] - base[2]) * k) * s; pd[i + 3] = 255;
    }
    x.putImageData(img, 0, 0); return cv;
  })());
  const scratches = (ctx) => {   // worn-print finish, same seed every frame
    const rs = H.rng(88);
    ctx.save(); ctx.strokeStyle = 'rgba(250,244,228,0.35)'; ctx.lineWidth = 1.5;
    for (let i = 0; i < 60; i++) { const x = rs.range(0, W), y = rs.range(0, HH), l = rs.range(8, 60), a2 = rs.range(0, 3); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(a2) * l, y + Math.sin(a2) * l); ctx.stroke(); }
    ctx.restore();
  };

  // ------------------------------------------------------------------ halftone photomontage
  const screenPhoto = (fn, w, h, seed = 19, S = 8.8, gam = 1) => {
    const PH = H.layer(w, h), pc = PH.getContext('2d'); fn(pc);
    const pdat = pc.getImageData(0, 0, w, h).data;
    const HT = H.layer(w, h), hc = HT.getContext('2d');
    const th = Math.PI / 4, cs = Math.cos(th), sn = Math.sin(th), ext = Math.hypot(w, h);
    hc.fillStyle = BLACK; hc.beginPath();
    for (let v = -ext / S; v < ext / S; v++) for (let u = -ext / S; u < ext / S; u++) {
      const x = (u * cs - v * sn) * S + w / 2, y = (u * sn + v * cs) * S + h / 2;
      if (x < 0 || y < 0 || x >= w || y >= h) continue;
      const k = ((y | 0) * w + (x | 0)) * 4;
      if (pdat[k + 3] / 255 < 0.5) continue;
      const lum = gam === 1 ? pdat[k] / 255 : Math.pow(pdat[k] / 255, gam);
      const rad = S * 0.62 * Math.sqrt(Math.pow(1 - lum, 0.9)) + 0.35;
      hc.moveTo(x + rad, y); hc.arc(x, y, rad, 0, Math.PI * 2);
    }
    hc.fill();
    const SIL = H.layer(w, h), sc = SIL.getContext('2d');
    sc.drawImage(PH, 0, 0); sc.globalCompositeOperation = 'source-in'; sc.fillStyle = '#efe5cc'; sc.fillRect(0, 0, w, h);
    inkify(HT, seed, 0.18, 0.004);
    return { PH, HT, SIL, w, h };
  };
  const paste = (ctx, Pp, x, y, s = 1, rot = 0) => {
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
    const ro = Math.max(1, 3.2 / Math.max(0.05, s) / 4);
    for (const [dx, dy] of [[-4, 0], [4, 0], [0, -4], [0, 4], [-3, -3], [3, 3], [3, -3], [-3, 3]]) ctx.drawImage(Pp.SIL, dx * ro, dy * ro);
    ctx.drawImage(Pp.SIL, 0, 0);
    ctx.globalAlpha = 0.18; ctx.globalCompositeOperation = 'multiply'; ctx.drawImage(Pp.PH, 0, 0);
    ctx.globalAlpha = 1; ctx.drawImage(Pp.HT, 1.5, -1);
    ctx.restore();
  };

  // grayscale "photographs" (invented generic props: no real logos or emblems)
  const grad = (c, x0, y0, x1, y1, stops) => { const g = c.createLinearGradient(x0, y0, x1, y1); stops.forEach(([o, v]) => g.addColorStop(o, `rgb(${v},${v},${v})`)); return g; };
  const rr = (c, x, y, w, h, r) => { c.beginPath(); c.roundRect(x, y, w, h, r); };
  const drawPhoneHand = (c) => {            // 760 x 1100
    c.fillStyle = grad(c, 250, 820, 600, 1100, [[0, 90], [0.5, 190], [1, 120]]);
    c.beginPath(); c.moveTo(240, 1100); c.lineTo(290, 820); c.lineTo(560, 790); c.lineTo(610, 1100); c.closePath(); c.fill();
    c.fillStyle = grad(c, 170, 520, 640, 900, [[0, 110], [0.6, 205], [1, 150]]); rr(c, 160, 520, 480, 390, 130); c.fill();
    c.fillStyle = grad(c, 200, 60, 580, 880, [[0, 45], [0.5, 75], [1, 30]]); rr(c, 200, 60, 380, 800, 48); c.fill();
    c.fillStyle = grad(c, 222, 92, 560, 840, [[0, 214], [1, 242]]); rr(c, 222, 92, 336, 736, 30); c.fill();
    c.fillStyle = 'rgb(105,105,105)'; rr(c, 222, 92, 336, 84, 30); c.fill(); c.fillRect(222, 140, 336, 36);
    c.fillStyle = 'rgb(200,200,200)'; c.beginPath(); c.arc(272, 134, 22, 0, 7); c.fill();
    c.fillStyle = 'rgb(165,165,165)'; rr(c, 245, 214, 230, 92, 26); c.fill(); rr(c, 245, 324, 262, 124, 26); c.fill();
    c.fillStyle = 'rgb(135,135,135)'; rr(c, 322, 470, 214, 84, 26); c.fill();
    c.fillStyle = 'rgb(165,165,165)'; rr(c, 245, 576, 240, 92, 26); c.fill();
    c.fillStyle = grad(c, 120, 520, 300, 720, [[0, 120], [0.5, 218], [1, 150]]); c.beginPath(); c.ellipse(222, 650, 54, 124, -0.5, 0, 7); c.fill();
    for (let i = 0; i < 4; i++) { c.fillStyle = grad(c, 540, 0, 650, 0, [[0, 120], [0.5, 222], [1, 140]]); c.beginPath(); c.ellipse(588, 410 + i * 96, 64, 42, 0.15, 0, 7); c.fill(); }
    c.strokeStyle = 'rgb(255,255,255)'; c.lineWidth = 7; c.beginPath(); c.moveTo(250, 760); c.lineTo(350, 660); c.stroke();
  };
  const drawSheet = (c) => { c.fillStyle = grad(c, 0, 0, 560, 720, [[0, 248], [1, 214]]); rr(c, 20, 20, 520, 680, 6); c.fill(); };
  const drawBank = (c) => {                 // 560 x 720: statement / slip
    drawSheet(c);
    c.fillStyle = 'rgb(55,55,55)'; c.fillRect(50, 50, 460, 74);
    c.fillStyle = 'rgb(225,225,225)'; c.fillRect(70, 72, 150, 14); c.fillRect(70, 96, 100, 10);
    for (let i = 0; i < 9; i++) {
      const y = 160 + i * 52; c.fillStyle = i % 2 ? 'rgb(200,200,200)' : 'rgb(228,228,228)'; c.fillRect(50, y, 460, 44);
      c.fillStyle = 'rgb(85,85,85)'; c.fillRect(70, y + 16, 150 + (i * 37) % 60, 12); c.fillRect(390, y + 16, 100, 12);
    }
    c.fillStyle = 'rgb(40,40,40)'; c.fillRect(270, 640, 240, 30);
  };
  const drawOfficial = (c) => {             // 560 x 720: official-looking letter with a generic seal
    drawSheet(c);
    c.strokeStyle = 'rgb(50,50,50)'; c.lineWidth = 9; c.beginPath(); c.arc(280, 150, 78, 0, 7); c.stroke();
    c.lineWidth = 4; c.beginPath(); c.arc(280, 150, 60, 0, 7); c.stroke();
    c.fillStyle = 'rgb(45,45,45)'; c.beginPath();
    for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 18 : 44; c.lineTo(280 + Math.cos(a) * r, 150 + Math.sin(a) * r); }
    c.closePath(); c.fill();
    c.fillStyle = 'rgb(60,60,60)'; c.fillRect(150, 260, 260, 20); c.fillRect(190, 292, 180, 14);
    c.fillStyle = 'rgb(140,140,140)'; for (let i = 0; i < 8; i++) c.fillRect(70, 340 + i * 30, 420 - (i % 3) * 50, 10);
    c.strokeStyle = 'rgb(40,40,40)'; c.lineWidth = 5; c.beginPath(); c.moveTo(320, 640); c.bezierCurveTo(350, 590, 380, 670, 410, 615); c.bezierCurveTo(430, 590, 450, 650, 490, 625); c.stroke();
    c.strokeStyle = 'rgb(90,90,90)'; c.lineWidth = 6; c.beginPath(); c.arc(140, 620, 48, 0, 7); c.stroke();
  };
  const drawForm = (c) => {                 // 560 x 720: a generic form / web page / ID request
    drawSheet(c);
    c.fillStyle = 'rgb(70,70,70)'; c.fillRect(50, 50, 460, 56);
    c.fillStyle = 'rgb(170,170,170)'; c.fillRect(60, 140, 150, 190);
    for (let i = 0; i < 4; i++) { c.fillStyle = 'rgb(120,120,120)'; c.fillRect(240, 150 + i * 46, 230, 14); }
    for (let i = 0; i < 5; i++) {
      const y = 380 + i * 58; c.strokeStyle = 'rgb(90,90,90)'; c.lineWidth = 4; c.strokeRect(60, y, 30, 30);
      c.fillStyle = 'rgb(140,140,140)'; c.fillRect(110, y + 9, 300 - (i % 2) * 80, 12);
    }
    c.fillStyle = 'rgb(45,45,45)'; c.fillRect(300, 650, 210, 36);
  };
  let PHOTOS = null;
  const photos = () => PHOTOS || (PHOTOS = {
    phone: screenPhoto(drawPhoneHand, 760, 1100, 19),
    bank: screenPhoto(drawBank, 560, 720, 23, 8.4, 0.8),
    official: screenPhoto(drawOfficial, 560, 720, 29, 8.4, 0.8),
    form: screenPhoto(drawForm, 560, 720, 31, 8.4, 0.8),
  });
  const docKind = (label) => /ธนาคาร|สเตท|สลิป|บัญชี|โอน|statement|slip/i.test(label) ? 'bank'
    : /ตำรวจ|ศาล|หมาย|ราชการ|กรม|อัยการ|DSI|ดีเอสไอ|ทางการ|official/i.test(label) ? 'official' : 'form';

  // ------------------------------------------------------------------ lettering, arrows, shapes
  let SEGS = {};
  const tokens = (ph) => {          // word breaks from Python (pythainlp), keeping spaces
    const out = [];
    ph.split(/(\s+)/).filter((x) => x.length).forEach((part) => {
      if (/^\s+$/.test(part)) out.push(' '); else (SEGS[part] || [part]).forEach((t) => out.push(t));
    });
    return out;
  };
  // wrap: phrase-first (break at spaces), word-level only when a phrase is too wide
  const UNITS = new Set(['บาท', 'ล้าน', 'ล้านบาท', 'หมื่น', 'พัน', 'คน', 'ราย', 'ครั้ง', 'วัน', 'เดือน', 'ปี', 'นาที', 'ชั่วโมง', '%']);
  const wrap = (c, txt, maxW) => {
    const phrases = [], lines = [];
    for (const ph of txt.split(/\s+/).filter(Boolean)) {   // keep numbers with their words: "356 บาท", "ลด 70%"
      if (phrases.length && (/^\d/.test(ph) || UNITS.has(ph))) phrases[phrases.length - 1] += ' ' + ph; else phrases.push(ph);
    }
    let line = '';
    const push = (ph) => {
      const cand = line ? line + ' ' + ph : ph;
      if (c.measureText(cand).width <= maxW) { line = cand; return true; }
      return false;
    };
    for (const ph of phrases) {
      if (push(ph)) continue;
      if (c.measureText(ph).width <= maxW) { if (line) lines.push(line); line = ph; continue; }
      // phrase too wide: start a fresh line and break it between words
      if (line) { lines.push(line); line = ''; }
      for (const tk of tokens(ph)) {
        const cand = line + tk;
        if (c.measureText(cand).width <= maxW || !line.trim()) line = cand;
        else { lines.push(line.trim()); line = tk.trim() ? tk : ''; }
      }
      line = line.trim();
    }
    if (line) lines.push(line);
    return lines;
  };
  const fitSize = (c, txt, font, size, maxW, min = 34) => {
    let s = size; c.font = font.replace('{s}', s);
    while (c.measureText(txt).width > maxW && s > min) { s -= 3; c.font = font.replace('{s}', s); }
    return s;
  };
  // slanted bar with lettering; p<1 shoots the bar across, text appears when it lands (on twos)
  const slab = (c, txt, x, y, ang, font, size, fg, bg, maxW = 940, padX = 20, padY = 12, p = 1) => {
    if (p <= 0 || !txt) return;
    c.save(); c.translate(x, y); c.rotate(ang);
    fitSize(c, txt, font, size, maxW);
    const m = c.measureText(txt), w = m.width + padX * 2, hgt = (m.actualBoundingBoxAscent + m.actualBoundingBoxDescent) + padY * 2;
    if (bg) { c.fillStyle = bg; c.fillRect(-padX, -m.actualBoundingBoxAscent - padY, w * Math.min(1, p), hgt); }
    if (p >= 1) { c.fillStyle = fg; c.fillText(txt, 0, 0); }
    c.restore();
  };
  // big slogan slammed down from oversize (k: 0 -> 1 over 3 frames), with an offset shadow
  const slogan = (c, txt, x, y, ang, size, fill, shadow, maxW, k = 1, font = '900 {s}px "Kanit"') => {
    if (k <= 0 || !txt) return;
    c.save(); c.translate(x, y); c.rotate(ang);
    const s = fitSize(c, txt, font, size, maxW, 40), sc = 1 + 0.6 * (1 - k);
    c.scale(sc, sc);
    if (shadow) { c.fillStyle = shadow; c.fillText(txt, s * 0.045, s * 0.045); }
    c.fillStyle = fill; c.fillText(txt, 0, 0); c.restore();
  };
  const barArrow = (c, x0, y0, x1, y1, p, w, col) => {
    if (p <= 0) return; const a = Math.atan2(y1 - y0, x1 - x0), l = Math.hypot(x1 - x0, y1 - y0) * p;
    c.save(); c.translate(x0, y0); c.rotate(a); c.fillStyle = col; c.fillRect(0, -w / 2, Math.max(0, l - w * 2.2), w);
    c.beginPath(); c.moveTo(l, 0); c.lineTo(l - w * 2.6, -w * 1.4); c.lineTo(l - w * 2.6, w * 1.4); c.closePath(); c.fill(); c.restore();
  };
  const disc = (c, x, y, r) => { if (r <= 0) return; c.fillStyle = RED; c.beginPath(); c.arc(x, y, r, 0, 7); c.fill(); };
  const beamsFrom = (c, x, y, list, len, p = 1) => list.forEach(([a, w], i) => {
    const pp = typeof p === 'function' ? p(i) : p; if (pp <= 0) return;
    c.fillStyle = i % 2 ? RED : BLACK; c.beginPath(); c.moveTo(x, y);
    c.lineTo(x + Math.cos(a - w) * len * pp, y + Math.sin(a - w) * len * pp); c.lineTo(x + Math.cos(a + w) * len * pp, y + Math.sin(a + w) * len * pp); c.closePath(); c.fill();
  });
  const box = (c, x, y, ang, w, h, p = 1) => { if (p <= 0) return; c.save(); c.translate(x, y); c.rotate(ang); c.fillStyle = BLACK; c.fillRect(-10, -h, w * p, h + 40); c.restore(); };
  const fmt = (n) => Math.round(n).toLocaleString('en-US');
  const stepIn = (u, a, n) => cl(Math.floor((u - a) * FPS) / n, 0, 1);   // 0..1 over n frames, on twos

  // ------------------------------------------------------------------ Thailand map
  const drawMap = (c, box4, target, hot) => {
    const M = root.TH_MAP; if (!M) return [0, 0];
    const k = Math.cos(13 * Math.PI / 180);
    if (!CACHE.mapBounds) {
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const rings of Object.values(M)) for (const r of rings) for (const [x, y] of r) { x0 = Math.min(x0, x * k); x1 = Math.max(x1, x * k); y0 = Math.min(y0, -y); y1 = Math.max(y1, -y); }
      CACHE.mapBounds = [x0, y0, x1, y1];
    }
    const [x0, y0, x1, y1] = CACHE.mapBounds;
    const s = Math.min((box4[2] - box4[0]) / (x1 - x0), (box4[3] - box4[1]) / (y1 - y0));
    const PJ = ([x, y]) => [box4[0] + (x * k - x0) * s, box4[1] + (-y - y0) * s];
    let cx = 0, cy = 0, n = 0;
    for (const [name, rings] of Object.entries(M)) for (const r of rings) {
      c.beginPath(); r.forEach((p, i) => { const [X, Y] = PJ(p); i ? c.lineTo(X, Y) : c.moveTo(X, Y); if (name === target) { cx += X; cy += Y; n++; } });
      c.closePath(); c.fillStyle = name === target && hot ? RED : BLACK; c.fill();
      c.strokeStyle = CREAM; c.lineWidth = 2.5; c.stroke();
    }
    return n ? [cx / n, cy / n] : [(box4[0] + box4[2]) / 2, (box4[1] + box4[3]) / 2];
  };

  // ------------------------------------------------------------------ the explainer
  function make(job) {
    const S0 = job.script, durs = job.durs, words = job.words || [];
    SEGS = job.segs || {};
    const channel = job.channel || '';
    const scenes = S0.scenes, n = scenes.length;
    const starts = []; { let t = 0; for (const d of durs) { starts.push(t); t += d; } }
    const DURATION = starts[starts.length - 1] + durs[durs.length - 1];
    const endStart = starts[n], endDur = durs[n];
    const t1441 = ((words[n] || []).find(([, w]) => w === '1441') || [null])[0];
    const ctaAt = endStart + cl(t1441 == null ? endDur * 0.55 : t1441 - 0.35, Math.min(1.8, endDur * 0.4), Math.max(endDur - 2.2, endDur * 0.4));

    // beat kinds per scene
    const kindOf = (s) => s.visual ? s.visual.type : (s.stamp ? 'reveal' : 'chat');
    const kinds = scenes.map(kindOf);
    // the red wedge drives across where the story really moves on (max 3, the call to action always gets one)
    const numberish = (k) => ['money', 'stat', 'compare', 'bars', 'percent'].includes(k);
    let wedgeAt = [];
    for (let j = 1; j < n; j++) {
      if (kinds[j] === 'map' || ((kinds[j] === 'chat' || kinds[j] === 'proof') && numberish(kinds[j - 1]))) wedgeAt.push(starts[j]);
    }
    wedgeAt = wedgeAt.slice(0, 2).concat([ctaAt]).map((b) => b - 0.5);

    // narrative state carried from beat to beat
    const lastMsg = [], lastProof = [], prevKind = [];
    { let m = null, pr = null, pk = null;
      for (let j = 0; j < n; j++) { lastMsg.push(m); lastProof.push(pr); prevKind.push(pk);
        if (scenes[j].message) m = scenes[j].message;
        if (kinds[j] === 'proof') pr = scenes[j].visual;
        pk = kinds[j]; } }
    const reveal = S0.reveal || 'มิจฉาชีพ!';
    const rule = S0.rule && S0.rule.then ? S0.rule : (() => {
      const parts = (S0.tip || '').split(/\s+/).filter(Boolean);
      const half = Math.ceil(parts.length / 2);
      return { if: [parts.slice(0, half).join(' '), parts.slice(half).join(' ')].filter(Boolean), then: 'อย่าหลงเชื่อ!' };
    })();

    const PL = H.layer(W, HH), WL = H.layer(W, HH);
    const sceneAt = (t) => { for (let j = n; j >= 0; j--) if (t >= starts[j] - 1e-6) return j; return 0; };

    // ---------------- pieces shared by beats
    const corner = (c) => {
      slab(c, S0.hook, 64, 158, -0.04, '800 {s}px "Kanit"', 50, CREAM, BLACK, 900, 20, 14);
      slab(c, S0.source_label, 72, 246, -0.04, '500 {s}px "Kanit"', 42, CREAM, RED, 900, 16, 10);
    };
    const subtitle = (c, line, u) => {
      const txt = line === n ? S0.end_narration : scenes[line].narration;
      c.fillStyle = BLACK; c.fillRect(48, 1584, W - 96, 236);
      let s = 56; c.font = `500 ${s}px "Kanit"`; let lines = wrap(c, txt, 940);
      while (lines.length > 3 && s > 40) { s -= 4; c.font = `500 ${s}px "Kanit"`; lines = wrap(c, txt, 940); }
      lines = lines.slice(0, 3);
      const lh = s * 1.38, top = 1584 + (236 - lh * lines.length) / 2 + s * 0.98;
      const lit = (words[line] || []).filter(([t]) => t <= u).map(([, w]) => w);
      lines.forEach((ln, i) => {
        const y = top + i * lh, wd = c.measureText(ln).width, x0 = W / 2 - wd / 2;
        for (const w of lit) {   // spoken key words land on a red bar
          const at = ln.indexOf(w); if (at < 0) continue;
          const xa = x0 + c.measureText(ln.slice(0, at)).width, ww = c.measureText(w).width;
          c.fillStyle = RED; c.fillRect(xa - 8, y - s * 0.95, ww + 16, s * 1.25);
        }
        c.fillStyle = CREAM; c.fillText(ln, x0, y);
      });
    };

    // ---------------- hook (first ~2.3 s, over scene 1)
    const hookParts = (() => {
      const h = S0.hook.trim(), i = h.indexOf(' ');
      return i > 0 && i < h.length - 2 ? [h.slice(0, i), h.slice(i + 1)] : ['', h];
    })();
    const drawHook = (c, u) => {
      const hp = E.inOut(P(u, 1.6, 2.3)); if (hp >= 1) return;
      const dp = E.out(stepIn(u, 0, 6)), off = hp * 900;
      disc(c, 700 - (1 - dp) * 900 + off, 700, 330);
      beamsFrom(c, 700 + off, 700, [[-2.55, 0.07], [-2.2, 0.11], [-1.85, 0.05], [-1.55, 0.12]], 1500, (i) => stepIn(u, 0.2 + i * 0.08, 2));
      c.save(); c.translate(H.lerp(0, -40, hp), H.lerp(0, -880, hp)); const sc = H.lerp(1, 0.35, hp);
      c.translate(70, 1040); c.scale(sc, sc); c.translate(-70, -1040);
      slab(c, hookParts[0], 70, 1040, -0.2, '900 {s}px "Kanit"', 104, CREAM, BLACK, 900, 24, 16, stepIn(u, 0.35, 2));
      slogan(c, hookParts[1], 60, 1310, -0.2, 168, RED, BLACK, 960, stepIn(u, 0.6, 3));
      slab(c, S0.source_label, 110, 1440, -0.2, '500 {s}px "Kanit"', 44, CREAM, RED, 860, 16, 10, stepIn(u, 0.85, 2));
      c.restore();
    };

    // ---------------- beats: each draws plates on c and queues halftone pastes; u = local seconds
    const B = {};
    B.chat = (c, j, u, pastes) => {
      const m = scenes[j].message || lastMsg[j], fresh = !!scenes[j].message, cont = prevKind[j] === 'chat' || prevKind[j] === 'reveal';
      const sl = cont ? 1 : E.out(P(u, 0, 0.35));
      pastes.push(['phone', -20 - (1 - sl) * 600, 380 + (1 - sl) * 300, 0.82, -0.06]);
      disc(c, 880 + (cont ? 0 : (1 - E.out(stepIn(u, 0.1, 4))) * 600), 560, 170);
      if (fresh) beamsFrom(c, 470, 820, [[-0.05, 0.05], [0.18, 0.07], [0.42, 0.04]], 700, (i) => stepIn(u, 0.2 + i * 0.07, 2));
      slab(c, S0.sender, 560, 420, -0.12, '800 {s}px "Kanit"', 54, CREAM, RED, 480, 16, 10, cont ? 1 : stepIn(u, 0.25, 2));
      if (!m) return;
      c.font = '800 56px "Kanit"'; let size = 56, lines = wrap(c, m.text, 440);
      if (lines.length > 3) { size = 46; c.font = '800 46px "Kanit"'; lines = wrap(c, m.text, 440); }
      if (lines.length > 5) { size = 40; c.font = '800 40px "Kanit"'; lines = wrap(c, m.text, 440).slice(0, 6); }
      const mine = m.from === 'me', top = lines.length > 3 ? 1040 : 1130;
      lines.forEach((ln, i) => slab(c, ln, mine ? 580 : 560, top + (mine ? 40 : 0) + i * size * 1.95, -0.12, `800 {s}px "Kanit"`, size,
        CREAM, mine ? RED : BLACK, 470, 16, 11, fresh ? stepIn(u, 0.35 + i * 0.13, 2) : 1));
    };
    const proofLayout = (k) => k === 1 ? [[300, 470, 0.95, -0.04]] : k === 2 ? [[420, 380, 0.85, -0.07], [480, 790, 0.85, 0.09]]
      : [[380, 340, 0.62, -0.07], [520, 720, 0.62, 0.08], [330, 1070, 0.6, -0.05]];
    B.proof = (c, j, u, pastes) => {
      const items = scenes[j].visual.items, L = proofLayout(items.length), hadPhone = lastMsg[j] != null;
      if (hadPhone) { pastes.push(['phone', -70, 900, 0.6, -0.12]); barArrow(c, 300, 1150, L[0][0] + 50, L[0][1] + 420 * L[0][2], E.out(P(u, 0.25, 0.5)), 30, RED); }
      items.forEach((it, i) => {
        const [x, y, s, rot] = L[i], d = stepIn(u, 0.15 + i * 0.35, 3);
        if (d <= 0) return;
        pastes.push([docKind(it), x, y - (1 - d) * 260, s, rot]);
        const ly = i === items.length - 1 && items.length > 1 ? y + 720 * s + 80 : y - 24;
        slab(c, it, x + 20, ly, -0.08, '800 {s}px "Kanit"', 56, CREAM, i % 2 ? RED : BLACK, 1040 - x - 40, 16, 10, stepIn(u, 0.3 + i * 0.35, 2));
      });
    };
    const flowPos = (k) => k === 2 ? [[110, 660], [380, 1010]] : k === 3 ? [[110, 560], [380, 860], [110, 1160]] : [[110, 500], [400, 740], [110, 980], [400, 1220]];
    const counterBox = (c, u, num, unit, x, y, t0, maxW = 520, size = 300) => {     // stencil counter in a slanted black box
      const v = parseFloat(String(num).replace(/,/g, '')), isInt = Number.isFinite(v);
      const p = E.out(P(u, t0, t0 + 1.2));
      const shown = isInt ? fmt(v * p) : num;
      c.save(); c.translate(x, y); c.rotate(-0.12);
      const label = isInt ? fmt(v) : String(num);
      const s = fitSize(c, label, '400 {s}px "Anton"', size, maxW, 120);
      const wd = c.measureText(label).width;
      c.fillStyle = BLACK; c.fillRect(-10, -s * 1.0, (wd + 60) * E.out(stepIn(u, t0 - 0.2, 2)), s * 1.13);
      if (u >= t0) { c.fillStyle = CREAM; c.fillText(shown, 20, 0); }
      c.restore();
      if (unit) {
        const room = 1040 - (x + wd + 80);
        if (room >= 140) slogan(c, unit, x + wd + 80, y - 40, -0.12, 96, RED, null, room, stepIn(u, t0 + 1.25, 3));
        else slogan(c, unit, x + 10, y + 105, -0.12, 80, RED, null, 1030 - x, stepIn(u, t0 + 1.25, 3));
      }
    };
    const splitNum = (s) => { const m = /^(.*?)(\d[\d,.]*)\s*(.*)$/.exec(s || ''); return m ? { pre: m[1].trim(), num: m[2], unit: m[3].trim() } : null; };
    B.flow = (c, j, u) => {
      const v = scenes[j].visual, steps = v.steps, pos = flowPos(steps.length);
      const gap = 0.45, all = 0.2 + steps.length * gap;
      const act = u < all ? Math.min(steps.length - 1, Math.floor((u - 0.2) / gap)) : Math.floor((u - all) * 1.5) % steps.length;
      steps.forEach((st, i) => slab(c, st, pos[i][0], pos[i][1], -0.12, '800 {s}px "Kanit"', 64, CREAM, i === act ? RED : BLACK, 600, 20, 14, stepIn(u, 0.2 + i * gap, 2)));
      for (let i = 1; i < steps.length; i++) {
        const [xa, ya] = pos[i - 1], [xb, yb] = pos[i], right = xb > xa;
        barArrow(c, right ? xa + 230 : xa + 280, ya + 40, right ? xb + 90 : xb + 260, yb - 90, E.out(P(u, 0.2 + i * gap - 0.1, 0.2 + i * gap + 0.05)), 24, BLACK);
      }
      if (steps.length >= 3) barArrow(c, 70, pos[steps.length - 1][1] - 70, 70, pos[0][1] + 60, E.out(P(u, all, all + 0.25)), 24, RED);
      const cap = splitNum(v.caption);
      if (cap) {
        if (cap.pre) slab(c, cap.pre, 640, 1180, -0.12, '800 {s}px "Kanit"', 56, CREAM, RED, 380, 16, 10, stepIn(u, all + 0.1, 2));
        counterBox(c, u, cap.num, cap.unit, 640, 1450, all + 0.3, 380, 210);
      } else slab(c, v.caption, 520, 1440, -0.12, '800 {s}px "Kanit"', 58, CREAM, RED, 520, 18, 12, stepIn(u, all + 0.1, 2));
    };
    B.money = (c, j, u) => {
      const v = scenes[j].visual, amt = v.amount;
      slab(c, v.label || 'ความเสียหาย', 90, 620, -0.12, '800 {s}px "Kanit"', 58, CREAM, RED, 900, 18, 12, stepIn(u, 0.1, 2));
      const p = 1 - Math.pow(1 - P(u, 0.3, 1.8), 3), num = fmt(amt * p);
      c.save(); c.translate(70, 1000); c.rotate(-0.12);
      c.fillStyle = BLACK; c.fillRect(-10, -250, 960 * E.out(stepIn(u, 0.05, 3)), 300);
      if (u >= 0.3) { const s = fitSize(c, fmt(amt), '400 {s}px "Anton"', 214, 900, 90); c.font = `400 ${s}px "Anton"`; c.fillStyle = CREAM; c.fillText(num, 18, 0); }
      c.restore();
      slogan(c, 'บาท', 650, 1180, -0.12, 150, RED, BLACK, 400, stepIn(u, 1.85, 3));
      c.save(); c.translate(0, 1400); c.rotate(-0.12); c.fillStyle = RED; c.fillRect(-40, 0, 1300 * E.out(P(u, 1.85, 2.1)), 22); c.restore();
    };
    B.stat = (c, j, u) => {
      const v = scenes[j].visual, sp = splitNum(v.value);
      slab(c, v.label, 90, 620, -0.12, '800 {s}px "Kanit"', 58, CREAM, RED, 900, 18, 12, stepIn(u, 0.1, 2));
      if (sp) { if (sp.pre) slab(c, sp.pre, 90, 760, -0.12, '800 {s}px "Kanit"', 56, CREAM, BLACK, 900, 16, 10, stepIn(u, 0.2, 2)); counterBox(c, u, sp.num, sp.unit, 90, 1180, 0.35); }
      else { box(c, 70, 1100, -0.12, 940, 330, E.out(stepIn(u, 0.1, 3))); slogan(c, v.value, 100, 1060, -0.12, 200, CREAM, null, 880, stepIn(u, 0.35, 3)); }
    };
    // two numbers side by side on slanted cards (red vs black)
    B.compare = (c, j, u) => {
      const v = scenes[j].visual;
      slab(c, v.title, 90, 560, -0.08, '800 {s}px "Kanit"', 60, CREAM, BLACK, 900, 20, 14, stepIn(u, 0.1, 2));
      v.items.forEach((it, i) => {
        const k = stepIn(u, 0.25 + i * 0.3, 3); if (k <= 0) return;
        const x = i ? 560 : 80, y = i ? 790 : 760, w = 440, h = 520, sc = 1 + 0.4 * (1 - k);
        c.save(); c.translate(x + w / 2, y + h / 2); c.rotate(-0.08); c.scale(sc, sc); c.translate(-w / 2, -h / 2);
        c.fillStyle = i ? BLACK : RED; c.fillRect(0, 0, w, h);
        c.fillStyle = CREAM; c.textAlign = 'center';
        fitSize(c, it.label, '800 {s}px "Kanit"', 52, w - 50); c.fillText(it.label, w / 2, 96);
        const p = 1 - Math.pow(1 - P(u, 0.45 + i * 0.3, 1.6 + i * 0.3), 3);
        fitSize(c, fmt(it.value), '400 {s}px "Anton"', 200, w - 50, 70); c.fillText(fmt(it.value * p), w / 2, 330);
        fitSize(c, it.unit, '800 {s}px "Kanit"', 50, w - 50); c.fillText(it.unit, w / 2, 450);
        c.textAlign = 'left'; c.restore();
      });
    };
    // heavy bars rising off a slanted base
    B.bars = (c, j, u) => {
      const v = scenes[j].visual, items = v.items, nb = items.length, mx = Math.max(...items.map((it) => it.value));
      slab(c, v.title, 90, 560, -0.08, '800 {s}px "Kanit"', 60, CREAM, BLACK, 900, 20, 14, stepIn(u, 0.1, 2));
      c.save(); c.translate(90, 1380); c.rotate(-0.08);
      c.fillStyle = BLACK; c.fillRect(-20, 0, 940 * E.out(stepIn(u, 0.15, 3)), 16);
      const slot = 900 / nb, bw = slot * 0.62;
      items.forEach((it, i) => {
        const g = E.out(P(u, 0.35 + i * 0.22, 0.95 + i * 0.22)), hgt = 620 * (it.value / mx) * g, x = i * slot + (slot - bw) / 2;
        if (g <= 0) return;
        c.fillStyle = it.value === mx ? RED : (i % 2 ? BLACK : RED); c.fillRect(x, -hgt, bw, hgt);
        c.textAlign = 'center';
        fitSize(c, fmt(it.value), '400 {s}px "Anton"', 84, slot - 6, 34); c.fillStyle = BLACK;
        if (g > 0.6) c.fillText(fmt(it.value * g), x + bw / 2, -hgt - 18);
        fitSize(c, it.label, '700 {s}px "Kanit"', 42, slot - 6, 26); c.fillText(it.label, x + bw / 2, 70);
        c.textAlign = 'left';
      });
      c.restore();
      if (v.unit) slab(c, v.unit, 640, 1530, -0.08, '700 {s}px "Kanit"', 44, CREAM, RED, 380, 14, 8, stepIn(u, 0.3, 2));
    };
    // a percentage as a red wedge sweeping round a black disc
    B.percent = (c, j, u) => {
      const v = scenes[j].visual, pv = cl(v.value / 100, 0, 1), cx = 540, cy = 900, r = 330;
      const k = E.out(stepIn(u, 0.05, 3));
      c.fillStyle = BLACK; c.beginPath(); c.arc(cx, cy, r * k, 0, 7); c.fill();
      const sw = pv * E.inOut(P(Math.floor(u * FPS) / FPS, 0.3, 1.5));
      if (sw > 0) { c.fillStyle = RED; c.beginPath(); c.moveTo(cx, cy); c.arc(cx, cy, r * k, -Math.PI / 2, -Math.PI / 2 + sw * Math.PI * 2); c.closePath(); c.fill(); }
      if (u >= 0.3) {
        c.fillStyle = CREAM; c.textAlign = 'center';
        const txt = (v.value * (sw / Math.max(pv, 1e-6))).toFixed(v.value % 1 ? 1 : 0) + '%';
        fitSize(c, '100%', '400 {s}px "Anton"', 220, 520, 80); c.fillText(txt, cx, cy + 80); c.textAlign = 'left';
      }
      slab(c, v.label, 90, 1400, -0.08, '800 {s}px "Kanit"', 60, CREAM, RED, 900, 20, 14, stepIn(u, 1.5, 2));
    };
    B.map = (c, j, u) => {
      const v = scenes[j].visual, hot = u >= 0.45;
      disc(c, 900, 1230, 170 * E.back(stepIn(u, 0.1, 3)));
      c.save(); const sc = 1 + 0.06 * (1 - stepIn(u, 0, 3)); c.translate(405, 930); c.scale(sc, sc); c.translate(-405, -930);
      const [px, py] = drawMap(c, [110, 360, 700, 1500], v.province, hot);
      c.restore();
      if (hot && Math.floor(u * 4) % 2 === 0) { c.strokeStyle = RED; c.lineWidth = 10; c.beginPath(); c.arc(px, py, 34, 0, 7); c.stroke(); }
      const name = v.province === 'กรุงเทพมหานคร' ? v.province : 'จ.' + v.province;
      slab(c, name, 520, 520, -0.12, '900 {s}px "Kanit"', 72, CREAM, BLACK, 520, 20, 14, stepIn(u, 0.3, 2));
      slab(c, v.label, 560, 640, -0.12, '800 {s}px "Kanit"', 54, CREAM, RED, 480, 16, 10, stepIn(u, 0.5, 2));
      barArrow(c, 760, 720, px + 18, py - 12, E.out(P(u, 0.6, 0.8)), 26, RED);
    };
    B.reveal = (c, j, u, pastes) => {
      const pr = lastProof[j], doc = pr ? (pr.items.find((x) => docKind(x) === 'official') || pr.items[0]) : null;
      const cx = 540, cy = doc ? 880 : 860;
      if (doc) pastes.push([docKind(doc), 250, 520, 0.98, 0.05]); else pastes.push(['phone', 160, 330, 0.82, 0.03]);
      const bp = stepIn(u, 0.3, 2);
      if (bp > 0) {
        c.save(); c.beginPath(); c.rect(0, 0, W, HH); doc ? c.rect(232, 500, 590, 740) : c.rect(260, 360, 440, 860); c.clip('evenodd');
        for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2 + 0.1; c.fillStyle = i % 2 ? RED : BLACK; c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(a - 0.07) * 600 * bp, cy + Math.sin(a - 0.07) * 600 * bp); c.lineTo(cx + Math.cos(a + 0.07) * 600 * bp, cy + Math.sin(a + 0.07) * 600 * bp); c.closePath(); c.fill(); }
        c.restore();
      }
      const xk = stepIn(u, 0.45, 2);
      if (xk > 0) { const s = 1 + 0.6 * (1 - xk); c.save(); c.translate(cx, cy); c.rotate(0.785); c.scale(s, s); c.fillStyle = RED; c.fillRect(-230, -38, 460, 76); c.fillRect(-38, -230, 76, 460); c.restore(); }
      slogan(c, reveal, 70, 1470, -0.15, 200, RED, BLACK, 940, stepIn(u, 0.6, 3));
    };
    const drawRule = (c, u) => {
      disc(c, 930, 1040, 280 * E.out(stepIn(u, 0, 3)));
      const a = rule.if[0] || '', b = rule.if[1] ? '+ ' + rule.if[1] : '';
      slab(c, a, 80, 600, -0.15, '900 {s}px "Kanit"', 92, CREAM, BLACK, 900, 24, 16, stepIn(u, 0.15, 2));
      slab(c, b, 180, 800, -0.15, '900 {s}px "Kanit"', 92, CREAM, RED, 860, 24, 16, stepIn(u, 0.45, 2));
      barArrow(c, 330, 880, 410, 1080, E.out(P(u, 0.75, 0.95)), 34, RED);
      slogan(c, rule.then, 90, 1380, -0.15, 250, BLACK, RED, 940, stepIn(u, 1.0, 3));
    };
    const drawCTA = (c, u) => {
      disc(c, 200, 470, 230 * E.out(stepIn(u, 0, 3)));
      c.save(); c.translate(90, 1120); c.rotate(-0.12); c.fillStyle = BLACK; c.fillRect(-20, -520, 940 * E.out(stepIn(u, 0.05, 3)), 600);
      if (u >= 0.2) { c.fillStyle = CREAM; c.font = '800 84px "Kanit"'; c.fillText('สงสัย โทร', 30, -400); }
      const k = stepIn(u, 0.35, 3); if (k > 0) { const s = 1 + 0.6 * (1 - k); c.translate(20, 20); c.scale(s, s); c.fillStyle = RED; c.font = '400 340px "Anton"'; c.fillText('1441', 0, 0); }
      c.restore();
      slab(c, 'ส่งต่อให้พ่อแม่ด้วยนะ', 140, 1330, -0.12, '800 {s}px "Kanit"', 62, CREAM, RED, 900, 20, 12, stepIn(u, 0.7, 2));
      if (channel) slab(c, 'กดติดตาม ' + channel, 150, 1470, -0.12, '700 {s}px "Kanit"', 50, CREAM, BLACK, 880, 18, 10, stepIn(u, 0.9, 2));
    };

    // ---------------- camera: slow push-in + drift on every beat (never fully still)
    const camOf = (j, u, dur) => {
      const r = H.rng(1000 + j), dir = r() < 0.5 ? -1 : 1, x = cl(u / Math.max(dur, 0.5), 0, 1);
      return { z: 1 + 0.045 * E.inOut(x), dx: dir * 18 * Math.sin(x * Math.PI * 0.9), dy: -14 * x };
    };
    const camPaste = (pastes, cam) => pastes.map(([k, x, y, s, rot]) => [k, W / 2 + cam.dx + (x - W / 2) * cam.z, 930 + cam.dy + (y - 930) * cam.z, s * cam.z, rot]);
    const withCam = (c, cam, fn) => { c.save(); c.translate(W / 2 + cam.dx, 930 + cam.dy); c.scale(cam.z, cam.z); c.translate(-W / 2, -930); fn(); c.restore(); };

    // ---------------- one frame
    function draw(ctx, t) {
      ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
      ctx.drawImage(paperC(), 0, 0);
      const c = PL.getContext('2d'); c.setTransform(1, 0, 0, 1, 0, 0); c.clearRect(0, 0, W, HH); c.textBaseline = 'alphabetic';
      let pastes = [];
      const j = sceneAt(t), u = t - starts[j];
      if (j < n) {
        const ub = j === 0 ? u - HOOK_OUT : u, dur = durs[j] - (j === 0 ? HOOK_OUT : 0);
        if (j === 0) drawHook(c, u);
        if (!(j === 0 && u < 2.3)) corner(c);
        if (ub >= 0) {
          const cam = camOf(j, ub, dur), own = [];
          withCam(c, cam, () => B[kinds[j]](c, j, ub, own));
          pastes = camPaste(own, cam);
        }
        subtitle(c, j, u);
      } else if (t < ctaAt) { corner(c); withCam(c, camOf(n, t - endStart, ctaAt - endStart), () => drawRule(c, t - endStart)); subtitle(c, n, u); }
      else { withCam(c, camOf(n + 1, t - ctaAt, DURATION - ctaAt), () => drawCTA(c, t - ctaAt)); subtitle(c, n, u); }
      // print: photos, then the ink plates multiplied over them
      const PHS = photos();
      pastes.forEach(([k, x, y, s, rot]) => paste(ctx, PHS[k], x, y, s, rot || 0));
      exInk(PL, 7, 0.26, 0.006);
      ctx.save(); ctx.globalCompositeOperation = 'multiply'; ctx.drawImage(PL, 0, 0); ctx.restore();
      // Lissitzky's red wedge drives across between scenes
      let wedgeOn = false; const wc = WL.getContext('2d');
      for (const w of wedgeAt) {
        const q = P(t, w, w + 0.95); if (q <= 0 || q >= 1) continue;
        if (!wedgeOn) { wc.setTransform(1, 0, 0, 1, 0, 0); wc.clearRect(0, 0, W, HH); }
        wedgeOn = true; const tx = H.lerp(-100, W + 2600, E.inOut(q));
        wc.fillStyle = RED; wc.beginPath(); wc.moveTo(tx, HH / 2); wc.lineTo(tx - 2600, -2200); wc.lineTo(tx - 2600, HH + 2200); wc.closePath(); wc.fill();
        wc.fillStyle = BLACK; wc.beginPath(); wc.moveTo(tx + 60, HH / 2 + 30); wc.lineTo(tx - 2600, -2160); wc.lineTo(tx - 2600, -2120); wc.closePath(); wc.fill();
      }
      if (wedgeOn) { exInk(WL, 7, 0.12, 0.004); ctx.drawImage(WL, 0, 0); }
      scratches(ctx);
      H.grain(ctx, W, HH, 0.08, 4 + Math.floor(t * 12), true);
      H.vignette(ctx, W, HH, 0.25, '50,30,10');
    }

    // ---------------- sound: a print works on agitprop duty (times match the picture above)
    function scoreSound(k) {
      const q = (b) => Math.ceil(b * FPS - 1e-6) / FPS;      // first frame where a twos-step completes
      const slam = (t, g = 1, minor = false) => { k.play('slap', t, { gain: 0.55 * g, minor }); k.play('thud', t, { f: 110, gain: 0.5 * g, minor }); };
      const horn = (t, notes, dur, g, minor) => notes.forEach((nn, i) => { for (const det of [-9, 9])
        k.tone(t, { f: nn, type: 'sawtooth', detune: det, dur, gain: 0.035 * g, a: 0.02, hold: dur * 0.6, filter: 'bandpass', f2: [[0, 700], [0.05, 1500], [dur, 1000]], q: 0.9, pan: (i - (notes.length - 1) / 2) * 0.15, verb: 0.2, minor }); });
      const beam = (t, g = 1) => k.noise(t, { dur: 0.09, filter: 'bandpass', f: [[0, 600], [0.09, 1800]], q: 0.8, gain: 0.22 * g, a: 0.004, minor: true });
      const numb = (t, g = 1) => k.withMinor(() => { k.noise(t, { dur: 0.03, filter: 'bandpass', f: 1500, q: 1.2, gain: 0.32 * g, a: 0.001 }); k.tone(t, { f: 130, dur: 0.05, gain: 0.12 * g }); });
      const ram = (w) => {
        k.noise(w, { dur: 0.95, color: 'brown', filter: 'lowpass', f: [[0, 150], [0.47, 900], [0.95, 200]], gain: 0.45, a: 0.4, pan: -0.3 });
        k.noise(w + 0.2, { dur: 0.75, color: 'pink', filter: 'bandpass', f: [[0, 300], [0.27, 1300], [0.75, 400]], q: 0.8, gain: 0.16, a: 0.25, pan: 0.3 });
        k.tone(w, { f: [[0, 45], [0.47, 72], [0.95, 40]], type: 'sawtooth', dur: 0.95, gain: 0.1, a: 0.4, filter: 'lowpass', f2: 300 });
      };
      const ticks = (t0, t1, g = 1) => { for (let t = t0; t < t1; ) { const s = (t - t0) / (t1 - t0); numb(t, 0.7 + 0.4 * s); t += Math.max(1 / 12, 0.16 - 0.075 * s); } };
      k.bed('hum', 0, DURATION, { gain: 0.35 }); k.bed('room', 0, DURATION, { gain: 0.4 });   // dropped under a voiceover
      // hook
      k.noise(0, { dur: 0.4, color: 'brown', filter: 'lowpass', f: [[0, 200], [0.4, 700]], gain: 0.3, a: 0.3 });
      k.play('thud', q(0.4), { f: 90, gain: 0.6 });
      [0, 1, 2, 3].forEach((i) => beam(q(0.2 + i * 0.08) + 1 / FPS));
      if (hookParts[0]) slam(q(0.5), 0.8, true);
      k.play('stamp', q(0.8), { gain: 0.65 }); k.play('impact', q(0.8), { gain: 0.3 });
      k.noise(1.6, { dur: 0.7, color: 'pink', filter: 'bandpass', f: [[0, 400], [0.7, 900]], q: 0.7, gain: 0.08, a: 0.3, minor: true });
      wedgeAt.forEach(ram);
      // beats
      for (let j = 0; j < n; j++) {
        const s0 = starts[j] + (j === 0 ? HOOK_OUT : 0), kd = kinds[j], v = scenes[j].visual;
        if (kd === 'chat') {
          const cont = prevKind[j] === 'chat' || prevKind[j] === 'reveal';
          if (!cont) { k.noise(s0, { dur: 0.35, color: 'brown', filter: 'lowpass', f: [[0, 250], [0.35, 600]], gain: 0.25, a: 0.12, minor: true }); k.play('thud', s0 + 0.33, { f: 100, gain: 0.4, minor: true }); }
          if (scenes[j].message) { [0, 1, 2].forEach((i) => beam(q(0.2 + i * 0.07) + s0)); slam(q(s0 + 0.35), 0.6, true); }
        } else if (kd === 'proof') {
          v.items.forEach((_, i) => { k.play('paper', s0 + 0.15 + i * 0.35, { gain: 0.8, minor: true }); slam(q(s0 + 0.3 + i * 0.35), 0.55, true); });
          if (lastMsg[j]) { k.noise(s0 + 0.25, { dur: 0.25, color: 'brown', filter: 'lowpass', f: [[0, 250], [0.2, 700]], gain: 0.2, a: 0.1, minor: true }); k.play('thud', s0 + 0.5, { f: 120, gain: 0.4, minor: true }); }
        } else if (kd === 'flow') {
          const gap = 0.45, all = 0.2 + v.steps.length * gap;
          v.steps.forEach((_, i) => { slam(q(s0 + 0.2 + i * gap), 0.55, true); if (i) k.play('tock', s0 + 0.2 + i * gap + 0.05, { f: 360, gain: 0.4, minor: true }); });
          const cap = splitNum(v.caption);
          if (cap) { ticks(s0 + all + 0.3, s0 + all + 1.45); k.play('stamp', s0 + all + 1.5, { gain: 0.6 }); }
          else slam(q(s0 + all + 0.1), 0.6, true);
        } else if (kd === 'money') {
          slam(q(s0 + 0.15), 0.6, true); ticks(s0 + 0.3, s0 + 1.75);
          k.play('stamp', q(s0 + 1.85), { gain: 0.8 }); k.play('thud', q(s0 + 1.85), { f: 90, gain: 0.5 });
        } else if (kd === 'stat') {
          slam(q(s0 + 0.1), 0.55, true);
          if (splitNum(v.value)) { ticks(s0 + 0.35, s0 + 1.5); k.play('stamp', s0 + 1.55, { gain: 0.7 }); } else k.play('stamp', q(s0 + 0.55), { gain: 0.7 });
        } else if (kd === 'compare') {
          slam(q(s0 + 0.1), 0.5, true);
          [0, 1].forEach((i) => { k.play('stamp', q(s0 + 0.25 + i * 0.3) + 2 / FPS, { gain: 0.6 }); });
          ticks(s0 + 0.45, s0 + 1.85); k.play('thud', s0 + 1.9, { f: 90, gain: 0.5 });
        } else if (kd === 'bars') {
          slam(q(s0 + 0.1), 0.5, true);
          v.items.forEach((it, i) => k.play('thud', s0 + 0.95 + i * 0.22, { f: 80 + i * 14, gain: 0.35, minor: true }));
          k.play('stamp', s0 + 0.95 + (v.items.length - 1) * 0.22 + 0.05, { gain: 0.7 });
        } else if (kd === 'percent') {
          k.play('press', s0 + 0.05, { gain: 0.45 }); k.play('roller', s0 + 0.3, { dur: 1.2, gain: 0.5 });
          k.play('stamp', s0 + 1.5, { gain: 0.8 }); k.play('thud', s0 + 1.5, { f: 85, gain: 0.5 }); slam(q(s0 + 1.5), 0.5, true);
        } else if (kd === 'map') {
          k.play('press', s0, { gain: 0.6 }); slam(q(s0 + 0.3), 0.6, true); slam(q(s0 + 0.5), 0.5, true);
          k.play('stamp', q(s0 + 0.45), { gain: 0.8 }); k.play('thud', s0 + 0.8, { f: 120, gain: 0.45 });
        } else if (kd === 'reveal') {
          k.play('riser', Math.max(0, s0 + 0.45 - 0.55), { dur: 0.55, gain: 0.8 });
          for (let i = 0; i < 3; i++) beam(q(s0 + 0.3) + i * 0.05);
          const hit = q(s0 + 0.45 + 1 / FPS);
          k.play('impact', hit, { gain: 1.6 }); k.play('stamp', hit, { gain: 1.0 }); k.play('thud', hit, { f: 70, gain: 0.8 });
          horn(hit + 0.01, ['C3', 'G3', 'C4', 'Eb4'], 0.7, 1.2);
          slam(q(s0 + 0.8), 0.9);
        }
      }
      // rule + call to action
      slam(q(endStart + 0.25), 0.8, true); slam(q(endStart + 0.55), 0.8, true);
      k.noise(endStart + 0.75, { dur: 0.2, color: 'brown', filter: 'lowpass', f: [[0, 250], [0.2, 700]], gain: 0.2, a: 0.1, minor: true });
      k.play('stamp', q(endStart + 1.2), { gain: 0.7 }); horn(q(endStart + 1.2) + 0.02, ['F3', 'A3', 'C4'], 0.35, 0.8, true);
      k.play('press', ctaAt + 0.05, { gain: 0.5 });
      k.play('stamp', q(ctaAt + 0.55), { gain: 1.0 }); k.play('thud', q(ctaAt + 0.55), { f: 80, gain: 0.5 });
      slam(q(ctaAt + 0.8), 0.6, true); slam(q(ctaAt + 1.0), 0.5, true);
      horn(Math.min(DURATION - 0.8, ctaAt + 1.3), ['C3', 'G3', 'C4', 'E4'], 0.6, 0.9);
    }

    return { W, HH, FPS, DURATION, draw, scoreSound, coverT: Math.min(DURATION - 0.1, starts[0] + HOOK_OUT + 2.0) };
  }

  root.TT = { make, W, HH, FPS };
})(typeof window !== 'undefined' ? window : globalThis);
