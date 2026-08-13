#!/usr/bin/env node
// Contrato do placar local: uso, falha e avaliação devem convergir por ferramenta.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const raiz = path.join(__dirname, '..');
const metricas = fs.readFileSync(path.join(raiz, 'modulos', 'metricas_ferramentas.py'), 'utf8');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');

assert.ok(metricas.includes('uso_ferramentas.jsonl') &&
          metricas.includes('uso_ferramentas_resumo.json'),
          'FALHA: métricas não têm histórico incremental e resumo legível');
for (const campo of ['"usos"', '"sucessos"', '"erros"', '"avaliacoes_bom"', '"avaliacoes_ruim"']) {
    assert.ok(metricas.includes(campo), `FALHA: resumo perdeu o campo ${campo}`);
}
assert.ok(pensar.includes('metricas_ferramentas.registrar_uso(') &&
          pensar.includes('time.time() - inicio_ferramenta'),
          'FALHA: execução não registra uso e duração');
assert.ok(servidor.includes('metricas_ferramentas.vincular_avaliacao(') &&
          servidor.includes('registro["ferramenta"] = ferramenta'),
          'FALHA: 👍/👎 não é associado à ferramenta no log de avaliações');
assert.ok(metricas.includes('if uso["id"] in _avaliados:'),
          'FALHA: o motivo posterior do 👎 pode contar a mesma avaliação duas vezes');

console.log('PASSOU — uso e avaliação das ferramentas alimentam o placar local');
