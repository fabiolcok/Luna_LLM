#!/usr/bin/env node
// O roteador decide ferramentas; conversa e personalidade pertencem à segunda chamada.
const assert = require('assert');
const fs = require('fs');
const path = require('path');

// Os prompts sairam do pensar.py para o modulos/prompts.py (separados por eixo).
// A regra pode estar em qualquer um dos dois: o teste cobra o CONCEITO, nao o arquivo.
const leia = (nome) => fs.readFileSync(path.join(__dirname, '..', 'modulos', nome), 'utf8');
const pensar = leia('pensar.py') + leia('prompts.py');

assert.ok(pensar.includes('responda EXATAMENTE SEM_FERRAMENTA') &&
          pensar.includes('_cru != "SEM_FERRAMENTA"'),
          'FALHA: ausência de ferramenta não possui marcador curto ou ainda aparece como desvio');
assert.ok(pensar.includes('_max_tokens_roteador = max_tokens if modo_memoria else min(max_tokens, 256)') &&
          pensar.includes('max_tokens=_max_tokens_roteador'),
          'FALHA: roteador voltou a herdar o orçamento grande da persona');
assert.ok(pensar.includes('saudacao_simples = bool(re.fullmatch(') &&
          pensar.includes('O usuário fez somente uma saudação e perguntou como você está.') &&
          pensar.includes('puxe memória, perfil, programa aberto, jogo, backlog, trabalho'),
          'FALHA: saudação simples pode voltar a importar assunto do prompt ou da memória');

console.log('PASSOU — roteador fica curto e saudação continua na persona');
