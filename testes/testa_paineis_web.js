/** Organização dos painéis, foco e estados reais de acompanhamento. */
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
const ids = {};
let document;
function elemento(tag = 'div') {
    const el = {
        tagName: tag.toUpperCase(), attrs: {}, dataset: {}, children: [], events: {}, style: {},
        parentNode: null, value: '', disabled: false, hidden: false, open: false, inert: false,
        get childNodes() { return this.children; },
        get scrollHeight() {
            if (!this.getClientRects().length) return 0;
            return Math.max(this.alturaConteudo || 24, parseFloat(this.style.height) || 0);
        },
        setAttribute(nome, valor) {
            this.attrs[nome] = String(valor);
            if (nome === 'id') { this.id = String(valor); ids[this.id] = this; }
            if (nome.startsWith('data-')) this.dataset[nome.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(valor);
        },
        getAttribute(nome) { return this.attrs[nome]; },
        addEventListener(nome, fn) { (this.events[nome] ||= []).push(fn); },
        appendChild(child) { child.parentNode = this; this.children.push(child); return child; },
        querySelectorAll(selector) {
            const todos = [];
            const andar = no => { no.children.forEach(child => { todos.push(child); andar(child); }); };
            andar(this);
            return todos.filter(no => selector.split(',').some(item => {
                const s = item.trim();
                if (s === '[data-config-grupo]') return no.dataset.configGrupo !== undefined;
                if (s === 'details[open]') return no.tagName === 'DETAILS' && no.open;
                if (s === '[tabindex="0"]') return no.getAttribute('tabindex') === '0';
                if (s.startsWith('.')) return no.classList.contains(s.slice(1));
                if (s === 'a[href]') return no.tagName === 'A' && no.getAttribute('href');
                return no.tagName.toLowerCase() === s;
            }));
        },
        querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
        contains(el) { for (let p = el; p; p = p.parentNode) if (p === this) return true; return false; },
        focus() { document.activeElement = this; },
        scrollIntoView() { this.scrolled = true; },
        getClientRects() {
            for (let p = this; p; p = p.parentNode) if (p.hidden || p.inert) return [];
            return [{}];
        },
        set innerHTML(value) { this.children = []; this.html = value; },
        get innerHTML() { return this.html || ''; },
        set textContent(value) { this.children = []; this.text = String(value); },
        get textContent() { return this.text || this.children.map(c => c.textContent).join(''); },
        set className(value) { this.classes = new Set(value.split(/\s+/).filter(Boolean)); },
        get className() { return [...(this.classes || [])].join(' '); },
    };
    el.classes = new Set();
    el.classList = {
        add(...names) { names.forEach(n => el.classes.add(n)); },
        remove(...names) { names.forEach(n => el.classes.delete(n)); },
        contains(n) { return el.classes.has(n); },
        toggle(n, force) { const on = force === undefined ? !el.classes.has(n) : force; if (on) el.classes.add(n); else el.classes.delete(n); return on; },
    };
    return el;
}
// Ler a estrutura publicada pega controles duplicados e movimentos para o grupo errado.
const root = elemento('body');
const stack = [root];
const markup = html.split(/<body[^>]*>/)[1].split('<script')[0];
const voids = new Set(['input', 'img', 'br', 'hr', 'source', 'link', 'meta', 'area', 'wbr']);
for (const token of markup.matchAll(/<!--[\s\S]*?-->|<\/?[\w:-]+\b[^>]*>/g)) {
    const raw = token[0];
    if (raw.startsWith('<!--')) continue;
    const tag = raw.match(/^<\/?([\w:-]+)/)[1].toLowerCase();
    if (raw.startsWith('</')) {
        assert.equal(stack[stack.length - 1].tagName.toLowerCase(), tag, 'Tag fora de ordem: ' + raw);
        stack.pop();
        continue;
    }
    const el = elemento(tag);
    for (const attr of raw.slice(tag.length + 1, -1).matchAll(/([\w:-]+)(?:\s*=\s*"([^"]*)"|\s*=\s*'([^']*)')?/g)) {
        const [, name, double, single] = attr;
        if (name === 'id') assert.ok(!ids[double || single], 'ID duplicado: ' + (double || single));
        el.setAttribute(name, double ?? single ?? '');
        if (name === 'class') el.className = double || single;
        if (['hidden', 'open', 'inert', 'disabled'].includes(name)) el[name] = true;
    }
    stack[stack.length - 1].appendChild(el);
    if (!voids.has(tag) && !raw.endsWith('/>')) stack.push(el);
}
assert.equal(stack.length, 1, 'Estrutura HTML não fechou.');
document = {
    getElementById: id => ids[id] || null,
    createElement: elemento,
    querySelectorAll: s => s === '#config-panel .config-recolhivel'
        ? ids['config-panel'].querySelectorAll('.config-recolhivel') : root.querySelectorAll(s),
    activeElement: root, events: {},
    addEventListener(nome, fn) { (this.events[nome] ||= []).push(fn); }
};
const dentro = (id, ancestor) => {
    for (let p = ids[id]; p; p = p.parentNode) if (p === ids[ancestor]) return true;
    return false;
};
assert.ok(dentro('sopro-painel', 'acompanhamentos-panel'));
assert.ok(dentro('acompanhamentos-lista', 'acompanhamentos-panel'));
assert.ok(!dentro('sopro-painel', 'config-panel') && !dentro('sopro-painel', 'presenca'));
assert.ok(dentro('texto-input', 'avaliacao-bar') === false);
for (const id of ['cfg-voz', 'cfg-voz-menu', 'cfg-volume', 'cfg-velocidade', 'cfg-fonte-conversa', 'tecla-ptt']) assert.ok(dentro(id, 'config-grupo-uso'));
for (const id of ['cfg-dark-souls', 'cfg-tarefa-acompanhamentos', 'cfg-tarefa-radar_rss']) assert.ok(dentro(id, 'config-grupo-proatividade'));
assert.ok(dentro('mem-pendentes', 'config-grupo-memoria'));
assert.ok(dentro('mem-assuntos', 'acompanhamentos-panel'));
assert.ok(!dentro('mem-assuntos', 'config-grupo-memoria'));
assert.ok(!ids['secao-tarefas'].classList.contains('config-recolhivel'));
for (const id of ['cfg-personalidade', 'cfg-modelo', 'dic-wrap', 'chaves-lista']) assert.ok(dentro(id, 'config-grupo-avancado'));
assert.ok(ids['config-panel'].inert && ids['acompanhamentos-panel'].inert);
assert.ok(ids['acompanhamentos-badge'].hidden);
const enviados = [];
const socket = { readyState: 1, send: data => enviados.push(JSON.parse(data)) };
function trecho(start, end) {
    const i = html.indexOf(start), j = html.indexOf(end, i);
    assert.ok(i >= 0 && j > i, 'Trecho não encontrado: ' + start);
    return html.slice(i, j);
}
const vozesUI = new Function('document', 'socket', 'WebSocket', 'enviarConfig',
    trecho('        function atualizarControleVoz(', '        // Avaliação 👍/👎') +
    '; return {atualizarControleVoz, fecharMenuVoz, abrirMenuVoz};'
)(document, socket, { OPEN: 1 }, dados => enviados.push(dados));
const controleVoz = vozesUI.atualizarControleVoz;
const seletorVoz = ids['cfg-voz'];
const menuVoz = ids['cfg-voz-menu'];
const opcaoVoz = id => menuVoz.querySelectorAll('.voz-menu-opcao').find(o => o.dataset.voz === id);
const estrelaVoz = id => menuVoz.querySelectorAll('.voz-menu-favorita').find(o => o.dataset.voz === id);
const tituloGrupoVoz = grupo => grupo.querySelector('.voz-menu-titulo').textContent;
assert.equal(seletorVoz.tagName, 'BUTTON');
assert.ok(seletorVoz.disabled);
assert.ok(menuVoz.hidden);
controleVoz({ voz: 'jf_alpha' });
assert.ok(seletorVoz.disabled);
controleVoz({ voz: 'jf_alpha', vozes: [
    { idioma: 'Português (Brasil)', vozes: [
        { id: 'pf_dora', nome: 'Dora', genero: 'feminina' },
        { id: 'pm_alex', nome: 'Alex', genero: 'masculina' },
    ] },
    { idioma: 'Japonês', vozes: [{ id: 'jf_alpha', nome: 'Alpha', genero: 'feminina' }] },
    { idioma: 'Inglês (EUA)', vozes: [{ id: 'af_nicole', nome: 'Nicole', genero: 'feminina' }] },
] });
assert.equal(seletorVoz.value, 'jf_alpha');
assert.equal(seletorVoz.disabled, false);
assert.equal(tituloGrupoVoz(menuVoz.children[0]), 'Português (Brasil)');
assert.equal(menuVoz.querySelectorAll('.voz-menu-opcao').length, 4);
assert.equal(menuVoz.querySelectorAll('.voz-menu-favorita').length, 4);
const primeiroGrupoVoz = menuVoz.children[0];
controleVoz({ voz: 'pm_alex' });
assert.equal(seletorVoz.value, 'pm_alex');
assert.equal(menuVoz.children[0], primeiroGrupoVoz, 'Atualizações de volume não devem recriar a lista.');
assert.ok(ids['cfg-voz-status'].textContent.includes('Português (Brasil)'));
seletorVoz.onclick();
assert.equal(menuVoz.hidden, false);
assert.equal(seletorVoz.getAttribute('aria-expanded'), 'true');
opcaoVoz('af_nicole').onclick();
assert.deepEqual(enviados.pop(), { config: 'voz', valor: 'af_nicole' });
assert.ok(seletorVoz.disabled);
assert.ok(menuVoz.hidden);
assert.equal(seletorVoz.value, 'pm_alex', 'A voz ativa aguarda a confirmação do servidor.');
controleVoz({ voz: 'af_nicole' });
assert.equal(seletorVoz.disabled, false);
assert.equal(opcaoVoz('af_nicole').getAttribute('aria-pressed'), 'true');
assert.ok(estrelaVoz('jf_alpha').disabled, 'Servidor antigo não pode aparentar salvar favoritas.');
controleVoz({ voz: 'af_nicole', vozes_favoritas: [] });
seletorVoz.onclick();
assert.equal(estrelaVoz('jf_alpha').disabled, false);
estrelaVoz('jf_alpha').focus();
estrelaVoz('jf_alpha').onclick();
assert.deepEqual(enviados.pop(), { config: 'voz_favorita', voz: 'jf_alpha', valor: true });
assert.equal(seletorVoz.value, 'af_nicole', 'Favoritar outra voz não pode selecionar essa voz.');
assert.equal(menuVoz.hidden, false, 'Favoritar deve manter a lista aberta.');
assert.ok(estrelaVoz('jf_alpha').disabled);
assert.equal(estrelaVoz('jf_alpha').textContent, '☆', 'A estrela aguarda a confirmação do servidor.');
controleVoz({ voz: 'af_nicole', vozes_favoritas: ['jf_alpha', 'af_nicole'] });
assert.equal(tituloGrupoVoz(menuVoz.children[0]), '★ Favoritas');
assert.deepEqual(menuVoz.children[0].querySelectorAll('.voz-menu-opcao').map(o => o.dataset.voz), ['jf_alpha', 'af_nicole']);
assert.equal(menuVoz.querySelectorAll('.voz-menu-opcao').length, 4, 'Favoritas não duplicam as opções.');
assert.equal(menuVoz.hidden, false);
assert.equal(document.activeElement, estrelaVoz('jf_alpha'), 'A confirmação deve preservar o foco da estrela.');
assert.equal(estrelaVoz('jf_alpha').textContent, '★');
assert.equal(estrelaVoz('jf_alpha').getAttribute('aria-pressed'), 'true');
const grupoFavoritas = menuVoz.children[0];
controleVoz({ voz: 'af_nicole', vozes_favoritas: ['jf_alpha', 'af_nicole'], volume: 0.5 });
assert.equal(menuVoz.children[0], grupoFavoritas);
estrelaVoz('jf_alpha').onclick();
assert.deepEqual(enviados.pop(), { config: 'voz_favorita', voz: 'jf_alpha', valor: false });
controleVoz({ voz: 'af_nicole', vozes_favoritas: ['af_nicole'] });
assert.equal(estrelaVoz('jf_alpha').textContent, '☆');
assert.equal(seletorVoz.value, 'af_nicole');
assert.equal(menuVoz.querySelectorAll('.voz-menu-opcao').filter(o => o.dataset.voz === 'jf_alpha').length, 1);
socket.readyState = 0;
opcaoVoz('pf_dora').onclick();
assert.equal(seletorVoz.value, 'af_nicole');
assert.equal(enviados.length, 0);
assert.ok(ids['cfg-voz-status'].textContent.includes('Sem conexão'));
estrelaVoz('af_nicole').onclick();
assert.equal(enviados.length, 0);
assert.equal(estrelaVoz('af_nicole').textContent, '★');
socket.readyState = 1;
controleVoz({ voz: 'jf_alpha', vozes_favoritas: ['af_nicole'] });
assert.equal(estrelaVoz('af_nicole').disabled, false);
controleVoz({ voz: 'jf_alpha', vozes_favoritas: [] });
assert.equal(tituloGrupoVoz(menuVoz.children[0]), 'Português (Brasil)');
assert.equal(menuVoz.querySelectorAll('.voz-menu-opcao').length, 4);
document.events.click.at(-1)({ target: root });
assert.ok(menuVoz.hidden);
const teclaVoz = (alvo, key) => {
    const event = { key, target: alvo, preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; } };
    const receptor = alvo === seletorVoz ? seletorVoz : menuVoz;
    receptor.events.keydown[0](event);
    return event;
};
assert.ok(teclaVoz(seletorVoz, 'ArrowDown').prevented);
assert.equal(menuVoz.hidden, false);
assert.equal(document.activeElement, opcaoVoz('jf_alpha'));
assert.ok(teclaVoz(opcaoVoz('jf_alpha'), 'Home').prevented);
assert.equal(document.activeElement, opcaoVoz('pf_dora'));
assert.ok(teclaVoz(opcaoVoz('pf_dora'), 'ArrowDown').prevented);
assert.equal(document.activeElement, opcaoVoz('pm_alex'));
teclaVoz(estrelaVoz('pm_alex'), 'End');
assert.equal(document.activeElement, opcaoVoz('af_nicole'));
assert.ok(teclaVoz(opcaoVoz('af_nicole'), 'Escape').stopped);
assert.ok(menuVoz.hidden);
assert.equal(document.activeElement, seletorVoz);
const windowEvents = {};
const memoria = new Function('document', 'socket', 'window',
    trecho('        function ajustarAlturaMemoria(', "        document.getElementById('mem-processar').onclick") +
    '; return {renderMemoria, ajustarCaixasMemoria};'
)(document, socket, { addEventListener: (nome, fn) => { windowEvents[nome] = fn; } });
const controller = new Function('document', 'configPanel', 'configOverlay', 'ajustarCaixasMemoria', 'fecharMenuVoz',
    trecho('        let painelOrigem =', '        function enviarConfig(') +
    '; return {abrirPainelLateral, fecharConfig, selecionarGrupoConfig, tratarTeclaPainel};'
)(document, ids['config-panel'], ids['config-overlay'], memoria.ajustarCaixasMemoria, vozesUI.fecharMenuVoz);
ids['btn-config'].onclick.call(ids['btn-config']);
assert.ok(ids['config-panel'].classList.contains('aberto'));
assert.equal(ids['config-panel'].inert, false);
assert.equal(document.activeElement, ids['btn-config-fechar']);
controller.selecionarGrupoConfig('memoria');
assert.equal(ids['config-grupo-memoria'].hidden, false);
assert.equal(ids['config-grupo-uso'].hidden, true);
assert.equal(root.querySelectorAll('[data-config-grupo]').find(b => b.dataset.configGrupo === 'memoria').getAttribute('aria-pressed'), 'true');
controller.selecionarGrupoConfig('inexistente');
assert.equal(ids['config-grupo-uso'].hidden, false);

