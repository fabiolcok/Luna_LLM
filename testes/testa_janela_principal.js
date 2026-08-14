#!/usr/bin/env node
// A janela web deve voltar ao tamanho e lugar escolhidos, sem versionar preferência local.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const main = fs.readFileSync(path.join(raiz, 'main.py'), 'utf8');
const ignore = fs.readFileSync(path.join(raiz, '.gitignore'), 'utf8');

assert.ok(main.includes('import json'),
          'FALHA: persistência da janela usa JSON sem importar o módulo');
assert.ok(main.includes('modelos", "janela_principal.json"') &&
          main.includes('class _GeometriaJanela:'),
          'FALHA: janela principal não possui configuração local');
assert.ok(main.includes('janela.events.moved += geometria.mover') &&
          main.includes('janela.events.resized += geometria.redimensionar'),
          'FALHA: mover e redimensionar não atualizam a configuração');
assert.ok(main.includes('**janela_kwargs') &&
          main.includes('janela_kwargs.update(x=geometria.dados["x"]'),
          'FALHA: posição e tamanho salvos não são restaurados no boot');
assert.ok(main.includes('380 <= largura <= 4000') && main.includes('520 <= altura <= 2400'),
          'FALHA: geometria corrompida pode tornar a janela inutilizável');
assert.ok(ignore.includes('modelos/janela_principal.json'),
          'FALHA: preferência pessoal da janela pode ir para o Git');

console.log('PASSOU — janela principal restaura posição e tamanho locais');
