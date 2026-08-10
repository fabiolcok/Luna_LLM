// Testa o CICLO da fuligem de verdade: suja -> esfrega em cima -> mancha some.
// Um DOM minimo, mas com elementos que realmente guardam filhos e opacidade.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  return {
    tag, filhos: [], style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(), attrs: {}, innerHTML: '', textContent: '',
    classList: { add(){}, remove(){}, toggle(){}, contains: () => false },
    setAttribute(k, v) { this.attrs[k] = v; },
    getAttribute(k) { return this.attrs[k]; },
    removeAttribute(k) { delete this.attrs[k]; },
    insertBefore(c) { this.filhos.unshift(c); c._pai = this; return c; },
    contains: () => false, focus(){}, blur(){}, scrollIntoView(){}, click(){},
    appendChild(c) { this.filhos.push(c); c._pai = this; return c; },
    remove() { const p = this._pai; if (p) p.filhos.splice(p.filhos.indexOf(this), 1); },
    querySelector(sel) { return (this._q || (this._q = {}))[sel] || (this._q[sel] = El(sel)); },
    querySelectorAll: () => [], addEventListener(){},
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 196, height: 196 }),
    offsetWidth: 1,
  };
}
const elos = {};
const pega = (id) => (elos[id] || (elos[id] = El('g')));

global.document = {
  getElementById: pega,
  querySelector: (s) => pega(s), querySelectorAll: () => [],
  addEventListener(){}, createElement: () => El('div'),
  createElementNS: (ns, t) => El(t), body: El('body'), documentElement: El('html'),
};
global.window = { location: { host: 'x' }, addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}}) };
global.WebSocket = function(){ this.send=()=>{}; this.addEventListener=()=>{}; this.close=()=>{}; };
global.requestAnimationFrame = () => 0;
global.anime = Object.assign(() => ({ pause(){}, play(){} }), { stagger: () => 0 });
global.getComputedStyle = () => ({ getPropertyValue: () => '0' });
global.navigator = { userAgent: '' };
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.setInterval = () => 0; global.setTimeout = () => 0;
global.clearInterval = () => {}; global.clearTimeout = () => {};

new Function(src + '\n;globalThis.__t = { sujar, esfregar, ficouLimpa, limparSujeira,' +
                   ' historiasAtivas, manchas: () => _sujeira, contador: () => _sujeiraNaCara,' +
                   ' SUJ_RAIO, SUJ_VIDA };')();
const t = globalThis.__t;
const grupo = pega('sujeira');
let ok = true;
const diz = (cond, txt) => { if (!cond) ok = false; console.log((cond ? '  OK   ' : '  FALHA') + '  ' + txt); };

// 1) sujar cria manchas no grupo certo, dentro da cabeça
t.sujar(2);
const m = t.manchas();
diz(m.length === 2, 'sujar(2) criou 2 manchas');
diz(grupo.filhos.length === 2, 'as manchas foram parar no <g id="sujeira">');
diz(t.contador() === 2, 'o contador de história subiu');
diz(t.historiasAtivas() === 1, 'fuligem conta como UMA história, não como 2 objetos');
const dentro = m.every(x => Math.hypot(x.x - 100, x.y - 100) < 66);
diz(dentro, 'as manchas caem dentro da cabeça (r < 66)');
const foraDoMiolo = m.every(x => Math.hypot(x.x - 100, x.y - 100) > 20);
diz(foraDoMiolo, 'e fora do miolo, pra não tampar o rosto');

// 2) esfregar LONGE não faz nada
const rect = { left: 0, top: 0, width: 196, height: 196 };
const paraTela = (vx, vy) => [vx / 200 * 196, vy / 200 * 196];   // viewBox -> tela
// canto do viewBox: as manchas vivem entre r=27 e r=51 do centro, entao daqui esta longe
// de TODAS. Medir a partir da primeira mancha as vezes caia em cima da segunda.
const longe = paraTela(5, 5);
diz(t.esfregar(longe[0], longe[1], rect, 30) === false, 'esfregar longe da mancha não conta');
diz(t.manchas()[0].vida === t.SUJ_VIDA, '...e não gasta a vida dela');

// 3) esfregar EM CIMA gasta, e some quando a vida acaba
const alvo = t.manchas()[0];
const emCima = paraTela(alvo.x, alvo.y);
diz(t.esfregar(emCima[0], emCima[1], rect, 40) === true, 'esfregar em cima é detectado');
diz(alvo.vida === t.SUJ_VIDA - 40, 'a vida cai pelo tanto que a mão percorreu');
let voltas = 0;
while (t.manchas().includes(alvo) && voltas++ < 50) t.esfregar(emCima[0], emCima[1], rect, 40);
diz(!t.manchas().includes(alvo), 'insistindo, a mancha some');
diz(!grupo.filhos.includes(alvo.el), 'e sai do SVG junto (sem elemento órfão)');
// nao dá pra fixar a contagem: as manchas nascem em posicao aleatoria e duas sobrepostas
// saem na mesma esfregada (o que é o comportamento certo). O que TEM que valer sempre é
// a lista e o SVG andarem juntos.
diz(grupo.filhos.length === t.manchas().length, 'lista e SVG seguem em sincronia');

// 4) limpando a última, a história encerra
voltas = 0;
while (t.manchas().length && voltas++ < 80) {
    const alv = t.manchas()[0];
    const pt = paraTela(alv.x, alv.y);
    t.esfregar(pt[0], pt[1], rect, 40);
}
diz(t.contador() === 0, 'contador zera na última mancha');
diz(t.historiasAtivas() === 0, 'a história encerra');
diz(grupo.filhos.length === 0, 'o SVG fica limpo');

// 5) teto de manchas
t.sujar(99);
diz(t.manchas().length === 4, 'SUJ_MAX segura o acúmulo em 4');
t.limparSujeira();
diz(t.manchas().length === 0 && grupo.filhos.length === 0, 'limparSujeira() zera tudo');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
