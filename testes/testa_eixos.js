// EIXOS: estado / atividade / emocao / ambiente tem que compor sem regra combinatoria.
// O marcador `com-ferramenta` e o que permite as regras de ESTADO dizerem "so quando nao ha
// ferramenta" com UM :not() — antes eram cinco, um por ferramenta.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const src = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  const cls = new Set();
  return {
    tag, filhos: [], attrs: {}, innerHTML: '', textContent: '', offsetWidth: 1,
    style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(),
    classList: { add:(...c)=>c.forEach(x=>cls.add(x)), remove:(...c)=>c.forEach(x=>cls.delete(x)),
                 toggle(c,v){ v===undefined ? (cls.has(c)?cls.delete(c):cls.add(c)) : (v?cls.add(c):cls.delete(c)); },
                 contains:c=>cls.has(c), _set: cls },
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
;globalThis.__t = { aplicar: aplicarFerramenta, limpar: limparFerramenta, jogo: modoJogo,
  sincronizar: sincronizarFerramenta, VISUAL: FERRAMENTAS_VISUAL,
  presenca: aplicarPresenca, ESTADOS: PRES_ESTADOS, rosto: () => _rostoAtual };`)();
const t = globalThis.__t;
const pres = pega('presenca');
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };
const tem = (c) => pres.classList.contains(c);

// ---- 1) o CSS nao pode ter regra que case dois eixos ----
const css = html.match(/<style>([\s\S]*?)<\/style>/)[1].replace(/\/\*[\s\S]*?\*\//g, '');
const regras = [...css.matchAll(/([^{}]+)\{[^{}]*\}/g)].map(m => m[1].trim())
                 .filter(r => r && !r.startsWith('@') && !r.includes('%'));
const EIXOS = ['est-', 'ferr-', 'irrit-'];
const comb = regras.filter(r => new Set([...r.matchAll(/\.([a-z][\w-]*)/g)]
                 .flatMap(m => EIXOS.filter(p => m[1].startsWith(p)))).size >= 2);
diz(comb.length === 0, 'nenhuma das ' + regras.length + ' regras casa dois eixos' +
    (comb.length ? ' — COMBINA: ' + comb.join(' | ') : ''));
diz(!css.includes(':not(.ferr-'), 'nenhum :not() enumera ferramenta uma a uma');
diz(css.split(':not(.com-ferramenta)').length - 1 === 3, 'as 3 regras de estado usam o marcador único');

// ---- 2) o marcador segue as classes de verdade, em todo caminho ----
diz(!tem('com-ferramenta'), 'sem ferramenta, sem marcador');
for (const [tool, modo] of Object.entries(t.VISUAL)) {
  t.aplicar('▸ Usando: ' + tool);
  diz(tem('ferr-' + modo) && tem('com-ferramenta'), tool + ' liga ferr-' + modo + ' E o marcador');
}
diz(t.VISUAL.consultar_jogo_steam === t.VISUAL.pesquisar_web,
    'consulta de jogo Steam reutiliza exatamente o radar da pesquisa web');
t.limpar();
diz(!tem('com-ferramenta'), 'limparFerramenta desliga o marcador');

// modo jogo entra pelo mesmo eixo, por um caminho diferente
t.jogo('Teste');
diz(tem('ferr-jogo') && tem('com-ferramenta'), 'modo jogo também liga o marcador');
diz(css.includes('#presenca.ferr-jogo    { --cor-halo: #b56cff; }'),
    'modo jogo usa violeta elétrico na cabeça, sem disputar o verde do Spotify');
diz(css.includes('animation: none;') && css.includes('opacity: .68;'),
    'modo jogo mantém a cabeça violeta acesa e estável, sem efeito de pop');
diz(css.includes('#presenca.ferr-jogo #orbita rect:nth-child(4n+1)'),
    'os quatro pixels principais do jogo têm escala própria');
diz(css.includes('animation: jogo-montanha-russa 14s ease-in-out infinite'),
    'a órbita do jogo alterna aceleração e desaceleração');
t.jogo(null);
diz(!tem('ferr-jogo') && !tem('com-ferramenta'), '...e desliga ao sair');

// ---- 3) a rede de seguranca: derivado, nao mantido a mao ----
pres.classList.add('ferr-spotify');          // alguem mexeu na classe por fora
t.sincronizar();
diz(tem('com-ferramenta'), 'o marcador é DERIVADO: sincronizar() o recupera sozinho');
pres.classList.remove('ferr-spotify');
t.sincronizar();
diz(!tem('com-ferramenta'), '...nos dois sentidos');

// ---- 4) proativos são transitórios e o sonar é exclusivo dos radares ----
for (const tarefa of ['radar_rss', 'radar_promocoes', 'animes']) {
  t.aplicar('◗ Proativo: ' + tarefa);
  diz(tem('proat-radar'), tarefa + ' liga o sonar proativo');
  diz(t.rosto() === '⇀‸↼', tarefa + ' mantém a cara fixa do sonar');
}
t.aplicar('◗ Proativo: checar_agenda');
diz(!tem('proat-radar'), 'outro proativo fica sem efeito enquanto refinamos o radar');
t.aplicar('◗ Por aqui');
diz(!tem('proat-radar'), 'Por aqui encerra o visual proativo');
diz(html.includes('x1="100" y1="100" x2="160" y2="100"'),
    'o sonar nasce no centro e termina dentro da cabeça');
diz(html.includes('M 100 100 L 150.9 68.2 A 60 60 0 0 1 160 100 Z'),
    'a linha do sonar carrega um setor translúcido como rastro');
diz(css.includes('animation-delay: calc(var(--d-seq) * 1.8s)'),
    'cada bola grande pisca quando a linha alcança seu ângulo');
diz(css.includes('#presenca.proat-radar #orbita-escala') && css.includes('drop-shadow(0 0 12px #ffffff)'),
    'o clarão branco das bolas não é apagado pela opacidade do idle');

// ---- 5) uma classe por eixo: estado nao acumula ----
for (const e of t.ESTADOS) {
  t.presenca(e);
  const ligados = t.ESTADOS.filter(x => tem('est-' + x));
  diz(ligados.length === 1 && ligados[0] === e, 'estado ' + e + ': exatamente UMA classe est-* ligada');
}

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
