#!/usr/bin/env node
// A personalidade pode opinar, mas não deve recusar tarefas banais nem mandar Markdown ao TTS.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const pensar = fs.readFileSync(path.join(__dirname, '..', 'modulos', 'pensar.py'), 'utf8');

assert.ok(pensar.includes('AUTONOMIA NÃO É BIRRA') &&
          pensar.includes('pedido simples, seguro e possível deve ser atendido'),
          'FALHA: opinião voltou a servir como desculpa para recusar pedido simples');
assert.ok(pensar.includes('CANAL DE TEXTO (Web ou Telegram)') &&
          !pensar.includes('Formatação e Markdown dependem do canal') &&
          !pensar.includes('Markdown, tabela, lista, título ou bloco de código'),
          'FALHA: canal de texto voltou a gastar prompt explicando uma capacidade natural');
assert.ok(pensar.includes('CANAL DE VOZ:') &&
          pensar.includes('Use somente texto falável: sem emojis, Markdown'),
          'FALHA: emojis ou Markdown podem vazar para o TTS');
assert.ok(!pensar.includes('Sem emojis, asteriscos ou markdown.'),
          'FALHA: proibição global ainda contradiz o canal de texto');
assert.ok(!pensar.includes('"- Sem emojis.\\n"'),
          'FALHA: canal de texto voltou a gastar prompt proibindo emojis');
assert.ok(pensar.includes('regra_emoji_enxuta = " e não use emoji" if not responder_completo else ""') &&
          pensar.includes('f"Não cumprimente{regra_emoji_enxuta}.'),
          'FALHA: prompt curto voltou a proibir emoji também nos canais de texto');
assert.ok(pensar.includes('return texto_luna if responder_completo else limpar_texto_para_voz(texto_luna)') &&
          pensar.includes('return resposta_tecnica if responder_completo else limpar_texto_para_voz(resposta_tecnica)'),
          'FALHA: limpeza final do TTS voltou a apagar o Markdown do Web/Telegram');

console.log('PASSOU — pedido simples é atendido e Markdown respeita o canal');
