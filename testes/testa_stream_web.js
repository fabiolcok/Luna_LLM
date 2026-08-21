#!/usr/bin/env node
// Garante que só o texto Web recebe fragmentos e que a prévia nunca vira histórico.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const raiz = path.join(__dirname, '..');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');
const main = fs.readFileSync(path.join(raiz, 'main.py'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');
const telegram = fs.readFileSync(path.join(raiz, 'modulos', 'telegram_bot.py'), 'utf8');

assert.ok(/def gerar_resposta\([^)]*ao_fragmento=None\)/s.test(pensar),
          'FALHA: persona perdeu o callback opcional de streaming');
assert.ok(/_chamar_llm\(stream=True, \*\*_parametros_persona\)/.test(pensar) &&
          /_visivel = _bruto\[:-20\]/.test(pensar),
          'FALHA: streaming deixou de usar a API ou voltou a expor metadados finais');
assert.ok(/def responder_texto_web[\s\S]*?def _mostrar_fragmento[\s\S]*?ao_fragmento=_mostrar_fragmento/.test(main) &&
          /def _mostrar_fragmento[\s\S]*?atualizar_estado_rosto\("digitando"\)[\s\S]*?atualizar_stream_resposta/.test(main),
          'FALHA: texto Web deixou de ligar o streaming da persona');
assert.ok(!telegram.includes('ao_fragmento='),
          'FALHA: Telegram passou a receber streaming sem suporte do canal');

const inicio = servidor.indexOf('def atualizar_stream_resposta(');
const fim = servidor.indexOf('\ndef ', inicio + 5);
const funcao = servidor.slice(inicio, fim);
assert.ok(funcao.includes('"tipo": "resposta_stream"') &&
          !funcao.includes('_registrar_turno') && !funcao.includes('_ultima_fala_luna'),
          'FALHA: prévia do streaming está contaminando histórico ou avaliação');

console.log('PASSOU — streaming fica restrito ao texto Web e só a resposta final é registrada');
