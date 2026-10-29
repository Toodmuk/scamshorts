'use strict';
const fs = require('fs');
const path = require('path');
const { createCanvas, registerFont } = require(path.join(__dirname, '../../web/node_modules/canvas'));
const F = path.join(__dirname, '../../web/fonts') + '/';
registerFont(F + 'Kanit-Black.ttf', { family: 'Kanit', weight: '900' });
registerFont(F + 'Kanit-ExtraBold.ttf', { family: 'Kanit', weight: '800' });
registerFont(F + 'Kanit-Bold.ttf', { family: 'Kanit', weight: '700' });
registerFont(F + 'Kanit-Medium.ttf', { family: 'Kanit', weight: '500' });
registerFont(F + 'Anton-Regular.ttf', { family: 'Anton', weight: '400' });
const T = require('./theme.js');
const { W, HH, C } = T;
const M = JSON.parse(fs.readFileSync(path.join(__dirname, 'basemap.json'), 'utf8'));

const TH_ALL = T.camFit(97.3, 5.6, 105.7, 20.5, 330, 1480);
const [cx, cy] = T.provinceCenter(M, 'จันทบุรี');
const CHAN = { lon: cx, lat: cy, s: 420, cy: 900 };
const EAST = { lon: 101.6, lat: 13.3, s: 190, cy: 880 };

const base = (c, cam, opts) => T.drawMap(c, M, cam, opts);
const bottomCap = (c, lines) => T.caption(c, lines, 1640, { size: 58 });
const chipTop = (c) => T.chip(c, 'ทันท่วงที · EP.12', 40, 60);
const sources = (c) => { c.font = '500 26px "Kanit"'; c.fillStyle = 'rgba(55,65,81,0.85)'; c.fillText('แผนที่: Natural Earth · ที่มาข่าว: The Thaiger 12 ต.ค.', 40, 1880); };

