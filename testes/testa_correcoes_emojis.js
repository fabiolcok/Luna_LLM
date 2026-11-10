const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');
const pasta = path.join(__dirname, '../static/piloto-emojis');
const contexto = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(pasta, 'correcoes.js'), 'utf8') +
    '\nglobalThis.api = {CORRECOES_EMOJIS, aplicarCorrecaoEmoji};', contexto);
const {CORRECOES_EMOJIS, aplicarCorrecaoEmoji} = contexto.api;
assert.equal(Object.keys(CORRECOES_EMOJIS).length, 15);
for (const codigo of Object.keys(CORRECOES_EMOJIS)) {
    const original = JSON.parse(fs.readFileSync(path.join(pasta, 'assets', codigo + '.json')));
    const referencia = structuredClone(original);
    aplicarCorrecaoEmoji(referencia, codigo, 'original');
    assert.deepEqual(referencia, original, 'Modo original preservado: ' + codigo);
    const copia = structuredClone(original);
    aplicarCorrecaoEmoji(copia, codigo, 'ciano');
    const comps = d => ({raiz: d.layers, ...Object.fromEntries((d.assets || []).filter(a => a.layers).map(a => [a.id, a.layers]))});
    const antes = comps(original), depois = comps(copia);
    for (const [nome, layers] of Object.entries(antes)) {
        for (const layer of layers.filter(l => l.td)) {
            assert.deepEqual(depois[nome].find(l => l.ind === layer.ind), layer, 'Máscara preservada: ' + codigo);
        }
    }
    for (const [nome, indices] of Object.entries(CORRECOES_EMOJIS[codigo].ocultar || {})) {
        for (const id of indices) assert.equal(depois[nome].find(l => l.ind === id).ks.o.k, 0);
    }
    for (const [nome, indices] of Object.entries(CORRECOES_EMOJIS[codigo].maos || {})) {
        for (const id of indices) assert.notDeepEqual(depois[nome].find(l => l.ind === id).shapes,
            antes[nome].find(l => l.ind === id).shapes, 'Mão recolorida: ' + codigo);
    }
}
console.log('ok');
