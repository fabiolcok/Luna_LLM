#!/usr/bin/env node
// Texto digitado não toca TTS, mas não pode ficar invisível no terminal de diagnóstico.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const fonte = fs.readFileSync(path.join(__dirname, '..', 'main.py'), 'utf8');

assert.ok(fonte.includes('def _mostrar_resposta_web_no_terminal(texto: str):'),
          'FALHA: resposta digitada perdeu o banner do CMD');
assert.ok(fonte.includes('[🌚💬 Luna respondeu]'),
          'FALHA: banner do texto web não identifica a resposta da Luna');

const trecho = fonte.slice(fonte.indexOf('def responder_texto_web'),
                           fonte.indexOf('\ndef loop_voz'));
const chamadas = trecho.match(/_mostrar_resposta_web_no_terminal\(/g) || [];
assert.strictEqual(chamadas.length, 2,
                   'FALHA: resposta normal e acompanhamento precisam aparecer no CMD');
assert.ok(!trecho.includes('falar_texto('),
          'FALHA: digitar no web passou a tocar áudio sem decisão explícita');

console.log('PASSOU — resposta web volta a aparecer no terminal sem ligar TTS');
