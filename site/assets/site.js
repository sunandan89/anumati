/* Anumati website. Lifted from docs/anumati-prototype.html by site/tools/build_from_prototype.py.
   Edit the prototype, then regenerate; hand edits here are overwritten. */
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => Number(n).toLocaleString('en-IN');
const ICONS = {
  plus:'<path d="M12 5v14M5 12h14"/>', x:'<path d="M6 6l12 12M18 6L6 18"/>', search:'<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/>',
  back:'<path d="M15 5l-7 7 7 7"/>', check:'<path d="M5 12l5 5 9-11"/>', mic:'<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M6 11a6 6 0 0012 0M12 17v4"/>',
  thumb:'<path d="M8 20c-1-3-1-9 4-11s6 3 6 7M10 20c0-4 0-7 2-8M14 20c1-2 1-5 0-6"/>', user:'<circle cx="12" cy="8" r="4"/><path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6"/>',
  sync:'<path d="M4 12a8 8 0 0114-5l2 2M20 12a8 8 0 01-14 5l-2-2M20 4v5h-5M4 20v-5h5"/>', play:'<path d="M7 4v16l13-8z" fill="currentColor" stroke="none"/>',
  pause:'<path d="M7 4h3v16H7zM14 4h3v16h-3z" fill="currentColor" stroke="none"/>', phone:'<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
  shield:'<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>', chain:'<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
  globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>', slip:'<path d="M6 3h12v18H6z"/><path d="M6 14h12" stroke-dasharray="2 2"/><path d="M9 7h6M9 10h4"/>',
  wa:'<path d="M4 20l1.5-4A8 8 0 1112 20a8 8 0 01-4-1z"/>', sms:'<path d="M4 5h16v11H9l-5 4z"/>', code:'<path d="M9 7l-5 5 5 5M15 7l5 5-5 5"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>', eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'
};
const ic = (n, s=20) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n]||''}</svg>`;


/* ================= ART: logo, Maina, line illustrations ================= */
let _mk = 0;
function mark(s = 28){
  const id = 'fp' + (++_mk);
  const rings = [[5,'9 3'],[9,'18 4 6 3'],[13,'26 5 10 4'],[17,'34 6 14 5'],[21,'40 7 22 6'],[25,'52 8 18 6'],[29,'60 9 30 7']];
  return `<svg class="logo" width="${s}" height="${s}" viewBox="0 0 64 64" aria-hidden="true"><defs><clipPath id="${id}"><circle cx="32" cy="32" r="30"/></clipPath></defs>
    <circle cx="32" cy="32" r="31" fill="#B4532A"/>
    <g clip-path="url(#${id})" fill="none" stroke="#F6D2BA" stroke-width="1.6" stroke-linecap="round" opacity=".7">${rings.map(([r,da],i) => `<circle cx="30" cy="37" r="${r}" stroke-dasharray="${da}" transform="rotate(${i*47} 30 37)"/>`).join('')}</g>
    <text x="32" y="46" text-anchor="middle" style="font-family:Hind,'Noto Sans Devanagari',sans-serif;font-weight:600;font-size:38px;fill:#FFF7EF;stroke:#B4532A;stroke-width:6px;paint-order:stroke;stroke-linejoin:round">अ</text></svg>`;
}
function wordmark(s = 40){
  return `<span class="row" style="gap:10px">${mark(s)}<span style="display:flex;flex-direction:column;line-height:1"><span style="font-family:var(--disp);font-variation-settings:'SOFT' 100;font-weight:600;font-size:${s*0.55}px;color:var(--ink)">Anumati</span><span class="hi" style="font-size:${s*0.3}px;color:var(--ink3);margin-top:3px">अनुमति</span></span></span>`;
}
/* Maina — an original mynah mascot. poses: perch | envelope | sleep | wave | talk */
function maina(pose = 'perch', w = 120, cls = ''){
  const eye = pose === 'sleep'
    ? `<path d="M81 40 q4 3 8 0" stroke="#1E1611" stroke-width="1.8" fill="none" stroke-linecap="round"/>`
    : `<circle cx="85" cy="39" r="2.7" fill="#1E1611"/><circle cx="86" cy="38" r=".9" fill="#fff"/>`;
  const beak = pose === 'talk'
    ? `<path d="M93 38 L108 37 L93 43 Z" fill="#E8B53A"/><path d="M93 45 L106 50 L93 48 Z" fill="#E8B53A"/>`
    : `<path d="M93 40 L108 44 L93 48 Z" fill="#E8B53A"/>`;
  const wing = pose === 'wave'
    ? `<path d="M46 56 C48 34 64 20 80 24 C74 40 62 54 50 62 Z" fill="#3A281C" stroke="var(--ink)" stroke-width="1.2"/><ellipse cx="66" cy="34" rx="5" ry="2.6" fill="#F3EADB" transform="rotate(-35 66 34)"/>`
    : `<path d="M40 58 C52 46 70 48 76 60 C68 70 52 72 40 66 Z" fill="#3A281C" stroke="var(--ink)" stroke-width="1.2"/><ellipse cx="64" cy="63" rx="6" ry="2.8" fill="#F3EADB"/>`;
  const extra = pose === 'envelope'
    ? `<g transform="rotate(-8 110 46)"><rect x="100" y="40" width="20" height="13" rx="2" fill="#FFFDF8" stroke="var(--ink)" stroke-width="1.3"/><path d="M100 41 L110 48 L120 41" fill="none" stroke="#B4532A" stroke-width="1.3"/></g>`
    : pose === 'sleep' ? `<text x="98" y="22" style="fill:var(--ink3);font-family:var(--disp);font-size:15px">z</text><text x="107" y="11" style="fill:var(--ink3);font-family:var(--disp);font-size:11px">z</text>` : '';
  return `<svg class="maina ${cls}" width="${w}" height="${w*110/120}" viewBox="0 0 120 110" role="img" aria-label="Maina the mynah">
    <path d="M34 62 L8 74 L13 85 L38 72 Z" fill="#2A1D14" stroke="var(--ink)" stroke-width="1.2" stroke-linejoin="round"/>
    <path d="M52 85 L50 99 M64 85 L66 99" stroke="#E8B53A" stroke-width="3" stroke-linecap="round"/>
    <path d="M44 99 L56 99 M60 99 L72 99" stroke="#E8B53A" stroke-width="2.4" stroke-linecap="round"/>
    <ellipse cx="56" cy="64" rx="28" ry="21" fill="#6B4A33" stroke="var(--ink)" stroke-width="1.4"/>
    <path d="M42 76 C52 86 72 85 81 71" fill="none" stroke="#8C6448" stroke-width="3" stroke-linecap="round"/>
    ${wing}
    <circle cx="80" cy="40" r="15" fill="#1E1611" stroke="var(--ink)" stroke-width="1.2"/>
    <path d="M72 27 C76 22 82 22 86 26" fill="none" stroke="#1E1611" stroke-width="3" stroke-linecap="round"/>
    <ellipse cx="85" cy="40" rx="7" ry="6" fill="#E8B53A"/>
    ${eye}${beak}${extra}
  </svg>`;
}
const LN = (d, c = '', extra = '') => `<path class="ln ${c}" pathLength="1" d="${d}" ${extra}/>`;
function heroArt(){
  return `<svg class="ill" viewBox="0 0 560 460" width="100%" role="img" aria-label="A health worker plays the consent notice from her phone to a mother and child under a neem tree; a thread connects the phone to an SMS receipt on a basic phone.">
    <ellipse cx="300" cy="318" rx="210" ry="128" fill="var(--leaf-soft)" opacity=".75"/>
    <circle cx="455" cy="165" r="92" fill="var(--terra-soft)" opacity=".6"/>
    <g fill="none" stroke="var(--ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <!-- neem tree -->
      <path class="ln" pathLength="1" d="M60 200 C40 170 60 128 96 134 C102 100 150 86 176 110 C202 86 252 100 246 136 C282 142 286 186 256 202 C250 226 200 232 186 216 C160 236 112 236 100 216 C76 226 54 216 60 200 Z" fill="var(--leaf)" fill-opacity=".14"/>
      ${LN('M112 430 C120 360 106 300 128 240 C134 222 130 206 138 192')}
      ${LN('M142 430 C142 370 152 310 148 250 C147 228 154 212 162 198')}
      ${LN('M148 252 C172 240 200 234 226 228')}
      ${LN('M96 170 q10 -8 20 0 M150 140 q10 -8 20 0 M196 176 q10 -8 20 0 M126 196 q8 -6 16 0 M216 148 q8 -6 16 0','d1')}
      <!-- ground -->
      ${LN('M0 432 C80 420 140 442 220 430 S380 420 460 434 S540 442 560 430')}
      <!-- elder with stick -->
      ${LN('M52 298 C52 280 80 280 80 298 M50 300 L82 300','d1')}
      <circle class="ln d1" pathLength="1" cx="66" cy="312" r="13"/>
      ${LN('M54 328 C50 360 50 395 52 428 M78 328 C82 360 82 395 80 428 M78 340 L92 344 M92 336 L100 430','d1')}
      <!-- health worker -->
      <circle class="ln d2" pathLength="1" cx="332" cy="192" r="17"/>
      <circle class="ln d2" pathLength="1" cx="347" cy="184" r="7"/>
      ${LN('M316 188 C318 172 346 170 349 186','d2')}
      ${LN('M332 209 L332 216 M314 218 C306 252 300 302 296 362 L366 362 C362 302 356 252 350 218 C342 213 322 213 314 218 Z','d2')}
      ${LN('M316 224 C332 252 348 272 358 302','d2','stroke="var(--terra)"')}
      ${LN('M316 226 C302 242 288 252 272 258 M350 226 C356 262 358 282 354 302 M320 362 L318 424 M344 362 L346 424','d2')}
      <rect class="ln d2" pathLength="1" x="256" y="246" width="16" height="27" rx="3" transform="rotate(-14 264 259)"/>
      ${LN('M246 252 q-8 10 0 20 M237 245 q-14 17 0 34','d3','stroke="var(--terra)"')}
      <rect class="ln d2" pathLength="1" x="322" y="236" width="14" height="10" rx="2"/>
      <!-- mother and child -->
      <circle class="ln d2" pathLength="1" cx="200" cy="302" r="16"/>
      ${LN('M182 304 C180 280 220 276 222 302 C224 320 216 332 208 336','d2','stroke="var(--terra)"')}
      ${LN('M188 320 C176 342 170 372 172 394 C200 402 240 404 262 398 C260 382 250 362 232 352 C222 338 214 328 208 324','d2')}
      ${LN('M172 394 C200 410 250 414 282 406 M192 338 C202 358 222 368 242 372','d2')}
      <circle class="ln d3" pathLength="1" cx="238" cy="346" r="9"/>
      ${LN('M234 356 C238 370 252 378 264 380','d3')}
      <!-- slip with thumbprint -->
      <g transform="rotate(-8 300 416)"><rect class="ln d3" pathLength="1" x="272" y="398" width="64" height="36" rx="3" fill="var(--raised)"/><path d="M280 416 H328" stroke-dasharray="3 3"/></g>
      <g stroke="var(--terra)" stroke-width="1.4"><circle class="ln d3" pathLength="1" cx="318" cy="424" r="3"/><circle class="ln d3" pathLength="1" cx="318" cy="424" r="6"/></g>
      <!-- thread to basic phone -->
      ${LN('M262 252 C292 150 384 112 424 152 C448 176 468 206 474 238','d3','stroke="var(--terra)" stroke-dasharray="0"')}
      <rect class="ln d4" pathLength="1" x="454" y="240" width="40" height="76" rx="9" fill="var(--raised)"/>
      <rect class="ln d4" pathLength="1" x="461" y="248" width="26" height="18" rx="2"/>
      <g fill="var(--ink)" stroke="none">${[0,1,2].flatMap(r => [0,1,2].map(c => `<circle cx="${466+c*8}" cy="${276+r*9}" r="1.8"/>`)).join('')}</g>
    </g>
    <g class="pop">
      <rect x="400" y="150" width="138" height="54" rx="14" fill="var(--raised)" stroke="var(--ink)" stroke-width="1.6"/>
      <path d="M470 204 L478 216 L484 204" fill="var(--raised)" stroke="var(--ink)" stroke-width="1.6" stroke-linejoin="round"/>
      <text x="414" y="170" style="fill:var(--ink3);font-size:10.5px;letter-spacing:.06em">SMS RECEIPT</text>
      <text x="414" y="192" style="fill:var(--ink);font-family:var(--mono);font-size:17px;font-weight:500;letter-spacing:.08em">AN-7K2Q</text>
    </g>
  </svg>`;
}
function whyArt(){
  return `<svg class="ill" viewBox="0 0 520 190" width="100%" role="img" aria-label="A laptop full of cookie pop-ups cannot reach a basic keypad phone.">
    <g fill="none" stroke="var(--ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect class="ln" pathLength="1" x="30" y="30" width="170" height="110" rx="8" fill="var(--surface)"/>
      ${LN('M10 150 H220 L208 162 H22 Z')}
      <rect class="ln d1" pathLength="1" x="46" y="46" width="138" height="30" rx="4" fill="var(--terra-soft)"/>
      ${LN('M56 58 H130 M56 66 H110','d1')}
      <rect class="ln d1" pathLength="1" x="58" y="84" width="118" height="42" rx="4" fill="var(--raised)"/>
      ${LN('M68 98 H150 M68 108 H126','d2')}
      <rect class="ln d2" pathLength="1" x="126" y="112" width="42" height="10" rx="3" fill="var(--terra)" fill-opacity=".6"/>
      <path d="M232 96 C280 70 320 120 360 94" stroke="var(--terra)" stroke-dasharray="5 7"/>
      ${LN('M366 86 L378 98 M378 86 L366 98','d3','stroke="var(--danger)"')}
      <rect class="ln d3" pathLength="1" x="420" y="36" width="54" height="120" rx="12" fill="var(--raised)"/>
      <rect class="ln d3" pathLength="1" x="430" y="48" width="34" height="26" rx="3" fill="var(--leaf-soft)"/>
    </g>
    <g fill="var(--ink)">${[0,1,2,3].flatMap(r => [0,1,2].map(c => `<circle cx="${436+c*11}" cy="${92+r*14}" r="2.4"/>`)).join('')}</g>
  </svg>`;
}
function rungArt(i){
  const s = `fill="none" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
  const art = [
    `<rect x="26" y="6" width="26" height="46" rx="5" ${s}/><path d="M34 46 h10" ${s}/><path d="M60 22 q8 -8 16 0 M63 27 q5 -5 10 0" ${s} stroke="var(--leaf)"/>`,
    `<path d="M14 10 h20 l8 8 v32 h-28 z" ${s}/><rect x="20" y="26" width="16" height="14" rx="2" ${s}/><path d="M46 30 h14 m-5 -5 l5 5 -5 5" ${s} stroke="var(--terra)"/><rect x="62" y="22" width="16" height="12" rx="2" ${s}/><path d="M62 23 l8 6 8 -6" ${s}/>`,
    `<path d="M20 14 c-6 6 -6 22 6 34 s28 12 34 6 l-6 -8 -8 4 c-6 -3 -12 -9 -15 -15 l4 -8 z" ${s}/><path d="M54 12 l14 14 m0 -10 v10 h-10" ${s} stroke="var(--terra)"/>`,
    `<path d="M18 40 a12 12 0 0 1 4 -23 a16 16 0 0 1 30 2 a11 11 0 0 1 4 21 z" ${s}/><path d="M24 12 L60 48" ${s} stroke="var(--danger)"/>`,
    `<g ${s} stroke="var(--terra)"><ellipse cx="40" cy="30" rx="6" ry="8"/><ellipse cx="40" cy="30" rx="11" ry="14"/><ellipse cx="40" cy="30" rx="16" ry="20" stroke-dasharray="20 5"/></g>`
  ][i];
  return `<svg viewBox="0 0 86 56" width="86" height="56" aria-hidden="true">${art}</svg>`;
}
function stopArt(){
  const nodes = [['Field app',420,40],['Your MIS',450,112],['District Health Office',420,186],['Bank partner',360,250]];
  return `<svg class="ill stopart" data-io viewBox="0 0 520 290" width="100%" role="img" aria-label="Her withdrawal flows from Anumati to every connected system, each confirming with a tick.">
    <g fill="none" stroke="var(--ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle class="ln" pathLength="1" cx="70" cy="150" r="20"/>
      ${LN('M50 152 C48 128 92 124 92 152 C94 172 86 184 78 188','','stroke="var(--terra)"')}
      ${LN('M46 180 C36 210 34 250 36 280 M94 180 C104 210 106 250 104 280')}
      <rect class="ln d1" pathLength="1" x="96" y="76" width="118" height="44" rx="14" fill="var(--raised)"/>
      ${LN('M112 120 L104 134 L126 120','d1')}
    </g>
    <text x="112" y="104" class="hi" style="fill:var(--ink);font-size:17px;font-weight:600">बंद करें</text>
    <text x="172" y="104" style="fill:var(--ink3);font-size:11px">stop</text>
    <g fill="none" stroke-width="2">${nodes.map(([,x,y]) => `<path class="flow" d="M250 150 C${(250+x)/2} 150 ${(250+x)/2} ${y} ${x-10} ${y}" stroke="var(--terra)"/>`).join('')}
      <path class="flow" d="M112 152 C160 152 190 150 222 150" stroke="var(--terra)"/></g>
    <g transform="translate(222 122)">${mark(56)}</g>
    ${nodes.map(([l,x,y],i) => `<g><rect x="${x-10}" y="${y-16}" width="${l.length*6.6+44}" height="32" rx="16" fill="var(--surface)" stroke="var(--line)"/><circle class="chk" style="animation-delay:${.6+i*.35}s" cx="${x+6}" cy="${y}" r="9" fill="var(--leaf)"/><path class="chk" style="animation-delay:${.6+i*.35}s" d="M${x+2} ${y} l3 3 6 -6" stroke="#F4F8EF" stroke-width="2" fill="none" stroke-linecap="round"/><text x="${x+22}" y="${y+4}" style="fill:var(--ink);font-size:12.5px">${l}</text></g>`).join('')}
  </svg>`;
}
function wayArt(k){
  const s = `fill="none" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
  const a = {
    office: `<ellipse cx="120" cy="92" rx="100" ry="46" fill="var(--terra-soft)" opacity=".6"/><path d="M20 118 H220" ${s}/><circle cx="70" cy="58" r="11" ${s}/><path d="M52 104 c0 -22 8 -32 18 -32 s18 10 18 32" ${s}/><circle cx="170" cy="56" r="11" ${s}/><circle cx="180" cy="50" r="5" ${s}/><path d="M152 104 c0 -22 8 -34 18 -34 s18 12 18 34" ${s}/><path d="M100 118 l6 -26 h34 l-6 26" ${s} fill="var(--raised)"/><path d="M196 118 v-18 h14 v18 M200 100 c-4 -14 4 -20 6 -26 M206 100 c6 -10 10 -12 12 -20" ${s} stroke="var(--leaf)"/>`,
    tablet: `<ellipse cx="120" cy="80" rx="96" ry="52" fill="var(--leaf-soft)" opacity=".8"/><rect x="72" y="18" width="96" height="112" rx="10" ${s} fill="var(--raised)"/><path d="M86 38 H150 M86 52 H136 M86 66 H144" ${s}/><rect x="86" y="80" width="68" height="18" rx="4" fill="var(--terra-soft)" stroke="var(--terra)" stroke-width="1.6"/><text x="92" y="93" style="fill:var(--terra-deep);font-family:var(--mono);font-size:10px">AN-7K2Q</text><rect x="86" y="106" width="12" height="12" rx="2" ${s}/><path d="M88 112 l3 3 5 -6" ${s} stroke="var(--leaf)"/>`,
    code: `<ellipse cx="120" cy="84" rx="98" ry="48" fill="var(--indigo-soft)" opacity=".9"/><rect x="50" y="24" width="140" height="88" rx="8" ${s} fill="var(--raised)"/><path d="M34 120 H206 L196 130 H44 Z" ${s}/><text x="64" y="50" style="fill:var(--ink3);font-family:var(--mono);font-size:10px">consent.check()</text><text x="64" y="70" style="fill:var(--leaf);font-family:var(--mono);font-size:11px">{ allow: true }</text><path d="M64 88 H150 M64 98 H120" ${s} stroke="var(--line)"/>`
  }[k];
  return `<svg viewBox="0 0 240 140" width="100%" style="max-width:260px" aria-hidden="true">${a}</svg>`;
}
function quiltArt(withMaina = true){
  const s = `fill="none" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"`;
  const fills = ['var(--terra-soft)','var(--leaf-soft)','var(--turmeric-soft)','var(--indigo-soft)'];
  let cells = '';
  for (let r = 0; r < 3; r++) for (let c = 0; c < 4; c++) {
    const x = 40 + c*64, y = 40 + r*50;
    cells += `<rect x="${x}" y="${y}" width="64" height="50" fill="${fills[(r+c)%4]}" stroke="var(--ink)" stroke-width="1.4"/><path d="M${x+8} ${y+25} q14 -12 24 0 t24 0" fill="none" stroke="var(--terra)" stroke-width="1.3" stroke-dasharray="3 3"/>`;
  }
  return `<svg class="ill" viewBox="0 0 420 240" width="100%" role="img" aria-label="Many patches stitched into one quilt, with Maina pulling the thread.">${cells}
    <g ${s}>${LN('M296 60 C330 40 356 70 350 100 C344 130 372 150 392 130','','stroke="var(--terra)" stroke-width="2"')}${LN('M388 126 L406 108','d1')}</g>
    ${withMaina ? `<g transform="translate(330 150) scale(.55)">${maina('talk',120)}</g>` : ''}
  </svg>`;
}
function setupIO(){
  if (!('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting){ e.target.classList.remove('play'); void e.target.getBoundingClientRect(); e.target.classList.add('play'); io.unobserve(e.target); } }), { threshold: .35 });
  document.querySelectorAll('[data-io]').forEach(el => io.observe(el));
}

/* ---------- Maina's stitched story: travels down the page on a thread ---------- */
let ST = null, stRaf = 0;
function catmull(pts){
  if (pts.length < 2) return '';
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++){
    const p0 = pts[i-1] || pts[i], p1 = pts[i], p2 = pts[i+1], p3 = pts[i+2] || p2;
    const c1 = [p1[0] + (p2[0]-p0[0])/6, p1[1] + (p2[1]-p0[1])/6], c2 = [p2[0] - (p3[0]-p1[0])/6, p2[1] - (p3[1]-p1[1])/6];
    d += ` C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0]} ${p2[1]}`;
  }
  return d;
}
function storyInit(){
  window.removeEventListener('scroll', storyTick); window.removeEventListener('resize', storyBuild);
  const root = document.querySelector('.story');
  if (!root){ ST = null; return; }
  ST = { root, layer: root.querySelector('.story-layer'), svg: root.querySelector('.thread'), trav: root.querySelector('.traveler'), bird: root.querySelector('.bird'), bub: root.querySelector('.say-bubble'), pose: null, say: null, lastL: 0 };
  storyBuild();
  window.addEventListener('scroll', storyTick, { passive: true });
  window.addEventListener('resize', storyBuild);
  setTimeout(storyBuild, 800);
}
function storyBuild(){
  if (!ST || !document.body.contains(ST.root)) return;
  const W = ST.root.clientWidth, H = ST.root.scrollHeight;
  ST.mode = W >= 1260 ? 'path' : 'dock';
  ST.layer.classList.toggle('dock', ST.mode === 'dock');
  const secs = [...ST.root.querySelectorAll(':scope > [data-pose]')];
  ST.secs = secs.map(el => ({ top: el.offsetTop, h: el.offsetHeight, pose: el.dataset.pose, say: el.dataset.say }));
  if (ST.mode === 'path'){
    const gut = Math.max(0, (W - 1180) / 2), L = Math.max(34, gut * 0.5), R = W - Math.max(34, gut * 0.5);
    const pts = [[R, 30]];
    ST.secs.forEach((s, i) => { const x = i % 2 ? L : R; pts.push([x, s.top + Math.min(70, s.h * 0.2)]); if (s.h > 220) pts.push([x, s.top + s.h - Math.min(70, s.h * 0.2)]); });
    pts.push([W / 2, H - 20]);
    const d = catmull(pts);
    ST.svg.setAttribute('width', W); ST.svg.setAttribute('height', H); ST.svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    ST.svg.innerHTML = `<defs><mask id="sewmask" maskUnits="userSpaceOnUse" x="0" y="0" width="${W}" height="${H}"><path id="sewreveal" d="${d}" fill="none" stroke="#fff" stroke-width="10"/></mask></defs><path class="thread-ghost" d="${d}"/><path class="thread-sewn" d="${d}" mask="url(#sewmask)"/>`;
    ST.path = ST.svg.querySelector('.thread-ghost'); ST.len = ST.path.getTotalLength(); ST.reveal = ST.svg.querySelector('#sewreveal');
    ST.reveal.style.strokeDasharray = `${ST.len} ${ST.len}`;
  } else { ST.svg.innerHTML = ''; ST.path = null; ST.trav.style.transform = ''; }
  storyUpdate();
}
function storyTick(){ if (stRaf) return; stRaf = requestAnimationFrame(() => { stRaf = 0; storyUpdate(); }); }
function storyUpdate(){
  if (!ST || !document.body.contains(ST.root)) return;
  const rootTop = ST.root.getBoundingClientRect().top + window.scrollY;
  const target = window.scrollY + window.innerHeight * 0.56 - rootTop;
  let cur = ST.secs[0];
  ST.secs.forEach(s => { if (target >= s.top - 60) cur = s; });
  if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) cur = ST.secs[ST.secs.length - 1];
  if (cur && cur.pose !== ST.pose + '|' && (cur.pose !== ST.pose || cur.say !== ST.say)){
    ST.pose = cur.pose; ST.say = cur.say;
    ST.bird.innerHTML = maina(cur.pose, ST.mode === 'path' ? 68 : 58);
    ST.bub.textContent = cur.say || '';
    ST.bub.classList.remove('show'); void ST.bub.offsetWidth; ST.bub.classList.add('show');
    clearTimeout(ST.hideT); ST.hideT = setTimeout(() => ST && ST.bub.classList.remove('show'), 4200);
  }
  if (ST.mode !== 'path' || !ST.path) return;
  let lo = 0, hi = ST.len;
  for (let i = 0; i < 22; i++){ const mid = (lo + hi) / 2; if (ST.path.getPointAtLength(mid).y < target) lo = mid; else hi = mid; }
  const l = Math.max(0, Math.min(ST.len, lo));
  const pt = ST.path.getPointAtLength(l), ahead = ST.path.getPointAtLength(Math.min(ST.len, l + 30));
  const W = ST.root.clientWidth;
  ST.trav.style.transform = `translate(${(Math.min(Math.max(pt.x, 40), W - 40) - 34).toFixed(1)}px, ${(pt.y - 58).toFixed(1)}px)`;
  ST.trav.classList.toggle('left', pt.x < W / 2);
  ST.bird.classList.toggle('flip', ahead.x < pt.x - 2);
  ST.reveal.style.strokeDashoffset = (ST.len - l).toFixed(1);
}
/* ================= WEBSITE ================= */
const SITE_PAGES = [['home','Home'],['how','How it works'],['ngos','For NGOs'],['open','Open source'],['pricing','Pricing'],['demo','Talk to us']];