// Sugestões chegam com a aba escondida; abrir e editar devem mostrar o texto inteiro.
memoria.renderMemoria({ pendentes: [{ id: 'm1', fato: 'Uma lembrança longa', tipo: 'fato', evidencia: 'Conversa' }] });
let caixaMemoria = ids['mem-pendentes'].querySelector('textarea');
caixaMemoria.alturaConteudo = 84;
assert.equal(caixaMemoria.style.height, undefined);
controller.selecionarGrupoConfig('memoria');
assert.equal(caixaMemoria.style.height, '84px');
caixaMemoria.alturaConteudo = 124;
caixaMemoria.value = 'Lembrança editada';
caixaMemoria.events.input[0]();
assert.equal(caixaMemoria.style.height, '124px');
caixaMemoria.alturaConteudo = 44;
caixaMemoria.events.input[0]();
assert.equal(caixaMemoria.style.height, '44px', 'Apagar texto deve diminuir a caixa.');
ids['mem-pendentes'].querySelector('button').onclick();
assert.deepEqual(enviados.pop(), { comando: 'memoria_confirmar', id: 'm1', texto: 'Lembrança editada' });
caixaMemoria.alturaConteudo = 64;
windowEvents.resize();
assert.equal(caixaMemoria.style.height, '64px', 'Mudar a largura da janela deve recalcular as quebras de linha.');
memoria.renderMemoria({ pendentes: [{ id: 'm2', fato: 'Nova lembrança' }] });
caixaMemoria = ids['mem-pendentes'].querySelector('textarea');
assert.equal(caixaMemoria.style.height, '24px', 'Sugestão recebida na aba aberta deve ajustar imediatamente.');
controller.fecharConfig();
caixaMemoria.alturaConteudo = 104;
ids['btn-config'].onclick.call(ids['btn-config']);
assert.equal(caixaMemoria.style.height, '104px', 'Reabrir a gaveta deve recalcular a altura.');
controller.selecionarGrupoConfig('uso');

