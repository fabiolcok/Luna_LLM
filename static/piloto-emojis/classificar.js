'use strict';
const el=id=>document.getElementById(id),chave='luna-piloto-classificacao-v1';
const grupos={
 'Tom da resposta':[['zoeira','Zoeira'],['revolta','Revolta'],['facepalm','Sem paciência'],['choque','Choque'],['carinho','Carinho'],['cansaco','Cansaço'],['festa','Festa'],['orgulho','Orgulho'],['suspeita','Suspeita'],['duvida','Dúvida'],['tedio','Tédio'],['tristeza','Tristeza']],
 'Estados da interface':[['repouso','Padrão / repouso'],['jogos','Jogos / concentrada'],['pensando','Pensando'],['dormindo','Ausente / dormindo'],['ouvindo','Ouvindo'],['radar','Radar / pesquisando']],
 'Easter eggs e interações':[['cliques','Cliques repetidos / cara aumentando'],['foguetes','Foguetes incomodando'],['satelites','Satélites incomodando'],['impacto','Cometão / impacto'],['sujeira','Fuligem / suja'],['limpeza','Durante a limpeza'],['invasao','Invasão / medo'],['desistiu','Desistiu / ignorando'],['susto','Susto / medo'],['irritada','Irritada / incomodada'],['tonta','Tonta / chacoalhada'],['alivio','Problema resolvido / alívio'],['afago','Carinho / afago'],['encarada','Encarando'],['oculos','Óculos / eclipse']],
 'Especiais · acionamento a definir':[['doente','Doente'],['machucada','Machucada'],['dinheiro','Dinheiro']],
 'Fora da seleção automática':[['reservada','Reservada / não usar agora']]
};
let base={},itens=[],atual=null,registros={};try{registros=JSON.parse(localStorage.getItem(chave)||'{}');}catch{}
const norm=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function salvar(){try{localStorage.setItem(chave,JSON.stringify(registros));}catch{el('progresso').textContent='Não foi possível salvar no navegador. Exporte antes de fechar.';return;}listar();}
function filtrados(){const cat=el('filtro-categoria').value;return itens.filter(i=>norm(i.name+' '+i.emoji).includes(norm(el('buscar').value))&&(!el('pendentes').checked||!registros[i.code]?.revisada)&&(!cat||(cat==='sem_categoria'?!registros[i.code]?.categorias?.length:registros[i.code]?.categorias?.includes(cat))));}
function atualizarFiltro(){
 const select=el('filtro-categoria'),valor=select.value;select.replaceChildren();
 const opcao=(pai,id,nome,n)=>{const o=document.createElement('option');o.value=id;o.textContent=nome+' ('+n+')';pai.append(o);};
 opcao(select,'','Todas',itens.length);opcao(select,'sem_categoria','Sem categoria',itens.filter(i=>!registros[i.code]?.categorias?.length).length);
 for(const [nome,categorias] of Object.entries(grupos)){const grupo=document.createElement('optgroup');grupo.label=nome;for(const [id,label] of categorias)opcao(grupo,id,label,itens.filter(i=>registros[i.code]?.categorias?.includes(id)).length);select.append(grupo);}
 select.value=valor;
}
function listar(){atualizarFiltro();el('lista').replaceChildren();for(const i of filtrados()){const b=document.createElement('button'),s=document.createElement('span');s.textContent=i.emoji;b.append(s,document.createTextNode(i.name+(registros[i.code]?.revisada?' ✓':'')+(base[i.code]?.problema?' ⚠':'')));b.setAttribute('aria-pressed',String(atual?.code===i.code));b.onclick=()=>selecionar(i);el('lista').append(b);}if(!filtrados().length)el('lista').textContent='Nenhuma expressão neste filtro.';el('progresso').textContent=itens.filter(i=>registros[i.code]?.revisada).length+' de '+itens.length+' revisadas';}
function selecionar(i){atual=i;const r=registros[i.code]||{};el('titulo').textContent=i.emoji+' '+i.name;el('nota').value=r.nota||'';el('revisada').checked=!!r.revisada;el('categorias').replaceChildren();
 for(const [nome,opcoes] of Object.entries(grupos)){const f=document.createElement('fieldset'),l=document.createElement('legend');l.textContent=nome;f.append(l);for(const [id,titulo] of opcoes){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=id;input.checked=!!r.categorias?.includes(id);input.onchange=gravar;label.append(input,document.createTextNode(' '+titulo));f.append(label);}el('categorias').append(f);}
 const p=base[i.code]?.problema;el('problemas').textContent=p?'⚠ Revisar visual: '+[...(p.tipos||[]).map(t=>({cabeca:'cabeça aparecendo',cor:'cor estranha',outro:'outro problema'}[t]||t)),p.nota].filter(Boolean).join(' · '):'★ Favorita · sem problema visual registrado';
 el('preview').contentWindow.postMessage({tipo:'piloto-selecionar',codigo:i.code},location.origin);listar();
}
function gravar(evento){if(!atual)return;
 const inputs=Array.from(el('categorias').querySelectorAll('input'));
 if(evento?.target?.checked&&evento.target.value==='reservada')inputs.forEach(x=>{if(x.value!=='reservada')x.checked=false;});
 else if(evento?.target?.checked&&inputs.includes(evento.target))inputs.forEach(x=>{if(x.value==='reservada')x.checked=false;});
 registros[atual.code]={categorias:inputs.filter(x=>x.checked).map(x=>x.value),nota:el('nota').value,revisada:el('revisada').checked};salvar();}