/* small line icons, 64×48, shared stroke */
function icon64(n){
  const s = 'fill="none" stroke="var(--ink)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"';
  const t = 'fill="none" stroke="var(--terra)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"';
  const g = 'fill="none" stroke="var(--leaf)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"';
  const txt = (x,y,v,c='var(--ink)',sz=13) => `<text x="${x}" y="${y}" style="fill:${c};font-family:Hind,sans-serif;font-size:${sz}px;font-weight:600">${v}</text>`;
  const M = {
    lang: `<path d="M8 8h26v18H18l-6 6v-6H8z" ${s}/>${txt(16,22,'अ','var(--terra)',14)}<path d="M30 20h26v18h-4v6l-6-6H30z" ${s}/>${txt(38,34,'A')}`,
    notice: `<path d="M34 6h16l6 6v30H34z" ${s}/><path d="M39 18h12M39 25h12M39 32h8" ${s}/><path d="M8 20h6l8-7v22l-8-7H8z" ${s}/><path d="M26 18q4 6 0 12" ${t}/>`,
    choices: `<rect x="8" y="8" width="30" height="14" rx="7" ${s}/><circle cx="31" cy="15" r="4.5" fill="var(--leaf)"/><rect x="8" y="28" width="30" height="14" rx="7" ${s}/><circle cx="15" cy="35" r="4.5" ${s}/><path d="M46 15h10M46 35h10" ${s}/>`,
    evidence: `<g ${t}><ellipse cx="32" cy="24" rx="5" ry="7"/><ellipse cx="32" cy="24" rx="10" ry="13"/><ellipse cx="32" cy="24" rx="15" ry="19" stroke-dasharray="22 5"/></g>`,
    verify: `<path d="M10 40v-6M18 40v-12M26 40v-18M34 40v-24" ${s}/><circle cx="48" cy="18" r="9" ${g}/><path d="M44 18l3 3 6-6" ${g}/>`,
    receipt: `<path d="M16 4h32v40H16z" ${s}/><path d="M16 30h32" ${s} stroke-dasharray="3 3"/><text x="20" y="20" style="fill:var(--terra);font-family:var(--mono);font-size:8.5px">AN-7K2Q</text><path d="M22 37h10" ${s}/>`,
    featurephone: `<rect x="22" y="4" width="20" height="40" rx="5" ${s}/><rect x="26" y="9" width="12" height="9" rx="1.5" ${s}/><g fill="var(--ink)">${[0,1,2].flatMap(r=>[0,1,2].map(c=>`<circle cx="${28+c*4}" cy="${25+r*5}" r="1.2"/>`)).join('')}</g><path d="M48 12l6 6m0-6l-6 6" ${t}/>`,
    sharedphone: `<circle cx="14" cy="14" r="6" ${s}/><path d="M4 40c0-10 4-16 10-16s10 6 10 16" ${s}/><circle cx="50" cy="14" r="6" ${s}/><path d="M40 40c0-10 4-16 10-16s10 6 10 16" ${s}/><rect x="27" y="18" width="10" height="18" rx="2" ${t}/>`,
    nophone: `<path d="M12 8h28v34H12z" ${s}/><path d="M18 16h16M18 22h10" ${s}/><g ${t}><ellipse cx="46" cy="32" rx="4" ry="5.5"/><ellipse cx="46" cy="32" rx="8" ry="10"/></g>`,
    cantread: `<path d="M8 10h22v28H8z" ${s}/><path d="M13 18h12M13 24h12M13 30h8" ${s} stroke-dasharray="2 3"/><path d="M36 20h5l7-6v20l-7-6h-5z" ${s}/><path d="M52 18q4 6 0 12M56 14q7 10 0 20" ${t}/>`,
    child: `<circle cx="22" cy="12" r="6" ${s}/><path d="M12 44c0-14 4-22 10-22s10 8 10 22" ${s}/><circle cx="44" cy="22" r="4.5" ${s}/><path d="M37 44c0-9 3-14 7-14s7 5 7 14" ${s}/><path d="M30 30l8 2" ${t}/>`,
    guardian: `<circle cx="20" cy="12" r="6" ${s}/><path d="M10 44c0-14 4-22 10-22s10 8 10 22" ${s}/><path d="M44 8l12 4v9c0 8-5 12-12 15-7-3-12-7-12-15v-9z" ${t}/><path d="M39 22l4 4 7-7" ${g}/>`,
    existing: `<path d="M6 14h18l4 5h30v24H6z" ${s}/><circle cx="42" cy="31" r="8" ${t}/><path d="M42 26v5l3 2" ${t}/>`,
    received: `<path d="M8 26l8-16h32l8 16v14H8z" ${s}/><path d="M8 26h14l3 5h14l3-5h14" ${s}/><path d="M32 4v14m-5-5l5 5 5-5" ${t}/>`,
    matched: `<circle cx="26" cy="22" r="13" ${s}/><path d="M36 32l12 12" ${s}/><circle cx="26" cy="18" r="4" ${t}/><path d="M18 30c1-5 4-7 8-7s7 2 8 7" ${t}/>`,
    enforced: `<path d="M32 4l18 6v12c0 12-8 18-18 22-10-4-18-10-18-22V10z" ${s}/><path d="M24 24l6 6 11-11" ${g}/>`,
    propagated: `<circle cx="12" cy="24" r="6" ${t}/><path d="M18 24h10M28 24c6 0 8-14 16-14M28 24c6 0 8 14 16 14M28 24h16" ${t} stroke-dasharray="3 3"/><circle cx="50" cy="10" r="5" ${g}/><circle cx="50" cy="24" r="5" ${g}/><circle cx="50" cy="38" r="5" ${g}/>`,
    server: `<rect x="14" y="6" width="36" height="10" rx="2" ${s}/><rect x="14" y="19" width="36" height="10" rx="2" ${s}/><rect x="14" y="32" width="36" height="10" rx="2" ${s}/><circle cx="20" cy="11" r="1.5" fill="var(--leaf)"/><circle cx="20" cy="24" r="1.5" fill="var(--leaf)"/><circle cx="20" cy="37" r="1.5" fill="var(--terra)"/>`,
    phone: `<rect x="20" y="4" width="24" height="40" rx="5" ${s}/><path d="M28 38h8" ${s}/><path d="M26 14h12M26 20h8" ${t}/><path d="M48 16a8 8 0 010 12" ${g}/>`,
    plug: `<path d="M24 6v10M40 6v10M18 16h28v8c0 8-6 13-14 13s-14-5-14-13z" ${s}/><path d="M32 37v7" ${s}/><path d="M50 30c6 0 8 6 8 12" ${t}/>`,
    code: `<path d="M20 14l-10 10 10 10M44 14l10 10-10 10" ${s}/><path d="M36 8l-8 32" ${t}/>`,
    table: `<rect x="8" y="8" width="48" height="32" rx="3" ${s}/><path d="M8 18h48M24 8v32M40 8v32" ${s}/><path d="M12 13h8" ${t}/>`,
    export: `<path d="M10 20v22h34V20" ${s}/><path d="M27 30V4m-8 8l8-8 8 8" ${t}/>`,
    unlock: `<rect x="14" y="22" width="30" height="22" rx="3" ${s}/><path d="M20 22v-7a9 9 0 0118 0" ${t}/><circle cx="29" cy="33" r="3" ${s}/>`,
    house: `<path d="M8 24L32 6l24 18M14 20v22h36V20" ${s}/><rect x="24" y="28" width="16" height="14" rx="1" ${t}/>`,
    onephone: `<rect x="24" y="6" width="16" height="34" rx="4" ${s}/><path d="M29 35h6" ${s}/><path d="M8 42h48" ${t} stroke-dasharray="3 3"/>`,
    many: `<rect x="6" y="12" width="14" height="26" rx="3" ${s}/><rect x="25" y="8" width="14" height="30" rx="3" ${s}/><rect x="44" y="12" width="14" height="26" rx="3" ${s}/><path d="M6 44h52" ${t} stroke-dasharray="3 3"/>`,
    building: `<path d="M14 44V8h24v36M38 18h14v26M8 44h50" ${s}/><path d="M20 14h4M28 14h4M20 22h4M28 22h4M20 30h4M28 30h4M43 26h4M43 34h4" ${t}/>`
  };
  return `<svg class="ic64" viewBox="0 0 64 48" width="64" height="48" aria-hidden="true">${M[n]||''}</svg>`;
}

