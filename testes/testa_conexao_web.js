// Uma conexão encerrada descarta send() sem erro: o rascunho só sai após confirmação.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

const conexoes = [], timers = new Map();
let proximoTimer = 0;
class SocketFalso {
    constructor(url) { this.url = url; this.readyState = 0; this.events = {}; this.enviados = []; conexoes.push(this); }
    addEventListener(tipo, fn) { (this.events[tipo] ||= []).push(fn); }
    emitir(tipo, dados = {}) { for (const fn of this.events[tipo] || []) fn(dados); }
    abrir() { this.readyState = 1; this.emitir('open'); }
    close() { this.readyState = 3; this.emitir('close'); }
    send(dados) {
        if (this.falharEnvio) throw new Error('Falha de envio simulada');
        if (this.readyState === 0) throw new Error('Ainda conectando');
        if (this.readyState === 1) this.enviados.push(JSON.parse(dados));
    }
}
const elementos = {};
const document = { getElementById(id) {
    return elementos[id] ||= { value: '', style: {}, scrollHeight: 42, disabled: false,
        hidden: true, textContent: '', events: {},
        setAttribute(nome, valor) { this[nome] = valor; },
        addEventListener(tipo, fn) { (this.events[tipo] ||= []).push(fn); } };
} };
const contexto = vm.createContext({ document, WebSocket: SocketFalso, console,
    window: { location: { protocol: 'http:', host: 'localhost:5000' } },
    setTimeout(fn, atraso) { const id = ++proximoTimer; timers.set(id, { fn, atraso }); return id; },
    clearTimeout(id) { timers.delete(id); },
    finalizarRespostaStreamInterrompida() {}, aplicarPresenca() {}, interromperCadastroFonte() {},
    cartoesEstadoRecebido: true, acompanhamentoEstado: { ativos: [] },
});
function trecho(inicio, fim) {
    const i = html.indexOf(inicio), j = html.indexOf(fim, i);
    assert.ok(i >= 0 && j > i, 'Trecho não encontrado: ' + inicio);
    return html.slice(i, j);
}
vm.runInContext(trecho('        function criarConexaoWeb(', '        const PAPEL_MASCOTE ='), contexto);
vm.runInContext(trecho('        // --- Caixa de texto', '        // --- Acompanhamentos:'), contexto);
vm.runInContext(trecho('        function atualizarCartoesAcompanhamento(', '        function criarTurnoEl('), contexto);
let ultimoEstadoDoCartao = 'inicial';
document.getElementById('historico-lista').querySelectorAll = seletor => seletor === '.cartao-acompanhamento' ? [{
    atualizarEstado(estado) { ultimoEstadoDoCartao = estado; },
}] : [];
vm.runInContext(trecho('        socket.onmessage = function(event)', "            if (dados.tipo === 'evento_visual')") + '};', contexto);
vm.runInContext(trecho('        // Sem isso, uma queda durante a geração', '        // ── Oficina:'), contexto);
const socket = vm.runInContext('socket', contexto);
const caixa = elementos['texto-input'], enviar = elementos['texto-enviar'], aviso = elementos['texto-envio-aviso'];
const confirmar = (pedido, ok = true) => socket.onmessage({ data: JSON.stringify({
    tipo: 'mensagem_texto_recebida', request_id: pedido.request_id, ok, erro: 'Luna ainda iniciando',
}) });
const dispararTimer = atraso => {
    const entrada = [...timers.entries()].find(([, t]) => t.atraso === atraso);
    assert.ok(entrada, 'Timer não encontrado: ' + atraso);
    timers.delete(entrada[0]); entrada[1].fn();
};

// Ainda conectando: nem Enter nem botão podem apagar o texto ou tentar enviar.
caixa.value = 'Primeira mensagem';
enviar.onclick();
assert.equal(caixa.value, 'Primeira mensagem');
assert.equal(conexoes[0].enviados.length, 0);
assert.equal(aviso.hidden, false);
conexoes[0].abrir();
enviar.onclick();
const primeira = conexoes[0].enviados[0];
assert.equal(primeira.tipo, 'mensagem_texto');
assert.equal(primeira.texto, 'Primeira mensagem');
assert.equal(caixa.value, 'Primeira mensagem', 'send() sozinho não confirma entrega.');
assert.equal(enviar.disabled, true);
enviar.onclick();
assert.equal(conexoes[0].enviados.length, 1, 'Clique repetido duplicou a mensagem.');
confirmar({ request_id: 'outro-pedido' });
assert.equal(caixa.value, 'Primeira mensagem');
confirmar(primeira);
assert.equal(caixa.value, '');
assert.equal(enviar.disabled, false);
assert.equal(aviso.hidden, true);
assert.equal(timers.size, 0);

