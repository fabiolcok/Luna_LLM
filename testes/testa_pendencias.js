const fs = require('fs');
const assert = require('assert');

const habilidades = fs.readFileSync('modulos/habilidades.py', 'utf8');
const pensar = fs.readFileSync('modulos/pensar.py', 'utf8');
const obsidian = fs.readFileSync('modulos/obsidian.py', 'utf8');
const pendencias = fs.readFileSync('modulos/pendencias.py', 'utf8');

assert.ok(habilidades.includes('"name": "consultar_pendencias"') &&
          habilidades.includes('Para perguntar APENAS o que há na agenda'),
          'FALHA: o roteador não distingue pendências amplas de agenda');
assert.ok(pensar.includes('"consultar_pendencias": pendencias.consultar') &&
          pensar.includes('não chame') &&
          pensar.includes('aniversário ou outro compromisso de tarefa atrasada'),
          'FALHA: consulta de pendências não está ligada à persona com categorias seguras');
assert.ok(obsidian.includes('def listar_tarefas_pendentes(') &&
          obsidian.includes("r'^\\s*[-*]\\s*\\[\\s*\\]"),
          'FALHA: Obsidian não procura checkboxes realmente abertas');
assert.ok(pendencias.includes('COMPROMISSOS FUTUROS NA AGENDA') &&
          pendencias.includes('ACOMPANHAMENTOS ESPERANDO DESFECHO'),
          'FALHA: consulta ampla não reúne as três categorias');

console.log('  testa_pendencias ok');
