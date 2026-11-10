/* Expressões locais: o modelo continua emitindo apenas os 12 climas. */
(() => {
 const pres=document.getElementById('presenca'),rosto=document.getElementById('rosto');
 if(!pres||!rosto||!window.lottie)return;
 const host=document.createElement('div');host.id='rosto-animado';host.setAttribute('aria-hidden','true');rosto.appendChild(host);
 const reduzido=matchMedia('(prefers-reduced-motion: reduce)');
 const climas={'ᗒᗜᗕ':'zoeira','Ò﹏Ó':'revolta','ಠ_ಠ':'facepalm','O_O':'choque','ᵔ ᵕ ᵔ':'carinho','╥‸╥':'cansaco','◞_◟':'cansaco','◉‿◉':'festa','ꈍ◡ꈍ':'orgulho','ㆆ_ㆆ':'suspeita','≖_≖':'suspeita','⚈₋⚈':'duvida','￢_￢':'tedio','T_T':'tristeza'};
 let grupos=null,player=null,geracao=0,chave='',ultimo='',timer=null,visivel=true;
 const cache=new Map(),recentes=new Map();
 const FACE_PONTE='1f642',PAUSA_NEUTRA_MS=400;
 let ponte=false;
 const esperar=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 async function carregar(codigo){
  if(!cache.has(codigo)){const r=await fetch('/static/rosto-animado/assets/'+codigo+'.json');if(!r.ok)throw Error(r.status);cache.set(codigo,await r.json());}
  return structuredClone(cache.get(codigo));
 }
 function categoria(txt,c){
  if(c.afk)return 'dormindo';
  if(c.gigante)return 'cliques';
  if(c.chacoalhando||txt==='಄ᆺ಄')return 'tonta';
  if(c.afago)return 'afago';
  if(c.esfregando)return 'limpeza';
  if(c.invasao)return 'invasao';
  if(c.medo)return 'susto';
  if(c.desistiu)return 'desistiu';
  if(c.reacao===txt&&climas[txt])return climas[txt];
  if(c.foguetes)return 'foguetes';
  if(c.satelites)return 'satelites';
  if(c.cometao)return 'impacto';
  if(c.sujeira)return 'sujeira';
  if(txt==='⌐■_■')return 'oculos';
  if(txt==='⇀‸↼')return 'radar';
  if(txt==='･ ᴗ ･')return 'ouvindo';
  if(txt==='◐_◑')return 'pensando';
  if(txt==='ᓀ‸ᓂ')return 'jogos';
  if(txt==='_　_ 💤')return 'dormindo';
  if(['ᗜ⩊ᗜ','•𐃷•','• ₃ •'].includes(txt))return c.jogo?'jogos':'repouso';
  if(txt==='◉‿◉')return 'alivio';
  if(['｀皿´','｀Д´','ᗒ_ᗕ','>_<'].includes(txt))return 'irritada';
  if(['≖_≖','• _ •','- _ -'].includes(txt))return 'encarada';
  return climas[txt]||'repouso';
 }
 function contexto(){return typeof contextoRostoAnimado==='function'?contextoRostoAnimado():{};}
 function podeAnimar(){return !document.hidden&&visivel&&!reduzido.matches;}
 function suspender(){if(!player)return;if(!ponte&&podeAnimar())player.play();else player.pause();}
 function fallback(){host.classList.remove('trocando');ponte=false;clearTimeout(timer);if(player)player.destroy();player=null;host.replaceChildren();rosto.classList.remove('com-rosto-animado');}
 function montar(d,codigo,cat,token,estatica=false){
  if(player)player.destroy();ponte=estatica;
  player=lottie.loadAnimation({container:host,renderer:'svg',loop:false,autoplay:false,animationData:d});
  const atual=player;host.dataset.categoria=cat;host.dataset.emoji=codigo;
  return new Promise(resolve=>{
   atual.addEventListener('DOMLoaded',()=>{
    if(token===geracao){
     rosto.classList.add('com-rosto-animado');host.classList.remove('trocando');
     const rest=d.markers?.find(m=>m.cm==='rest');
     if(!estatica&&podeAnimar())atual.play();else atual.goToAndStop(rest?.tm||0,true);
    }
    resolve();
   });
   atual.addEventListener('complete',()=>{if(!estatica&&token===geracao)timer=setTimeout(()=>{if(token===geracao&&podeAnimar())atual.goToAndPlay(0,true);},8000);});
   atual.addEventListener('data_failed',()=>{if(token===geracao){fallback();chave='';}resolve();});
  });
 }
 async function atualizar(txt){
  ultimo=txt||ultimo;if(!grupos||!ultimo)return;
  const c=contexto();
  // Piscadas do kaomoji não substituem a animação, que já tem seus próprios olhos.
  if(c.atual&&ultimo!==c.atual&&!c.afago&&!c.esfregando)return;
  const cat=categoria(ultimo,c),nova=cat+'|'+(c.atual||ultimo);
  if(nova===chave)return;chave=nova;const token=++geracao;
  const pool=grupos[cat]||grupos.repouso,anterior=recentes.get(cat);
  const opcoes=pool.filter(id=>id!==anterior);const op=opcoes.length?opcoes:pool;
  const codigo=op[Math.floor(Math.random()*op.length)];recentes.set(cat,codigo);
  clearTimeout(timer);
  try{
   const d=await carregar(codigo);
   if(token!==geracao)return;
   if(player){
    const neutra=FACE_PONTE,nd=await carregar(neutra);
    if(token!==geracao)return;
    host.classList.add('trocando');await esperar(reduzido.matches?0:100);
    if(token!==geracao)return;
    await montar(nd,neutra,'transicao',token,true);
    if(token!==geracao)return;
    await esperar(PAUSA_NEUTRA_MS);
    if(token!==geracao)return;
    host.classList.add('trocando');await esperar(reduzido.matches?0:100);
    if(token!==geracao)return;
   }
   await montar(d,codigo,cat,token);
  }catch{if(token===geracao){fallback();chave='';}}
 }
 window.lunaRostoAnimado={atualizar};
 new MutationObserver(()=>atualizar(contexto().atual||ultimo)).observe(pres,{attributes:true,attributeFilter:['class']});
 document.addEventListener('visibilitychange',suspender);reduzido.addEventListener('change',suspender);
 if(typeof IntersectionObserver!=='undefined')new IntersectionObserver(entries=>{visivel=entries[0].isIntersecting;suspender();}).observe(pres);
 fetch('/static/rosto-animado/catalogo.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{grupos=d.grupos;atualizar(contexto().atual||document.getElementById('rosto-txt').textContent);}).catch(fallback);
})();
