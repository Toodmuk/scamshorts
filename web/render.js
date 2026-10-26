// Renders one day's Short in the Constructivist style, in Node (no browser needed).
//   node web/render.js job.json
// job.json: { script, durs, words, segs, channel, out_video, out_audio, out_cover }
// Writes a silent H.264 video (15 fps on twos, delivered at 30 fps), the sound-effects WAV and a cover PNG.
'use strict';
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { createCanvas, registerFont } = require('canvas');
const { OfflineAudioContext } = require('node-web-audio-api');

const FONTS = path.join(__dirname, 'fonts');
registerFont(path.join(FONTS, 'Kanit-Black.ttf'), { family: 'Kanit', weight: '900' });
registerFont(path.join(FONTS, 'Kanit-ExtraBold.ttf'), { family: 'Kanit', weight: '800' });
registerFont(path.join(FONTS, 'Kanit-Bold.ttf'), { family: 'Kanit', weight: '700' });
registerFont(path.join(FONTS, 'Kanit-Medium.ttf'), { family: 'Kanit', weight: '500' });
registerFont(path.join(FONTS, 'Anton-Regular.ttf'), { family: 'Anton', weight: '400' });

global.window = global;
global.document = { createElement: () => createCanvas(1, 1) };
global.OfflineAudioContext = OfflineAudioContext;
require('./harness.js');
require('./sound.js');
require('./thmap.js');
require('./explainer.js');

function wav16(inter, sr) {                       // interleaved float stereo -> 16-bit PCM WAV
  const n = inter.length, buf = Buffer.alloc(44 + n * 2);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + n * 2, 4); buf.write('WAVE', 8); buf.write('fmt ', 12);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(sr, 24);
  buf.writeUInt32LE(sr * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34); buf.write('data', 36); buf.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) buf.writeInt16LE(Math.max(-32768, Math.min(32767, Math.round(inter[i] * 32767))), 44 + i * 2);
  return buf;
}

(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const ex = global.TT.make(job);
  const t0 = Date.now();

  // sound effects, scored to the same clock as the picture (voiceover mode keeps them under the voice)
  const snd = await global.SOUND.renderOffline(ex.scoreSound, ex.DURATION, 48000, { voiceover: true });
  fs.writeFileSync(job.out_audio, wav16(snd.inter, snd.sr));

  // picture: every frame is a pure function of t
  const cv = createCanvas(ex.W, ex.HH), ctx = cv.getContext('2d');
  const frames = Math.round(ex.DURATION * ex.FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', `${ex.W}x${ex.HH}`,
    '-r', String(ex.FPS), '-i', '-', '-r', '30', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-maxrate', '4M', '-bufsize', '8M',
    '-pix_fmt', 'yuv420p', job.out_video], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => { ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exited ' + c)))); ff.on('error', rej); });
  for (let f = 0; f < frames; f++) {
    ex.draw(ctx, f / ex.FPS);
    if (!ff.stdin.write(cv.toBuffer('raw'))) await new Promise((r) => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await done;

  ex.draw(ctx, Math.floor(ex.coverT * ex.FPS) / ex.FPS);
  fs.writeFileSync(job.out_cover, cv.toBuffer('image/png'));
  console.log(`Constructivist render OK: ${frames} frames, ${ex.DURATION.toFixed(1)} s, peak ${snd.peak.toFixed(2)}, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
})().catch((e) => { console.error('RENDER FAILED:', e && e.stack || e); process.exit(1); });
