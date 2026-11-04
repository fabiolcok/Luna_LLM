(() => {
    const menu=document.getElementById('menu-atalhos-itens'); if(!menu) return;
    const criar=(tag,texto)=>{const e=document.createElement(tag);if(texto)e.textContent=texto;return e;};
    const botao=(texto,fn)=>{const b=criar('button',texto);b.type='button';b.onclick=fn;return b;};
    let conectado=false;
    const envios=new Map();
    const painel=criar('dialog');painel.className='discord-dialog';
    const status=criar('p');status.setAttribute('role','status');
    const erro=criar('p');erro.setAttribute('role','alert');
    const entrar=botao('Entrar no canal',()=>agir({acao:'conectar'}));
    const sair=botao('Sair do canal',()=>agir({acao:'desconectar'}));
    const jogos=criar('input');jogos.type='checkbox';jogos.onchange=()=>agir({acao:'jogos',valor:jogos.checked});
    const label=criar('label');label.append(jogos,document.createTextNode(' Compartilhar comentários dos jogos'));
    painel.append(botao('Fechar',()=>painel.close()),criar('h2','Voz no Discord'),status,erro,entrar,sair,label,
        criar('p','A Luna só transmite voz. Escolha uma resposta no chat para compartilhar. Avisos pessoais continuam locais.'),
        criar('p','Configuração inicial: consulte integracoes/discord/README.md no projeto.'));
    document.body.appendChild(painel);
    const abrirDiscord=botao('',()=>{painel.showModal();atualizar();});
    abrirDiscord.setAttribute('aria-label','Discord');
    abrirDiscord.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex-shrink:0"><path d="M4 13v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="12" width="4" height="8" rx="2"/><rect x="17" y="12" width="4" height="8" rx="2"/></svg>';
    menu.prepend(abrirDiscord);
    async function agir(dados, local) {
        erro.textContent='';
        if(local){local.textContent='Enviando…';local.previousElementSibling.disabled=true;}
        try {
            const r=await fetch('/api/discord-voz',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(dados)});
            const d=await r.json();if(!r.ok)throw new Error(d.erro || 'Não foi possível executar.');mostrar(d);
            if(local){envios.set(d.envio_id,local);local.textContent='Na fila…';mostrar(d);}
        }catch(e){if(local){local.textContent=e.message;local.previousElementSibling.disabled=false;}else erro.textContent=e.message;}
    }
    function mostrar(d) {
        conectado=d.estado==='conectado';
        status.textContent= d.mensagem || (conectado ? 'Conectada a '+d.canal : d.estado==='conectando' ? 'Conectando…' : 'Desconectada');
        if(!d.configurado)status.textContent='Discord não configurado. Preencha o token e o canal no .env.';
        else if(!d.instalado)status.textContent='Instale as dependências opcionais do Discord.';
        entrar.disabled=!d.configurado || !d.instalado || ['conectado','conectando','desligando'].includes(d.estado);
        sair.disabled=!['conectado','conectando'].includes(d.estado);
        jogos.checked=d.jogos; jogos.disabled=!conectado;
        for(const [id,local] of envios){
            const mensagem=d.envios && d.envios[id];
            if(mensagem)local.textContent=mensagem;
            if(!conectado || !mensagem || /finalizada|Falha/.test(mensagem)){
                if(!conectado)local.textContent='Discord desconectado.';
                local.previousElementSibling.disabled=false;envios.delete(id);
            }
        }
        montar();
    }
    function montar() {
        document.querySelectorAll('.turno[data-turno-id]').forEach(t=>{
            const luna=t.querySelector('.turno-luna');if(!luna)return;
            let b=luna.querySelector('.discord-compartilhar');
            if(!b && conectado){
                const linha=criar('div');linha.style.cssText='display:flex;align-items:center;gap:8px;flex-wrap:wrap';
                const mini=criar('span');mini.className='discord-envio-status';mini.setAttribute('role','status');
                mini.style.cssText='font-size:12px;opacity:.8';
                b=botao('Falar no Discord',()=>agir({acao:'falar',turno_id:t.dataset.turnoId},mini));
                b.className='discord-compartilhar';linha.append(b,mini);luna.appendChild(linha);
            }
            if(b)b.hidden=!conectado;
        });
    }
    async function atualizar(){try{const r=await fetch('/api/discord-voz');if(!r.ok)throw new Error();mostrar(await r.json());}catch{status.textContent='Não foi possível consultar o Discord.';conectado=false;montar();}}
    const alvo=document.getElementById('historico-lista');
    if(alvo)new MutationObserver(montar).observe(alvo,{childList:true});
    setInterval(()=>{if(painel.open || conectado)atualizar();},3000);
    atualizar();
})();
