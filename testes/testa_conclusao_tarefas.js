const fs = require('fs');
const assert = require('assert');

const habilidades = fs.readFileSync('modulos/habilidades.py', 'utf8');
const pensar = fs.readFileSync('modulos/pensar.py', 'utf8');
const main = fs.readFileSync('main.py', 'utf8');
const telegram = fs.readFileSync('modulos/telegram_bot.py', 'utf8');
const servidor = fs.readFileSync('servidor.py', 'utf8');
const html = fs.readFileSync('templates/Index.html', 'utf8');

assert.ok(habilidades.includes('"name": "concluir_tarefa_obsidian"') &&
          habilidades.includes('nunca diga que concluiu antes do próximo sim'),
          'FALHA: roteador não trata conclusão como proposta confirmável');
assert.ok(pensar.includes('"concluir_tarefa_obsidian": conclusao_tarefas.propor') &&
          pensar.includes('texto_resposta = resultado_str'),
          'FALHA: item exato pode ser reescrito pela persona depois de travado');
assert.ok((main.match(/conclusao_tarefas\.interceptar_resposta/g) || []).length >= 2 &&
          telegram.includes('conclusao_tarefas.interceptar_resposta'),
          'FALHA: confirmação não funciona igualmente em web, voz e Telegram');
assert.ok(servidor.includes("dados.get('comando') == 'conclusao_tarefa_acao'") &&
          html.includes("'conclusao_tarefa_acao'"),
          'FALHA: botões web não resolvem a mesma confirmação determinística');

console.log('  testa_conclusao_tarefas ok');
