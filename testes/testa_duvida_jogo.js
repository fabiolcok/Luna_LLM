#!/usr/bin/env node
// O roteador pode resolver o jogo pelo contexto, mas não pode fabricar uma dúvida de gameplay.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const raiz = path.join(__dirname, '..');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');
const habilidades = fs.readFileSync(path.join(raiz, 'modulos', 'habilidades.py'), 'utf8');

assert.ok(pensar.includes('validar_pedido_gameplay(') &&
          pensar.includes('_args_guard.get("trecho_pedido", "")') &&
          pensar.includes('dúvida de jogo sem evidência literal de pedido') &&
          pensar.includes('_jogo_contexto_guard = str(') &&
          pensar.includes('_args_guard.get("nome_jogo") or _contexto_gameplay.get("nome_jogo")') &&
          pensar.includes('nome_contexto=_jogo_contexto_guard'),
          'FALHA: comentário sobre jogo pode voltar a acionar tutorial sem pedido');
assert.ok(/def duvida_do_jogo\(pergunta: str, nome_jogo: str = ""\)/.test(habilidades) &&
          /jogo = \(nome_jogo or ler_estado_luna\(\)\.get\("jogo_ativo"\)/.test(habilidades),
          'FALHA: dúvida de jogo voltou a depender exclusivamente do título aberto');
assert.ok(/"name": "duvida_do_jogo"[\s\S]*?"trecho_pedido"[\s\S]*?"nome_jogo"[\s\S]*?"required": \["pergunta", "trecho_pedido"\]/.test(habilidades),
          'FALHA: roteador não precisa provar literalmente o pedido ou passar o jogo do contexto');
assert.ok(pensar.includes('_turno_assistente["_ferramenta"] = "duvida_do_jogo"') &&
          pensar.includes('contexto_gameplay_anterior(historico)'),
          'FALHA: follow-up voltou a depender de palavras soltas em vez do contexto estruturado');

console.log('PASSOU — dúvida de gameplay exige pedido real e aceita jogo do contexto');
