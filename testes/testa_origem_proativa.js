#!/usr/bin/env node
// A origem precisa viajar com a fala; status global muda antes de o balão ser registrado.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const raiz = path.join(__dirname, '..');
const proativa = fs.readFileSync(path.join(raiz, 'modulos', 'proativa.py'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');
const html = fs.readFileSync(path.join(raiz, 'templates', 'Index.html'), 'utf8');

assert.ok(proativa.includes('class _FalaProativa(str)') &&
          proativa.includes('return _FalaProativa(resposta, tarefa) if resposta else None') &&
          proativa.includes('origem_proativa=getattr(texto_resposta, "origem_proativa", "")'),
          'FALHA: tarefa proativa não acompanha o texto até o servidor');
assert.ok(/def _registrar_turno\([^)]*origem_proativa/s.test(servidor) &&
          servidor.includes('turno["origem_proativa"] = origem_proativa'),
          'FALHA: histórico não preserva a origem daquela fala proativa');
assert.ok(html.includes('luna.dataset.origemProativa = turno.origem_proativa') &&
          /content:\s*'Luna · Proativo: '\s*attr\(data-origem-proativa\)/.test(html) &&
          /\.turno-luna\[data-origem-proativa\]::before\s*\{[^}]*text-transform:\s*none/s.test(html),
          'FALHA: balão não mostra a origem proativa registrada');

console.log('PASSOU — cada fala proativa mostra a tarefa que realmente a originou');
