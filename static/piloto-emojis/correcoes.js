'use strict';
// Índices conferidos nos arquivos originais locais. Nunca ocultar os mattes:
// alguns recortam olhos e boca, mesmo tendo "base" no nome.
const CORRECOES_EMOJIS = {
 '1f923': {ocultar:{comp_0:[12,13]}},
 '1f601': {ocultar:{comp_0:[16,17]}},
 '1f605': {ocultar:{comp_0:[11,12]}},
 '1f602': {ocultar:{comp_0:[12,13]}},
 '1f61c': {ocultar:{comp_0:[24,25]}},
 '1f92a': {ocultar:{comp_0:[18,19]}},
 '1fae3': {ocultar:{comp_0:[11,12,13]},maos:{comp_0:[4,6]}},
 '1f910': {ocultar:{comp_0:[14,15]}},
 '1fae8': {ocultar:{comp_0:[14]}},
 '1f635': {ocultar:{comp_0:[9,10]}},
 '1f917': {maos:{raiz:[6,7,9,11]}},
 '1f92d': {maos:{raiz:[3,4]}},
 '1fae2': {maos:{raiz:[2]}},
 '1f92b': {maos:{raiz:[1,11]}},
 '1f914': {maos:{raiz:[2,3]}}
};
function tonalidadeMao(c){
 const luz=Math.max(0,Math.min(1,.2126*c[0]+.7152*c[1]+.0722*c[2]));
 return [.10+.64*luz,.24+.76*luz,.29+.70*luz];
}
function mapearCorAnimada(prop,transformar){
 if(!prop)return;
 if(prop.a===0)prop.k=transformar(prop.k);
 else for(const quadro of prop.k||[]){if(quadro.s)quadro.s=transformar(quadro.s);if(quadro.e)quadro.e=transformar(quadro.e);}
}
function colorirMao(node){
 if(!node||typeof node!=='object')return;
 if(['fl','st'].includes(node.ty))mapearCorAnimada(node.c,c=>[...tonalidadeMao(c),...c.slice(3)]);
 if(['gf','gs'].includes(node.ty)&&node.g)mapearCorAnimada(node.g.k,cores=>{
  const r=cores.slice();for(let i=0;i<node.g.p;i++){const p=i*4+1;r.splice(p,3,...tonalidadeMao(cores.slice(p,p+3)));}return r;
 });
 for(const v of Object.values(node))if(v&&typeof v==='object')colorirMao(v);
}
function aplicarCorrecaoEmoji(d,codigo,modo){
 const config=CORRECOES_EMOJIS[codigo];if(!config||modo==='original')return;
 const composicoes={raiz:d.layers,...Object.fromEntries((d.assets||[]).filter(a=>a.layers).map(a=>[a.id,a.layers]))};
 for(const [nome,indices] of Object.entries(config.ocultar||{}))for(const l of composicoes[nome]||[]){if(indices.includes(l.ind)&&!l.td)l.ks.o={a:0,k:0};}
 if(modo==='ciano')for(const [nome,indices] of Object.entries(config.maos||{}))for(const l of composicoes[nome]||[]){if(indices.includes(l.ind))colorirMao(l.shapes);}
}
