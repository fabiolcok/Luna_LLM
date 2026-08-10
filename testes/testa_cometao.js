// O bug: a martelada vinha de uma classe CSS, e animacao de transform no CSS SUBSTITUI o
// atributo transform do SVG — o cometao perdia o translate e piscava na origem do viewBox.
// Este teste trava isso: TODO frame do tranco tem que carregar a posicao dele junto.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

const frames = [];   // todo transform escrito no #cometao
function El(tag, id) {
  const cls = new Set();
  return {
    tag, id, filhos: [], style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(), attrs: {}, innerHTML: '', textContent: '', offsetWidth: undefined,
    classList: { add:(...c)=>c.forEach(x=>cls.add(x)), remove:(...c)=>c.forEach(x=>cls.delete(x)),
                 toggle(c,v){ v?cls.add(c):cls.delete(c); }, contains:c=>cls.has(c) },
    setAttribute(k,v){ this.attrs[k]=v; if (this.id==='cometao' && k==='transform') frames.push(v); },
    getAttribute(k){ return this.attrs[k]; }, removeAttribute(k){ delete this.attrs[k]; },
    appendChild(c){ this.filhos.push(c); c._pai=this; return c; },
    insertBefore(c){ this.filhos.unshift(c); c._pai=this; return c; },
    remove(){ const p=this._pai; if(p) p.filhos.splice(p.filhos.indexOf(this),1); },
    querySelector(sel){ return (this._q||(this._q={}))[sel] || (this._q[sel]=El(sel)); },
    querySelectorAll: () => [], addEventListener(){}, focus(){}, blur(){}, click(){},
    getBoundingClientRect: () => ({ left:0, top:0, width:196, height:196 }),
  };
}
const elos = {}; const pega = id => (elos[id] || (elos[id] = El('g', id)));
global.document = { getElementById: pega, querySelector: pega, querySelectorAll: () => [],
  addEventListener(){}, createElement: () => El('div'), createElementNS: (n,t) => El(t),
  body: El('body'), documentElement: El('html') };
global.window = { location:{host:'x'}, addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}}) };
global.WebSocket = function(){ this.send=()=>{}; this.addEventListener=()=>{}; this.close=()=>{}; };
global.requestAnimationFrame = () => 0;
global.getComputedStyle = () => ({ getPropertyValue: () => '0' });
global.navigator = { userAgent:'' };
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.setInterval = () => 0; global.setTimeout = () => 0;
global.clearInterval = () => {}; global.clearTimeout = () => {};

// anime falso que RODA: aplica cada keyframe (ou os valores finais) e chama update/complete.
global.anime = Object.assign(function (cfg) {
  const t = cfg.targets;
  const aplica = (vals) => {
    if (t && typeof t === 'object') for (const k in vals)
      if (!['duration','easing','delay','elasticity'].includes(k)) t[k] = vals[k];
    cfg.update && cfg.update();
  };
  if (cfg.keyframes) cfg.keyframes.forEach(aplica);
  else {
    const vals = {}; for (const k in cfg)
      if (!['targets','duration','easing','delay','update','complete','loop','direction','keyframes'].includes(k))
        vals[k] = cfg[k];
    aplica(vals);
  }
  cfg.complete && cfg.complete();
  return { pause(){}, play(){} };
}, { stagger: () => 0 });

new Function(src + '\n;globalThis.__t = { cometao, marretar, tranco: trancoNoCometao,' +
                   ' onde: () => _cometaoEl, vida: () => _cometaoVida };')();
const t = globalThis.__t;
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };

t.cometao();
const base = t.onde();
diz(!!base, 'o cometão encaixou e guardou a posição');

frames.length = 0;
t.marretar();
diz(frames.length > 0, 'a martelada escreve transform (o tranco existe)');

const semTranslate = frames.filter(f => !f.includes('translate('));
diz(semTranslate.length === 0, 'NENHUM frame do tranco perde o translate');

const alvo = 'translate(' + base.x.toFixed(1) + ' ' + base.y.toFixed(1) + ')';
const fora = frames.filter(f => !f.startsWith(alvo));
diz(fora.length === 0, 'todo frame fica exatamente na posição dele — nada de pular pra origem');
diz(frames[frames.length - 1].includes('scale(1.000)'), 'o último frame volta ao tamanho normal');

// offsetWidth e undefined em SVG (so existe em HTMLElement) — era isso que fazia o bug ser
// intermitente. Tira os comentarios antes de olhar: o proprio comentario que explica o bug
// contem o trecho e dava falso positivo. Em #presenca (uma div) o uso e legitimo.
const codigo = src.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
const offs = [...codigo.matchAll(/(\w+)\.offsetWidth/g)].map(m => m[1]);
diz(offs.every(v => v === 'pres'), 'offsetWidth só é lido em #presenca (HTML), nunca num nó SVG — achei: ' + (offs.join(', ') || 'nenhum'));
diz(!/classList\.(add|remove)\('batida'\)/.test(codigo), 'a classe CSS .batida não é mais usada');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