function renderSite(){
  const pg = { home: siteHome, how: siteHow, ngos: siteNgos, open: siteOpen, pricing: sitePricing, demo: siteDemo }[S.site.page]();
  return `<div class="site">
    <nav class="site-nav" aria-label="Website">
      ${wordmark(34)}
      <div class="links">${SITE_PAGES.map(([k,l]) => `<button class="${S.site.page===k?'on':''}" data-a="site" data-p="${k}">${l}</button>`).join('')}</div>
      <span class="spacer"></span>
      <div class="row navcta" style="gap:8px"><button class="btn sm" data-a="lens" data-k="guide">Product guide</button>${SITE.consoleUrl ? `<button class="btn sm pri" data-a="lens" data-k="con">Sign in</button>` : ''}</div>
    </nav>
    <hr class="stitch">
    <div class="story">
      <div class="story-layer" aria-hidden="true"><svg class="thread"></svg><div class="traveler"><div class="say-bubble"></div><div class="bird"></div></div></div>
      ${pg}
      <footer class="foot" data-pose="wave" data-say="That’s the whole thread. The product guide shows every screen."><div class="wrap row wr" style="gap:28px;align-items:flex-start">
        <div class="stack" style="gap:8px;max-width:320px">${wordmark(38)}<div class="small muted">Open-source DPDP consent for the social sector. Built by Dhwani RIS on Frappe. Server AGPL-3.0, field app MIT.</div></div>
        <div class="stack small" style="gap:6px"><strong>Product</strong><button class="btn ghost sm fl" data-a="site" data-p="how">How it works</button><button class="btn ghost sm fl" data-a="site" data-p="pricing">Pricing</button><button class="btn ghost sm fl" data-a="lens" data-k="api">API reference</button></div>
        <div class="stack small" style="gap:6px"><strong>Learn more</strong><button class="btn ghost sm fl" data-a="lens" data-k="guide">Product guide</button><button class="btn ghost sm fl" data-a="lens" data-k="qa">Test cases</button><button class="btn ghost sm fl" data-a="lens" data-k="code">Code on GitHub</button><button class="btn ghost sm fl" data-a="lens" data-k="proto">Design prototype</button></div>
        <div class="small muted" style="margin-left:auto;max-width:280px">Phase 1 is built and ready for a pilot. Features marked “coming” are planned for Phases 2 and 3. The design prototype also shows planned screens. Names and numbers on this site are illustrative.</div>
      </div></footer>
    </div>
  </div>`;
}
function heroReceipt(){
  return `<div class="stitch-box" style="background:var(--surface);border-radius:20px;padding:28px;box-shadow:var(--shadow);max-width:420px;justify-self:center;width:100%">
    <div class="row" style="justify-content:space-between"><span class="eyebrow">Consent receipt</span><span class="chip c-ok">Confirmed</span></div>
    <div class="mono" style="font-size:34px;letter-spacing:.08em;margin:10px 0 4px;font-weight:500">AN-7K2Q9C</div>
    <div class="hi" style="font-size:17px">सुनीता डी. · स्वास्थ्य जाँच</div>
    <div class="stack small" style="gap:8px;margin-top:16px">
      ${[['leaf','Captured offline · Khairi village · 11:20'],['leaf','Notice played in Hindi · 1:42'],['leaf','Voice “haan” + witness (ASHA)'],['leaf','SMS code read back from her phone'],['terra','Signed and chained on sync']].map(([c,t]) => `<div class="row"><span class="dot" style="background:var(--${c})"></span>${t}</div>`).join('')}
    </div>
    <hr class="stitch" style="margin:18px 0 12px">
    <div class="small muted">To withdraw: tell any worker · show this slip · SMS STOP AN-7K2Q9C</div>
  </div>`;
}
const secHead = (eyebrow, title, lede) => `<span class="eyebrow">${eyebrow}</span><h2 style="max-width:19em">${title}</h2>${lede?`<p class="lede" style="margin:0">${lede}</p>`:''}`;

