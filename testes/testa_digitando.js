#!/usr/bin/env node
// Resposta somente em texto tem assinatura visual própria, sem fingir fala.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(raiz, 'templates', 'Index.html'), 'utf8');
const main = fs.readFileSync(path.join(raiz, 'main.py'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');

assert.ok(html.includes("'digitando'") &&
          html.includes("moverBolasDigitando(estado === 'digitando')"),
          'FALHA: resposta escrita não tem estado visual próprio');
assert.ok(html.includes('data-lab="digitando"') &&
          html.includes("digitando:function () { aplicarPresenca('digitando'); }"),
          'FALHA: laboratório não consegue demonstrar o estado digitando');
assert.ok(servidor.includes('"falando", "digitando", "afk"'),
          'FALHA: servidor bloqueia o botão digitando do laboratório');
assert.ok(html.includes("document.querySelectorAll('#orbita rect:nth-child(4n+1)')") &&
          html.includes('x: entrando ? 72 + i * 18') && html.includes('y: entrando ? 172'),
          'FALHA: as quatro bolas grandes não descem suavemente para a base');
assert.ok(html.includes('@keyframes digita-tecla') &&
          html.includes('animation: digita-tecla .42s') &&
          html.includes('animation-delay: calc(var(--d-rand) * -.42s)'),
          'FALHA: as teclas não piscam em branco num ritmo irregular');
assert.ok(html.includes("classList.contains('est-digitando')") &&
          html.includes('leituraX = Math.sin(agora / 520 * Math.PI) * 2.2'),
          'FALHA: o rosto não acompanha a escrita com movimento curto');

const trecho = main.slice(main.indexOf('def responder_texto_web'), main.indexOf('\ndef loop_voz'));
assert.ok(trecho.includes('atualizar_estado_rosto("digitando")') &&
          trecho.includes('min(9.0, max(4.0, len(resposta) * 0.03))'),
          'FALHA: backend não sustenta a animação enquanto o texto aparece');
assert.ok(!trecho.includes('falar_texto('),
          'FALHA: estado digitando ligou o TTS');

console.log('PASSOU — texto usa animação de digitação sem tocar voz');
