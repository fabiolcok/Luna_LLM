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
const index = fs.readFileSync(path.join(raiz, 'templates', 'Index.html'), 'utf8');

assert.ok(main.includes('_mostrar_fragmento.cancelado = _interromper.is_set') &&
          main.includes('except GeracaoInterrompida:') &&
          main.includes('atualizar_stream_interrompido()') &&
          pensar.includes('resposta.close()') &&
          pensar.includes('raise GeracaoInterrompida()'),
          'FALHA: botão parar deixou de cancelar a geração Web real');
assert.ok(servidor.includes('"tipo": "resposta_stream_interrompida"'),
          'FALHA: backend deixou de avisar o navegador sobre geração interrompida');
assert.ok(main.includes('atualizar_stream_interrompido("falhou")'),
          'FALHA: resposta vazia pode deixar uma prévia de streaming presa');
assert.ok(index.includes("if (dados.tipo === 'resposta_stream_interrompida')") &&
          index.includes('function finalizarRespostaStreamInterrompida') &&
          index.includes("turno.classList.add('turno-incompleto')") &&
          index.includes('tempo.dataset.interrupcao = motivo') &&
          index.includes('b.disabled = true') && index.includes('b.disabled = false'),
          'FALHA: interface não preserva a prévia interrompida ou libera avaliação incompleta');
assert.ok(index.includes("socket.addEventListener('error'") &&
          index.includes("socket.addEventListener('close'") &&
          index.includes("aplicarPresenca('dormindo')"),
          'FALHA: queda do WebSocket pode deixar streaming ou mascote presos');

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