function siteHome(){
  const rungs = [['Online','Anumati’s server texts her a code; she reads it back',4,0],['Signal, no data','Code from the worker’s own phone, plus her voice “haan”',3,1],['No signal','Evidence now, confirmed later by SMS',1,3],['No phone','Her voice “haan” or thumbprint, and a witness if it was read to her',0,4],['Child or guardian','Code to the parent’s or guardian’s phone, or a photo of their ID',2,2]];
  const chans = [['Tell a field worker',1],['Paper slip or letter',1],['SMS STOP',1],['Missed call',1],['Staff in the console',1],['WhatsApp',0],['IVR helpline',0],['Web preference centre',0],['Email',0],['Through a partner system',0]];
  const gaps = [
    ['A smartphone with data','Many people share a basic phone, or have none.','featurephone'],
    ['She can read the notice','Many need it read or played aloud, in their own language.','cantread'],
    ['Consent is a checkbox','In the field it is a conversation, often with a witness.','evidence'],
    ['Withdrawal happens on a website','People say stop to a worker, by SMS, or on paper.','received'],
    ['Price per consent','Programmes grow with people served, not with income.','many']
  ];
  return `
  <section class="pattern" data-pose="envelope" data-say="Namaste! I’m Maina. I carry consent receipts. Follow me down the page."><div class="wrap hero">
    <div class="stack" style="gap:22px">
      <span class="eyebrow">Open-source consent for India’s DPDP Act</span>
      <h1>Consent that works where the <em>internet doesn’t.</em></h1>
      <p class="lede">Anumati lets nonprofits take, prove and honour consent in the field: offline, in the person’s own language, for people who can’t read the notice, share a phone, or don’t own one.</p>
      <div class="row wr"><button class="btn pri" data-a="site" data-p="demo">Plan a pilot</button><button class="btn" data-a="lens" data-k="guide">See every screen ${ic('arrow',16)}</button></div>
      <div class="row wr small muted" style="gap:18px"><span class="chip c-ok">Phase 1 built · pilot next</span><span>Android field app</span><span>·</span><span>Hindi and English</span><span>·</span><span>Built on Frappe</span></div>
    </div>
    <div style="width:100%;max-width:620px;justify-self:center">${heroArt()}</div>
  </div></section>

  <section class="section" data-pose="talk" data-say="Most consent tools expect a browser. The people you serve often don’t have one."><div class="wrap stack" style="gap:24px">
    ${secHead('Why we built it','Most consent tools were designed for websites. The field works differently.')}
    <div class="grid g2" style="gap:32px;align-items:center">
      <div class="gapgrid">
        <div class="gaprow head"><span class="eyebrow">Web tools assume</span><span class="eyebrow">In the field</span></div>
        ${gaps.map(([a,b,i]) => `<div class="gaprow"><span class="assume">${a}</span><span class="reality">${icon64(i)}<span>${b}</span></span></div>`).join('')}
      </div>
      <div>${whyArt()}</div>
    </div>
  </div></section>

  <section class="section" style="background:var(--surface)" data-pose="sleep" data-say="No signal? I wait on the phone and deliver the receipt when it comes back."><div class="wrap stack" style="gap:24px">
    ${secHead('The verification ladder','Proof that fits the signal you have.','Each programme picks the methods it allows and how SMS codes are sent. The field app checks for internet by itself, picks the right route and records which proof was used.')}
    <div class="ladder" data-io>${rungs.map(([t,d,n,ai]) => `<div class="rung"><div class="wayimg" style="justify-content:flex-start">${rungArt(ai)}</div><div class="sig">${[1,2,3,4].map(i => `<i class="${i<=n?'on':''}" style="height:${i*4+2}px"></i>`).join('')}</div><strong>${t}</strong><span class="small muted">${d}</span></div>`).join('')}</div>
  </div></section>

  <section class="section" data-pose="envelope" data-say="She said stop. I carry it to the inbox and the ledger."><div class="wrap grid g2" style="gap:40px;align-items:start">
    <div class="stack" style="gap:16px">
      ${secHead('Withdrawal, the way people actually ask','Saying stop must be as easy as saying yes.','Every route lands in one inbox with a due date, is matched to the right person even on a shared phone, and is signed into the ledger. Connected systems see the change at once when they check consent.')}
      <button class="btn" data-a="site" data-p="how" style="align-self:flex-start">What happens after she says stop ${ic('arrow',16)}</button>
    </div>
    <div class="grid g2" style="gap:10px">${chans.map(([c,on]) => `<div class="card row" style="padding:12px 14px;gap:10px${on?'':';opacity:.72'}"><span class="dot" style="background:var(--${on?'terra':'line'})"></span>${c}${on?'':' <span class="chip c-neu" style="margin-left:auto">coming</span>'}</div>`).join('')}</div>
  </div><div class="wrap" style="margin-top:28px"><div style="max-width:720px;margin:0 auto">${stopArt()}</div></div></section>

  <section class="section" style="background:var(--surface)" data-pose="perch" data-say="Three ways in. Start wherever your systems already are."><div class="wrap stack" style="gap:24px">
    ${secHead('Three ways to use it','Start where your systems are.')}
    <div class="grid g3">
      <div class="card stack"><div class="wayimg">${wayArt('office')}</div><span class="chip c-terra" style="align-self:flex-start">No IT team · ready now</span><h3 style="font-size:22px">Full stack</h3><p class="muted" style="margin:0">Web console plus the Anumati Collect Android app. Set up a programme and notice, sign in your field team, and start the same week.</p></div>
      <div class="card stack"><div class="wayimg">${wayArt('tablet')}</div><span class="chip c-neu" style="align-self:flex-start">Coming · ODK first, then CommCare</span><h3 style="font-size:22px">Connectors</h3><p class="muted" style="margin:0">Open Anumati’s consent screens from inside your ODK or Kobo form; the survey goes ahead only with consent. ODK is next, CommCare follows.</p></div>
      <div class="card stack"><div class="wayimg">${wayArt('code')}</div><span class="chip c-ind" style="align-self:flex-start">Own developers · ready now</span><h3 style="font-size:22px">API</h3><p class="muted" style="margin:0">REST API with an OpenAPI spec: add people, record and withdraw consent, and check consent in milliseconds before you use data. An event feed tells your systems what changed.</p></div>
    </div>
  </div></section>

  <section class="section" data-pose="talk" data-say="Every organisation adds a patch. Together it’s one quilt."><div class="wrap grid g2" style="gap:40px;align-items:center">
    <div>${quiltArt(false)}</div>
    <div class="stack" style="gap:18px"><p class="quote" style="margin:0">Built as a digital public good: open code, open data model, hostable by anyone, with Dhwani offering hosting and support for those who want it.</p>
      <div class="row wr"><button class="btn pri" data-a="site" data-p="open">Read the open-source plan</button><button class="btn" data-a="site" data-p="pricing">See pricing</button></div></div>
  </div></section>`;
}

