// Trava o ritmo: as historias nao podem se amontoar. O relato foi "2 min fora e ja tem 4
// coisas acontecendo" — entao o teste mede exatamente isso.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  const cls = new Set();
  return {
    tag, filhos: [], style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(), attrs: {}, innerHTML: '', textContent: '', offsetWidth: 1,
    classList: { add:(...c)=>c.forEach(x=>cls.add(x)), remove:(...c)=>c.forEach(x=>cls.delete(x)),
                 toggle(c,v){ v?cls.add(c):cls.delete(c); }, contains:c=>cls.has(c) },
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
  pode: podeComecarHistoria, marcar: marcarHistoria, historias: historiasAtivas,
  foguete: novoFoguete, sujar, chuva: chuvaAsteroides, satelite: novoSatelite,
  recuar: (ms) => { _ultimaHistoria = Date.now() - ms; },
  afk: (v) => { _afk = v; }, desistir: (v) => { _desistiu = v; },
  ESPACO: HISTORIA_ESPACO, TETO: HISTORIA_TETO,
};`)();
const t = globalThis.__t;
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };

diz(t.pode() === true, 'de saída, uma história pode começar');
t.marcar();
diz(t.pode() === false, 'logo depois de uma começar, a próxima é barrada');

// o cerne da queixa: 2 minutos parado nao pode render uma enxurrada
t.recuar(120000);
diz(t.pode() === false, '2 minutos depois ainda está barrada (era essa a queixa)');
t.recuar(t.ESPACO - 1000);
diz(t.pode() === false, 'um segundo antes do espaçamento, ainda não');
t.recuar(t.ESPACO + 1000);
diz(t.pode() === true, 'passado o espaçamento de ' + (t.ESPACO/60000) + ' min, libera');

// teto de historias simultaneas
t.foguete(); t.sujar(1); t.chuva();
diz(t.historias() === t.TETO, 'três histórias abertas');
t.recuar(t.ESPACO * 10);
diz(t.pode() === false, 'no teto, nem o tempo destrava: não vira bagunça');
diz(t.TETO >= 3, 'mas o teto ainda permite as 3 que o "desistir" exige');

// AFK e de costas nao acumulam nada
t.recuar(t.ESPACO * 10);
t.afk(true);
diz(t.pode() === false, 'AFK não acumula história');
t.afk(false); t.desistir(true);
diz(t.pode() === false, 'de costas também não');
t.desistir(false);

// nenhum agendamento pode ter voltado a ser curto
const agendas = [...src.matchAll(/(\d{5,})\s*\+\s*Math\.random\(\)\s*\*\s*(\d{5,})/g)]
                  .map(m => ({ min: +m[1], max: +m[1] + +m[2] }));
diz(agendas.length >= 8, 'achei os ' + agendas.length + ' agendamentos no arquivo');
const curtos = agendas.filter(a => a.min < 600000);
diz(curtos.length === 0, 'nenhum agendamento dispara em menos de 10 min — mínimos: ' +
    agendas.map(a => (a.min/60000).toFixed(0)).sort((x,y)=>x-y).join(', ') + ' min');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
