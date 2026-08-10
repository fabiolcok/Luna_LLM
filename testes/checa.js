// EXTRAI o <script> do Index.html AGORA e roda. O roda.js lia um luna.js
// pre-extraido, o que permitia "validar" uma copia velha sem perceber.
const fs = require('fs');
const HTML = require('path').join(__dirname, '..', 'templates', 'Index.html');
const html = fs.readFileSync(HTML, 'utf8');

const blocos = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!blocos.length) { console.log('QUEBROU: nenhum <script> encontrado'); process.exit(1); }
const src = blocos.join('\n;\n');
console.log('extraido de Index.html:', src.length, 'chars,', blocos.length, 'bloco(s)');

const fake = () => new Proxy(function(){}, {
  get: (t,p) => p === 'classList' ? { add(){}, remove(){}, toggle(){}, contains:()=>false }
             : p === 'style' ? { setProperty(){}, getPropertyValue: () => '', removeProperty(){} } : p === 'textContent' ? '' : fake(),
  set: () => true, apply: () => fake(),
});
global.document = { getElementById: () => fake(), querySelector: () => fake(),
  querySelectorAll: () => [], addEventListener(){}, createElement: () => fake(),
  createElementNS: () => fake(), body: fake(), documentElement: fake() };
global.window = { location: { host: 'x' }, addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}}) };
global.WebSocket = function(){ this.send=()=>{}; this.addEventListener=()=>{}; this.close=()=>{}; };
global.requestAnimationFrame = () => 0;
global.anime = Object.assign(() => ({ pause(){}, play(){} }), { stagger: () => 0 });
global.getComputedStyle = () => ({ getPropertyValue: () => '0' });
global.navigator = { userAgent: '' };
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.setInterval = () => 0; global.setTimeout = () => 0;
global.clearInterval = () => {}; global.clearTimeout = () => {};

try { new Function(src)(); console.log('SCRIPT RODOU ATE O FIM — sem ReferenceError'); }
catch (e) { console.log('QUEBROU:', e.constructor.name + ':', e.message); process.exit(1); }