function siteHow(){
  const steps = [
    ['lang','Who and which language','Is she consenting for herself, or is a parent or guardian? Hindi or English today; more languages as reviewed translations are added.'],
    ['notice','Hear the notice','Text and a reviewed natural-voice recording. The choices stay locked until the notice has played through, or the worker confirms she read it all aloud.'],
    ['choices','Choose purposes','Every optional use starts off. “Yes to all” and “No to all” carry equal weight. Uses not allowed for children are never offered for a child.'],
    ['evidence','Record evidence','Voice “haan”, a photo of her thumbprint or signature, and a witness when the notice was read to her. Parents and guardians give their own details.'],
    ['verify','Verify','An SMS code from Anumati’s server, or from the worker’s phone with a voice “haan”; confirm later by SMS; or evidence only.'],
    ['receipt','Give a receipt','A code she keeps on a paper slip, with the ways to withdraw. An SMS receipt follows where SMS is set up.']
  ];
  const after = [['received','Received','Told to a worker, a paper slip or letter, SMS STOP or a missed call. A 30-day due date starts now.'],['matched','Matched','By receipt code or phone. When several people share a number, staff pick the right person.'],['enforced','Enforced','A new signed event. The consent check returns “no” from now on, and the field phone updates at once.'],['propagated','Tracked','Staff are reminded 3 days before the due date; overdue requests show in red. Telling partners automatically is coming in Phase 2.']];
  return `
  <section class="section pattern" data-pose="envelope" data-say="Six steps in the field, one receipt at the end. Let’s walk them."><div class="wrap grid g2" style="gap:40px;align-items:center">
    <div class="stack" style="gap:18px">${secHead('How it works','Six steps in the field. One signed record on the server.','The flow runs in the Anumati Collect Android app, offline. Other systems record and check consent through the API.')}<button class="btn" data-a="lens" data-k="guide" style="align-self:flex-start">See the app’s screens, journey by journey ${ic('arrow',16)}</button></div>
    ${heroReceipt()}
  </div></section>

  <section class="section" data-pose="talk" data-say="Each step leaves evidence. Nothing is pre-ticked."><div class="wrap stack" style="gap:24px">
    ${secHead('In the field','What the field worker and the beneficiary do together')}
    <ol class="steps">${steps.map(([ico,t,d],i) => `<li class="card step"><div class="row" style="justify-content:space-between;align-items:flex-start">${icon64(ico)}<span class="mono muted small">${String(i+1).padStart(2,'0')}</span></div><h3 style="font-size:21px">${t}</h3><p class="muted" style="margin:0">${d}</p></li>`).join('')}</ol>
  </div></section>

  <section class="section" style="background:var(--surface)" data-pose="envelope" data-say="When she says stop, I make sure everyone hears it."><div class="wrap stack" style="gap:24px">
    ${secHead('After she says stop','A withdrawal lands in one inbox, with proof.')}
    <ol class="flowline">${after.map(([ico,t,d]) => `<li><div class="flowdot">${icon64(ico)}</div><strong>${t}</strong><span class="small muted">${d}</span></li>`).join('')}</ol>
    <div style="max-width:720px;margin:8px auto 0;width:100%">${stopArt()}</div>
  </div></section>

  <section class="section" data-pose="perch" data-say="For your tech team: here’s what sits underneath."><div class="wrap grid g3" style="gap:16px">
    ${[['server','A ledger you can prove','Frappe app on MariaDB. Consent events are append-only, signed with Ed25519 and hash-chained; the chain is checked every night. Names, phones and evidence are encrypted.'],['phone','A field app that waits','Flutter on Dhwani’s frappe_mobile_sdk: offline outbox, sync that never duplicates, encrypted storage, PIN lock and remote wipe of a lost phone.'],['plug','Open doors','REST API with an OpenAPI spec, an event feed, and public signature checks anyone can run. Connectors for ODK and CommCare are next.']].map(([i,t,d]) => `<div class="card stack" style="gap:8px">${icon64(i)}<h3 style="font-size:20px">${t}</h3><p class="muted small" style="margin:0">${d}</p></div>`).join('')}
    <div class="row wr" style="grid-column:1/-1"><button class="btn sm" data-a="lens" data-k="api">API reference</button><button class="btn sm" data-a="lens" data-k="code">Code on GitHub</button></div>
  </div></section>`;
}

