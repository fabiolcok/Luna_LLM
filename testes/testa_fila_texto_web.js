// A mensagem aceita precisa aparecer mesmo quando outra execução ainda ocupa a Luna.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

class Elemento {
    constructor() {
        this.children = []; this.parentNode = null; this.dataset = {}; this.style = {};
        this.className = ''; this.id = ''; this.textContent = ''; this._html = '';
        this.scrollHeight = 500; this.scrollTop = 500; this.clientHeight = 500;
        this.classList = {
            contains: nome => this.className.split(' ').includes(nome),
            add: (...nomes) => { this.className = [...new Set([...this.className.split(' '), ...nomes])].join(' '); },
            remove: (...nomes) => { this.className = this.className.split(' ').filter(n => !nomes.includes(n)).join(' '); },
        };
    }
    appendChild(el) { if (el.parentNode) el.remove(); el.parentNode = this; this.children.push(el); return el; }
    append(...els) { els.forEach(el => this.appendChild(el)); }
    insertBefore(el, anterior) { if (el.parentNode) el.remove(); el.parentNode = this; this.children.splice(this.children.indexOf(anterior), 0, el); }
    remove() { if (this.parentNode) this.parentNode.children.splice(this.parentNode.children.indexOf(this), 1); this.parentNode = null; }
    removeAttribute(nome) { if (nome === 'id') this.id = ''; }
    setAttribute(nome, valor) { this[nome] = valor; }
    buscar(fn) { if (fn(this)) return this; for (const el of this.children) { const achado = el.buscar(fn); if (achado) return achado; } return null; }
    querySelector(seletor) { return this.buscar(el => el.classList.contains(seletor.slice(1))); }
    set innerHTML(valor) { for (const el of this.children) el.parentNode = null; this.children = []; this._html = valor; }
    get innerHTML() { return this._html; }
}
const lista = new Elemento(), details = new Elemento(), conteudo = new Elemento();
const document = {
    createElement: () => new Elemento(),
    getElementById: id => id === 'historico-lista' ? lista : lista.buscar(el => el.id === id),
    querySelectorAll: () => [],
};
const contexto = vm.createContext({
    document, console, Date, socket: {}, detailsEl: details, conteudoEl: conteudo,
    _climaTurnoPendente: '', receberConfirmacaoTexto() {},
    definirAlvoAvaliacao(turno) { contexto.alvoAvaliacao = turno; },
    renderizarMarkdownSeguro: texto => texto, copiarMensagem() {}, criarCartaoWeb: () => null,
    linkNovidade: () => null, atualizarFadeConversa() {},
    setInterval: () => 1, clearInterval() {},
});
function trecho(inicio, fim) {
    const i = html.indexOf(inicio), j = html.indexOf(fim, i);
    assert.ok(i >= 0 && j > i, 'Trecho não encontrado: ' + inicio);
    return html.slice(i, j);
}
vm.runInContext(trecho('        function iconeCopiarMensagem()', '        function copiarMensagem('), contexto);
vm.runInContext(trecho('        const historicoLista ', '        const fonteConversa '), contexto);
vm.runInContext(trecho('        function criarSugestoesNovidade(', '        // --- Config panel ---'), contexto);
vm.runInContext(trecho('        socket.onmessage = function(event)', "            if (dados.tipo === 'avaliacao_salva')") + '};', contexto);
const receber = dados => contexto.socket.onmessage({ data: JSON.stringify(dados) });
const textos = () => lista.children.map(el => el.querySelector('.turno-usuario')?.textContent);
const pendentes = [
    { id: 'a', usuario: 'Primeira mensagem', tempo: '09:43', estado: 'fila' },
    { id: 'b', usuario: 'Segunda mensagem', tempo: '09:43', estado: 'fila' },
];

receber({ tipo: 'historico_novo', turno: { luna: 'Bom dia!', usuario: '', id: 'proativo' } });
receber({ tipo: 'fila_texto', mensagens: pendentes });
assert.deepEqual(textos(), [undefined, 'Primeira mensagem', 'Segunda mensagem']);
assert.ok(lista.children[1].classList.contains('turno-fila'));
assert.equal(contexto.alvoAvaliacao.id, 'proativo', 'Texto na fila mudou o alvo da avaliação.');
assert.equal(document.getElementById('turno-pendente'), null, 'Entrada na fila foi confundida com geração iniciada.');

contexto.mostrarUsuarioPendente('Primeira mensagem', 'a');
const emExecucao = document.getElementById('turno-pendente');
assert.equal(emExecucao, lista.children[1], 'Início da geração duplicou a entrada já mostrada.');
contexto.mostrarRespostaStream('Resposta parcial');
receber({ tipo: 'fila_texto', mensagens: [{ ...pendentes[0], estado: 'respondendo' }, pendentes[1]] });
contexto.mostrarUsuarioPendente('Primeira mensagem', 'a');
assert.equal(document.getElementById('turno-pendente'), emExecucao);
assert.ok(emExecucao.querySelector('.turno-luna'), 'Atualização da fila apagou a prévia em curso.');

receber({ tipo: 'historico_novo', turno: { usuario: 'Primeira mensagem', luna: 'Primeira resposta', request_id: 'a', id: 'r1' } });
assert.deepEqual(textos(), [undefined, 'Primeira mensagem', 'Segunda mensagem']);
assert.equal(lista.children[1].querySelector('.mensagem-conteudo').innerHTML, 'Primeira resposta');
assert.ok(lista.children[2].classList.contains('turno-fila'), 'Resposta da primeira apagou a segunda entrada.');
// A confirmação e um retrato atrasado da fila não podem duplicar uma mensagem já respondida.
receber({ tipo: 'mensagem_texto_recebida', request_id: 'a', ok: true });
receber({ tipo: 'fila_texto', mensagens: pendentes });
assert.equal(lista.children.length, 3);
receber({ tipo: 'fila_texto', mensagens: [pendentes[1]] });

// Reconectar/recarregar deve restaurar tanto o histórico quanto os textos ainda não atendidos.
receber({ tipo: 'historico_completo', turnos: [{ usuario: 'Primeira mensagem', luna: 'Primeira resposta', request_id: 'a' }],
    pendentes: [{ ...pendentes[1], estado: 'respondendo' }, { id: 'c', usuario: 'Terceira mensagem', estado: 'fila' }] });
assert.deepEqual(textos(), ['Primeira mensagem', 'Segunda mensagem', 'Terceira mensagem']);
assert.equal(document.getElementById('turno-pendente').dataset.requestId, 'b');
contexto.mostrarRespostaStream('Ainda pensando');
contexto.finalizarRespostaStreamInterrompida();
receber({ tipo: 'fila_texto', mensagens: [{ ...pendentes[1], estado: 'respondendo' }, { id: 'c', usuario: 'Terceira mensagem', estado: 'fila' }] });
assert.equal(document.getElementById('turno-pendente'), null, 'Atualização da fila reativou uma resposta interrompida.');
receber({ tipo: 'fila_texto', mensagens: [{ id: 'c', usuario: 'Terceira mensagem', estado: 'fila' }] });
assert.ok(lista.children[1].classList.contains('turno-incompleto'));
assert.equal(lista.children[2].querySelector('.turno-usuario').textContent, 'Terceira mensagem');
console.log('PASSOU — fila visível, respostas no turno correto e recuperação após reconexão');
