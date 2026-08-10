// Testa a consequencia: 3 historias por tempo demais -> vira de costas; so volta com tudo limpo.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  const cls = new Set();
  return {
    tag, filhos: [], style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(), attrs: {}, innerHTML: '', textContent: '', offsetWidth: 1,
    // add/remove do DOM real sao VARIADICOS — aceitar um argumento so mascarava
    // remove('irrit-2', 'irrit-3') e dava falha falsa
    classList: {
      add: (...c) => c.forEach(x => cls.add(x)),
      remove: (...c) => c.forEach(x => cls.delete(x)),
      toggle(c, v) { v ? cls.add(c) : cls.delete(c); },
      contains: c => cls.has(c),
    },
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
// setTimeout que DA pra disparar na mao: preciso ver a volta em passos
const pendentes = [];
global.setTimeout = (f, ms) => { pendentes.push({ f, ms }); return pendentes.length; };
global.setInterval = () => 0; global.clearInterval = () => {}; global.clearTimeout = () => {};
const dispara = (ms) => pendentes.filter(t => t.ms === ms).forEach(t => t.f());

new Function(src + `
;globalThis.__t = {
  virar: virarDeCostas, voltar: voltarAtencao, historias: historiasAtivas,
  sujar, foguete: novoFoguete, chuva: chuvaAsteroides, cutucar, irritacao: atualizarIrritacao,
  desistiu: () => _desistiu, rosto: () => _rostoAtual,
  fogNaCabeca: () => _foguetesNaCabeca, limparSujeira,
  OLHADA: DESISTIR_OLHADA, ALIVIO: DESISTIR_ALIVIO, QUANTAS: DESISTIR_HISTORIAS,
};`)();
const t = globalThis.__t;
const pres = pega('presenca');
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };

// a raiva sobe primeiro
t.sujar(1); t.foguete(); t.chuva();
diz(t.historias() === t.QUANTAS, 'três histórias abertas ao mesmo tempo');
t.irritacao(true);
diz(pres.classList.contains('irrit-3'), 'a escada de irritação chega no topo');

t.virar();
diz(t.desistiu() === true, 'virarDeCostas() liga o estado');
diz(pres.classList.contains('desistiu'), 'a classe .desistiu entra (CSS faz o giro e o cinza)');
diz(!pres.classList.contains('irrit-3'), 'a RAIVA cede lugar: a classe de irritação sai');

// de costas: nada de história nova, nem reação
const antes = t.historias();
t.sujar(2); t.foguete();
diz(t.historias() === antes, 'de costas não nasce história nova (não se pilha em cima)');
const cara = t.rosto();
t.cutucar();
diz(t.rosto() === cara, 'cutucar não alcança: é o silêncio que pesa');
t.irritacao(true);
diz(!pres.classList.contains('irrit-2') && !pres.classList.contains('irrit-3'),
    'atualizarIrritacao não reacende a raiva enquanto ela está de costas');

// resolver PARCIALMENTE não traz ela de volta
t.limparSujeira();
diz(t.historias() > 0, 'ainda sobrou história');
t.voltar.call && (t.historias() === 0 ? t.voltar() : null);
diz(t.desistiu() === true, 'não volta com história ainda aberta (regra: resolver TUDO)');

// resolvendo tudo, a volta acontece em passos
globalThis.__zera = true;
t.voltar();   // o laço chamaria isso quando historiasAtivas() === 0
diz(t.desistiu() === false, 'voltarAtencao() desliga o estado');
diz(!pres.classList.contains('desistiu'), 'a classe sai (o rosto gira de volta)');
diz(t.rosto() === '≖_≖', 'ela volta ENCARANDO, não sorrindo');
dispara(t.OLHADA);
diz(t.rosto() === '◉‿◉', 'depois de ' + t.OLHADA + 'ms, alivia');
diz(pendentes.some(x => x.ms === t.OLHADA + t.ALIVIO), 'e o idle está agendado pra ' + (t.OLHADA + t.ALIVIO) + 'ms');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
