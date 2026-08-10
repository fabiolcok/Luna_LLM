// Testa a invasao: frota nasce, orbita, o cerco fecha ao atrapalhar, e some no fim.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  const cls = new Set();
  return {
    tag, filhos: [], style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(), attrs: {}, innerHTML: '', textContent: '', offsetWidth: 1,
    classList: { add: c => cls.add(c), remove: c => cls.delete(c), toggle(){}, contains: c => cls.has(c) },
    setAttribute(k,v){ this.attrs[k]=v; }, getAttribute(k){ return this.attrs[k]; },
    removeAttribute(k){ delete this.attrs[k]; },
    appendChild(c){ this.filhos.push(c); c._pai=this; return c; },
    insertBefore(c){ this.filhos.unshift(c); c._pai=this; return c; },
    remove(){ const p=this._pai; if(p) p.filhos.splice(p.filhos.indexOf(this),1); },
    querySelector(sel){ return (this._q||(this._q={}))[sel] || (this._q[sel]=El(sel)); },
    querySelectorAll: () => [], addEventListener(){}, focus(){}, blur(){}, click(){},
    getBoundingClientRect: () => ({ left:0, top:0, width:196, height:196 }),
  };
}
const elos = {}; const pega = id => (elos[id] || (elos[id] = El('g')));
global.document = { getElementById: pega, querySelector: pega, querySelectorAll: () => [],
  addEventListener(){}, createElement: () => El('div'), createElementNS: (n,t) => El(t),
  body: El('body'), documentElement: El('html') };
global.window = { location:{host:'x'}, addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}}) };
global.WebSocket = function(){ this.send=()=>{}; this.addEventListener=()=>{}; this.close=()=>{}; };
global.requestAnimationFrame = () => 0;
global.anime = Object.assign(() => ({ pause(){}, play(){} }), { stagger: () => 0 });
global.getComputedStyle = () => ({ getPropertyValue: () => '0' });
global.navigator = { userAgent:'' };
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.setInterval = () => 0; global.setTimeout = () => 0;
global.clearInterval = () => {}; global.clearTimeout = () => {};

new Function(src + `
;globalThis.__t = {
  invasao: invasaoOvnis, chuva: chuvaAsteroides, voar: voarFrota, feixe: desenharFeixe,
  atrapalhar, passou: passouAInvasao, historias: historiasAtivas,
  frota: () => _frota, temMedo: () => _medo, ehInvasao: () => _invasao,
  alerta: () => _invAlerta, ate: () => _medoAte, rosto: () => _rostoAtual,
  esfriar: () => { _medoUltimoSusto = 0; },
  QUANTOS: INV_QUANTOS, PERTO: INV_PERTO, LONGE: INV_LONGE, ROSTO_MEDO,
};`)();
const t = globalThis.__t;
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };

t.invasao();
diz(t.temMedo() && t.ehInvasao(), 'invasaoOvnis() liga medo + invasão');
diz(t.frota().length === t.QUANTOS, 'nasceram ' + t.QUANTOS + ' discos');
diz(pega('frota').filhos.length === t.QUANTOS, 'os discos entraram no <g id="frota">');
diz(pega('feixes').filhos.length === t.QUANTOS, 'cada disco tem seu feixe');
diz(t.rosto() === t.ROSTO_MEDO, 'a cara vira °ᯅ°');
diz(t.historias() === 1, 'conta como história');
diz(t.frota().every(o => o.raio === 150), 'começam de fora do quadro');

// voando relaxados: o raio converge pro LONGE e os feixes ficam apagados
for (let i = 0; i < 200; i++) t.voar();
const rLonge = t.frota()[0].raio;
diz(Math.abs(rLonge - t.LONGE) < 1, 'sem ninguém por perto, a ronda estabiliza no raio largo');
diz(t.frota().every(o => o.fx.getAttribute('opacity') === '0'), 'e os feixes ficam apagados');
diz(t.frota().every(o => Math.hypot(o.x - 100, o.y - 100) > 40), 'ficam FORA da cabeça dela');

// atrapalhar: fecham o cerco e acendem
const antes = t.ate();
t.atrapalhar();
diz(t.ate() > antes, 'atrapalhar estica a invasão');
diz(t.alerta() > Date.now(), 'e dispara o alerta do cerco');
for (let i = 0; i < 200; i++) t.voar();
diz(t.frota()[0].raio < rLonge - 20, 'no cerco eles CHEGAM PERTO');
diz(Math.abs(t.frota()[0].raio - t.PERTO) < 2, '...convergindo pro raio fechado');
diz(t.frota().every(o => o.fx.getAttribute('opacity') === '0.3'), 'e os feixes acendem');
diz(t.frota().every(o => (o.fx.getAttribute('d') || '').startsWith('M ')), 'o cone do feixe é desenhado');

// o cone aponta do disco pra cabeça: o ponto de partida é o disco
const d = t.feixe(20, 20);
const p0 = d.match(/^M ([-\d.]+) ([-\d.]+)/);
diz(Math.hypot(+p0[1] - 20, +p0[2] - 20) < 6, 'o feixe começa no disco, não no meio da tela');

t.passou();
diz(!t.temMedo() && !t.ehInvasao(), 'passouAInvasao() encerra');
diz(t.frota().length === 0, 'a frota é esvaziada');
diz(t.historias() === 0, 'a história encerra');

// os dois eventos de medo não podem rodar juntos (compartilham _medoAte)
t.invasao(); t.chuva();
diz(t.ehInvasao() === true, 'chuva não começa por cima da invasão');
t.passou();

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
