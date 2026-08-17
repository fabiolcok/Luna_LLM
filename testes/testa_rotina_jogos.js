#!/usr/bin/env node
// A rotina enriquece a fala Steam existente; nunca cria um segundo proativo.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const proativa = fs.readFileSync(path.join(raiz, 'modulos', 'proativa.py'), 'utf8');
const rotina = fs.readFileSync(path.join(raiz, 'modulos', 'rotina_jogos.py'), 'utf8');
const ignore = fs.readFileSync(path.join(raiz, '.gitignore'), 'utf8');

assert.ok(proativa.includes('rotina_jogos.registrar_abertura(appid, nome)') &&
          proativa.includes('rotina_jogos.registrar_fechamento(appid_antes, nome_antes, dur_min)'),
          'FALHA: monitor Steam não alimenta abertura e fechamento da rotina');
assert.ok(proativa.includes('info = "" if contexto_rotina else _steam_info_jogo(appid)'),
          'FALHA: marco de rotina voltou a competir com a sinopse inteira');
assert.ok(proativa.includes('Use NO MÁXIMO um dado') &&
          proativa.includes('CITE o número exato') &&
          proativa.includes('Steam abertura — dados'),
          'FALHA: rotina entrou sem prioridade ou diagnóstico de orçamento');
assert.ok(rotina.includes('_MARCOS_SESSAO = {3, 5, 10}') &&
          rotina.includes('sessoes > 10 and sessoes % 10 == 0'),
          'FALHA: rotina pode falar em toda abertura em vez de só nos marcos');
assert.ok(rotina.includes('mesma_sessao') && rotina.includes('12 * 3600'),
          'FALHA: reiniciar a Luna durante o jogo pode inflar a contagem de sessões');
assert.ok(ignore.includes('modelos/rotina_jogos.json'),
          'FALHA: rotina pessoal pode ser versionada no Git');

const chamadas = (proativa.match(/_gerar_fala_proativa\(prompt, f"steam_abriu_/g) || []).length;
assert.strictEqual(chamadas, 1,
                   'FALHA: rotina criou uma segunda fala ao abrir o jogo');

console.log('PASSOU — rotina compartilha a fala Steam com orçamento e marcos discretos');
