'use strict';
const $=id=>document.getElementById(id);
let catalogo=[],atual=null,dados=null,player=null,geracao=0,pausado=matchMedia('(prefers-reduced-motion: reduce)').matches;
let escolhas={};try{escolhas=JSON.parse(localStorage.getItem('luna-piloto-emojis')||'{}');}catch{}
const salvar=()=>{try{localStorage.setItem('luna-piloto-emojis',JSON.stringify(escolhas));}catch{$('status').textContent='Não foi possível salvar neste navegador. Use Exportar escolhas.';}};
const normalizar=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function padraoCamada(l){return !(/base|background|head|cabe[cç]a/i.test(l.nm||'')&&!/matte/i.test(l.nm||'')&&l.ty!==3);}
function chave(l,i){return i+':'+l.ind;}
function camadasEditaveis(d){return (d.layers||[]).map((l,i)=>({l,i})).filter(({l})=>[0,1,2,4].includes(l.ty)&&!l.td&&!/matte/i.test(l.nm||''));}
function corCiano(node){
 if(!node||typeof node!=='object')return;
 if(['fl','st'].includes(node.ty)&&node.c&&node.c.a===0){const c=node.c.k;if(Array.isArray(c)&&c.length>=3&&Math.max(...c.slice(0,3))<.65)node.c.k=[.706,.976,.973,...c.slice(3)];}
 for(const value of Object.values(node))if(value&&typeof value==='object')corCiano(value);
}
function renderizar(){
 if(!dados)return;
 if(player)player.destroy();
 const d=structuredClone(dados),modo=$('modo').value,config=escolhas[atual.code]||{};
 if(modo!=='original'){
  for(const {l,i} of camadasEditaveis(d)){const mostrar=config.camadas?.[chave(l,i)]??padraoCamada(l);if(!mostrar&&l.ks)l.ks.o={a:0,k:0};}
  if(modo==='ciano')corCiano(d);
  if($('aplicar-correcoes').checked){
   // Recolorir mãos a partir das cores originais conserva a diferença entre
   // contornos, sombras e superfícies, perdida na conversão genérica.
   const original=structuredClone(dados);aplicarCorrecaoEmoji(original,atual.code,modo);
   const maos=CORRECOES_EMOJIS[atual.code]?.maos||{};
   if(modo==='ciano')for(const [comp,ids] of Object.entries(maos)){
    const source=comp==='raiz'?original.layers:original.assets.find(a=>a.id===comp).layers;
    const dest=comp==='raiz'?d.layers:d.assets.find(a=>a.id===comp).layers;
    for(const l of dest)if(ids.includes(l.ind))l.shapes=source.find(x=>x.ind===l.ind).shapes;
   }
   aplicarCorrecaoEmoji(d,atual.code,'face');
  }
 }
 $('expressao').classList.toggle('ciano',modo==='ciano');
 player=lottie.loadAnimation({container:$('expressao'),renderer:'svg',loop:$('loop').checked,autoplay:!pausado,animationData:d,rendererSettings:{progressiveLoad:false}});
 player.setSpeed(Number($('velocidade').value));
 player.addEventListener('data_failed',()=>{$('status').textContent='Não foi possível renderizar esta animação.';});
 $('play').textContent=pausado?'Reproduzir':'Pausar';
 $('status').textContent=modo==='original'?'Referência original do Google.':'Adaptação experimental · confira o resultado e ajuste as partes abaixo.';
 if(modo!=='original'&&CORRECOES_EMOJIS[atual.code])$('status').textContent=$('aplicar-correcoes').checked?'Correção aplicada · aguardando sua revisão visual.':'Antes da correção · comparação.';
}
function listarCamadas(){
 $('camadas').replaceChildren();
 for(const {l,i} of camadasEditaveis(dados)){
  const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';
  input.checked=escolhas[atual.code]?.camadas?.[chave(l,i)]??padraoCamada(l);
  input.onchange=()=>{const c=escolhas[atual.code]??={};c.camadas??={};c.camadas[chave(l,i)]=input.checked;salvar();renderizar();};
  label.append(input,document.createTextNode(l.nm||'Parte '+i));$('camadas').append(label);
 }
}
async function selecionar(item){
 atual=item;dados=null;const token=++geracao;if(player){player.destroy();player=null;}
 $('nome').textContent=item.emoji+' '+item.name;$('status').textContent='Carregando expressão…';
 $('camadas').replaceChildren();atualizarFavorito();atualizarProblema();galeria();
 try{const r=await fetch('assets/'+item.code+'.json');if(!r.ok)throw Error(r.status);const d=await r.json();if(token!==geracao)return;dados=d;listarCamadas();renderizar();}
 catch(e){if(token===geracao)$('status').textContent='Falha ao carregar esta expressão. Tente outra.';}
}
function filtrados(){const q=normalizar($('busca').value);return catalogo.filter(e=>e.available&&normalizar(e.name+' '+e.emoji).includes(q)&&(!$('so-favoritas').checked||escolhas[e.code]?.favorita)&&(!$('so-problemas').checked||escolhas[e.code]?.problema)&&(!$('so-corrigidos').checked||CORRECOES_EMOJIS[e.code]));}
function galeria(){
 const lista=filtrados();$('galeria').replaceChildren();$('contagem').textContent=lista.length+' expressões';
 for(const item of lista){const b=document.createElement('button');b.className='emoji-item';b.setAttribute('aria-pressed',String(atual?.code===item.code));b.title=item.name;
  for(const text of [item.emoji,item.name+(escolhas[item.code]?.problema?' · ⚠':'')]){const s=document.createElement('span');s.textContent=text;b.append(s);}b.onclick=()=>selecionar(item);$('galeria').append(b);}
 if(!lista.length)$('galeria').textContent='Nenhuma expressão encontrada.';
}
function atualizarFavorito(){const fav=!!escolhas[atual?.code]?.favorita;$('favorito').textContent=fav?'★ Favorita':'☆ Marcar favorita';$('favorito').setAttribute('aria-pressed',String(fav));}
function atualizarProblema(){
 const p=escolhas[atual?.code]?.problema;
 $('problema').textContent=p?'⚠ Problema marcado · desmarcar':'⚠ Marcar problema';
 $('problema').setAttribute('aria-pressed',String(!!p));$('problema').setAttribute('aria-expanded',String(!!p));
 $('problema-opcoes').hidden=!p;
 document.querySelectorAll('[data-problema]').forEach(b=>b.checked=!!p?.tipos?.includes(b.dataset.problema));
 $('problema-nota').value=p?.nota||'';
}
function salvarProblema(){
 if(!atual||!escolhas[atual.code]?.problema)return;
 escolhas[atual.code].problema={tipos:Array.from(document.querySelectorAll('[data-problema]:checked'),b=>b.dataset.problema),nota:$('problema-nota').value,modo:$('modo').value,escala:Number($('escala').value)};
 salvar();
}
document.querySelectorAll('[data-problema]').forEach(b=>b.onchange=salvarProblema);
$('problema-nota').oninput=salvarProblema;
$('problema').onclick=()=>{
 if(!atual)return;const c=escolhas[atual.code]??={};
 if(c.problema)delete c.problema;else c.problema={tipos:[],nota:'',modo:$('modo').value,escala:Number($('escala').value)};
 salvar();atualizarProblema();galeria();
};
function navegar(passo){const lista=filtrados();if(!lista.length)return;const i=lista.findIndex(x=>x.code===atual?.code);selecionar(lista[(i+passo+lista.length)%lista.length]);}
$('busca').oninput=galeria;$('so-favoritas').onchange=galeria;$('so-problemas').onchange=galeria;
$('so-corrigidos').onchange=galeria;$('aplicar-correcoes').onchange=renderizar;
$('anterior').onclick=()=>navegar(-1);$('proximo').onclick=()=>navegar(1);
$('play').onclick=()=>{pausado=!pausado;if(player)pausado?player.pause():player.play();$('play').textContent=pausado?'Reproduzir':'Pausar';};
$('repetir').onclick=()=>{if(player){pausado=false;player.goToAndPlay(0,true);$('play').textContent='Pausar';}};
$('modo').onchange=renderizar;$('velocidade').onchange=()=>player?.setSpeed(Number($('velocidade').value));$('loop').onchange=()=>{if(player)player.loop=$('loop').checked;};
$('escala').oninput=()=>{const v=$('escala').value+'%';$('expressao').style.width=v;$('expressao').style.height=v;$('escala-valor').textContent=v;};
$('estado').onchange=()=>{$('presenca').className='est-'+$('estado').value;};
$('favorito').onclick=()=>{if(!atual)return;const c=escolhas[atual.code]??={};c.favorita=!c.favorita;salvar();atualizarFavorito();galeria();};
$('restaurar').onclick=()=>{if(!atual)return;delete escolhas[atual.code]?.camadas;salvar();listarCamadas();renderizar();};
$('exportar').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({versao:1,escolhas},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='luna-expressoes-piloto.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
async function iniciar(){
 const [c,s]=await Promise.all([fetch('catalogo.json'),fetch('avatar.svg')]);if(!c.ok||!s.ok)throw Error('Arquivos indisponíveis');catalogo=await c.json();$('corpo').innerHTML=await s.text();
 // Geometria estática do piloto: não executa o chat nem os easter eggs da produção.
 for(const [id,r,inicio,fim] of [['arco-1',60,20,210],['arco-2',53,80,240],['arco-3',45,140,290]]){const p=a=>[100+r*Math.cos(a*Math.PI/180),100+r*Math.sin(a*Math.PI/180)];const a=p(inicio),b=p(fim);$(id)?.setAttribute('d',`M${a} A${r} ${r} 0 ${fim-inicio>180?1:0} 1 ${b}`);}
 for(let i=0;i<10;i++){const dot=document.createElementNS('http://www.w3.org/2000/svg','circle'),a=i*Math.PI/5;dot.setAttribute('cx',100+81*Math.cos(a));dot.setAttribute('cy',100+81*Math.sin(a));dot.setAttribute('r',i%3===0?1.7:1);dot.setAttribute('fill','#b4f9f8');dot.setAttribute('opacity','.4');$('orbita')?.append(dot);}
 const params=new URLSearchParams(location.search);
 if(params.get('embed')==='1')document.body.classList.add('embed');
 const escala=Number(params.get('escala')||75);
 $('escala').value=String(Math.max(40,Math.min(90,escala)));$('escala').oninput();
 galeria();await selecionar(catalogo.find(x=>x.code===params.get('emoji'))||catalogo.find(x=>x.code==='1f978')||catalogo[0]);
 if(params.get('embed')==='1')parent.postMessage({tipo:'piloto-pronto'},location.origin);
}
window.addEventListener('message',e=>{
 if(e.origin!==location.origin||e.source!==parent||e.data?.tipo!=='piloto-selecionar')return;
 const item=catalogo.find(x=>x.code===e.data.codigo);if(item)selecionar(item);
});
iniciar().catch(()=>{$('status').textContent='Abra esta página pelo endereço local da Luna para carregar os arquivos.';});