function siteNgos(){
  const segs = [
    ['featurephone','Basic phones, no data','OTP links and web pages never load.','A plain SMS code she reads back. Withdraw by SMS STOP or a missed call once your number is set up.'],
    ['sharedphone','A shared household phone','The phone number gets treated as the person.','Each person has their own record. When a STOP comes from a shared number, staff pick the right person.'],
    ['nophone','No phone at all','No way to prove consent or to withdraw.','Voice “haan” or a thumbprint photo, a witness, and a receipt code on a paper slip she can bring back.'],
    ['cantread','Can’t read the notice','A tick box is not informed consent.','The notice is played aloud and must finish before choices unlock; a witness confirms it was read fairly.'],
    ['child','Children in your programmes','No verifiable step for the parent.','The parent gets the SMS code, or shows ID. Uses not allowed for children are never offered; turning 18 is flagged.'],
    ['guardian','People with a lawful guardian','Rarely supported at all.','Guardian appointed by a court or Local Level Committee, with the order number required. No order yet: nothing is saved.'],
    ['existing','People you already hold data on','Consent was never recorded.','Coming in Phase 2: catch-up and re-consent campaigns. Today, a field worker can add a new use on the next visit.']
  ];
  return `
  <section class="section pattern" data-pose="talk" data-say="Tell me who you work with. I’ll show you how each of them can say yes, or no."><div class="wrap stack" style="gap:24px">
    ${secHead('For nonprofits','Designed for the people you actually serve.','Pick the situations that sound like your programmes. Each one changes how consent is taken and proved.')}
    <div class="grid g3 segs">${segs.map(([i,t,p,a]) => `<div class="card stack seg-card" style="gap:10px">${icon64(i)}<h3 style="font-size:20px">${t}</h3><div class="small"><span class="muted">Usually goes wrong: </span>${p}</div><div class="small fix">${ic('check',16)}<span>${a}</span></div></div>`).join('')}</div>
  </div></section>

  <section class="section" style="background:var(--surface)" data-pose="envelope" data-say="Week one: set up, translate, and take your first fifty consents."><div class="wrap grid g2" style="gap:24px;align-items:start">
    <div class="card stack"><h3 style="font-size:22px">Your first week</h3>
      ${['Organisation and DPO set up','First programme and purposes','Notice in your languages, reviewed','SMS sender ID and DLT templates','Field team logged in to Anumati Collect','Pilot with 50 real consents'].map((t,i) => `<label class="check"><input type="checkbox" ${i<3?'checked':''} id="wk${i}"> ${t}</label>`).join('')}
    </div>
    <div class="card stack"><div class="wayimg" style="justify-content:flex-start">${icon64('unlock')}</div><h3 style="font-size:22px">What stays yours</h3><p class="muted" style="margin:0">Your data sits in your own Frappe site, hosted in India or on your own server. You can export everything, run the same code yourself, and leave any time. Dhwani acts as your processor under a data processing agreement.</p><button class="btn pri" data-a="site" data-p="demo" style="align-self:flex-start">Plan a pilot</button></div>
  </div></section>`;
}