const P = [];
// 1. hook
P.push((c) => {
  base(c, TH_ALL, {});
  T.caption(c, [[['คนคุยออนไลน์ ขอยืม', false]], [['21 ล้าน!', true], [' จริงไหม?', false]]], 200, { size: 84, weight: 900 });
  T.mascot(c, 250, 1560, 0.95, 'wave', 0.5);
  bottomCap(c, [[['ผู้เสียหายโอนให้คนรักออนไลน์', false]], [['ไปกว่า ', false], ['21 ล้านบาท', true]]]);
  sources(c);
});
// 2. the loss: money card floating over the map
P.push((c) => {
  base(c, T.camLerp(TH_ALL, EAST, 0.25), {}); chipTop(c);
  T.card(c, 150, 520, 780, 430);
  c.fillStyle = C.muted; c.font = '700 42px "Kanit"'; c.textAlign = 'center'; c.fillText('เงินและทรัพย์สินที่เสียไป', W / 2, 610);
  c.fillStyle = C.red; c.font = '400 170px "Anton"'; c.fillText('21,000,000', W / 2, 800);
  c.fillStyle = C.navy; c.font = '800 60px "Kanit"'; c.fillText('บาท · ใน 17 เดือน', W / 2, 890); c.textAlign = 'left';
  T.mascot(c, 250, 1560, 0.95, 'shock', 0.9);
  bottomCap(c, [[['เสียไปกว่า ', false], ['21 ล้านบาท', true]], [['ในเวลา 17 เดือน', false]]]);
  sources(c);
});
// 3. sweet talk: light chat phone card + mascot holding a phone
P.push((c) => {
  base(c, EAST, { towns: true }); chipTop(c);
  const x = 470, y = 330, w = 520, h = 900;
  T.shadowed(c, () => { c.fillStyle = C.navy; T.rrect(c, x, y, w, h, 60); c.fill(); });
  c.fillStyle = '#eef2f7'; T.rrect(c, x + 16, y + 16, w - 32, h - 32, 46); c.fill();
  c.fillStyle = C.white; T.rrect(c, x + 16, y + 16, w - 32, 110, 46); c.fill(); c.fillRect(x + 16, y + 80, w - 32, 46);
  c.fillStyle = C.navy; c.font = '700 38px "Kanit"'; c.fillText('คนรักออนไลน์ 💙'.replace(' 💙', ''), x + 110, y + 92);
  c.fillStyle = '#c7d2fe'; c.beginPath(); c.arc(x + 70, y + 80, 28, 0, 7); c.fill();
  const bub = (txt, by, mine) => { c.font = '500 36px "Kanit"'; const bw = Math.min(380, c.measureText(txt).width + 50);
    const bx = mine ? x + w - 40 - bw : x + 40; c.fillStyle = mine ? '#06c755' : C.white; T.rrect(c, bx, by, bw, 74, 30); c.fill();
    c.fillStyle = mine ? C.white : C.navy; c.fillText(txt, bx + 25, by + 50); };
  bub('ที่รัก ช่วยผมก่อนนะ', y + 190); bub('เดี๋ยวคืนให้ทั้งหมด', y + 280); bub('ได้ค่ะ โอนให้แล้ว', y + 400, true);
  T.mascot(c, 250, 1560, 0.95, 'phone', 0.4);
  bottomCap(c, [[['เริ่มจากคุยหวานทุกวัน แล้ว', false], ['ขอยืมเงิน', true]], [['บอกว่าเดี๋ยวคืนให้แน่นอน', false]]]);
  sources(c);
});
// 4. fake proof: two document cards with labels
P.push((c) => {
  base(c, EAST, {}); chipTop(c);
  const doc = (x, y, rot, title, kind) => {
    c.save(); c.translate(x, y); c.rotate(rot);
    T.card(c, -200, -260, 400, 520, 22);
    c.fillStyle = kind === 'bank' ? '#2f6fe4' : C.navy; c.fillRect(-200, -260, 400, 80);
    c.fillStyle = C.white; c.font = '700 34px "Kanit"'; c.textAlign = 'center'; c.fillText(title, 0, -206);
    c.fillStyle = '#d1d5db'; for (let i = 0; i < 8; i++) c.fillRect(-160, -140 + i * 42, 320 - (i % 3) * 60, 16);
    if (kind === 'police') { c.strokeStyle = C.navy; c.lineWidth = 6; c.beginPath(); c.arc(110, 170, 50, 0, 7); c.stroke(); }
    c.textAlign = 'left'; c.restore();
  };
  doc(370, 720, -0.07, 'สเตทเมนต์ธนาคาร', 'bank');
  doc(700, 860, 0.08, 'เอกสารตำรวจ', 'police');
  T.pill(c, 'ส่งมาให้ดูในแชต', 540, 1240, { dot: C.red });
  T.mascot(c, 240, 1560, 0.9, 'point', 0.5);
  bottomCap(c, [[['พอเริ่มสงสัย ก็ส่ง', false], ['เอกสารตำรวจปลอม', true]], [['กับสเตทเมนต์ธนาคารมาให้ดู', false]]]);
  sources(c);
});
// 5. the loop: steps as stations on a line (like a route timeline)
P.push((c) => {
  base(c, EAST, {}); chipTop(c);
  T.card(c, 60, 480, 960, 520);
  c.fillStyle = C.navy; c.font = '800 50px "Kanit"'; c.textAlign = 'center'; c.fillText('วนซ้ำแบบนี้ นาน 17 เดือน', W / 2, 570);
  const xs = [170, 400, 650, 900];
  c.strokeStyle = C.blue; c.lineWidth = 14; c.beginPath(); c.moveTo(xs[0], 720); c.lineTo(xs[3], 720); c.stroke();
  c.setLineDash([14, 12]); c.strokeStyle = C.red; c.lineWidth = 8; c.beginPath(); c.moveTo(xs[3], 750); c.bezierCurveTo(xs[3], 900, xs[0], 900, xs[0], 750); c.stroke(); c.setLineDash([]);
  const st = ['ขอยืมเงิน', 'ส่งเอกสารปลอม', 'ขอโอนเพิ่ม', 'วนใหม่'];
  st.forEach((s, i) => { c.fillStyle = i === 1 ? C.red : C.white; c.strokeStyle = i === 1 ? C.red : C.blue; c.lineWidth = 8;
    c.beginPath(); c.arc(xs[i], 720, 26, 0, 7); c.fill(); c.stroke();
    T.fitFont(c, s, 700, 36, 220); c.fillStyle = C.navy; c.fillText(s, xs[i], 660); });
  c.fillStyle = C.red; c.font = '800 40px "Kanit"'; c.fillText('↺ 17 เดือน', W / 2, 950); c.textAlign = 'left';
  T.mascot(c, 250, 1560, 0.95, 'point', 0.3);
  bottomCap(c, [[['หลอกให้โอนซ้ำแบบนี้', false]], [['นานถึง ', false], ['17 เดือน', true]]]);
  sources(c);
});
// 6. the arrest: camera flies to Chanthaburi, zone + pin + label
P.push((c) => {
  const Pj = base(c, CHAN, { hot: 'จันทบุรี' }); chipTop(c);
  const [x, y] = Pj([cx, cy]);
  T.zone(c, x, y, 150, 0.4); T.pin(c, x, y, 1.2);
  T.pill(c, 'ตำรวจจันทบุรี จับผู้ต้องหาแล้ว', x, y - 170, { dot: C.red, size: 40 });
  T.mascot(c, 240, 1560, 0.9, 'point', 0.5);
  bottomCap(c, [[['ล่าสุด ', false], ['ตำรวจจันทบุรี', true]], [['จับผู้ต้องหาได้แล้ว', false]]]);
  sources(c);
});
// 7. the reveal: police letter + red stamp, mascot with megaphone
P.push((c) => {
  base(c, CHAN, { hot: 'จันทบุรี' }); chipTop(c);
  c.save(); c.translate(600, 800); c.rotate(0.05);
  T.card(c, -250, -330, 500, 660, 24);
  c.fillStyle = C.navy; c.fillRect(-250, -330, 500, 90); c.fillStyle = C.white; c.font = '700 40px "Kanit"'; c.textAlign = 'center'; c.fillText('เอกสารตำรวจ', 0, -270);
  c.fillStyle = '#d1d5db'; for (let i = 0; i < 9; i++) c.fillRect(-200, -190 + i * 46, 400 - (i % 3) * 70, 18);
  c.rotate(-0.25); c.strokeStyle = C.red; c.lineWidth = 14; T.rrect(c, -230, -80, 460, 170, 24); c.stroke();
  c.fillStyle = C.red; c.font = '900 120px "Kanit"'; c.fillText('ปลอม!', 0, 50); c.textAlign = 'left'; c.restore();
  T.mascot(c, 240, 1560, 0.9, 'megaphone', 0.8);
  bottomCap(c, [[['เอกสารตำรวจในแชต คือ', false], ['ของปลอม', true]], [['ตำรวจจริงไม่ทักมาขอเงิน', false]]]);
  sources(c);
});
// 8. rule + call to action
P.push((c) => {
  base(c, TH_ALL, {}); chipTop(c);
  T.card(c, 80, 380, 920, 560);
  c.textAlign = 'center'; c.fillStyle = C.navy; c.font = '800 54px "Kanit"'; c.fillText('ไม่เคยเจอตัว + ขอยืมเงิน', W / 2, 500);
  c.fillStyle = C.red; c.font = '900 150px "Kanit"'; c.fillText('อย่าโอน!', W / 2, 690);
  c.fillStyle = C.navy; c.font = '700 48px "Kanit"'; c.fillText('สงสัย โทร', W / 2 - 120, 850); c.fillStyle = C.red; c.font = '400 110px "Anton"'; c.fillText('1441', W / 2 + 150, 862);
  c.textAlign = 'left';
  T.pill(c, 'ส่งคลิปนี้ให้พ่อแม่ดูด้วย', 640, 1060, { bg: C.yellow, size: 40 });
  T.pill(c, 'กดติดตาม ทันท่วงที', 680, 1170, { bg: C.navy, fg: C.white, size: 38 });
  T.mascot(c, 250, 1560, 0.95, 'thumb', 0.4);
  bottomCap(c, [[['คนที่ไม่เคยเจอตัว ขอยืมเงิน ', false], ['อย่าโอน', true]], [['สงสัยโทร 1441 แล้วส่งต่อให้พ่อแม่', false]]]);
  sources(c);
});

const out = [];
P.forEach((fn, i) => {
  const big = createCanvas(W, HH), c = big.getContext('2d'); fn(c);
  const sm = createCanvas(540, 960); sm.getContext('2d').drawImage(big, 0, 0, 540, 960);
  fs.mkdirSync(path.join(__dirname, 'out'), { recursive: true }); const f = path.join(__dirname, 'out', `panel${i + 1}.png`); fs.writeFileSync(f, sm.toBuffer('image/png')); out.push(f);
});
console.log('panels', out.length);
