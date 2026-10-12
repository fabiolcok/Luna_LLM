// A consulta tem seu próprio estado: abrir a biblioteca não mexe no turno nem no rascunho.
var consultaWebEstado = {modo: 'itens', pagina: 0, pedido: 0, timer: null, resposta: null};

function obterRespostaSelecionada() { return consultaWebEstado.resposta; }

function selecionarResposta(referencia, trecho) {
    consultaWebEstado.resposta = referencia;
    document.getElementById('resposta-selecionada-texto').textContent = String(trecho || '').slice(0, 160);
    document.getElementById('resposta-selecionada').hidden = false;
    fecharConsultaWeb();
    document.getElementById('texto-input').focus();
}

function limparRespostaSelecionada(referencia) {
    // O envio anterior não pode apagar outra referência escolhida enquanto o ACK chegava.
    if (referencia && referencia !== consultaWebEstado.resposta) return;
    consultaWebEstado.resposta = null;
    document.getElementById('resposta-selecionada').hidden = true;
}

function fecharConsultaWeb() {
    const dialogo = document.getElementById('consulta-web');
    if (dialogo.open) dialogo.close();
    ++consultaWebEstado.pedido;
}

function abrirBiblioteca(tipo='') {
    abrirConsultaWeb('itens', tipo);
}

function abrirConsultaWeb(modo, tipo='') {
    const dialogo = document.getElementById('consulta-web');
    consultaWebEstado.modo = modo;
    dialogo.classList.toggle('consulta-biblioteca', modo !== 'historico');
    const fechar = document.getElementById('consulta-fechar');
    fechar.textContent = modo === 'historico' ? '✕' : '← Voltar à conversa';
    fechar.setAttribute('aria-label', modo === 'historico' ? 'Fechar busca de conversas' : 'Voltar à conversa');
    document.getElementById('consulta-titulo').textContent = modo === 'historico' ? 'Conversas salvas' : 'Notícias e promoções';
    document.getElementById('consulta-busca').value = '';
    document.getElementById('consulta-busca').placeholder = modo === 'historico' ? 'Buscar nas conversas…' : 'Buscar por título, fonte ou assunto…';
    document.getElementById('consulta-filtros').hidden = modo === 'historico';
    document.getElementById('consulta-tipo').value = tipo;
    document.getElementById('consulta-leitura').value = '';
    document.getElementById('consulta-dica').textContent = modo === 'historico'
        ? 'Busca também nas conversas anteriores disponíveis no histórico local. Trechos recuperados do log podem estar incompletos.'
        : 'Os itens coletados pelo radar ficam aqui. Abrir o painel não os marca como lidos.';
    if (!dialogo.open) dialogo.showModal();
    document.getElementById('consulta-busca').focus();
    carregarConsultaWeb();
}