const key = (name, shiftKey = false) => {
    const event = { key: name, shiftKey, prevented: false, preventDefault() { this.prevented = true; } };
    controller.tratarTeclaPainel(event);
    return event;
};
seletorVoz.onclick();
assert.equal(menuVoz.hidden, false);
assert.ok(key('Escape').prevented);
assert.ok(menuVoz.hidden);
assert.ok(ids['config-panel'].classList.contains('aberto'), 'Escape na lista deve fechar só a lista.');
const visible = ids['config-panel'].querySelectorAll('button, input, select, textarea, summary, a[href], [tabindex="0"]').filter(el => !el.disabled && el.getClientRects().length);
visible[visible.length - 1].focus();
assert.ok(key('Tab').prevented);
assert.equal(document.activeElement, visible[0]);
assert.ok(key('Tab', true).prevented);
assert.equal(document.activeElement, visible[visible.length - 1]);
document.activeElement = root;
assert.ok(key('Tab').prevented, 'Atualização que perdeu foco deixou o Tab escapar da gaveta.');
assert.equal(document.activeElement, visible[0]);
assert.ok(key('Escape').prevented);
assert.equal(document.activeElement, ids['menu-atalhos-toggle']);
assert.ok(ids['config-panel'].inert);
ids['btn-acompanhamentos'].onclick.call(ids['btn-acompanhamentos']);
assert.ok(ids['acompanhamentos-panel'].classList.contains('aberto'));
assert.ok(!ids['config-panel'].classList.contains('aberto'));
ids['config-overlay'].onclick();
assert.equal(document.activeElement, ids['menu-atalhos-toggle']);
const inicio = html.indexOf('        let acompanhamentoEstado =');
const fim = html.indexOf('\n        }', html.indexOf('function renderAcompanhamentos(', inicio)) + '\n        }'.length;
const render = new Function('document', 'socket', 'linkNovidade',
    html.slice(inicio, fim) + html.slice(html.indexOf('function renderInteressesRadar('), html.indexOf('function criarTurnoEl(')) +
    '; return {renderAcompanhamentos};'
)(document, socket, () => null);
const sopro = { status: 'ativo', situacao: 'Sotaque incomodou', novidades: [], fontes: [] };
render.renderAcompanhamentos({ ativos: [{ id: 'a', assunto: '<img src=x> Modem', perguntar_em: '2026-10-06T12:00:00' }], sopro });
assert.equal(ids['acompanhamentos-badge'].hidden, true, 'Ativo sem novidade não deve acender o indicador.');
const item = ids['acompanhamentos-lista'].children[0];
assert.equal(item.children[0].children[0].textContent, '<img src=x> Modem');
item.open = true;
render.renderAcompanhamentos({ ativos: [{ id: 'a', assunto: 'Modem' }], sopro });
assert.equal(ids['acompanhamentos-lista'].children[0].open, true, 'Atualização recolheu um item que estava aberto.');
ids['acompanhamentos-lista'].children[0].children.find(b => b.tagName === 'BUTTON').onclick();
assert.deepEqual(enviados.pop(), { comando: 'acompanhamento_cancelar', id: 'a' });
render.renderAcompanhamentos({ ativos: [], sopro: { ...sopro, tem_novidade: true, novidades: [{ id: 'n', lido: false }] } });
assert.equal(ids['acompanhamentos-badge'].hidden, false);
assert.equal(ids['acompanhamentos-badge'].textContent, '1');
assert.ok(!ids['acompanhamentos-panel'].classList.contains('aberto'), 'Novidade abriu a gaveta sozinha.');
render.renderAcompanhamentos({ ativos: [], sopro: { ...sopro, novidades: [{ id: 'n', lido: true }] } });
assert.equal(ids['acompanhamentos-badge'].hidden, true);
render.renderAcompanhamentos({ ativos: [], confirmacao: { tipo: 'proposta', id: 'c', assunto: 'Modem' }, sopro });
assert.ok(ids['acompanhamento-card'].classList.contains('ativo'));
assert.equal(ids['acompanhamentos-decisao'].hidden, false);
ids['btn-acompanhamentos'].onclick.call(ids['btn-acompanhamentos']);
ids['btn-acompanhamentos-responder'].onclick();
assert.ok(ids['acompanhamento-card'].scrolled);
assert.equal(document.activeElement, ids['acompanhamento-acoes'].children[0]);
document.activeElement.onclick();
assert.deepEqual(enviados.pop(), { comando: 'acompanhamento_acao', acao: 'confirmar', id: 'c' });
// Um título estático não deve esconder os grupos, mesmo com a antiga preferência salva.
const localStorage = { getItem: () => 'fechado', setItem() {} };
new Function('document', 'localStorage',
    trecho("        document.querySelectorAll('#config-panel .config-recolhivel')", '        // ── ⌨ Teclas:')
)(document, localStorage);
const tarefas = ids['secao-tarefas'];
const tituloTarefas = tarefas.querySelector('.config-secao-titulo');
assert.ok(!tarefas.classList.contains('fechada'));
assert.ok(!tituloTarefas.classList.contains('acc'));
assert.ok(!tituloTarefas.events.click, 'Tarefas proativas deve ser apenas o título dos grupos.');

