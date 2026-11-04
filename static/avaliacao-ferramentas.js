/* Votos de ações ficam presos ao turno, mesmo com novas mensagens chegando. */
(() => {
    let itens = [], carregando = false, timer;
    const nomes = {controlar_spotify: '🎵 Spotify usado', consultar_biblioteca_steam: '🎮 Steam usado',
        ler_agenda_google: '📅 Agenda usada', salvar_obsidian: '📝 Obsidian usado',
        ler_obsidian: '📝 Obsidian usado', pesquisar_web: '🔎 Busca usada'};
    const motivos = {desnecessaria: 'Não era para chamar', ferramenta_errada: 'Ferramenta errada',
        parametros_errados: 'Dados errados', resultado_errado: 'Resultado diferente do esperado',
        faltou_ferramenta: 'Faltou executar uma ação'};
    const el = (tag, texto, classe) => {const n = document.createElement(tag); if (texto) n.textContent = texto; if (classe) n.className = classe; return n;};
    const botao = (texto, acao) => {const b = el('button', texto); b.type = 'button'; b.onclick = acao; return b;};
    const menu = document.getElementById('menu-atalhos-itens');
    if (!menu) return;
    const abrir = botao('', () => {renderLista(); dialog.showModal();});
    abrir.setAttribute('aria-label','Avaliações pendentes');
    abrir.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex-shrink:0"><rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="m8 13 3 3 5-6"/></svg>';
    const acompanhamentos = menu.querySelector('#btn-acompanhamentos');
    if (acompanhamentos) acompanhamentos.after(abrir);
    else menu.appendChild(abrir);
    const dialog = el('dialog', '', 'af-dialog');
    const lista = el('div');
    dialog.append(botao('Fechar', () => dialog.close()), el('h2', 'Avaliações pendentes'), lista);
    document.body.appendChild(dialog);

    async function votar(item, rating, motivo, comentario, status) {
        status.textContent = 'Salvando…';
        try {
            const r = await fetch('/api/avaliacoes-ferramentas', {method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({turno_id:item.turno_id, rating, motivo, comentario})});
            if (!r.ok) throw new Error();
            const d = await r.json();
            itens = itens.filter(i => i.turno_id !== item.turno_id).concat(d.item);
            document.querySelectorAll('.af-linha').forEach(n => {if(n.dataset.turnoId === item.turno_id) n.replaceWith(linha(d.item));});
            atualizarContagem(); renderLista();
        } catch {status.textContent = 'Não foi salvo. Tente novamente.';}
    }
    function linha(item, ausente=false) {
        const box = el('div', '', 'af-linha'); box.dataset.turnoId = item.turno_id;
        const nome = item.ferramenta?.nome;
        if (nome) box.appendChild(el('span', nomes[nome] || nome.replaceAll('_', ' ') + ' usado'));
        if (item.voto) {box.appendChild(el('span','✓ Avaliado')); return box;}
        const status = el('span'); status.setAttribute('role','status');
        function negativo() {
            if (box.querySelector('select')) return;
            const campos = el('div', '', 'af-form'); const select = el('select'); select.setAttribute('aria-label','Motivo da avaliação');
            for (const [valor, nome] of Object.entries(motivos)) {
                if (ausente !== (valor === 'faltou_ferramenta')) continue;
                const o = el('option', nome); o.value = valor; select.appendChild(o);
            }
            const texto = el('textarea'); texto.placeholder='Comentário opcional'; texto.maxLength=1000;
            texto.setAttribute('aria-label','Comentário opcional');
            campos.append(select, texto, botao('Salvar avaliação',()=>votar(item,'ruim',select.value,texto.value,status)), botao('Cancelar',()=>campos.remove()));
            box.appendChild(campos);
        }
        if (ausente) box.appendChild(botao('Faltou executar uma ação',negativo));
        else {
            const votos=el('span', '', 'af-votos');
            const sim=botao('👍',()=>votar(item,'bom','','',status)), nao=botao('👎',negativo);
            sim.setAttribute('aria-label','A ação foi correta'); nao.setAttribute('aria-label','A ação foi incorreta');
            votos.append(sim,nao); box.append(el('span','Foi o que você pediu?'),votos);
        }
        box.appendChild(status); return box;
    }
    function detalhes(item) {
        const d=el('details'), pre=el('pre'); d.appendChild(el('summary','Detalhes da ação'));
        const f=item.ferramenta || {};
        pre.textContent = `Ferramenta: ${f.nome || 'Nenhuma registrada'}\nParâmetros: ${JSON.stringify(f.argumentos ?? {},null,2)}\nEstado: ${f.sucesso === true ? 'Concluiu segundo o retorno' : f.sucesso === false ? 'Falhou segundo o retorno' : 'Não informado'}\nTempo da ferramenta: ${f.segundos ?? 'não informado'} s\n`;
        for (const c of item.chamadas || []) pre.textContent += `${c.etapa || 'Chamada'}: ${c.modelo} · thinking ${c.thinking === true ? 'ligado' : c.thinking === false ? 'desligado' : 'não informado'}\n`;
        d.appendChild(pre); return d;
    }
    function renderLista() {
        lista.replaceChildren();
        const pendentes=itens.filter(i=>!i.voto && i.ferramenta);
        if (!pendentes.length) lista.appendChild(el('p','Nenhuma avaliação pendente.'));
        for(const i of pendentes.slice().reverse()) {
            const card=el('article'); card.append(el('p',i.usuario || 'Comentário proativo'),el('p',i.luna),detalhes(i),linha(i)); lista.appendChild(card);
        }
    }
    function atualizarContagem() {abrir.setAttribute('aria-label','Avaliações pendentes · '+itens.filter(i=>!i.voto && i.ferramenta).length);}
    function montar() {
        document.querySelectorAll('.turno[data-turno-id]').forEach(t=>{
            const balao=t.querySelector('.turno-luna'); if(!balao || balao.querySelector('.af-linha')) return;
            const id=t.dataset.turnoId, item=itens.find(i=>i.turno_id===id);
            if(item) {balao.append(linha(item),detalhes(item));}
            else {const d=el('details');d.append(el('summary','Avaliar ação'),linha({turno_id:id},true));balao.appendChild(d);}
        }); atualizarContagem();
    }
    async function atualizar() {
        if(carregando) return; carregando=true;
        try {const r=await fetch('/api/avaliacoes-ferramentas'); if(!r.ok) throw new Error(); itens=(await r.json()).itens; montar();}
        catch {abrir.setAttribute('aria-label','Avaliações indisponíveis');}
        finally {carregando=false;}
    }
    const alvo=document.getElementById('historico-lista');
    if(alvo) new MutationObserver(ms=>{if(ms.some(m=>Array.from(m.addedNodes).some(n=>n.nodeType===1 && n.classList.contains('turno')))) {clearTimeout(timer);timer=setTimeout(atualizar,150);}}).observe(alvo,{childList:true});
    atualizar(); abrir.addEventListener('click',atualizar);
})();
