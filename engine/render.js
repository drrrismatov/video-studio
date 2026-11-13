// Frame-accurate renderer: drives player.html in headless Chromium, pipes JPEG frames into ffmpeg.
// usage: node render.js job.json
//   job = { width, height, fps, concurrency?, clips:[{scene, out}], stills:[{scene, t, out}] }
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const PLAYER = 'file://' + path.join(__dirname, 'web', 'player.html');

async function newPage(browser) {
  const page = await browser.newPage({ viewport: { width: job.width, height: job.height }, deviceScaleFactor: 1 });
  await page.goto(PLAYER);
  return page;
}

async function prep(page, scene) {
  await page.evaluate(([s, w, h]) => window.setup(s, w, h), [scene, job.width, job.height]);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))));
}

async function renderClip(page, clip) {
  await prep(page, clip.scene);
  const frames = Math.round(clip.scene.duration * job.fps);
  const alpha = !!clip.scene.transparent;
  const enc = alpha ? ['-c:v', 'qtrle'] : ['-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p'];
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(job.fps), '-c:v', alpha ? 'png' : 'mjpeg', '-i', '-',
    ...enc, '-r', String(job.fps), clip.out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', c => c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => window.seek(t), f / job.fps);
    const buf = alpha ? await page.screenshot({ type: 'png', omitBackground: true }) : await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end();
  await done;
  process.stdout.write(`  ✓ ${path.basename(clip.out)} (${frames} кадров)\n`);
}

(async () => {
  const browser = await chromium.launch();
  const conc = job.concurrency || 3;
  const queue = [...(job.clips || [])];
  const workers = Array.from({ length: Math.min(conc, Math.max(queue.length, 1)) }, async () => {
    const page = await newPage(browser);
    while (queue.length) await renderClip(page, queue.shift());
    await page.close();
  });
  await Promise.all(workers);
  if (job.stills && job.stills.length) {
    const page = await newPage(browser);
    for (const s of job.stills) {
      await prep(page, s.scene);
      await page.evaluate(t => window.seek(t), s.t);
      await page.screenshot({ path: s.out, type: 'png', omitBackground: !!s.scene.transparent });
    }
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
