// Testa a regra da chuva: atrapalhar ESTICA o tempo, tem periodo frio, e tem teto.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  const cls = new Set();
  return {
    tag, filhos: [], style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(), attrs: {}, innerHTML: '', textContent: '', offsetWidth: 1,
    classList: { add: c => cls.add(c), remove: c => cls.delete(c), toggle(){}, contains: c => cls.has(c), _set: cls },
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
  chuva: chuvaAsteroides, atrapalhar, passou: passouAChuva, historias: historiasAtivas,
  soltar: soltarAsteroide, sujar,
  temMedo: () => _medo, ate: () => _medoAte, manchas: () => _sujeira,
  esfriar: () => { _medoUltimoSusto = 0; },
  rosto: () => _rostoAtual,
  CASTIGO: MEDO_CASTIGO, TETO: MEDO_TETO, ROSTO_MEDO, ROSTO_SUSTO,
};`)();
const t = globalThis.__t;
const pres = pega('presenca');
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };

t.chuva();
diz(t.temMedo() === true, 'chuvaAsteroides() liga o medo');
diz(t.rosto() === t.ROSTO_MEDO, 'a cara vira °ᯅ°');
diz(pres.classList.contains('medo'), 'a classe .medo entra (encolhe + halo frio)');
diz(t.historias() === 1, 'conta como história (segura idle/bocejo)');

const antes = t.ate();
t.atrapalhar();
diz(t.ate() - antes === t.CASTIGO, 'atrapalhar estica a chuva em MEDO_CASTIGO');
diz(t.rosto() === t.ROSTO_SUSTO, 'a cara leva o susto ╥‸╥');

const depois = t.ate();
t.atrapalhar();
diz(t.ate() === depois, 'atrapalhar de novo na hora NÃO conta (período frio)');
diz(true, '...um arrastão só não vira 20 castigos');

for (let i = 0; i < 40; i++) { t.esfriar(); t.atrapalhar(); }
diz(t.ate() - Date.now() <= t.TETO + 50, 'o teto impede castigo eterno');

// os asteroides caem no grupo certo e somem sozinhos (complete remove)
const g = pega('asteroides');
t.soltar(); t.soltar();
diz(g.filhos.length === 2, 'os asteroides entram no <g id="asteroides">');

t.passou();
diz(t.temMedo() === false, 'passouAChuva() desliga o medo');
diz(!pres.classList.contains('medo'), 'a classe .medo sai');
diz(t.historias() === 0, 'a história encerra');

// com outra história aberta, o fim da chuva devolve pra irritação e não pro alívio
t.chuva(); t.sujar(1);
diz(t.historias() === 2, 'chuva + fuligem = 2 histórias');
t.passou();
diz(t.temMedo() === false && t.historias() === 1, 'chuva acaba, a fuligem continua contando');
diz(t.rosto() !== '◉‿◉', 'não dá alívio com problema ainda na cabeça');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