function dataConsultaWeb(data) {
    const valor = new Date(data || '');
    return Number.isNaN(valor.getTime()) ? '' : valor.toLocaleString('pt-BR',
        {day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'});
}

function criarBotaoConsulta(rotulo, acao) {
    const botao = document.createElement('button');
    botao.type = 'button'; botao.textContent = rotulo; botao.onclick = acao;
    return botao;
}

function criarResultadoConversa(turno) {
    const item = document.createElement('article'); item.className = 'consulta-conversa';
    const data = document.createElement('span'); data.className = 'consulta-data';
    data.textContent = dataConsultaWeb(turno.data) + (turno.incompleto ? ' · Trecho recuperado do log' : '');
    const pergunta = document.createElement('p'); pergunta.className = 'consulta-pergunta';
    pergunta.textContent = turno.usuario || 'Luna · comentário proativo';
    const resposta = document.createElement('div'); resposta.className = 'mensagem-conteudo';
    resposta.innerHTML = renderizarMarkdownSeguro(turno.luna || '');
    const acoes = document.createElement('div'); acoes.className = 'consulta-acoes';
    acoes.appendChild(criarBotaoConsulta('Responder', () => selecionarResposta({turno_id: turno.id}, turno.luna)));
    const naConversa = Array.from(document.getElementById('historico-lista').children)
        .find(el => el.dataset.turnoId === turno.id);
    if (naConversa) acoes.appendChild(criarBotaoConsulta('Ir à mensagem', () => {
        fecharConsultaWeb(); naConversa.scrollIntoView({block: 'center', behavior: 'smooth'});
        naConversa.classList.add('turno-localizado');
        setTimeout(() => naConversa.classList.remove('turno-localizado'), 1800);
    }));
    item.append(data, pergunta, resposta, acoes);
    return item;
}

async function marcarItemConsulta(item, lido) {
    const resposta = await fetch('/api/biblioteca/' + encodeURIComponent(item.id) + '/leitura', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({lido})
    });
    if (!resposta.ok) throw new Error('Não consegui salvar a leitura. Tente novamente.');
}

function criarItemBiblioteca(item) {
    const card = criarCartaoWeb(item);
    if (!card) return null;
    if (item.tipo === 'noticia') {
        const rotulo = card.querySelector('.cartao-web-rotulo');
        if (rotulo) rotulo.remove();
    }
    // Na biblioteca já estamos vendo todas; o atalho para abrir o próprio painel seria redundante.
    const todas = card.querySelector('.cartao-noticia-todas');
    if (todas) todas.remove();
    card.classList.toggle('biblioteca-nao-lida', !item.lido);
    const status = document.createElement('span'); status.className = 'consulta-data';
    status.textContent = (item.lido ? 'Lida' : 'Não lida') + ' · ' + dataConsultaWeb(item.data);
    card.insertBefore(status, card.firstChild);
    const acoes = card.querySelector('.cartao-web-acoes');
    if (item.resumo) {
        const resumo = document.createElement('p'); resumo.className = 'consulta-resumo'; resumo.textContent = item.resumo;
        card.insertBefore(resumo, acoes);
    }
    const feedback = document.createElement('span'); feedback.className = 'consulta-feedback'; feedback.setAttribute('role', 'status');
    const leitura = criarBotaoConsulta(item.lido ? 'Marcar não lida' : 'Marcar lida', async () => {
        leitura.disabled = true;
        try { await marcarItemConsulta(item, !item.lido); await carregarConsultaWeb(); }
        catch (erro) { feedback.textContent = erro.message; leitura.disabled = false; }
    });
    const fonte = acoes.querySelector('a');
    if (fonte) fonte.addEventListener('click', () => {
        if (!item.lido) marcarItemConsulta(item, true).then(() => {
            if (document.getElementById('consulta-web').open) carregarConsultaWeb();
        }).catch(erro => { feedback.textContent = erro.message; });
    });
    acoes.append(leitura, criarBotaoConsulta('Conversar sobre isso', () => selecionarResposta({item_id: item.id}, item.titulo)));
    card.appendChild(feedback);
    return card;
}

async function carregarConsultaWeb(mais=false) {
    const numero = ++consultaWebEstado.pedido;
    const inicio = mais ? consultaWebEstado.pagina : 0;
    const lista = document.getElementById('consulta-lista');
    const status = document.getElementById('consulta-status');
    const carregar = document.getElementById('consulta-mais');
    carregar.hidden = true; status.textContent = 'Carregando…';
    if (!mais) lista.replaceChildren();
    const parametros = new URLSearchParams({busca: document.getElementById('consulta-busca').value,
        tipo: document.getElementById('consulta-tipo').value, leitura: document.getElementById('consulta-leitura').value,
        inicio: String(inicio)});
    try {
        const resposta = await fetch('/api/' + (consultaWebEstado.modo === 'historico' ? 'historico' : 'biblioteca') + '?' + parametros);
        if (!resposta.ok) throw new Error('Não consegui abrir a consulta. Tente novamente.');
        const dados = await resposta.json();
        if (numero !== consultaWebEstado.pedido || !document.getElementById('consulta-web').open) return;
        for (const item of dados.itens) {
            const el = consultaWebEstado.modo === 'historico' ? criarResultadoConversa(item) : criarItemBiblioteca(item);
            if (el) lista.appendChild(el);
        }
        consultaWebEstado.pagina = inicio + dados.itens.length;
        status.textContent = dados.total ? dados.total + (dados.total === 1 ? ' resultado' : ' resultados') : 'Nenhum resultado por aqui.';
        carregar.hidden = !dados.mais;
    } catch (erro) {
        if (numero === consultaWebEstado.pedido) status.textContent = erro.message;
    }
}

function abrirImagem(imagem, titulo) {
    const dialogo = document.getElementById('imagem-ampliada');
    const copia = document.getElementById('imagem-ampliada-arquivo');
    copia.src = imagem.currentSrc || imagem.src;
    copia.alt = titulo || '';
    document.getElementById('imagem-ampliada-titulo').textContent = titulo || 'Imagem';
    if (!dialogo.open) dialogo.showModal();
}

function iniciarConsultaWeb() {
    document.getElementById('btn-biblioteca-web').onclick = () => abrirBiblioteca();
    document.getElementById('btn-buscar-conversa').onclick = () => abrirConsultaWeb('historico');
    document.getElementById('resposta-selecionada-remover').onclick = () => limparRespostaSelecionada();
    document.getElementById('consulta-fechar').onclick = fecharConsultaWeb;
    document.getElementById('consulta-mais').onclick = () => carregarConsultaWeb(true);
    document.getElementById('consulta-tentar').onclick = () => carregarConsultaWeb();
    document.getElementById('consulta-busca').addEventListener('input', () => {
        clearTimeout(consultaWebEstado.timer);
        // Invalidar a busca anterior imediatamente evita mostrar resultados de uma palavra apagada.
        ++consultaWebEstado.pedido;
        consultaWebEstado.timer = setTimeout(() => carregarConsultaWeb(), 250);
    });
    for (const id of ['consulta-tipo', 'consulta-leitura']) document.getElementById(id).onchange = () => carregarConsultaWeb();
    document.getElementById('imagem-ampliada-fechar').onclick = () => document.getElementById('imagem-ampliada').close();
    for (const id of ['consulta-web', 'imagem-ampliada']) {
        const dialogo = document.getElementById(id);
        dialogo.addEventListener('click', e => { if (e.target === dialogo) dialogo.close(); });
    }
    document.getElementById('imagem-ampliada').addEventListener('close', () => {
        document.getElementById('imagem-ampliada-arquivo').removeAttribute('src');
    });
    document.addEventListener('keydown', e => {
        // O dialog nativo cuida do foco e de Escape. O painel de configurações atrás dele não recebe Tab.
        if (['Tab', 'Escape'].includes(e.key) && (document.getElementById('consulta-web').open ||
            document.getElementById('imagem-ampliada').open)) e.stopImmediatePropagation();
    }, true);
}

document.addEventListener('DOMContentLoaded', iniciarConsultaWeb);