// Consultar acompanhamentos também atualiza os assuntos, sem depender de abrir a memória.
new Function('document', 'socket',
    trecho("        document.getElementById('btn-acompanhamentos').addEventListener('click'", '        // sub-sanfona do Lixo')
)(document, socket);
ids['btn-acompanhamentos'].events.click[0]();
assert.deepEqual(enviados.pop(), { comando: 'memoria_listar' });
socket.readyState = 3;
ids['btn-acompanhamentos'].events.click[0]();
assert.equal(enviados.length, 0);
socket.readyState = 1;

// A escolha só fica confirmada após o backend aplicar o perfil entre turnos.
const personalidade = new Function('document', 'socket', 'WebSocket', 'enviarConfig',
    trecho('        function atualizarControlePersonalidade(', '        function renderModelos(') +
    '; return {atualizarControlePersonalidade};'
)(document, socket, { OPEN: 1 }, dados => socket.send(JSON.stringify(dados)));
const atualizarPerfil = personalidade.atualizarControlePersonalidade;
const cfgPerfil = ids['cfg-personalidade'];
assert.deepEqual(cfgPerfil.children.map(o => o.getAttribute('value')), ['0', '1', '2', '3']);
atualizarPerfil({});
assert.ok(cfgPerfil.disabled, 'Backend anterior não deve habilitar uma troca que não suporta.');
atualizarPerfil({ personalidade: 2, personalidade_disponivel: true });
assert.equal(cfgPerfil.value, '2');
assert.ok(!cfgPerfil.disabled);
cfgPerfil.value = '3';
cfgPerfil.onchange();
assert.deepEqual(enviados.pop(), { config: 'personalidade', valor: 3 });
assert.ok(cfgPerfil.disabled, 'Clique repetido não pode iniciar duas trocas.');
atualizarPerfil({ personalidade: 2, personalidade_disponivel: true, personalidade_pendente: true });
assert.ok(cfgPerfil.disabled);
assert.ok(ids['cfg-personalidade-status'].textContent.includes('Aguardando'));
atualizarPerfil({ personalidade: 3, personalidade_disponivel: true });
assert.equal(cfgPerfil.value, '3');
assert.ok(!cfgPerfil.disabled);
atualizarPerfil({ personalidade: 3, personalidade_disponivel: true, personalidade_erro: 'Falhou' });
assert.equal(cfgPerfil.value, '3');
assert.equal(ids['cfg-personalidade-status'].textContent, 'Falhou');
atualizarPerfil({ personalidade: 0, personalidade_disponivel: true });
assert.equal(cfgPerfil.value, '0', 'O nível zero é uma escolha válida.');
socket.readyState = 3;
cfgPerfil.onchange();
assert.ok(cfgPerfil.disabled);
assert.equal(enviados.length, 0, 'Sem conexão não pode fingir que a troca foi enviada.');
socket.readyState = 1;
console.log('PASSOU — gavetas, grupos, foco, decisões e indicador preservam a conversa');
