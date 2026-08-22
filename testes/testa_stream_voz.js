#!/usr/bin/env node
// Contratos do TTS incremental: frases completas, duas filas e uso restrito ao loop de voz.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const raiz = path.join(__dirname, '..');
const main = fs.readFileSync(path.join(raiz, 'main.py'), 'utf8');
const falar = fs.readFileSync(path.join(raiz, 'modulos', 'falar.py'), 'utf8');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');
const telegram = fs.readFileSync(path.join(raiz, 'modulos', 'telegram_bot.py'), 'utf8');

assert.ok(falar.includes('class FalaEmFluxo:') &&
          falar.includes('self._textos = queue.Queue()') &&
          falar.includes('self._audios = queue.Queue()') &&
          falar.includes('target=self._rodar_sintese') &&
          falar.includes('target=self._rodar_audio'),
          'FALHA: TTS deixou de sintetizar a próxima frase enquanto toca a anterior');
assert.ok(main.includes('fala_fluxo = FalaEmFluxo(') &&
          main.includes('_enfileirar_fala.finalizar = fala_fluxo.finalizar') &&
          /def _enfileirar_fala[\s\S]*?fala_fluxo\.receber\(fragmento\)[\s\S]*?atualizar_stream_resposta\(fragmento\)/.test(main) &&
          /gerar_resposta\([\s\S]*?ao_fragmento=_enfileirar_fala/.test(main) &&
          main.includes('fala_fluxo.aguardar()'),
          'FALHA: conversa por voz deixou de alimentar ou aguardar o TTS incremental');
assert.ok(pensar.includes('getattr(ao_fragmento, "finalizar", None)') &&
          pensar.includes('_finalizar_stream(texto_luna)'),
          'FALHA: fim da persona não entrega o último trecho ao TTS');
assert.ok(falar.includes('sd.stop()') &&
          main.includes('fala_fluxo.cancelar()') &&
          /except GeracaoInterrompida:[\s\S]*?fala_fluxo\.cancelar\(\)[\s\S]*?atualizar_stream_interrompido\(\)/.test(main) &&
          main.includes('_enfileirar_fala.cancelado = _interromper.is_set'),
          'FALHA: interrupção não encerra geração, síntese e áudio do fluxo');
assert.ok(!telegram.includes('FalaEmFluxo') && !telegram.includes('ao_fragmento='),
          'FALHA: Telegram recebeu streaming de voz sem suporte do canal');

console.log('PASSOU — TTS usa frases completas com síntese e áudio em paralelo');
