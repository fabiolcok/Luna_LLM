const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates/Index.html'), 'utf8');
function elemento(dataset = {}) {
    const classes = new Set();
    return {dataset, hidden: true, value: '', textContent: '', attrs: {}, listeners: {},
        classList: {add: (...c) => c.forEach(x => classes.add(x)),
            remove: (...c) => c.forEach(x => classes.delete(x)), contains: c => classes.has(c)},
        setAttribute(k, v) {this.attrs[k] = v;},
        addEventListener(k, fn) {this.listeners[k] = fn;},
        click() {if (this.onclick) this.onclick(); else this.listeners.click.call(this);}};
}
const ids = Object.fromEntries(['aval-motivo', 'aval-motivo-input', 'aval-alvo', 'aval-categorias',
    'aval-motivo-enviar', 'aval-motivo-fechar'].map(id => [id, elemento()]));
const votos = ['bom', 'ruim'].map(rating => elemento({rating}));
const categorias = [...html.matchAll(/<button[^>]*data-categoria="([^"]+)"[^>]*data-voto="([^"]+)"[^>]*>/g)]
    .map(([, categoria, voto]) => elemento({categoria, voto}));
const categoria = nome => categorias.find(b => b.dataset.categoria === nome);
const visiveis = () => categorias.filter(b => !b.hidden).map(b => b.dataset.categoria);
const positivas = ['humor_bom', 'resposta_util', 'tom_bom', 'entendeu_contexto', 'boa_iniciativa'];
const negativas = ['humor_ruim', 'nao_ajudou', 'tom_inadequado', 'perdeu_assunto',
    'hora_ruim', 'inventou_informacao', 'repetitiva'];
const enviados = [];
const contexto = vm.createContext({
    document: {getElementById: id => ids[id], querySelectorAll: q => q.includes('data-rating') ? votos : categorias},
    socket: {send: texto => enviados.push(JSON.parse(texto))},
});
vm.runInContext(html.slice(html.indexOf('const botoesAval ='), html.indexOf('// 🔊 Repetir a última fala')), contexto);
const executar = codigo => vm.runInContext(codigo, contexto);
votos[0].click();
assert.equal(enviados.length, 0, 'Sem resposta não existe alvo');
executar('definirAlvoAvaliacao({id:"A", luna:"Filme A"})');
votos[1].click();
assert.equal(enviados.at(-1).turno_id, 'A');
assert.deepEqual(visiveis(), negativas, 'O voto ruim só mostra motivos negativos');
assert.equal(ids['aval-categorias'].attrs['aria-label'], 'O que não funcionou?');
ids['aval-motivo-input'].value = 'Confundiu o filme';
executar('definirAlvoAvaliacao({id:"B", luna:"Notícia B"}); limparAval()');
assert.equal(ids['aval-motivo-input'].value, 'Confundiu o filme');
assert.ok(ids['aval-motivo'].classList.contains('ativo'));
assert.deepEqual(visiveis(), negativas, 'Outra resposta não muda os motivos do voto em andamento');
categoria('perdeu_assunto').click();
assert.deepEqual(enviados.at(-1).categorias, ['perdeu_assunto']);
assert.equal(enviados.at(-1).turno_id, 'A', 'Nova fala não rouba o comentário');
ids['aval-motivo-enviar'].click();
assert.equal(enviados.at(-1).motivo, 'Confundiu o filme');
assert.equal(enviados.at(-1).turno_id, 'A');
assert.ok(!ids['aval-motivo'].classList.contains('ativo'));
votos[0].click();
assert.equal(enviados.at(-1).turno_id, 'B');
assert.equal(ids['aval-motivo-input'].value, '', 'O comentário não deve passar para outra resposta');
assert.deepEqual(visiveis(), positivas, 'O voto bom só mostra motivos positivos');
assert.equal(ids['aval-categorias'].attrs['aria-label'], 'O que funcionou?');
const antesCategoriaOculta = enviados.length;
categoria('perdeu_assunto').click();
assert.equal(enviados.length, antesCategoriaOculta, 'Categoria oculta não altera o voto');
categoria('humor_bom').click();
assert.deepEqual(enviados.at(-1).categorias, ['humor_bom']);
categoria('humor_bom').click();
assert.deepEqual(enviados.at(-1).categorias, []);
categoria('entendeu_contexto').click();
categoria('boa_iniciativa').click();
assert.deepEqual(enviados.at(-1).categorias, ['entendeu_contexto', 'boa_iniciativa']);
ids['aval-motivo-input'].value = 'Entendeu, mas o tom incomodou';
votos[1].click();
assert.equal(enviados.at(-1).rating, 'ruim');
assert.equal(enviados.at(-1).motivo, 'Entendeu, mas o tom incomodou');
assert.deepEqual(enviados.at(-1).categorias, [], 'Trocar o voto limpa as categorias anteriores');
assert.ok(categorias.every(b => b.attrs['aria-pressed'] === 'false'));
assert.deepEqual(visiveis(), negativas);
categoria('nao_ajudou').click();
categoria('tom_inadequado').click();
assert.deepEqual(enviados.at(-1).categorias, ['nao_ajudou', 'tom_inadequado']);
votos[0].click();
assert.deepEqual(enviados.at(-1).categorias, []);
assert.deepEqual(visiveis(), positivas);
ids['aval-motivo-input'].value = 'Gostei';
ids['aval-motivo-fechar'].click();
assert.equal(enviados.at(-1).motivo, 'Gostei');
executar('definirAlvoAvaliacao(undefined)');
const quantidade = enviados.length;
votos[0].click();
assert.equal(enviados.length, quantidade);
console.log('PASSOU: alvo fixo, motivos por voto, seleção múltipla, troca de voto e rascunho');
