// A cara voltou a ser UMA string (a boca separada foi abortada). O que precisa valer:
// (1) a cara e desenhada INTEIRA, (2) a curadoria dos climas se manteve, (3) a lista de quem
// pisca vale, (4) nao sobrou maquinaria de boca no arquivo.
const fs = require('fs');
const RAIZ = require('path').join(__dirname, '..');
const html = fs.readFileSync(require('path').join(RAIZ, 'templates', 'Index.html'), 'utf8');
const py   = fs.readFileSync(require('path').join(RAIZ, 'modulos', 'pensar.py'), 'utf8');
const servidor = fs.readFileSync(require('path').join(RAIZ, 'servidor.py'), 'utf8');
const src  = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

function El(tag) {
  const cls = new Set();
  return {
    tag, filhos: [], attrs: {}, innerHTML: '', textContent: '', offsetWidth: 1, value: '',
    style: (()=>{const o={};o.setProperty=(k,v)=>{o[k]=v};o.getPropertyValue=k=>o[k]||'';o.removeProperty=k=>{delete o[k]};return o})(),
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
  addEventListener(){}, createElement: () => El('span'), createElementNS: (n,t) => El(t),
  body: El('body'), documentElement: El('html') };
global.window = { location:{host:'x'}, addEventListener(){}, matchMedia: () => ({matches:false, addEventListener(){}}) };
global.WebSocket = function(){ this.send=()=>{}; this.addEventListener=()=>{}; this.close=()=>{}; };
global.requestAnimationFrame = () => 0;
global.getComputedStyle = () => ({ getPropertyValue: () => '0' });
global.navigator = { userAgent:'' };
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.setInterval = () => 0; global.setTimeout = () => 0;
global.clearInterval = () => {}; global.clearTimeout = () => {};
global.anime = Object.assign(() => ({ pause(){}, play(){} }), { stagger: () => 0 });

new Function(src + `
;globalThis.__t = { pintar: pintarRosto, direto: rostoDireto, piscada: versaoPiscada,
  podePiscar, NAO_PISCA, rosto: () => _rostoAtual,
  climas: CARAS_CLIMA, base: CARAS_BASE, hist: CARAS_HIST, IDLE: ROSTOS_IDLE };`)();
const t = globalThis.__t;
const rosto = pega('rosto-txt');
let ok = true;
const diz = (c, txt) => { if (!c) ok = false; console.log((c ? '  OK   ' : '  FALHA') + '  ' + txt); };

// ---- 1) a cara e UMA string de novo ----
const caras = new Set();
const blocoPy = py.match(/_ROSTOS = \{([\s\S]*?)\n\}/)[1];
for (const linha of blocoPy.split('\n')) {
  const m = linha.match(/\[(.*)\]/); if (!m) continue;
  for (const q of m[1].matchAll(/"([^"]*)"|'([^']*)'/g)) caras.add(q[1] !== undefined ? q[1] : q[2]);
}
for (const m of html.matchAll(/(?:trocarRosto|rostoDireto)\('([^']+)'\)/g)) caras.add(m[1]);
for (const m of html.matchAll(/const ROSTO_\w+\s*=\s*'([^']+)'/g)) caras.add(m[1]);
for (const m of html.matchAll(/\['([^']+)',\s*\d+\]/g)) caras.add(m[1]);
for (const m of html.matchAll(/ROSTOS_(?:IDLE|IRRITADA) = \[([^\]]+)\]/g))
  for (const q of m[1].matchAll(/'([^']+)'/g)) caras.add(q[1]);
for (const m of html.matchAll(/ROSTO_ESTADO = \{([\s\S]*?)\}/g))
  for (const q of m[1].matchAll(/:\s*'([^']+)'/g)) caras.add(q[1]);
for (const m of html.matchAll(/trocarRosto\([^)]*?\?\s*'([^']+)'\s*:\s*'([^']+)'\)/g)) { caras.add(m[1]); caras.add(m[2]); }

const erradas = [...caras].filter(c => { t.pintar(c); return rosto.textContent !== c; });
diz(erradas.length === 0, 'as ' + caras.size + ' caras são desenhadas INTEIRAS, sem partir' +
    (erradas.length ? ' — ERRO: ' + erradas.join(' | ') : ''));

// ---- 2) a maquinaria da boca sumiu de vez ----
const restos = ['SVG_BOCA','partirRosto','const BOCAS','formaBoca','caminhoBoca','K_CURVA',
                'desenharBoca','BOCA_MOD','ligarModulador','comecarBoca','pararBoca',
                'FALA_ABRE','_bocaForma','_bocaMod','_falandoBoca','OLHO_DESCE','alturaBoca',
                'ehRostoInteiro','_bancada','BOCA_CTRL','montarControlesBoca'];
const sobrou = restos.filter(r => src.includes(r));
diz(sobrou.length === 0, 'nenhuma sobra da boca no script' + (sobrou.length ? ' — SOBROU: ' + sobrou.join(', ') : ''));
const css = html.match(/<style>([\s\S]*?)<\/style>/)[1];
const cssSobra = ['olho-e','olho-d','--boca-','.boca','lab-bn','lab-valores'].filter(c => css.includes(c));
diz(cssSobra.length === 0, 'nem no CSS' + (cssSobra.length ? ' — SOBROU: ' + cssSobra.join(', ') : ''));

// ---- 3) a curadoria dos climas se manteve ----
const climasPy = [...caras].filter(c => blocoPy.includes(c));
const podadas = ['╭ರ_•́', '´ཀ`', '︶︹︺', '•̀ ᴗ -', '¬_¬', 'ᵔᗜᵔ', '- ‸ -'];
const voltou = podadas.filter(c => blocoPy.includes(c));
diz(voltou.length === 0, 'as caras podadas continuam fora' + (voltou.length ? ' — VOLTOU: ' + voltou.join(' ') : ''));
const semCara = [...blocoPy.matchAll(/"(\w+)":\s*\[(.*)\]/g)].filter(m => !m[2].trim()).map(m => m[1]);
diz(semCara.length === 0, 'nenhum clima ficou órfão');
diz(html.includes("ROSTO_MEDO = '°ᯅ°'"), 'a cara de medo é o °ᯅ° (o ᯅ volta a aparecer, é glifo de novo)');
diz(html.includes("ROSTO_JOGO = 'ᓀ‸ᓂ'"), 'modo jogo usa a cara concentrada ᓀ‸ᓂ');
diz(html.includes("ROSTO_RADAR_PROATIVO = '⇀‸↼'"), 'sonar proativo usa a cara fixa ⇀‸↼');
diz(html.includes("pensando: '◐_◑'"), 'pensando usa a cara ◐_◑');
diz(py.includes('_ult, _clima_escolhido, texto_luna = _extrair_clima(texto_luna)') &&
    py.includes('_srv.atualizar_kaomoji(_ult, _clima_escolhido)') &&
    py.includes('def obter_clima_resposta()') &&
    servidor.includes('turno["clima"] = clima_turno'),
    'o clima escolhido fica vinculado ao turno da resposta web');
diz(html.includes('⌐■_■ combina com um futuro eclipse'), 'a cara candidata ao eclipse ficou anotada');

// ---- 4) a lista de quem pisca continua valendo ----
const PISCAM = ['Ò﹏Ó','ಠ_ಠ','O_O','◉‿◉','ㆆ_ㆆ','⚈₋⚈','ᗜ⩊ᗜ','•𐃷•','• ₃ •','･ ᴗ ･','• _ •','◐_◑'];
const NAOPISCAM = ['ᗒᗜᗕ','ᵔ ᵕ ᵔ','╥‸╥','◞_◟','ꈍ◡ꈍ','≖_≖','￢_￢','T_T','_　_ 💤','｀皿´','｀Д´','಄ᆺ಄','°ᯅ°','ᗒ_ᗕ','>_<','- _ -','ᓀ‸ᓂ','⇀‸↼','⌐■_■'];
const errSim = PISCAM.filter(c => !t.podePiscar(c));
const errNao = NAOPISCAM.filter(c => t.podePiscar(c));
diz(errSim.length === 0, 'as ' + PISCAM.length + ' marcadas PISCA piscam' + (errSim.length ? ' — NÃO: ' + errSim.join(' ') : ''));
diz(errNao.length === 0, 'as ' + NAOPISCAM.length + ' marcadas NÃO não piscam' + (errNao.length ? ' — PISCA: ' + errNao.join(' ') : ''));
const indecisas = [...caras].filter(c => !PISCAM.includes(c) && !NAOPISCAM.includes(c));
diz(indecisas.length === 0, 'toda cara tem decisão de piscada' + (indecisas.length ? ' — SEM: ' + indecisas.join(' ') : ''));
const orfas = [...t.NAO_PISCA].filter(c => !caras.has(c));
diz(orfas.length === 0, 'NAO_PISCA sem entrada morta' + (orfas.length ? ' — ÓRFÃO: ' + orfas.join(' ') : ''));

// ---- 5) a piscada em si ----
diz(t.piscada('ಠ_ಠ') === '-_-', 'piscar troca os dois olhos por traço: ಠ_ಠ -> ' + t.piscada('ಠ_ಠ'));
diz(t.piscada('_　_ 💤') === null, 'cara com emoji não pisca (não dá pra achar os olhos)');
t.pintar(t.piscada('◉‿◉'));
diz(rosto.textContent === '-‿-', 'e a piscada é desenhada inteira também');

// ---- 6) o laboratorio continua de pe ----
diz(t.climas().length >= 12 && t.base().length >= 5 && t.hist().length >= 8,
    'o laboratório ainda lista as caras (' + (t.climas().length + t.base().length + t.hist().length) + ' botões)');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
