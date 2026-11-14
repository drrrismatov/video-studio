/* Studio motion-graphics templates.
 * Deterministic: every visual is a pure function of scene time t (seconds).
 * API: window.setup(scene, W, H)  ->  window.seek(t)
 */
(function () {
  // ------------------------------------------------------------- themes
  const THEMES = {
    midnight: { bg: ['#05070f', '#0b1230'], fg: '#eef2ff', muted: '#97a3c7', accent: '#4cc9f0', accent2: '#b388ff',
                blobs: ['#3a0ca3', '#4361ee', '#4cc9f0', '#7209b7'], glow: 'rgba(76,201,240,.55)',
                card: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.12)', leak: 'rgba(120,90,255,0.25)' },
    ember:    { bg: ['#080504', '#1d0d06'], fg: '#fff4e6', muted: '#c9a98b', accent: '#ff9f1c', accent2: '#ff4d6d',
                blobs: ['#9d0208', '#e85d04', '#ffba08', '#6a040f'], glow: 'rgba(255,159,28,.5)',
                card: 'rgba(255,255,255,0.05)', border: 'rgba(255,200,150,0.15)', leak: 'rgba(255,140,40,0.28)' },
    noir:     { bg: ['#050505', '#141414'], fg: '#f5f5f5', muted: '#9a9a9a', accent: '#e63946', accent2: '#f1faee',
                blobs: ['#2b2b2b', '#3d0c11', '#1f1f1f', '#5a0f16'], glow: 'rgba(230,57,70,.45)',
                card: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.1)', leak: 'rgba(255,60,60,0.18)' },
    aurora:   { bg: ['#020b0d', '#062226'], fg: '#ecfffb', muted: '#8fbfb6', accent: '#2ef2b5', accent2: '#7cf6ff',
                blobs: ['#00a676', '#0b6e4f', '#06d6a0', '#118ab2'], glow: 'rgba(46,242,181,.45)',
                card: 'rgba(255,255,255,0.05)', border: 'rgba(160,255,230,0.14)', leak: 'rgba(60,255,200,0.2)' },
    medical:  { bg: ['#03121c', '#082a3d'], fg: '#f0fbff', muted: '#9cc3d5', accent: '#3ddcff', accent2: '#7bf1a8',
                blobs: ['#0077b6', '#00b4d8', '#48cae4', '#023e8a'], glow: 'rgba(61,220,255,.45)',
                card: 'rgba(255,255,255,0.06)', border: 'rgba(160,230,255,0.16)', leak: 'rgba(80,200,255,0.2)' },
    clean:    { bg: ['#f7f8fc', '#e7ebf7'], fg: '#0d1321', muted: '#5c677d', accent: '#3a5cff', accent2: '#ff5c8a',
                blobs: ['#c7d2fe', '#fbcfe8', '#bae6fd', '#ddd6fe'], glow: 'rgba(58,92,255,.0)',
                card: 'rgba(255,255,255,0.75)', border: 'rgba(13,19,33,0.08)', leak: 'rgba(255,255,255,0)' },
    documentary: { bg: ['#050404', '#0d0a08'], fg: '#f6efe6', muted: '#b9ab98', accent: '#e8c99a', accent2: '#f3e3c8',
                blobs: ['#3a2a1c', '#21180f', '#2c2116', '#1a130c'], glow: 'rgba(232,201,154,.25)',
                card: 'rgba(255,255,255,0.04)', border: 'rgba(232,201,154,0.18)', leak: 'rgba(255,200,140,0.10)',
                fontDisplay: "'Playfair'", fontText: "'Manrope'", displayWeight: 500, displayTracking: '0em', italicAccent: true },
    gold:     { bg: ['#07060a', '#17131f'], fg: '#fbf6ea', muted: '#b5aa92', accent: '#e9c46a', accent2: '#f4a261',
                blobs: ['#3c2a4d', '#6b4e16', '#2a1f3d', '#8a6d1f'], glow: 'rgba(233,196,106,.45)',
                card: 'rgba(255,255,255,0.05)', border: 'rgba(233,196,106,0.2)', leak: 'rgba(255,200,100,0.22)' },
  };

  // ------------------------------------------------------------- helpers
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const P = (t, a, d) => clamp((t - a) / d);
  const E = {
    out: x => 1 - Math.pow(1 - x, 3),
    out5: x => 1 - Math.pow(1 - x, 5),
    inOut: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2,
    back: x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
    expo: x => x === 1 ? 1 : 1 - Math.pow(2, -10 * x),
  };
  const lerp = (a, b, x) => a + (b - a) * x;
  function mulberry(seed) { return function () { let t = seed += 0x6D2B79F5; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const h = (tag, cls, html, style) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; if (style) Object.assign(e.style, style); return e; };
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const U = n => `calc(var(--u)*${n})`;

  // "*word*" -> accent, "_word_" -> accent2
  function splitWords(text) {
    // *several words* -> accent, _words_ -> accent2 (markers may span many words)
    const out = [];
    let mode = '';
    String(text).split(/(\s+)/).forEach(tok => {
      if (!tok) return;
      if (/^\s+$/.test(tok)) { out.push({ space: tok }); return; }
      let cls = mode;
      if (tok.startsWith('*')) { mode = mode ? '' : 'accent glow'; cls = 'accent glow'; tok = tok.slice(1); }
      else if (tok.startsWith('_')) { mode = mode ? '' : 'accent2'; cls = 'accent2'; tok = tok.slice(1); }
      const m = tok.match(/[*_]([.,!?:;…]*)$/);
      if (m) { tok = tok.slice(0, m.index) + m[1]; mode = ''; }
      out.push({ word: tok, cls });
    });
    return out;
  }
  function wordsEl(text, cls = '') {
    const wrap = h('div', cls);
    const items = [];
    splitWords(text).forEach(w => {
      if (w.space) { wrap.appendChild(document.createTextNode(' ')); return; }
      const s = h('span', 'word ' + w.cls, esc(w.word));
      wrap.appendChild(s); items.push(s);
    });
    return { el: wrap, items };
  }
  function revealWords(items, t, start, stagger = 0.06, dur = 0.55, style = 'rise') {
    items.forEach((s, i) => {
      const x = E.out(P(t, start + i * stagger, dur));
      s.style.opacity = x;
      if (style === 'rise') s.style.transform = `translateY(${(1 - x) * 0.6}em)`;
      if (style === 'blur') { s.style.filter = `blur(${(1 - x) * 12}px)`; s.style.transform = `scale(${lerp(1.15, 1, x)})`; }
      if (style === 'slide') s.style.transform = `translateX(${(1 - x) * -0.5}em)`;
    });
  }
  function charsEl(text, cls = '') {
    const wrap = h('div', cls);
    const items = [];
    [...String(text)].forEach(c => { const s = h('span', 'char', c === ' ' ? '&nbsp;' : esc(c)); wrap.appendChild(s); items.push(s); });
    return { el: wrap, items };
  }
  function fadeUp(el, t, start, dur = 0.6, dist = 3) {
    const x = E.out(P(t, start, dur));
    el.style.opacity = x;
    el.style.transform = `translateY(${(1 - x) * dist}vh)`;
  }

  // ------------------------------------------------------------- background
  let ctx, W, H, theme, scene, rnd, particles, bgOpts;
  function initBg() {
    const c = document.getElementById('bg');
    c.width = W; c.height = H;
    ctx = c.getContext('2d');
    rnd = mulberry((scene.seed || 1) * 9973);
    const n = bgOpts.particles ?? 70;
    particles = Array.from({ length: n }, () => ({ x: rnd(), y: rnd(), s: 0.5 + rnd() * 2.2, v: 0.004 + rnd() * 0.02, ph: rnd() * 6.28, z: rnd() }));
  }
  function drawBg(t) {
    const T = t + (scene.tOffset || 0);
    const g = ctx.createLinearGradient(0, 0, W * 0.3, H);
    g.addColorStop(0, theme.bg[0]); g.addColorStop(1, theme.bg[1]);
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    const m = Math.max(W, H);
    // aurora blobs
    ctx.globalCompositeOperation = theme === THEMES.clean ? 'multiply' : 'screen';
    theme.blobs.forEach((col, i) => {
      const sp = bgOpts.speed ?? 1;
      const x = W * (0.5 + 0.38 * Math.sin(T * 0.11 * sp + i * 1.9));
      const y = H * (0.5 + 0.34 * Math.cos(T * 0.08 * sp + i * 2.7));
      const r = m * (0.35 + 0.1 * Math.sin(T * 0.2 + i));
      const rg = ctx.createRadialGradient(x, y, 0, x, y, r);
      rg.addColorStop(0, hexA(col, bgOpts.blobAlpha ?? 0.32)); rg.addColorStop(1, hexA(col, 0));
      ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
    });
    ctx.globalCompositeOperation = 'source-over';
    // perspective grid
    if (bgOpts.grid) {
      ctx.strokeStyle = hexA(theme.accent, 0.10); ctx.lineWidth = 1;
      const hor = H * 0.62;
      for (let i = -20; i <= 20; i++) { ctx.beginPath(); ctx.moveTo(W / 2 + i * W * 0.02, hor); ctx.lineTo(W / 2 + i * W * 0.25, H); ctx.stroke(); }
      for (let k = 0; k < 14; k++) { const z = ((k + T * 0.6) % 14) / 14; const y = hor + (H - hor) * z * z; ctx.globalAlpha = z; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
      ctx.globalAlpha = 1;
    }
    // particles (dust / stars)
    particles.forEach(p => {
      const y = ((p.y - T * p.v * (bgOpts.speed ?? 1)) % 1 + 1) % 1;
      const x = p.x + 0.01 * Math.sin(T * 0.5 + p.ph);
      const a = (0.25 + 0.55 * (0.5 + 0.5 * Math.sin(T * 1.7 + p.ph))) * (0.4 + p.z * 0.6);
      ctx.fillStyle = hexA(theme === THEMES.clean ? theme.accent : '#ffffff', a * 0.8);
      ctx.beginPath(); ctx.arc(x * W, y * H, p.s * (m / 1920) * (0.6 + p.z), 0, 6.283); ctx.fill();
    });
    // vignette inside frame
    const vg = ctx.createRadialGradient(W / 2, H / 2, m * 0.25, W / 2, H / 2, m * 0.75);
    vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, theme === THEMES.clean ? 'rgba(0,0,0,0.06)' : 'rgba(0,0,0,0.55)');
    ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
  }
  function hexA(hex, a) {
    if (hex.startsWith('rgba')) return hex;
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`;
  }

  // ------------------------------------------------------------- templates
  const T = {};

  T.title = (d, D) => {
    const box = h('div', '', null, { textAlign: d.align || 'center', maxWidth: '86%', display: 'flex', flexDirection: 'column', alignItems: d.align === 'left' ? 'flex-start' : 'center', gap: U(2.2) });
    const kick = d.kicker ? h('div', 'kicker', `<span class="line"></span>${esc(d.kicker)}<span class="line"></span>`) : null;
    const title = charsEl(d.title || '', 'h1 glow');
    title.el.style.fontSize = U(d.size || 11);
    const sub = d.subtitle ? wordsEl(d.subtitle, 'muted') : null;
    if (sub) { sub.el.style.fontSize = U(3.2); sub.el.style.fontWeight = 400; sub.el.style.maxWidth = U(110); }
    if (kick) box.appendChild(kick);
    box.appendChild(title.el);
    if (sub) box.appendChild(sub.el);
    return {
      el: box, update(t) {
        if (kick) { fadeUp(kick, t, 0.1, 0.8, 2); kick.querySelectorAll('.line').forEach(l => l.style.width = `calc(var(--u)*${6 * E.out(P(t, 0.2, 1))})`); }
        title.items.forEach((c, i) => {
          const x = E.out5(P(t, 0.35 + i * (d.charStagger || 0.035), 0.9));
          c.style.opacity = x;
          c.style.filter = `blur(${(1 - x) * 18}px)`;
          c.style.transform = `translateY(${(1 - x) * 0.35}em) scale(${lerp(1.4, 1, x)})`;
        });
        if (sub) revealWords(sub.items, t, 0.9 + title.items.length * 0.02, 0.05, 0.6, 'blur');
        box.style.transform = `scale(${1 + 0.035 * t / D})`;
      }
    };
  };

  T.chapter = (d, D) => {
    const box = h('div', '', null, { display: 'flex', alignItems: 'center', gap: U(4), maxWidth: '88%' });
    const num = h('div', 'h1 accent glow', esc(d.number || '01'), { fontSize: U(22), opacity: 0 });
    const bar = h('div', '', null, { width: '3px', background: 'var(--accent)', height: '0' });
    const col = h('div', '', null, { display: 'flex', flexDirection: 'column', gap: U(1.2) });
    const k = h('div', 'kicker', esc(d.kicker || 'Глава'));
    const tt = wordsEl(d.title || '', 'h1');
    tt.el.style.fontSize = U(d.size || 7.5);
    col.append(k, tt.el);
    box.append(num, bar, col);
    return {
      el: box, update(t) {
        const x = E.out5(P(t, 0.1, 1.1));
        num.style.opacity = x; num.style.transform = `translateX(${(1 - x) * -6}vw)`; num.style.filter = `blur(${(1 - x) * 10}px)`;
        bar.style.height = U(18 * E.inOut(P(t, 0.3, 0.8)));
        fadeUp(k, t, 0.5, 0.6, 2);
        revealWords(tt.items, t, 0.65, 0.08, 0.7, 'slide');
        box.style.transform = `scale(${1 + 0.03 * t / D})`;
      }
    };
  };

  T.statement = (d, D) => {
    const box = h('div', '', null, { maxWidth: d.width || '84%', textAlign: d.align || 'center',
      ...(d.pos === 'bottom' ? { position: 'absolute', bottom: W < H ? '27%' : '9%', left: '50%', translate: '-50% 0', width: W < H ? '80%' : '84%' } : {}) });
    if (d.shadow) box.style.textShadow = '0 4px 30px rgba(0,0,0,.85), 0 0 60px rgba(0,0,0,.6)';
    let root = box, band = null;
    if (d.pos === 'bottom') {  // soft dark band so gold words read on bright footage
      band = h('div', '', null, { position: 'absolute', left: 0, right: 0, bottom: 0, height: '45%',
        background: 'linear-gradient(0deg, rgba(8,6,12,.85) 0%, rgba(8,6,12,.55) 45%, rgba(8,6,12,0) 100%)' });
      root = h('div', '', null, { position: 'absolute', inset: 0 });
      root.append(band, box);
    }
    const k = d.kicker ? h('div', 'kicker', esc(d.kicker), { justifyContent: d.align === 'left' ? 'flex-start' : 'center', marginBottom: U(2.5) }) : null;
    const tx = wordsEl(d.text || '', 'h1');
    tx.el.style.fontSize = U(d.size || 7);
    tx.el.style.fontWeight = 700;
    tx.el.style.lineHeight = 1.12;
    if (k) box.appendChild(k);
    box.appendChild(tx.el);
    const span = Math.max(0.04, Math.min(0.14, (D * 0.45) / Math.max(tx.items.length, 1)));
    return {
      el: root, update(t) {
        if (band) band.style.opacity = E.out(P(t, 0, 0.25));
        if (k) fadeUp(k, t, 0.1, 0.6, 2);
        revealWords(tx.items, t, d.delay ?? 0.3, d.stagger || span, 0.6, d.style || 'blur');
        box.style.transform = `scale(${1 + 0.04 * t / D})`;
      }
    };
  };

  T.stat = (d, D) => {
    const box = h('div', '', null, { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: U(2), textAlign: 'center' });
    const ringSize = 52;
    const hasRing = d.percent != null;
    const wrap = h('div', '', null, { position: 'relative', width: hasRing ? U(ringSize) : 'auto', height: hasRing ? U(ringSize) : 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center' });
    let arc;
    if (hasRing) {
      const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('viewBox', '0 0 100 100'); Object.assign(svg.style, { position: 'absolute', inset: 0, width: '100%', height: '100%', transform: 'rotate(-90deg)' });
      svg.innerHTML = `<circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="3"/>
        <circle id="arc" cx="50" cy="50" r="45" fill="none" stroke="${theme.accent}" stroke-width="3.4" stroke-linecap="round" stroke-dasharray="282.7" stroke-dashoffset="282.7" style="filter:drop-shadow(0 0 4px ${theme.accent})"/>`;
      wrap.appendChild(svg); arc = svg.querySelector('#arc');
    }
    const num = h('div', 'h1 glow', '', { fontSize: U(d.size || (hasRing ? 13 : 18)), fontVariantNumeric: 'tabular-nums' });
    wrap.appendChild(num);
    const label = wordsEl(d.label || '', 'muted');
    label.el.style.fontSize = U(3.4); label.el.style.maxWidth = U(100);
    const k = d.kicker ? h('div', 'kicker', esc(d.kicker)) : null;
    if (k) box.appendChild(k);
    box.append(wrap, label.el);
    const val = Number(d.value || 0), dec = d.decimals || 0;
    const fmt = v => (d.prefix || '') + v.toLocaleString('ru-RU', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (d.suffix || '');
    return {
      el: box, update(t) {
        if (k) fadeUp(k, t, 0.05, 0.6, 2);
        const x = E.expo(P(t, 0.3, Math.min(2.2, D * 0.5)));
        num.textContent = fmt(val * x);
        num.style.opacity = E.out(P(t, 0.2, 0.4));
        if (arc) arc.setAttribute('stroke-dashoffset', 282.7 * (1 - (d.percent / 100) * x));
        revealWords(label.items, t, 0.9, 0.05, 0.6, 'rise');
        box.style.transform = `scale(${1 + 0.03 * t / D})`;
      }
    };
  };

  T.list = (d, D) => {
    const box = h('div', '', null, { width: '80%', display: 'flex', flexDirection: 'column', gap: U(2) });
    const head = d.title ? wordsEl(d.title, 'h1') : null;
    if (head) { head.el.style.fontSize = U(6); head.el.style.marginBottom = U(1.5); box.appendChild(head.el); }
    const items = (d.items || []).map((txt, i) => {
      const row = h('div', 'card', null, { display: 'flex', alignItems: 'center', gap: U(2.5), padding: `${U(1.8)} ${U(2.6)}` });
      const b = h('div', 'h1', String(i + 1).padStart(2, '0'), { fontSize: U(3.4), color: 'var(--accent)', minWidth: U(5) });
      const tx = h('div', '', esc(txt).replace(/\*(.+?)\*/g, '<span class="accent">$1</span>'), { fontSize: U(3.6), fontWeight: 500 });
      row.append(b, tx); box.appendChild(row); return row;
    });
    const n = Math.max(items.length, 1);
    const gap = Math.min(1.4, (D * 0.7 - 0.8) / n);
    return {
      el: box, update(t) {
        if (head) revealWords(head.items, t, 0.1, 0.06, 0.6, 'rise');
        items.forEach((r, i) => {
          const x = E.back(P(t, 0.6 + i * gap, 0.7));
          r.style.opacity = clamp(x);
          r.style.transform = `translateX(${(1 - x) * -8}vw)`;
        });
      }
    };
  };

  T.quote = (d, D) => {
    const box = h('div', '', null, { maxWidth: '80%', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: U(3) });
    const q = h('div', 'serif accent glow', '“', { fontSize: U(20), lineHeight: 0.6, height: U(9) });
    const tx = wordsEl(d.text || '', 'serif');
    tx.el.style.fontSize = U(d.size || 5.4); tx.el.style.fontStyle = 'italic'; tx.el.style.lineHeight = 1.3;
    const au = h('div', 'kicker', `<span class="line"></span>${esc(d.author || '')}`);
    box.append(q, tx.el); if (d.author) box.appendChild(au);
    const span = Math.min(0.12, (D * 0.5) / Math.max(tx.items.length, 1));
    return {
      el: box, update(t) {
        const x = E.out(P(t, 0, 0.9)); q.style.opacity = x; q.style.transform = `scale(${lerp(1.6, 1, x)})`;
        revealWords(tx.items, t, 0.5, span, 0.8, 'blur');
        fadeUp(au, t, 0.6 + tx.items.length * span, 0.8, 2);
      }
    };
  };

  T.compare = (d, D) => {
    const box = h('div', '', null, { width: '88%', display: 'flex', alignItems: 'stretch', gap: U(3), flexDirection: W < H ? 'column' : 'row' });
    const mk = (side, cls) => {
      const c = h('div', 'card', null, { flex: 1, padding: U(3.5), display: 'flex', flexDirection: 'column', gap: U(1.6) });
      c.appendChild(h('div', 'h1 ' + cls, esc(side.title || ''), { fontSize: U(5) }));
      (side.points || []).forEach(p => c.appendChild(h('div', '', '— ' + esc(p), { fontSize: U(3.1), color: 'var(--muted)' })));
      return c;
    };
    const L = mk(d.left || {}, 'accent2'), R = mk(d.right || {}, 'accent');
    const vs = h('div', 'h1 glow', esc(d.vs || 'VS'), { alignSelf: 'center', fontSize: U(5), color: 'var(--fg)' });
    box.append(L, vs, R);
    return {
      el: box, update(t) {
        const a = E.out(P(t, 0.2, 0.9)), b = E.out(P(t, 0.9, 0.9)), v = E.back(P(t, 0.6, 0.6));
        L.style.opacity = a; L.style.transform = `translateX(${(1 - a) * -6}vw)`;
        R.style.opacity = b; R.style.transform = `translateX(${(1 - b) * 6}vw)`;
        vs.style.opacity = clamp(v); vs.style.transform = `scale(${v})`;
      }
    };
  };

  T.timeline = (d, D) => {
    const pts = d.points || [];
    const vertical = W < H;
    const box = h('div', '', null, { position: 'relative', width: vertical ? '70%' : '86%', height: vertical ? '70%' : U(40) });
    const line = h('div', '', null, { position: 'absolute', background: 'var(--accent)', boxShadow: '0 0 12px var(--accent)',
      ...(vertical ? { left: '10%', top: 0, width: '3px', height: 0 } : { left: 0, top: '50%', height: '3px', width: 0 }) });
    box.appendChild(line);
    if (d.title) { const tt = h('div', 'h1', esc(d.title), { position: 'absolute', top: vertical ? U(-12) : U(-6), left: 0, fontSize: U(5) }); box.appendChild(tt); box._tt = tt; }
    const nodes = pts.map((p, i) => {
      const f = pts.length === 1 ? 0.5 : i / (pts.length - 1);
      const n = h('div', '', null, { position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: vertical ? 'flex-start' : 'center', gap: U(1),
        ...(vertical ? { top: `${f * 100}%`, left: '10%', transform: 'translateY(-50%)' } : { left: `${f * 100}%`, top: '50%', transform: 'translate(-50%,-50%)' }) });
      const dot = h('div', '', null, { width: U(2.2), height: U(2.2), borderRadius: '50%', background: 'var(--accent)', boxShadow: '0 0 18px var(--accent)', marginLeft: vertical ? U(-1.1) : 0 });
      const lab = h('div', '', `<div class="h1 accent" style="font-size:${U(4)}">${esc(p.label || '')}</div><div class="muted" style="font-size:${U(2.6)};max-width:${U(30)}">${esc(p.text || '')}</div>`,
        vertical ? { position: 'absolute', left: U(4), top: U(-2.5) } : { position: 'absolute', [i % 2 ? 'top' : 'bottom']: U(3.5), textAlign: 'center', width: U(32), left: U(-16) });
      n.append(dot, lab); box.appendChild(n); return { n, dot, lab, f };
    });
    return {
      el: box, update(t) {
        const span = Math.max(1.2, D * 0.65);
        const x = E.inOut(P(t, 0.3, span));
        if (vertical) line.style.height = `${x * 100}%`; else line.style.width = `${x * 100}%`;
        if (box._tt) fadeUp(box._tt, t, 0.05, 0.6, 2);
        nodes.forEach(o => {
          const st = 0.3 + o.f * span;
          const y = E.back(P(t, st, 0.5));
          o.dot.style.transform = `scale(${y})`;
          const z = E.out(P(t, st + 0.1, 0.6));
          o.lab.style.opacity = z;
        });
      }
    };
  };

  T.media = (d, D) => {
    const box = h('div', '', null, { position: 'absolute', inset: 0, overflow: 'hidden' });
    const img = h(d.video ? 'video' : 'img', '', null, { position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' });
    img.src = d.src; if (d.video) { img.muted = true; }
    const shade = h('div', '', null, { position: 'absolute', inset: 0, background: 'linear-gradient(0deg, rgba(0,0,0,.75) 0%, rgba(0,0,0,0) 45%)' });
    box.append(img, shade);
    let cap;
    if (d.caption || d.title) {
      cap = h('div', '', null, { position: 'absolute', left: '6%', bottom: '14%', maxWidth: '70%' });
      if (d.title) cap.appendChild(h('div', 'h1', esc(d.title), { fontSize: U(6), color: '#fff' }));
      if (d.caption) cap.appendChild(h('div', 'kicker', `<span class="line"></span>${esc(d.caption)}`, { marginTop: U(1.5) }));
      box.appendChild(cap);
    }
    const kb = d.kenburns || { from: [1.0, 0, 0], to: [1.15, -3, -2] };
    return {
      el: box, update(t) {
        const x = E.inOut(P(t, 0, D));
        const s = lerp(kb.from[0], kb.to[0], x), tx = lerp(kb.from[1], kb.to[1], x), ty = lerp(kb.from[2], kb.to[2], x);
        img.style.transform = `scale(${s}) translate(${tx}%, ${ty}%)`;
        if (d.video) img.currentTime = (d.start || 0) + t;
        if (cap) fadeUp(cap, t, 0.4, 0.8, 3);
      }
    };
  };

  T.outro = (d, D) => {
    const box = h('div', '', null, { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: U(3), textAlign: 'center' });
    const mark = h('div', '', null, { width: U(14), height: U(14), borderRadius: '50%', border: `3px solid var(--accent)`, boxShadow: '0 0 40px var(--accent), inset 0 0 30px var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center' });
    mark.appendChild(h('div', 'h1', esc(d.logo || '◆'), { fontSize: U(6), color: 'var(--accent)' }));
    const tt = wordsEl(d.title || '', 'h1');
    tt.el.style.fontSize = U(d.size || 7.5);
    const cta = d.cta ? h('div', 'card', esc(d.cta), { padding: `${U(1.4)} ${U(3.4)}`, fontSize: U(3), fontWeight: 600, borderRadius: U(10), border: '1px solid var(--accent)', color: 'var(--accent)' }) : null;
    box.append(mark, tt.el); if (cta) box.appendChild(cta);
    return {
      el: box, update(t) {
        const x = E.back(P(t, 0.1, 0.9));
        mark.style.transform = `scale(${x}) rotate(${(1 - clamp(x)) * -90}deg)`; mark.style.opacity = clamp(x);
        mark.style.boxShadow = `0 0 ${40 + 20 * Math.sin(t * 3)}px var(--accent), inset 0 0 30px var(--accent)`;
        revealWords(tt.items, t, 0.6, 0.08, 0.7, 'blur');
        if (cta) fadeUp(cta, t, 1.3, 0.7, 2);
      }
    };
  };


  // sequential lines: one calm phrase at a time (documentary intro / closing inscriptions)
  T.lines = (d, D) => {
    const box = h('div', '', null, { position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' });
    const L = (d.lines || []);
    const els = L.map(tx => {
      const e = h('div', 'display', null, { position: 'absolute', width: '80%', textAlign: 'center', fontSize: U(d.size || 5.2),
        fontWeight: d.weight || 400, letterSpacing: '0.01em', lineHeight: 1.25, color: 'var(--fg)' });
      e.innerHTML = esc(tx).replace(/\*(.+?)\*/g, '<span class="accent">$1</span>');
      box.appendChild(e); return e;
    });
    const k = d.kicker ? h('div', 'kicker', esc(d.kicker), { position: 'absolute', top: '18%', width: '100%', justifyContent: 'center' }) : null;
    if (k) box.appendChild(k);
    const lead = d.lead ?? 0.4, tail = d.tail ?? 0.6;
    const seg = (D - lead - tail) / Math.max(L.length, 1);
    const keep = d.stack;  // stack: lines stay and stack vertically
    if (keep) els.forEach((e, i) => { e.style.position = 'relative'; e.style.margin = U(1.2) + ' 0'; });
    if (keep) { box.style.flexDirection = 'column'; }
    return {
      el: box, update(t) {
        if (k) fadeUp(k, t, 0.1, 0.8, 1);
        els.forEach((e, i) => {
          const a = lead + i * seg;
          const inn = E.out(P(t, a, 0.9));
          const out = keep ? 0 : (i === L.length - 1 && d.holdLast ? 0 : E.inOut(P(t, a + seg - 0.55, 0.55)));
          e.style.opacity = inn * (1 - out);
          e.style.filter = `blur(${(1 - inn) * 8 + out * 6}px)`;
          e.style.transform = `translateY(${(1 - inn) * 1.2}vh) scale(${1 + 0.02 * P(t, a, seg)})`;
        });
      }
    };
  };

  // golden confetti + light sweep overlay (for joyful finale over a photo)
  function confettiLayer(seed, n, startT) {
    const c = h('canvas', '', null, { position: 'absolute', inset: 0, width: '100%', height: '100%' });
    c.width = W; c.height = H;
    const g = c.getContext('2d'), r = mulberry(seed);
    const P_ = Array.from({ length: n }, () => ({ x: r(), y: -0.2 - r() * 0.8, vy: 0.08 + r() * 0.12, vx: (r() - 0.5) * 0.04,
      s: 4 + r() * 9, rot: r() * 6, vr: (r() - 0.5) * 6, c: ['#f2d18b', '#ffffff', '#e8b86a', '#fff1cf', '#d9a55a'][Math.floor(r() * 5)], ph: r() * 6 }));
    return { el: c, draw(t) {
      g.clearRect(0, 0, W, H);
      const T_ = t - startT; if (T_ < 0) return;
      const sc = Math.min(W, H) / 1080;
      P_.forEach(p => {
        const y = (p.y + p.vy * T_) * H, x = (p.x + p.vx * T_ + 0.02 * Math.sin(T_ * 2 + p.ph)) * W;
        if (y > H + 20) return;
        g.save(); g.translate(x, y); g.rotate(p.rot + p.vr * T_);
        g.globalAlpha = 0.85; g.fillStyle = p.c;
        g.fillRect(-p.s * sc / 2, -p.s * sc / 4, p.s * sc, p.s * sc / 2 * (0.6 + 0.4 * Math.abs(Math.sin(T_ * 5 + p.ph))));
        g.restore();
      });
    } };
  }

  // living photo: smooth camera drift + warm bloom + confetti + caption
  T.photo = (d, D) => {
    const box = h('div', '', null, { position: 'absolute', inset: 0, overflow: 'hidden', background: '#000' });
    const img = h('img', '', null, { position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transformOrigin: d.origin || '50% 60%' });
    img.src = d.src;
    const warm = h('div', '', null, { position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 30%, rgba(255,210,150,.0) 0%, rgba(20,10,0,.45) 100%)' });
    const sweep = h('div', '', null, { position: 'absolute', inset: 0, mixBlendMode: 'screen' });
    const shade = h('div', '', null, { position: 'absolute', inset: 0, background: W < H
      ? 'linear-gradient(0deg, rgba(5,4,3,.55) 0%, rgba(5,4,3,.72) 22%, rgba(5,4,3,.45) 36%, rgba(5,4,3,0) 52%)'
      : 'linear-gradient(0deg, rgba(5,4,3,.82) 0%, rgba(5,4,3,0) 42%)' });
    const flash = h('div', '', null, { position: 'absolute', inset: 0, background: '#fff', opacity: 0 });
    box.append(img, warm, sweep);
    const conf = d.confetti ? confettiLayer(77, d.confetti, d.confettiAt ?? 0.4) : null;
    if (conf) box.appendChild(conf.el);
    box.append(shade);
    const cap = d.title ? h('div', '', null, { position: 'absolute', left: '6%', right: '6%', bottom: W < H ? '26%' : '9%', textAlign: 'center' }) : null;
    if (cap) {
      const t1 = h('div', 'display', esc(d.title), { fontSize: U(d.size || 5), fontWeight: 400, color: '#fff', letterSpacing: '.01em', textShadow: '0 2px 18px rgba(0,0,0,.85), 0 0 4px rgba(0,0,0,.5)' });
      cap.appendChild(t1);
      if (d.subtitle) cap.appendChild(h('div', 'display', esc(d.subtitle), { fontSize: U(4.2), fontWeight: 500, fontStyle: 'italic', color: 'var(--accent)', marginTop: U(0.6), textShadow: '0 2px 16px rgba(0,0,0,.9), 0 0 4px rgba(0,0,0,.6)' }));
      box.appendChild(cap);
    }
    box.appendChild(flash);
    const kb = d.kenburns || { from: [1.0, 0, 0], to: [1.12, 0, -2] };
    return { el: box, update(t) {
      const x = E.inOut(P(t, 0, D));
      img.style.transform = `scale(${lerp(kb.from[0], kb.to[0], x)}) translate(${lerp(kb.from[1], kb.to[1], x)}%, ${lerp(kb.from[2], kb.to[2], x)}%)`;
      if (d.pan) img.style.objectPosition = `${lerp(d.pan[0], d.pan[1], x)}% ${d.panY ?? 60}%`;  // vertical frame: travel across a wide group photo
      const sx = -30 + 160 * P(t, 0.3, Math.min(D, 4.5));
      sweep.style.background = `linear-gradient(105deg, rgba(255,220,160,0) ${sx - 18}%, rgba(255,220,160,.28) ${sx}%, rgba(255,220,160,0) ${sx + 18}%)`;
      if (d.flash) flash.style.opacity = 0.55 * (1 - E.out(P(t, 0, 0.7)));
      if (conf) conf.draw(t);
      if (cap) fadeUp(cap, t, d.titleAt ?? 1.2, 1.0, 2);
    } };
  };

  // ------------------------------------------------------------- cartoon shot (SVG characters, camera, lip-sync)
  // d: {set, cam:[[t,cx,cy,s]...], actors:[...], env:[mouth levels per frame], envLead, fps, label, hook, flicker, tint, bands}
  T.cartoon = (d, D) => {
    const CT = window.CARTOON;
    const box = h('div', '', null, { position: 'absolute', inset: 0, overflow: 'hidden', background: '#000' });
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', '0 0 1080 1920'); svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    Object.assign(svg.style, { position: 'absolute', inset: 0, width: '100%', height: '100%' });
    box.appendChild(svg);
    const vg = h('div', '', null, { position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,.55) 100%)' });
    box.appendChild(vg);
    let label, hook;
    if (d.label) { label = h('div', 'display', esc(d.label), { position: 'absolute', left: '7%', top: '9%', fontSize: U(4.2), fontStyle: 'italic', color: '#f3e3c8', textShadow: '0 2px 14px rgba(0,0,0,.8)' }); box.appendChild(label); }
    if (d.hook) { hook = h('div', 'display', d.hook.replace(/\*(.+?)\*/g, '<span class="accent">$1</span>'), { position: 'absolute', left: '8%', right: '8%', top: d.hookTop || '13%', textAlign: 'center', fontSize: U(6.4), fontWeight: 500, color: '#fff', lineHeight: 1.15, textShadow: '0 4px 24px rgba(0,0,0,.9)',
      padding: `${U(2.2)} ${U(3)}`, borderRadius: U(2), background: 'radial-gradient(ellipse at 50% 50%, rgba(10,6,4,.72) 0%, rgba(10,6,4,.45) 60%, rgba(10,6,4,0) 100%)' }); box.appendChild(hook); }
    const fps = d.fps || 30;
    const mouthAt = (t, ch) => {
      const env = ch.env ? d.envs?.[ch.env] : d.env; if (!env) return 0;
      const i = Math.round((t - (d.envLead || 0)) * fps);
      return i >= 0 && i < env.length ? env[i] : 0;
    };
    const blinkAt = (t, seed) => { const p = (t + seed * 1.37) % (3.1 + seed % 1.3); return p < 0.07 ? 1 : p < 0.13 ? 0.5 : 0; };
    const camAt = t => {
      const K = d.cam || [[0, 540, 960, 1]];
      if (t <= K[0][0]) return K[0];
      for (let i = 0; i < K.length - 1; i++) if (t < K[i + 1][0]) { const x = E.inOut((t - K[i][0]) / (K[i + 1][0] - K[i][0])); return [t, ...[1, 2, 3].map(j => lerp(K[i][j], K[i + 1][j], x))]; }
      return K[K.length - 1];
    };
    const draw = (t) => {
      let s = '';
      const fl = 0.85 + 0.15 * Math.sin(t * 13) * Math.sin(t * 7.3) + (d.flicker ? 0 : 0.15);
      s += d.set ? CT.S[d.set](t, fl) : '';
      if (d.set === 'tent' || d.lamp) s += `<g transform="translate(${d.lampX || 540} ${d.lampY || 330})">${CT.P.lamp({ flicker: fl })}</g>`;
      (d.actors || []).forEach((a, k) => {
        if (a.from !== undefined && t < a.from) return;
        if (a.to !== undefined && t > a.to) return;
        const br = 1 + 0.006 * Math.sin(t * 2.2 + k);
        const sway = (a.sway || 0) * Math.sin(t * 1.3 + k);
        const shake = a.shake ? a.shake * Math.sin(t * 37 + k) : 0;
        let inner = '';
        if (a.type === 'char') {
          const o = Object.assign({}, a.opts || {});
          if (a.talk) o.mouth = mouthAt(t, a);
          o.blink = (o.blink ?? 0) || blinkAt(t, k + 1);
          inner = CT.C[a.name](o);
        } else if (a.type === 'prop') {
          const o = Object.assign({}, a.opts || {});
          if (a.glint) o.glint = -0.2 + 1.4 * clamp((t - a.glint[0]) / (a.glint[1] - a.glint[0]));
          inner = CT.P[a.name](o);
        } else if (a.type === 'arm') {
          s += CT.P.arm(a.x1, a.y1, a.x2 + shake, a.y2, a.sleeve, a.w || 54);
          s += `<g transform="translate(${a.x2 + shake} ${a.y2})">${CT.P.hand(a.skin)}</g>`;
          return;
        } else if (a.type === 'svg') { inner = a.svg; }
        const fx = a.flip ? -1 : 1;
        s += `<g transform="translate(${a.x + sway + shake} ${a.y}) rotate(${(a.rot || 0) + (a.rotSway || 0) * Math.sin(t * 1.7)}) scale(${a.s * fx} ${a.s * br})">${inner}</g>`;
      });
      if (d.tint) s += `<rect width="1080" height="1920" fill="${d.tint}" opacity="${d.tintA || .12}"/>`;
      return s;
    };
    return {
      el: box, update(t) {
        const c = camAt(t);
        svg.innerHTML = `<g transform="translate(540 960) scale(${c[3]}) translate(${-c[1]} ${-c[2]})">${draw(t)}</g>`;
        if (label) fadeUp(label, t, d.labelAt ?? 0.6, 0.8, 1);
        if (hook) { const a = E.out(P(t, d.hookAt ?? 0.2, 0.6)); const z = 1 - E.inOut(P(t, (d.hookAt ?? 0.2) + (d.hookHold ?? 2.4), 0.5)); hook.style.opacity = a * z; hook.style.transform = `translateY(${(1 - a) * 2}vh)`; }
      }
    };
  };

  T.none = () => ({ el: h('div'), update() {} });

  // lower third — name / role plate over footage
  T.lower = (d, D) => {
    const box = h('div', '', null, { position: 'absolute', left: '6%', bottom: W < H ? '33%' : '14%', display: 'flex', alignItems: 'stretch', gap: U(1.6) });
    const bar = h('div', '', null, { width: U(0.6), background: 'var(--accent)', boxShadow: '0 0 14px var(--accent)', transformOrigin: 'bottom' });
    const col = h('div', '', null, { display: 'flex', flexDirection: 'column', gap: U(0.6), padding: `${U(1.2)} ${U(2.2)}`, background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(8px)', borderRadius: U(0.6) });
    const nm = h('div', d.plain ? '' : 'h1', esc(d.title || ''), { fontSize: U(d.size || 4.4), color: '#fff', ...(d.plain ? { fontWeight: 600, letterSpacing: '-0.01em', fontSize: U(d.size || 3.6) } : {}) });
    const rl = h('div', '', esc(d.caption || ''), d.plain
      ? { fontSize: U(2.3), color: 'var(--accent)', fontWeight: 400, letterSpacing: '.01em' }
      : { fontSize: U(2.4), color: 'var(--accent)', fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase' });
    col.append(nm); if (d.caption) col.append(rl);
    box.append(bar, col);
    const hold = d.hold || Math.min(D - 0.6, 5);
    return {
      el: box, update(t) {
        const a = E.out5(P(t, d.at || 0.4, 0.7)), z = 1 - E.inOut(P(t, (d.at || 0.4) + hold, 0.5));
        bar.style.transform = `scaleY(${a * z})`;
        col.style.opacity = a * z; col.style.transform = `translateX(${(1 - a) * -4}vw)`;
      }
    };
  };

  // ------------------------------------------------------------- driver
  let tpl, contentEl, subsEl, overlayEl, subEls = [];
  window.setup = function (sc, w, hgt) {
    scene = sc; W = w; H = hgt;
    theme = THEMES[sc.theme] || THEMES.midnight;
    bgOpts = sc.bg || {};
    const st = document.getElementById('stage');
    st.style.width = W + 'px'; st.style.height = H + 'px';
    const r = st.style;
    r.setProperty('--u', (Math.min(W, H) / 100) + 'px');
    ['fg', 'muted', 'accent', 'accent2', 'card', 'border', 'glow'].forEach(k => r.setProperty('--' + k, theme[k]));
    if (sc.accent) r.setProperty('--accent', sc.accent);
    if (theme.fontDisplay) r.setProperty('--font-display', theme.fontDisplay);
    if (theme.fontText) r.setProperty('--font-text', theme.fontText);
    if (theme.displayWeight) r.setProperty('--display-weight', theme.displayWeight);
    if (theme.displayTracking) r.setProperty('--display-tracking', theme.displayTracking);
    st.classList.toggle('italic-accent', !!theme.italicAccent);
    initBg();
    if (sc.transparent) { document.documentElement.style.background = 'transparent'; document.body.style.background = 'transparent'; }
    document.getElementById('overlay').style.background = 'none';
    contentEl = document.getElementById('content');
    subsEl = document.getElementById('subs');
    overlayEl = document.getElementById('overlay');
    contentEl.innerHTML = '';
    const make = T[sc.template] || T.statement;
    tpl = make(sc.data || {}, sc.duration);
    contentEl.appendChild(tpl.el);
    subsEl.innerHTML = '';
    subEls = (sc.subs || []).map(s => { const e = h('div', 'sub', esc(s.text), { display: 'none' }); subsEl.appendChild(e); return { e, ...s }; });
    if (W < H) { subsEl.style.paddingBottom = 'calc(var(--u) * 38)'; subsEl.querySelectorAll('.sub').forEach(e => e.style.maxWidth = '78%'); }
  };
  window.seek = function (t) {
    if (scene.transparent) { ctx.clearRect(0, 0, W, H); tpl.update(t); subEls.forEach(s => { const on = t >= s.start && t < s.end; s.e.style.display = on ? 'block' : 'none'; }); return; }
    drawBg(t);
    tpl.update(t);
    // global camera drift
    // light leak
    const T2 = t + (scene.tOffset || 0);
    const lx = 50 + 45 * Math.sin(T2 * 0.23), ly = 30 + 25 * Math.cos(T2 * 0.17);
    overlayEl.style.background = `radial-gradient(ellipse at ${lx}% ${ly}%, ${theme.leak} 0%, rgba(0,0,0,0) 55%)`;
    subEls.forEach(s => {
      const on = t >= s.start && t < s.end;
      s.e.style.display = on ? 'block' : 'none';
      if (on) { const x = E.out(P(t, s.start, 0.18)); s.e.style.opacity = x; s.e.style.transform = `translateY(${(1 - x) * 8}px)`; }
    });
  };
  window.THEMES = THEMES;
})();
