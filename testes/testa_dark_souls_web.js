const assert = require('assert');
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
const elementos = new Map();
const document = {
    getElementById(id) {
        if (!elementos.has(id)) elementos.set(id, {style: {}, listeners: {},
            addEventListener(nome, fn) { this.listeners[nome] = fn; }});
        return elementos.get(id);
    },
    querySelectorAll() { return []; },
};
const fonte = html.slice(html.indexOf('function atualizarControleDarkSouls('), html.indexOf('function renderModelos('));
const aplicar = new Function('document', 'atualizarBtnProativo', fonte + '; return aplicarEstadoConfig;')(document, () => {});
const controle = document.getElementById('cfg-dark-souls');
const status = document.getElementById('cfg-dark-souls-status');
aplicar({proativo: true, tarefas: {jogos: true}, dark_souls: true});
assert.strictEqual(controle.checked, true);
assert.strictEqual(controle.disabled, false);
aplicar({proativo: false, tarefas: {jogos: true}, dark_souls: true});
assert.strictEqual(document.getElementById('cfg-proativo-pausado').hidden, false);
assert.notStrictEqual(document.getElementById('secao-tarefas').style.display, 'none');
assert.match(status.textContent, /Proativo desligado/);
aplicar({proativo: true, tarefas: {jogos: false}, dark_souls: true});
assert.match(status.textContent, /Monitorar jogos/);
aplicar({proativo: true, dark_souls: false});
assert.strictEqual(controle.checked, false);
assert.match(status.textContent, /desligado/);
aplicar({proativo: true});
assert.strictEqual(controle.disabled, true, 'Servidor antigo não pode aparentar salvar um controle novo');
assert.match(status.textContent, /Reinicie/);

const inicio = html.indexOf("document.getElementById('cfg-dark-souls').addEventListener('change'");
const handler = html.slice(inicio, html.indexOf('// Task toggles', inicio));
const enviados = [];
new Function('document', 'enviarConfig', handler)(document, dados => enviados.push(dados));
aplicar({dark_souls: false});
controle.checked = true;
controle.listeners.change.call(controle);
assert.deepStrictEqual(enviados, [{config: 'dark_souls', valor: true}]);
assert.strictEqual(controle.disabled, true, 'Aguarda confirmação do servidor');
aplicar({dark_souls: true});
assert.strictEqual(controle.disabled, false);
controle.checked = false;
controle.listeners.change.call(controle);
assert.deepStrictEqual(enviados.at(-1), {config: 'dark_souls', valor: false});
aplicar({dark_souls: true, dark_souls_erro: 'Não foi possível salvar'});
assert.strictEqual(controle.checked, true, 'Falha restaura o estado real');
assert.match(status.textContent, /salvar/);
new Function('document', 'enviarConfig', handler)(document, () => {throw Error('offline');});
controle.checked = false;
controle.listeners.change.call(controle);
assert.strictEqual(controle.checked, true);
assert.strictEqual(controle.disabled, false);
assert.match(status.textContent, /Sem conexão/);
console.log('PASSOU: controle visível, estado confirmado, ativação, desativação e erro de gravação');
