/* Cartoon library: characters, props and sets drawn as SVG strings.
 * Every function is pure: state (mouth, blink, mood, t) -> SVG markup. Coordinates: stage 1080x1920.
 * Style: flat 2D with soft gradient shading, warm dark outlines, expressive eyes.
 */
(function () {
  const OUT = '#2a1a12';           // outline colour
  let UID = 0;
  const uid = p => `${p}${++UID}`;
  const f = n => (+n).toFixed(1);

  // ------------------------------------------------------------------ face
  // o: {skin, shade, hair, hairColor, beard, beardColor, brow, eye, mouth(0..1), blink(0..1), smile(-1..1),
  //     turn(-1..1), age, lips, lashes, blush, sweat, cap}
  function face(o) {
    const id = uid('f');
    const sk = o.skin || '#d9a77c', sh = o.shade || '#b9845c';
    const tx = (o.turn || 0) * 16;
    const blink = Math.min(1, o.blink || 0);
    const mood = o.brow || 'neutral';
    let s = '';
    s += `<defs><radialGradient id="${id}g" cx="45%" cy="38%" r="70%"><stop offset="0" stop-color="${sk}"/><stop offset="1" stop-color="${sh}"/></radialGradient>
      <clipPath id="${id}eL"><ellipse cx="${-38 + tx}" cy="0" rx="18" ry="12"/></clipPath>
      <clipPath id="${id}eR"><ellipse cx="${38 + tx}" cy="0" rx="18" ry="12"/></clipPath></defs>`;
    // neck
    s += `<path d="M-42 95 L-46 175 L46 175 L42 95 Z" fill="${sh}" stroke="${OUT}" stroke-width="4"/>`;
    // back hair (long hair behind head)
    if (o.hair === 'long') s += `<path d="M-112 -40 C-130 90,-120 200,-80 250 L80 250 C120 200,130 90,112 -40 C100 -150,-100 -150,-112 -40 Z" fill="${o.hairColor}" stroke="${OUT}" stroke-width="4"/>`;
    // ears
    s += `<ellipse cx="${-92 + tx * 0.5}" cy="8" rx="17" ry="26" fill="${sk}" stroke="${OUT}" stroke-width="4"/>`;
    s += `<ellipse cx="${92 + tx * 0.5}" cy="8" rx="17" ry="26" fill="${sk}" stroke="${OUT}" stroke-width="4"/>`;
    if (o.earrings) s += `<circle cx="${-94 + tx * .5}" cy="40" r="11" fill="#e8c35a" stroke="${OUT}" stroke-width="3"/><circle cx="${94 + tx * .5}" cy="40" r="11" fill="#e8c35a" stroke="${OUT}" stroke-width="3"/>`;
    // head
    s += `<path d="M-90 -25 C-92 -128,92 -128,90 -25 C92 62,52 122,0 126 C-52 122,-92 62,-90 -25 Z" fill="url(#${id}g)" stroke="${OUT}" stroke-width="4.5"/>`;
    // age lines
    if (o.age === 'old') s += `<path d="M-60 -62 Q-30 -70 0 -62 M-50 -50 Q-20 -58 10 -50 M${-62 + tx} 22 Q${-52 + tx} 30 ${-44 + tx} 22 M${44 + tx} 22 Q${52 + tx} 30 ${62 + tx} 22" stroke="${sh}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
    if (o.blush) s += `<ellipse cx="${-50 + tx}" cy="40" rx="20" ry="11" fill="#e0606a" opacity="${o.blush}"/><ellipse cx="${50 + tx}" cy="40" rx="20" ry="11" fill="#e0606a" opacity="${o.blush}"/>`;
    // eyes
    const eye = (cx, side) => {
      const gx = cx + tx + (o.gaze || 0) * 6, gy = (o.gazeY || 0) * 4;
      let e = `<ellipse cx="${cx + tx}" cy="0" rx="18" ry="12" fill="#fbf7f0" stroke="${OUT}" stroke-width="3"/>`;
      e += `<g clip-path="url(#${id}e${side})"><circle cx="${gx}" cy="${gy}" r="9" fill="${o.eye || '#4a2e1c'}"/><circle cx="${gx}" cy="${gy}" r="4.5" fill="#120a06"/><circle cx="${gx + 3}" cy="${gy - 3}" r="2.6" fill="#fff"/>`;
      // upper lid: blink + mood (angry lowers it diagonally, tired lowers it flat)
      const base = { angry: 0.38, tired: 0.42, sad: 0.3, closed: 1, neutral: 0.12, worried: 0.1, raised: 0.02, smug: 0.4, fear: 0 }[mood] ?? 0.12;
      const k = Math.max(base, blink);
      const tilt = mood === 'angry' ? (side === 'L' ? 7 : -7) : mood === 'worried' || mood === 'sad' ? (side === 'L' ? -6 : 6) : 0;
      const yl = -13 + 26 * k;
      e += `<path d="M${cx + tx - 22} -14 L${cx + tx + 22} -14 L${cx + tx + 22} ${yl - tilt} L${cx + tx - 22} ${yl + tilt} Z" fill="${sk}"/>`;
      e += `<path d="M${cx + tx - 20} ${yl + tilt} L${cx + tx + 20} ${yl - tilt}" stroke="${OUT}" stroke-width="3.5"/></g>`;
      if (o.lashes) e += `<path d="M${cx + tx + (side === 'L' ? -18 : 18)} ${-4 + 26 * Math.max(blink, 0.1) - 13} l${side === 'L' ? -8 : 8} -6" stroke="${OUT}" stroke-width="3.5" stroke-linecap="round"/>`;
      return e;
    };
    s += eye(-38, 'L') + eye(38, 'R');
    // brows
    const bw = o.browW || 7, bc = o.browColor || o.hairColor || '#2b1d14';
    const by = mood === 'raised' || mood === 'fear' ? -40 : -30;
    const bt = { angry: [12, -6], worried: [-10, 4], sad: [-10, 4], fear: [-12, 2], smug: [4, -4], tired: [-4, 2] }[mood] || [0, 0];
    s += `<path d="M${-62 + tx} ${by - bt[1]} Q${-42 + tx} ${by - 9} ${-16 + tx} ${by + bt[0]}" stroke="${bc}" stroke-width="${bw}" fill="none" stroke-linecap="round"/>`;
    s += `<path d="M${62 + tx} ${by - bt[1]} Q${42 + tx} ${by - 9} ${16 + tx} ${by + bt[0]}" stroke="${bc}" stroke-width="${bw}" fill="none" stroke-linecap="round"/>`;
    // nose
    s += `<path d="M${-2 + tx * 1.3} 8 Q${-14 + tx * 1.3} 38 ${-12 + tx * 1.3} 44 Q${2 + tx * 1.3} 52 ${14 + tx * 1.3} 44" stroke="${sh}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
    // sweat drop
    if (o.sweat) s += `<path d="M${76} -40 q8 16 0 22 q-8 -6 0 -22z" fill="#bfe6ff" stroke="${OUT}" stroke-width="2.5" opacity="${o.sweat}"/>`;
    // beard (under mouth)
    const bcol = o.beardColor || o.hairColor || '#2b1d14';
    if (o.beard === 'full') s += `<path d="M-88 10 C-86 80,-50 132,0 146 C50 132,86 80,88 10 C78 60,60 76,40 84 C20 74,-20 74,-40 84 C-60 76,-78 60,-88 10 Z" fill="${bcol}" stroke="${OUT}" stroke-width="3.5"/>`;
    if (o.beard === 'long') s += `<path d="M-88 10 C-90 110,-50 210,0 238 C50 210,90 110,88 10 C78 60,60 76,40 84 C20 74,-20 74,-40 84 C-60 76,-78 60,-88 10 Z" fill="${bcol}" stroke="${OUT}" stroke-width="3.5"/>`;
    if (o.beard === 'pointed') s += `<path d="M-86 14 C-80 80,-40 120,0 178 C40 120,80 80,86 14 C76 60,60 76,40 84 C20 74,-20 74,-40 84 C-60 76,-76 60,-86 14 Z" fill="${bcol}" stroke="${OUT}" stroke-width="3.5"/>`;
    if (o.beard === 'short') s += `<path d="M-84 20 C-78 82,-40 118,0 124 C40 118,78 82,84 20 C72 66,56 78,38 86 C20 78,-20 78,-38 86 C-56 78,-72 66,-84 20 Z" fill="${bcol}" opacity=".92" stroke="${OUT}" stroke-width="3"/>`;
    if (o.beard === 'stubble') s += `<path d="M-84 20 C-78 82,-40 118,0 124 C40 118,78 82,84 20 C72 66,56 78,38 86 C20 78,-20 78,-38 86 C-56 78,-72 66,-84 20 Z" fill="${bcol}" opacity=".28"/>`;
    // mouth
    const m = Math.max(0, Math.min(1, o.mouth || 0)), sm = o.smile || 0;
    const mx = tx * 1.1, my = 78;
    if (m < 0.08) {
      s += `<path d="M${mx - 24} ${my} Q${mx} ${my + 12 * sm} ${mx + 24} ${my}" stroke="${o.lips ? '#a02a3a' : '#5b2a1e'}" stroke-width="${o.lips ? 7 : 4.5}" fill="none" stroke-linecap="round"/>`;
    } else {
      const w = 22 + 6 * m, hgt = 6 + 22 * m;
      s += `<path d="M${mx - w} ${my} Q${mx} ${my - 6 + 10 * sm} ${mx + w} ${my} Q${mx} ${my + hgt * 2} ${mx - w} ${my} Z" fill="#5a1414" stroke="${o.lips ? '#b02a3e' : OUT}" stroke-width="${o.lips ? 6 : 3.5}"/>`;
      s += `<path d="M${mx - w + 6} ${my + 1} Q${mx} ${my + 4} ${mx + w - 6} ${my + 1} L${mx + w - 9} ${my + 6} Q${mx} ${my + 9} ${mx - w + 9} ${my + 6} Z" fill="#fff"/>`;
    }
    // mustache over mouth
    if (o.mustache || ['full', 'long', 'pointed', 'short'].includes(o.beard))
      s += `<path d="M${mx - 4} ${my - 14} C${mx - 30} ${my - 22},${mx - 46} ${my - 6},${mx - 50} ${my + 4} C${mx - 34} ${my - 4},${mx - 16} ${my - 6},${mx} ${my - 8} C${mx + 16} ${my - 6},${mx + 34} ${my - 4},${mx + 50} ${my + 4} C${mx + 46} ${my - 6},${mx + 30} ${my - 22},${mx + 4} ${my - 14} Z" fill="${bcol}" stroke="${OUT}" stroke-width="3"/>`;
    // hair on top
    const hc = o.hairColor || '#2b1d14';
    if (o.hair === 'short') s += `<path d="M-92 -20 C-104 -110,-40 -150,10 -140 C70 -142,104 -100,92 -20 C84 -64,66 -84,40 -90 C10 -76,-40 -80,-70 -78 C-84 -66,-90 -44,-92 -20 Z" fill="${hc}" stroke="${OUT}" stroke-width="4"/>`;
    if (o.hair === 'grey') s += `<path d="M-92 -10 C-100 -60,-80 -96,-50 -104 C-70 -80,-80 -50,-84 -10 Z M92 -10 C100 -60,80 -96,50 -104 C70 -80,80 -50,84 -10 Z" fill="#d8d4cc" stroke="${OUT}" stroke-width="3"/>`;
    if (o.hair === 'long') s += `<path d="M-94 -24 C-104 -128,-20 -160,20 -148 C92 -150,114 -92,96 -24 C88 -74,62 -102,24 -110 C-6 -92,-58 -86,-94 -24 Z" fill="${hc}" stroke="${OUT}" stroke-width="4"/>
       <path d="M-60 -120 C-20 -150,40 -150,70 -118" stroke="#fff" stroke-opacity=".25" stroke-width="10" fill="none" stroke-linecap="round"/>`;
    if (o.hair === 'kid') s += `<path d="M-90 -20 C-100 -120,-20 -146,20 -138 C80 -136,104 -90,90 -20 C80 -70,40 -70,20 -96 C0 -70,-50 -70,-90 -20 Z" fill="${hc}" stroke="${OUT}" stroke-width="4"/>`;
    return s;
  }

  // ------------------------------------------------------------------ bodies & outfits
  function torso(fill, trim, o = {}) {
    // shoulders / chest (bust), origin at chin; returns markup
    const w = o.w || 170;
    let s = `<path d="M${-w} 400 C${-w} 260,${-w + 30} 200,-60 168 L60 168 C${w - 30} 200,${w} 260,${w} 400 Z" fill="${fill}" stroke="${OUT}" stroke-width="5"/>`;
    if (trim) s += trim;
    return s;
  }

  const C = {};

  // DOCTOR — one face, three eras
  C.doctor = (o = {}) => {
    const era = o.era || 'modern';
    let s = '';
    const fo = { skin: '#d9a77c', shade: '#b9845c', hair: era === 'hakim' ? 'none' : 'short', hairColor: '#2b1d14', beard: 'short', beardColor: '#2b1d14',
      brow: o.mood || 'worried', mouth: o.mouth, blink: o.blink, smile: o.smile || 0, turn: o.turn || 0, gaze: o.gaze, gazeY: o.gazeY, sweat: o.sweat, eye: '#3b2414' };
    if (era === 'hakim') {
      s += torso('#e6dcc6', `<path d="M-60 168 L0 300 L60 168" fill="none" stroke="#8a6a44" stroke-width="7"/><path d="M-170 330 L170 330" stroke="#7a5230" stroke-width="22"/><path d="M-120 230 Q-110 300 -90 400 M120 230 Q110 300 90 400" stroke="#cbbd9f" stroke-width="5" fill="none"/>`);
      s += `<g>${face(fo)}</g>`;
      s += `<path d="M-96 -46 C-100 -150,100 -150,96 -46 C70 -70,-70 -70,-96 -46 Z" fill="#f2ead8" stroke="${OUT}" stroke-width="4"/><path d="M-90 -60 C-40 -80,40 -80,90 -60" stroke="#cdbf9f" stroke-width="5" fill="none"/>`;
    } else if (era === 'field') {
      s += torso('#8c7a4e', `<path d="M-60 168 L-20 240 L0 200 L20 240 L60 168" fill="#7a6a42" stroke="${OUT}" stroke-width="4"/><rect x="-150" y="250" width="60" height="44" rx="6" fill="#fff" stroke="${OUT}" stroke-width="3"/><path d="M-120 256 v32 M-136 272 h32" stroke="#d62c2c" stroke-width="9"/><path d="M-40 200 C-60 300,-20 330,10 300" stroke="#222" stroke-width="7" fill="none"/><circle cx="12" cy="300" r="13" fill="#bbb" stroke="#222" stroke-width="4"/>`);
      s += face(fo);
    } else {
      s += torso('#f4f6f8', `<path d="M-64 168 L0 260 L64 168 Z" fill="#7fb6c9" stroke="${OUT}" stroke-width="4"/><path d="M-64 168 L-30 400 M64 168 L30 400" stroke="#d7dde2" stroke-width="5"/><path d="M-50 190 C-80 290,-40 320,-6 296" stroke="#2a3a48" stroke-width="7" fill="none"/><circle cx="-4" cy="298" r="14" fill="#c7ccd1" stroke="#2a3a48" stroke-width="4"/><rect x="70" y="250" width="66" height="40" rx="5" fill="#fff" stroke="#8aa" stroke-width="3"/><rect x="78" y="258" width="20" height="24" fill="#9ab"/>`);
      s += face(fo);
    }
    return s;
  };

  C.padishah = (o = {}) => {
    let s = '';
    s += torso('#8e1b24', `<path d="M-70 168 C-40 230,40 230,70 168 L64 400 L-64 400 Z" fill="#c9a24a" stroke="${OUT}" stroke-width="4"/>
      <path d="M-160 290 Q0 330 160 290" stroke="#e2c065" stroke-width="10" fill="none"/>
      ${[0, 1, 2, 3].map(i => `<circle cx="0" cy="${240 + i * 40}" r="9" fill="#d81e3a" stroke="#e8c35a" stroke-width="4"/>`).join('')}
      <path d="M-150 230 q20 -20 40 0 q20 20 40 0 M110 230 q20 -20 40 0" stroke="#e2c065" stroke-width="5" fill="none"/>`, { w: 190 });
    s += face({ skin: '#c98d63', shade: '#a26a44', beard: 'pointed', beardColor: '#15100c', hairColor: '#15100c', brow: o.mood || 'angry', browW: 9,
      mouth: o.mouth, blink: o.blink, smile: o.smile ?? -0.3, turn: o.turn ?? 0.35, gaze: o.gaze ?? 1, eye: '#1d120a' });
    // turban with ruby aigrette and plume
    s += `<path d="M-112 -40 C-130 -170,130 -170,112 -40 C80 -66,-80 -66,-112 -40 Z" fill="#f6efe2" stroke="${OUT}" stroke-width="4.5"/>
      <path d="M-104 -70 C-50 -110,60 -120,108 -64 M-96 -100 C-40 -140,60 -140,100 -96" stroke="#d9cbb0" stroke-width="7" fill="none"/>
      <path d="M-8 -120 C-30 -210,10 -250,20 -300 C30 -240,40 -200,14 -120 Z" fill="#fff8e8" stroke="${OUT}" stroke-width="3.5"/>
      <path d="M8 -150 C0 -200,14 -240,20 -280" stroke="#e6d6b0" stroke-width="3" fill="none"/>
      <ellipse cx="2" cy="-112" rx="24" ry="30" fill="#c8102e" stroke="#e8c35a" stroke-width="7"/><ellipse cx="-6" cy="-122" rx="7" ry="9" fill="#ff8a9a" opacity=".8"/>`;
    return s;
  };

  C.warrior = (o = {}) => {
    let s = '';
    s += torso('#6a5e4c', `<path d="M-185 260 C-120 200,-60 190,0 230 C60 190,120 200,185 260 L185 400 L-185 400 Z" fill="#8a7c62" stroke="${OUT}" stroke-width="4.5"/>
      <path d="M-170 300 L170 300 M-176 340 L176 340" stroke="#a89878" stroke-width="5" stroke-dasharray="14 10"/>`, { w: 185 });
    s += face({ skin: '#b98060', shade: '#94603f', beard: 'long', beardColor: '#2c2420', hairColor: '#2c2420', brow: o.mood || 'angry', browW: 9,
      mouth: o.mouth, blink: o.blink, smile: -0.4, turn: o.turn ?? 0.35, gaze: o.gaze ?? 1, eye: '#24160c', age: 'mid' });
    s += `<path d="M-60 120 C-50 180,-30 220,-20 236 M40 140 C30 190,26 220,20 236" stroke="#5f544b" stroke-width="5" fill="none" opacity=".6"/>`;
    // pakol hat
    s += `<path d="M-100 -50 C-104 -120,104 -120,100 -50 Z" fill="#8a7458" stroke="${OUT}" stroke-width="4"/>
      <path d="M-108 -50 C-110 -20,110 -20,108 -50 C108 -80,-108 -80,-108 -50 Z" fill="#9b8466" stroke="${OUT}" stroke-width="4.5"/>
      <path d="M-100 -52 C-40 -64,40 -64,100 -52" stroke="#776248" stroke-width="5" fill="none"/>`;
    return s;
  };

  C.woman = (o = {}) => {
    let s = '';
    // fur coat
    s += torso('#c9ae8a', `${Array.from({ length: 22 }, (_, i) => `<circle cx="${-170 + i * 16}" cy="${236 + Math.sin(i * 1.7) * 10}" r="${20 + (i % 3) * 4}" fill="#e7d6bb" stroke="#b39a78" stroke-width="2"/>`).join('')}
      <path d="M-60 180 L0 260 L60 180" fill="#1e1e24" stroke="${OUT}" stroke-width="3"/><path d="M-30 210 Q0 240 30 210" stroke="#e8c35a" stroke-width="5" fill="none"/>`, { w: 180 });
    s += face({ skin: '#f1c9a8', shade: '#d9a582', hair: 'long', hairColor: '#d8b25e', brow: o.mood || 'angry', browColor: '#7a5a2a', browW: 6,
      mouth: o.mouth, blink: o.blink, smile: -0.4, turn: o.turn ?? -0.3, gaze: o.gaze ?? -1, lips: true, lashes: true, earrings: true, eye: '#3d6b8a', blush: .25 });
    // sunglasses on hair
    s += `<g transform="translate(0 -118)"><ellipse cx="-36" cy="0" rx="30" ry="18" fill="#141418" stroke="#e8c35a" stroke-width="4"/><ellipse cx="36" cy="0" rx="30" ry="18" fill="#141418" stroke="#e8c35a" stroke-width="4"/><path d="M-8 0 h16" stroke="#e8c35a" stroke-width="4"/></g>`;
    return s;
  };

  C.boy = (o = {}) => {  // lying, head on pillow, eyes closed
    let s = `<ellipse cx="0" cy="40" rx="250" ry="70" fill="#7d1d2a" stroke="${OUT}" stroke-width="4"/>
      <path d="M-120 20 C-60 -10,200 -10,260 30 C240 90,-100 100,-120 60 Z" fill="#e8d6a8" stroke="${OUT}" stroke-width="4"/>`;
    s += `<g transform="translate(-170 -10) rotate(-80) scale(.55)">${face({ skin: '#d9a77c', shade: '#b9845c', hair: 'kid', hairColor: '#20140c', brow: 'sad', blink: 1, mouth: 0, blush: .6 })}</g>`;
    s += `<rect x="-215" y="-45" width="70" height="26" rx="8" transform="rotate(-80 -180 -32)" fill="#fff" opacity=".9" stroke="${OUT}" stroke-width="2"/>`;
    return s;
  };

  C.oldman = (o = {}) => {
    let s = `<path d="M-280 70 C-200 20,260 10,300 70 L300 110 L-280 110 Z" fill="#5c4a6e" stroke="${OUT}" stroke-width="4"/>
      <path d="M-160 30 C-60 -20,240 -10,290 60 C200 90,-60 90,-160 70 Z" fill="#a36a4a" stroke="${OUT}" stroke-width="4"/>
      ${Array.from({ length: 8 }, (_, i) => `<path d="M${-120 + i * 50} 40 l20 30" stroke="#d7b26a" stroke-width="6"/>`).join('')}`;
    s += `<g transform="translate(-200 10) rotate(-85) scale(.55)">${face({ skin: '#c79270', shade: '#a2704f', hair: 'grey', beard: 'long', beardColor: '#e8e4dc', brow: 'sad', browColor: '#ddd', blink: 1, age: 'old' })}</g>`;
    return s;
  };

  // ------------------------------------------------------------------ props
  const P = {};
  P.scimitar = (o = {}) => {   // grip at origin, blade toward +x
    const g = uid('b'), gl = o.glint ?? -1;
    return `<defs><linearGradient id="${g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4f7fa"/><stop offset=".55" stop-color="#b9c3cc"/><stop offset="1" stop-color="#7f8a95"/></linearGradient>
        <linearGradient id="${g}s" x1="0" x2="1"><stop offset="${Math.max(0, gl - .08)}" stop-color="#fff" stop-opacity="0"/><stop offset="${Math.max(0, Math.min(1, gl))}" stop-color="#fff" stop-opacity=".95"/><stop offset="${Math.min(1, gl + .08)}" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
      <path d="M40 -10 C220 -30,420 -10,560 70 C440 30,240 20,40 18 Z" fill="url(#${g})" stroke="${OUT}" stroke-width="4"/>
      <path d="M40 -10 C220 -30,420 -10,560 70 C440 30,240 20,40 18 Z" fill="url(#${g}s)"/>
      <path d="M50 4 C220 -6,400 10,520 56" stroke="#8e98a2" stroke-width="2" fill="none"/>
      <rect x="22" y="-38" width="22" height="76" rx="8" fill="#d4a93c" stroke="${OUT}" stroke-width="4"/>
      <circle cx="33" cy="-26" r="7" fill="#d81e3a" stroke="#f0cf6a" stroke-width="2.5"/><circle cx="33" cy="26" r="7" fill="#d81e3a" stroke="#f0cf6a" stroke-width="2.5"/>
      <rect x="-80" y="-14" width="104" height="28" rx="12" fill="#5a1a1e" stroke="${OUT}" stroke-width="4"/>
      ${[-60, -36, -12].map(x => `<circle cx="${x}" cy="0" r="6" fill="#d81e3a" stroke="#f0cf6a" stroke-width="2"/>`).join('')}
      <circle cx="-92" cy="0" r="16" fill="#d4a93c" stroke="${OUT}" stroke-width="4"/><circle cx="-92" cy="0" r="8" fill="#c8102e"/>`;
  };
  P.pistol = () => `<path d="M0 -24 L200 -24 L200 6 L60 6 L50 30 L20 100 L-24 92 L0 20 Z" fill="#2a2c30" stroke="#0e0f11" stroke-width="4"/>
      <rect x="180" y="-30" width="22" height="10" fill="#2a2c30"/><path d="M10 -14 L190 -14" stroke="#4a4e55" stroke-width="4"/>
      <path d="M40 10 q14 28 -6 34" stroke="#0e0f11" stroke-width="5" fill="none"/>`;
  P.hand = (skin = '#d9a77c') => `<ellipse cx="0" cy="0" rx="34" ry="28" fill="${skin}" stroke="${OUT}" stroke-width="4"/><path d="M-20 -18 q-14 -10 -6 -24 M0 -24 q-4 -14 6 -22" stroke="${OUT}" stroke-width="3" fill="none"/>`;
  P.arm = (x1, y1, x2, y2, sleeve, w = 54) => `<path d="M${x1} ${y1} L${x2} ${y2}" stroke="${OUT}" stroke-width="${w + 9}" stroke-linecap="round"/><path d="M${x1} ${y1} L${x2} ${y2}" stroke="${sleeve}" stroke-width="${w}" stroke-linecap="round"/>`;
  P.phone = (o = {}) => `<rect x="-62" y="-118" width="124" height="236" rx="18" fill="#141418" stroke="#8a8f96" stroke-width="5"/>
      <rect x="-52" y="-100" width="104" height="200" rx="8" fill="#203040"/><circle cx="-26" cy="-80" r="9" fill="#ff2d3d" opacity="${o.rec ?? 1}"/><text x="-10" y="-73" font-family="Manrope" font-weight="800" font-size="20" fill="#fff">REC</text>
      <rect x="-40" y="-40" width="80" height="100" rx="6" fill="#2d4258"/><circle cx="0" cy="-5" r="20" fill="#d9a77c"/><path d="M-28 50 C-20 20,20 20,28 50 Z" fill="#f4f6f8"/>`;
  P.lamp = (o = {}) => {
    const fl = o.flicker ?? 1;
    return `<circle cx="0" cy="40" r="${220 * fl}" fill="url(#lampGlow)"/><path d="M0 -300 L0 -40" stroke="#3a2a1a" stroke-width="4"/>
      <path d="M-30 -40 L30 -40 L22 -20 L-22 -20 Z" fill="#6b4a22" stroke="${OUT}" stroke-width="3"/><path d="M-26 -20 C-40 30,40 30,26 -20 Z" fill="#ffe7a8" opacity=".85" stroke="${OUT}" stroke-width="3"/>
      <path d="M0 0 q-8 14 0 26 q8 -12 0 -26" fill="#ffb347"/><rect x="-30" y="26" width="60" height="22" rx="4" fill="#6b4a22" stroke="${OUT}" stroke-width="3"/>`;
  };

  // ------------------------------------------------------------------ sets (1080x1920)
  const S = {};
  S.palace = (t = 0) => {
    let s = `<defs><linearGradient id="pal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2a0d12"/><stop offset=".6" stop-color="#4a1520"/><stop offset="1" stop-color="#1a0709"/></linearGradient>
      <radialGradient id="palGlow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffcf7a" stop-opacity=".55"/><stop offset="1" stop-color="#ffcf7a" stop-opacity="0"/></radialGradient></defs>
      <rect width="1080" height="1920" fill="url(#pal)"/>`;
    // arches with lattice windows
    for (let i = 0; i < 3; i++) {
      const x = 60 + i * 340;
      s += `<path d="M${x} 1300 L${x} 520 Q${x} 330 ${x + 140} 260 Q${x + 280} 330 ${x + 280} 520 L${x + 280} 1300 Z" fill="#1a0a0c" stroke="#c9a24a" stroke-width="8"/>`;
      s += `<path d="M${x + 30} 1270 L${x + 30} 540 Q${x + 30} 380 ${x + 140} 320 Q${x + 250} 380 ${x + 250} 540 L${x + 250} 1270 Z" fill="#3b1830"/>`;
      for (let k = 0; k < 9; k++) s += `<path d="M${x + 30} ${560 + k * 80} L${x + 250} ${560 + k * 80}" stroke="#c9a24a" stroke-opacity=".35" stroke-width="3"/>`;
      for (let k = 0; k < 4; k++) s += `<path d="M${x + 30 + k * 55} 540 L${x + 30 + k * 55} 1270" stroke="#c9a24a" stroke-opacity=".35" stroke-width="3"/>`;
      s += `<ellipse cx="${x + 140}" cy="760" rx="120" ry="300" fill="#7a3fb0" opacity=".12"/>`;
    }
    // hanging lamps
    [200, 540, 880].forEach((x, i) => {
      const sw = Math.sin(t * 1.2 + i) * 4;
      s += `<g transform="translate(${x + sw} 200)"><path d="M0 -200 L0 0" stroke="#c9a24a" stroke-width="3"/><circle r="150" fill="url(#palGlow)"/><path d="M-24 0 L24 0 L14 44 L-14 44 Z" fill="#d4a93c" stroke="${OUT}" stroke-width="3"/><circle cy="20" r="10" fill="#fff1c0"/></g>`;
    });
    // carpet floor
    s += `<path d="M0 1300 L1080 1300 L1080 1920 L0 1920 Z" fill="#5a1520"/>
      <path d="M-60 1920 L180 1340 L900 1340 L1140 1920 Z" fill="#8e1b24" stroke="#d4a93c" stroke-width="10"/>
      <path d="M60 1920 L240 1400 L840 1400 L1020 1920 Z" fill="none" stroke="#d4a93c" stroke-width="5" stroke-dasharray="24 14"/>
      <path d="M540 1420 L640 1600 L540 1780 L440 1600 Z" fill="#1d3a6e" stroke="#d4a93c" stroke-width="6"/>`;
    return s;
  };
  S.tent = (t = 0, fl = 1) => {
    let s = `<defs><radialGradient id="lampGlow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#ffb347" stop-opacity=".55"/><stop offset="1" stop-color="#ffb347" stop-opacity="0"/></radialGradient>
      <linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b1430"/><stop offset="1" stop-color="#2a3150"/></linearGradient></defs>
      <rect width="1080" height="1920" fill="#2b2016"/>`;
    // tent opening to the night with mountains and stars
    s += `<path d="M300 1250 L540 420 L780 1250 Z" fill="url(#night)"/>`;
    for (let i = 0; i < 40; i++) { const x = 330 + ((i * 97) % 420), y = 520 + ((i * 53) % 520); if (Math.abs(x - 540) < (y - 420) * 0.28) s += `<circle cx="${x}" cy="${y}" r="${1.5 + (i % 3)}" fill="#fff" opacity="${0.4 + 0.5 * Math.abs(Math.sin(t * 2 + i))}"/>`; }
    s += `<path d="M330 1250 L420 1010 L480 1080 L560 930 L640 1060 L700 1000 L760 1250 Z" fill="#141a2c"/>`;
    // canvas walls
    s += `<path d="M0 0 L540 380 L0 1500 Z" fill="#6a5236"/><path d="M1080 0 L540 380 L1080 1500 Z" fill="#5a442c"/>
      <path d="M0 0 L540 380 L300 1250 L0 1500 Z" fill="#7a5e3e" opacity=".9"/><path d="M1080 0 L540 380 L780 1250 L1080 1500 Z" fill="#664c30" opacity=".9"/>
      <path d="M540 380 L300 1250 M540 380 L780 1250" stroke="#3a2a18" stroke-width="10"/>
      <path d="M100 200 L540 380 M980 200 L540 380" stroke="#4a3620" stroke-width="5" opacity=".6"/>`;
    // rug floor
    s += `<path d="M0 1250 L1080 1250 L1080 1920 L0 1920 Z" fill="#3a2a1c"/><path d="M80 1920 L200 1330 L880 1330 L1000 1920 Z" fill="#7a2626" stroke="#c99b4a" stroke-width="8"/>
      <path d="M180 1920 L270 1400 L810 1400 L900 1920 Z" fill="none" stroke="#1f3b5a" stroke-width="16"/>`;
    s += `<rect width="1080" height="1920" fill="#ffb347" opacity="${0.06 * fl}"/>`;
    return s;
  };
  S.clinic = (t = 0) => {
    let s = `<rect width="1080" height="1920" fill="#c9d6d9"/><rect y="0" width="1080" height="1180" fill="#b7c8cc"/>
      <rect x="80" y="260" width="420" height="560" fill="#e9f3f6" stroke="#8aa0a6" stroke-width="10"/>`;
    for (let k = 0; k < 14; k++) s += `<rect x="90" y="${270 + k * 39}" width="400" height="20" fill="#cfdde1"/>`;
    // monitor with ECG
    s += `<rect x="640" y="380" width="340" height="230" rx="16" fill="#1a2228" stroke="#56666d" stroke-width="8"/>`;
    let d = 'M660 500'; for (let x = 0; x < 300; x += 6) { const ph = (x / 300 + t * 0.6) % 1; const y = ph > 0.45 && ph < 0.5 ? -60 * Math.sin((ph - 0.45) / 0.05 * Math.PI) : ph > 0.5 && ph < 0.54 ? 30 : 0; d += ` L${660 + x} ${500 + y}`; }
    s += `<path d="${d}" stroke="#3dff8a" stroke-width="4" fill="none"/><text x="900" y="420" font-family="Manrope" font-size="30" font-weight="700" fill="#3dff8a">72</text>`;
    s += `<rect x="0" y="1180" width="1080" height="740" fill="#9fb0b5"/><path d="M0 1180 L1080 1180" stroke="#7d9096" stroke-width="6"/>`;
    s += `<rect width="1080" height="1920" fill="#7ad3e8" opacity=".08"/>`;
    return s;
  };
  S.corridor = (t = 0) => {
    let s = `<defs><linearGradient id="cor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0f1a22"/><stop offset="1" stop-color="#1c2a33"/></linearGradient></defs>
      <rect width="1080" height="1920" fill="url(#cor)"/>
      <path d="M0 0 L380 700 L380 1200 L0 1920 Z" fill="#16232b"/><path d="M1080 0 L700 700 L700 1200 L1080 1920 Z" fill="#132029"/>
      <rect x="380" y="700" width="320" height="500" fill="#24363f"/><rect x="470" y="780" width="140" height="380" fill="#3a5560" opacity=".6"/>
      <path d="M0 1920 L380 1200 L700 1200 L1080 1920 Z" fill="#203038"/>`;
    [0.2, 0.45, 0.7].forEach((k, i) => { const y = 700 * (1 - k) * 0.6; s += `<rect x="${380 - 380 * (1 - k)}" y="${y}" width="${320 + 760 * (1 - k)}" height="${12 + 20 * (1 - k)}" fill="#cfe9ff" opacity="${0.5 + 0.2 * Math.sin(t * 3 + i)}"/>`; });
    s += `<rect x="560" y="300" width="130" height="50" rx="6" fill="#1fbf6a"/><text x="572" y="336" font-family="Manrope" font-weight="800" font-size="30" fill="#fff">EXIT</text>`;
    return s;
  };
  S.dark = () => `<rect width="1080" height="1920" fill="#0b0907"/>`;

  window.CARTOON = { face, C, P, S, OUT };
})();