function siteOpen(){
  const repos = [['server','anumati','Server · AGPL-3.0','Frappe app: notices, consent ledger, requests inbox, SMS, records of processing, audit.'],['phone','anumati_collect','Field app · MIT','Anumati Collect for Android, on Dhwani’s offline-first frappe_mobile_sdk.'],['plug','anumati_connectors','Connectors · coming','ODK first, then CommCare and a web widget.']];
  const principles = [['code','Open code','Every line on a public repository, under licences that keep it open.'],['table','Open data model','Consent records follow a documented schema anyone can read or export.'],['export','Portable','Export all records with their signatures and verify them without us.'],['unlock','No lock-in','Self-host the same code, or move between hosted and self-hosted any time.']];
  const road = [['Done','Foundations','Signed, hash-chained ledger; roles; tenancy and tamper tests'],['Built','Core capture','Field app, guardians, SMS codes, receipts, withdrawal inbox, console, API. Pilot next'],['Next','Rights and channels','ODK connector, WhatsApp, IVR, self-service page, erasure, retention, campaigns'],['Later','Scale and trust','Security test, 22-language pack, CommCare, evidence certificate, breach notices']];
  return `
  <section class="section pattern" data-pose="talk" data-say="Everything here is open. Pull a thread, add a patch."><div class="wrap grid g2" style="gap:40px;align-items:center">
    <div class="stack" style="gap:18px">${secHead('Open source','Free to run, free to fork, built to be a public good.','Anumati is a server and a field app today, with connectors to follow. Use them together, or take only the parts you need.')}</div>
    <div>${quiltArt(false)}</div>
  </div></section>

  <section class="section" data-pose="perch" data-say="Every line is on GitHub."><div class="wrap stack" style="gap:24px">
    <div class="grid g3">${repos.map(([i,n,l,d]) => `<div class="card stack" style="gap:8px">${icon64(i)}<span class="mono muted">${n}</span><strong>${l}</strong><span class="small muted">${d}</span></div>`).join('')}</div>
    <div class="grid g4">${principles.map(([i,t,d]) => `<div class="stack" style="gap:6px">${icon64(i)}<strong>${t}</strong><span class="small muted">${d}</span></div>`).join('')}</div>
    <div class="small muted">Anumati reuses ideas from the open-source TSI DPDP CMS (Apache 2.0) with attribution, including its records of processing, breach and purge lifecycle.</div>
  </div></section>

  <section class="section" style="background:var(--surface)" data-pose="envelope" data-say="Here’s where the thread goes next."><div class="wrap stack" style="gap:24px">
    ${secHead('Roadmap','Stitched in four passes.')}
    <ol class="flowline">${road.map(([w,t,d],i) => `<li><div class="flowdot"><span class="chip ${i<2?'c-ok':i===2?'c-wait':'c-neu'}">${w}</span></div><strong>${t}</strong><span class="small muted">${d}</span></li>`).join('')}</ol>
  </div></section>

  <section class="section" data-pose="wave" data-say="That’s me in the brand sheet. Say hello!"><div class="wrap stack" style="gap:20px">
    ${secHead('Brand','The mark, the name and the bird.')}
    <div class="card grid g3" style="align-items:center;gap:24px">
      <div class="stack" style="align-items:center;gap:10px">${mark(96)}<span class="small muted" style="text-align:center">अ drawn over fingerprint ridges: consent from people who sign with a thumb.</span></div>
      <div class="stack" style="align-items:center;gap:10px">${wordmark(56)}<span class="small muted">Wordmark in Fraunces, with अनुमति in Hind</span></div>
      <div class="stack" style="align-items:center;gap:6px"><div class="row">${maina('perch',64)}${maina('envelope',64)}${maina('sleep',64)}</div><span class="small muted">Maina the mynah: perch, carry, wait</span></div>
    </div>
  </div></section>`;
}

