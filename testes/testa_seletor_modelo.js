#!/usr/bin/env node
// Contrato mínimo entre painel web, WebSocket e troca de modelo no Python.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(raiz, 'templates', 'Index.html'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');

for (const id of ['cfg-modelo', 'cfg-modelo-thinking', 'modelo-aplicar', 'modelo-status']) {
    assert.ok(html.includes(`id="${id}"`), `FALHA: seletor perdeu #${id}`);
}
assert.ok(html.includes("comando: 'modelo_trocar'"),
          'FALHA: botão não envia a troca ao servidor');
assert.ok(html.includes("comando: 'modelos_listar'"),
          'FALHA: painel não solicita a biblioteca do TurboLLM');
assert.ok(servidor.includes("dados.get('comando') == 'modelo_trocar'"),
          'FALHA: servidor não recebe a troca de modelo');
assert.ok(servidor.includes('if not _eh_local:'),
          'FALHA: troca de modelo deixou de ser restrita ao próprio PC');
assert.ok(pensar.includes('if _modelo_env:'),
          'FALHA: MODELO_LLM deixou de bloquear a escolha local');
assert.ok(pensar.includes('"modelo_local", "config_luna.json"') ||
          pensar.includes('dados.get("modelo_local")'),
          'FALHA: escolha local deixou de ser recuperada na inicialização');

console.log('PASSOU — seletor de modelo mantém os contratos web/Python');
