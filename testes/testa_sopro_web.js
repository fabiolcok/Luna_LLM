const fs = require('fs');
const path = require('path');
const assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
const inicio = html.indexOf('function acaoSopro(');
const fim = html.indexOf('function renderAcompanhamentos(', inicio);
const inicioLink = html.indexOf('function linkNovidade(');
const fimLink = html.indexOf('function criarTurnoEl(', inicioLink);
assert.ok(inicio >= 0 && fim > inicio);
function elemento() {
    return {
        children: [], dataset: {}, value: '', textContent: '', hidden: false, open: true,
        set innerHTML(value) { this.children = []; this.html = value; },
        get innerHTML() { return this.html || ''; },
        appendChild(child) { this.children.push(child); return child; }
    };
}
const elementos = {};
const document = {
    getElementById: id => elementos[id] || (elementos[id] = elemento()),
    createElement: elemento
};
const enviados = [];
const socket = { readyState: 1, send: value => enviados.push(JSON.parse(value)) };
const criar = new Function('document', 'socket', 'quandoAcompanhamento',
    html.slice(inicio, fim) + html.slice(inicioLink, fimLink) +
    '; return { renderAcompanhamentoSopro, acaoSopro };');
const api = criar(document, socket, () => '05/10 12:00');
const estado = {
    status: 'ativo', situacao: 'O sotaque incomodou.', resultado: 'Nenhuma menção nova.',
    verificado_em: 12345, fontes: [{ nome: 'GitHub', url: 'https://github.com/samuel-vitorino/sopro' }],
    novidades: [{ id: 'abc', trecho: '<img src=x onerror=alert(1)> PT-BR planned.',
        fonte: 'GitHub', url: 'https://github.com/samuel-vitorino/sopro', lido: false }]
};
api.renderAcompanhamentoSopro(estado);
assert.equal(elementos['sopro-situacao'].value, estado.situacao);
assert.equal(elementos['sopro-painel'].open, true, 'Atualização não deve recolher o painel.');
const acoes = () => elementos['sopro-acoes'].children;
acoes().find(b => b.textContent === 'Verificar agora').onclick();
assert.deepEqual(enviados.pop(), { comando: 'sopro_acao', acao: 'verificar', id: '', situacao: '' });
elementos['sopro-situacao'].value = 'Meu rascunho';
api.renderAcompanhamentoSopro({ ...estado, verificando: true });
assert.equal(elementos['sopro-situacao'].value, 'Meu rascunho', 'Consulta apagou a edição.');
elementos['sopro-situacao'].value = '';
api.renderAcompanhamentoSopro(estado);
assert.equal(elementos['sopro-situacao'].value, '', 'Consulta restaurou um campo apagado durante edição.');
elementos['sopro-situacao'].value = 'Meu rascunho';
api.renderAcompanhamentoSopro({ ...estado, verificando: true });
assert.equal(acoes().find(b => b.textContent === 'Verificar agora').disabled, true);
acoes().find(b => b.textContent === 'Salvar situação').onclick();
assert.equal(enviados.pop().situacao, 'Meu rascunho');
api.renderAcompanhamentoSopro({ ...estado, status: 'pausado' });
assert.equal(acoes().find(b => b.textContent === 'Verificar agora').disabled, true);
acoes().find(b => b.textContent === 'Retomar').onclick();
assert.equal(enviados.pop().acao, 'retomar');
const novidade = elementos['sopro-novidades'].children[0];
assert.equal(novidade.children[0].textContent, 'Menção na fonte: ' + estado.novidades[0].trecho);
novidade.children.find(b => b.textContent === 'Mais tarde (2h)').onclick();
assert.equal(enviados.pop().id, 'abc');
api.renderAcompanhamentoSopro({ ...estado,
    fontes: [{ nome: 'ruim', url: 'javascript:alert(1)' }],
    novidades: [{ ...estado.novidades[0], url: 'javascript:alert(1)', lido: true }] });
assert.equal(elementos['sopro-fontes'].children.length, 0);
assert.equal(elementos['sopro-novidades'].children[0].children.length, 1);
socket.readyState = 3;
api.acaoSopro('verificar');
assert.equal(enviados.length, 0, 'Conexão fechada não deve lançar erro ao clicar.');
api.renderAcompanhamentoSopro(null);
assert.equal(elementos['sopro-painel'].hidden, true);
console.log('PASSOU — painel preserva edição, envia ações e mostra fontes sem HTML externo');