function sitePricing(){
  const plans = [['house','Self-host','Free','Run it on your own server. Community support.',['All features','Frappe bench install','GitHub issues']],
    ['onephone','Hosted Starter','[₹ — / year]','One programme, pooled SMS.',['Hosted in India','Up to 3 field devices','Email support']],
    ['many','Hosted Programme','[₹ — / year]','Several programmes and your own SMS account.',['Unlimited consents','API access','Onboarding + DLT setup']],
    ['building','Dedicated','[₹ — / year]','Your own instance with an SLA.',['Dedicated tenant','99.5% uptime','Named support']]];
  return `
  <section class="section pattern" data-pose="talk" data-say="No meter running per consent. Promise."><div class="wrap stack" style="gap:24px">
    ${secHead('Pricing','Priced per organisation, never per consent.','Amounts are placeholders until Dhwani confirms them.')}
    <div class="grid g4">${plans.map(([ico,n,a,d,f],i) => `
      <div class="card price ${i===2?'stitch-box':''}" style="${i===2?'background:var(--raised)':''}">
        ${icon64(ico)}<strong>${n}</strong><div class="amt">${a}</div><span class="small muted">${d}</span>
        <div class="stack small" style="gap:6px">${f.map(x => `<div class="row" style="gap:8px">${ic('check',16)}${x}</div>`).join('')}</div>
        <button class="btn ${i===2?'pri':''}" ${i===0?'data-a="lens" data-k="code"':'data-a="site" data-p="demo"'}>${i===0?'See the code':'Talk to us'}</button>
      </div>`).join('')}</div>
  </div></section>
  <section class="section" style="background:var(--surface)" data-pose="envelope" data-say="SMS and calls are passed through at cost. I just carry them."><div class="wrap grid g3" style="gap:16px">
    ${[['featurephone','Messaging at cost','SMS on pooled accounts is billed at cost (about ₹0.2 per message). Bring your own MSG91 account if you prefer.'],['lang','Languages included','Hindi and English now, with natural-voice audio. More reviewed languages as they are added.'],['guardian','Grant-supported onboarding','Grants can cover onboarding for smaller NGOs. Ask us.']].map(([i,t,d]) => `<div class="stack" style="gap:6px">${icon64(i)}<strong>${t}</strong><span class="small muted">${d}</span></div>`).join('')}
  </div></section>`;
}

function siteDemo(){
  return `<section class="section pattern" data-pose="envelope" data-say="Write to us. I’ll carry it over."><div class="wrap grid g2" style="gap:40px;align-items:start">
    <div class="stack" style="gap:16px">${secHead('Talk to us','Plan a pilot with your field team.','Tell us about your programmes and where you collect data. We’ll set up a sandbox with your notice in your languages.')}
      <div class="stack small" style="gap:10px">${[['lang','Your notice in your languages'],['phone','Anumati Collect on your field team’s phones'],['verify','A pilot with real consents, in a week']].map(([i,t]) => `<div class="row" style="gap:12px">${icon64(i)}<span>${t}</span></div>`).join('')}</div></div>
    <form class="card stack" id="demoform" data-form="demo">
      <label class="field">Organisation<input id="d-org" required placeholder="Your organisation" autocomplete="organization"></label>
      <label class="field">Your name<input id="d-name" required placeholder="Your name" autocomplete="name"></label>
      <label class="field">How do you collect data today?<select id="d-sys"><option>Paper and Excel</option><option selected>ODK / KoBo</option><option>CommCare</option><option>OpenMRS</option><option>Our own app</option></select></label>
      <label class="field">People served per year<input id="d-n" placeholder="e.g. 25,000" inputmode="numeric"></label>
      <button class="btn pri" type="submit">Request a sandbox</button>
      <span class="small muted">Opens your email app with these details. This website stores nothing.</span>
    </form>
  </div></section>`;
}

/* ================= Site runtime (the only part not lifted from the prototype) ================= */
const SITE = {
  contactEmail: '',        // set to the team inbox to make "Request a sandbox" open an email
  consoleUrl: '',          // set to the Frappe Cloud site URL once it is live ("Sign in")
  prototypeUrl: 'prototype/'
};
const S = { site: { page: 'home' } };
const PAGE_TITLES = Object.fromEntries(SITE_PAGES);
function pageFromHash(){ const h = location.hash.slice(1); return PAGE_TITLES[h] ? h : 'home'; }
function toast(msg){
  const el = document.getElementById('toast');
  el.className = 'toast'; el.textContent = msg; el.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, 6000);
}
function render(){
  S.site.page = pageFromHash();
  document.getElementById('app').innerHTML = renderSite();
  document.title = S.site.page === 'home' ? 'Anumati · Consent that works where the internet doesn’t' : `${PAGE_TITLES[S.site.page]} · Anumati`;
  setupIO(); storyInit();
}
const LINKS = {
  guide: 'guide/',
  qa: 'guide/qa-test-cases.html',
  code: 'https://github.com/sunandan89/anumati',
  api: 'https://github.com/sunandan89/anumati/blob/main/docs/api.md'
};
const lensUrl = k => k === 'con' ? SITE.consoleUrl : k === 'proto' ? SITE.prototypeUrl : LINKS[k];
document.addEventListener('click', e => {
  const el = e.target.closest('[data-a]'); if (!el) return;
  if (el.dataset.a === 'site'){
    e.preventDefault();
    if (pageFromHash() === el.dataset.p) render(); else location.hash = el.dataset.p;
    window.scrollTo(0, 0);
  } else if (el.dataset.a === 'lens'){
    e.preventDefault(); location.href = lensUrl(el.dataset.k);
  }
});
window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0); });
document.addEventListener('submit', e => {
  if (e.target.dataset.form !== 'demo') return;
  e.preventDefault();
  const v = id => document.getElementById(id).value.trim();
  if (!SITE.contactEmail){ toast('Sandbox requests open soon. Thank you for your interest.'); return; }
  const body = `Organisation: ${v('d-org')}\nName: ${v('d-name')}\nHow we collect data today: ${v('d-sys')}\nPeople served per year: ${v('d-n')}\n`;
  location.href = `mailto:${SITE.contactEmail}?subject=${encodeURIComponent('Anumati sandbox request: ' + v('d-org'))}&body=${encodeURIComponent(body)}`;
});
render();