// Edição feita enquanto o servidor confirma deve permanecer na caixa.
caixa.value = 'Mensagem enviada';
enviar.onclick();
const segunda = conexoes[0].enviados[1];
caixa.value = 'Próxima mensagem em edição';
confirmar(segunda);
assert.equal(caixa.value, 'Próxima mensagem em edição');
enviar.onclick();
const terceira = conexoes[0].enviados[2];
confirmar(terceira, false);
assert.equal(caixa.value, 'Próxima mensagem em edição');
assert.equal(enviar.disabled, false);
assert.equal(aviso.textContent, 'Luna ainda iniciando');

// Reproduz o caso do usuário: socket fechado não lança erro, mas não entrega nada.
conexoes[0].close();
assert.equal(contexto.cartoesEstadoRecebido, false, 'Queda manteve controles baseados no estado antigo.');
assert.equal(ultimoEstadoDoCartao, null, 'Cartão não foi invalidado junto da conexão.');
enviar.onclick();
assert.equal(caixa.value, 'Próxima mensagem em edição');
assert.equal(conexoes[0].enviados.length, 3);
assert.ok(aviso.textContent.includes('conexão'));
assert.equal(timers.size, 1, 'Mais de uma reconexão foi agendada.');
let aberturas = 0;
socket.addEventListener('open', () => { aberturas++; });
dispararTimer(1000);
assert.equal(conexoes.length, 2);
conexoes[1].abrir();
assert.equal(aberturas, 1, 'A nova conexão perdeu os callbacks do painel.');
conexoes[0].emitir('message', { data: JSON.stringify({ ...primeira, tipo: 'mensagem_texto_recebida', ok: true }) });
assert.equal(caixa.value, 'Próxima mensagem em edição', 'Conexão velha alterou a nova sessão.');
enviar.onclick();
confirmar(conexoes[1].enviados[0]);
assert.equal(caixa.value, '');

// Queda após send(), antes da confirmação: preserva e não reenvia automaticamente.
caixa.value = 'Envio sem confirmação';
enviar.onclick();
conexoes[1].close();
assert.equal(caixa.value, 'Envio sem confirmação');
assert.equal(enviar.disabled, false);
dispararTimer(1000);
conexoes[2].abrir();
assert.equal(conexoes[2].enviados.length, 0, 'Reconexão reenviou texto cuja entrega era incerta.');
enviar.onclick();
dispararTimer(15000);
assert.equal(caixa.value, 'Envio sem confirmação');
assert.equal(enviar.disabled, false);
assert.ok(aviso.textContent.includes('confirmação'));
dispararTimer(1000);
conexoes[3].abrir();
assert.equal(conexoes[3].enviados.length, 0);

conexoes[3].falharEnvio = true;
enviar.onclick();
assert.equal(caixa.value, 'Envio sem confirmação');
assert.equal(enviar.disabled, false);
assert.equal(timers.size, 1);
dispararTimer(1000);
conexoes[4].close();
dispararTimer(2000);
conexoes[5].abrir();
assert.equal(aberturas, 4);
let preveniu = false;
caixa.events.keydown[0]({ key: 'Enter', shiftKey: true, preventDefault() { preveniu = true; } });
assert.equal(preveniu, false, 'Shift+Enter deixou de permitir quebra de linha.');
caixa.events.keydown[0]({ key: 'Enter', shiftKey: false, preventDefault() { preveniu = true; } });
assert.equal(preveniu, true);
confirmar(conexoes[5].enviados[0]);
assert.equal(caixa.value, '');
// Sugestões usam a mesma confirmação, sem apagar um rascunho de outra mensagem.
caixa.value = 'Ainda estou escrevendo outra coisa';
contexto.enviarPedidoTexto('Como fizeram esse teste?', null, {turno_id: 'rss-antigo', indice: 0});
const pergunta = conexoes[5].enviados.at(-1);
assert.deepEqual(pergunta.novidade, {turno_id: 'rss-antigo', indice: 0});
assert.equal(pergunta.texto, 'Como fizeram esse teste?');
contexto.enviarPedidoTexto('OLED ainda vale a pena?', null, {turno_id: 'rss-antigo', indice: 1});
assert.equal(conexoes[5].enviados.at(-1), pergunta, 'Clique durante confirmação duplicou o envio');
confirmar(pergunta);
assert.equal(caixa.value, 'Ainda estou escrevendo outra coisa');
assert.equal(enviar.disabled, false);
conexoes[5].close();
contexto.enviarPedidoTexto('OLED ainda vale a pena?', null, {turno_id: 'rss-antigo', indice: 1});
assert.equal(conexoes[5].enviados.at(-1), pergunta, 'Sugestão foi enviada sem conexão');
assert.equal(caixa.value, 'Ainda estou escrevendo outra coisa');
console.log('PASSOU — reconexão preserva callbacks e texto só sai após confirmação do servidor');