function atualizarOrganizacao(exportado){
 for(const i of exportado.expressoes){if(!registros[i.codigo])registros[i.codigo]={categorias:i.categorias||[],nota:i.nota||'',revisada:!!i.revisada};}
 if(localStorage.getItem(chave+'-organizacao-2'))return;
 localStorage.setItem(chave+'-backup-antes-organizacao-2',JSON.stringify(registros));
 const adicionar=(codigo,...cats)=>{const r=registros[codigo];if(r)r.categorias=[...new Set([...r.categorias,...cats])];};
 for(const r of Object.values(registros))r.categorias=r.categorias.filter(c=>!['falando','digitando','easter_eggs','disfarce'].includes(c));
 for(const codigo of ['1f978','1f92b','1f910','1f924'])registros[codigo].categorias=['reservada'];
 for(const codigo of ['1f642','1f60a','1f60c'])adicionar(codigo,'repouso');
 for(const codigo of ['1f9d0','1f914'])adicionar(codigo,'radar');
 adicionar('1f92c','cliques');registros['1f92c'].categorias=registros['1f92c'].categorias.filter(c=>c!=='irritada');
 for(const codigo of ['1f624','1f620'])adicionar(codigo,'foguetes','satelites');
 adicionar('1f635','tonta');
 for(const codigo of ['1f62c','1f616','1f623'])adicionar(codigo,'impacto');
 adicionar('1f612','sujeira');adicionar('1f60c','limpeza');
 for(const codigo of ['1fae3','1fae2'])adicionar(codigo,'invasao','susto');
 adicionar('1f636','desistiu');adicionar('1f61e','desistiu','tristeza');
 adicionar('1f642','alivio');adicionar('1f92a','zoeira');adicionar('1f92d','zoeira','choque');adicionar('1fae2','choque');
 for(const codigo of ['1f616','1f623'])adicionar(codigo,'irritada');
 localStorage.setItem(chave,JSON.stringify(registros));localStorage.setItem(chave+'-organizacao-2','1');
}
el('nota').oninput=gravar;el('revisada').onchange=gravar;el('buscar').oninput=listar;el('pendentes').onchange=listar;
el('filtro-categoria').onchange=listar;
function navegar(delta){const f=filtrados();if(!f.length)return;const idx=f.findIndex(i=>i.code===atual?.code);selecionar(f[idx<0?0:(idx+delta+f.length)%f.length]);}
el('anterior').onclick=()=>navegar(-1);el('proximo').onclick=()=>navegar(1);
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===el('preview').contentWindow&&e.data?.tipo==='piloto-pronto'&&atual)el('preview').contentWindow.postMessage({tipo:'piloto-selecionar',codigo:atual.code},location.origin);});
el('exportar-classificacao').onclick=()=>{const resultado={versao:2,tipo:'classificacao_expressoes',escala:75,regras:{falando:'manter_expressao_da_resposta',digitando:'usar_pensando',reservada:'fora_da_selecao_automatica',especiais:'acionamento_a_definir'},categorias:grupos,expressoes:itens.map(i=>({codigo:i.code,nome:i.name,emoji:i.emoji,...base[i.code],categorias:registros[i.code]?.categorias||[],nota:registros[i.code]?.nota||'',revisada:!!registros[i.code]?.revisada}))};const url=URL.createObjectURL(new Blob([JSON.stringify(resultado,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='luna-classificacao-expressoes.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
Promise.all([fetch('catalogo.json').then(r=>r.json()),fetch('selecao-base.json').then(r=>r.json()),fetch('classificacao-base.json').then(r=>r.json())]).then(([catalogo,selecao,classificacao])=>{base=selecao.escolhas;itens=catalogo.filter(i=>base[i.code]?.favorita||base[i.code]?.problema);atualizarOrganizacao(classificacao);listar();if(itens.length){el('preview').src='index.html?embed=1&escala=75&emoji='+itens[0].code;selecionar(itens[0]);}}).catch(()=>{el('progresso').textContent='Não foi possível carregar sua seleção. Recarregue a página.';});
