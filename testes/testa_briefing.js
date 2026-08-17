#!/usr/bin/env node
// O briefing junta fontes existentes sem consumir os estados dos radares proativos.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const briefing = fs.readFileSync(path.join(raiz, 'modulos', 'briefing.py'), 'utf8');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');
const habilidades = fs.readFileSync(path.join(raiz, 'modulos', 'habilidades.py'), 'utf8');

assert.ok(habilidades.includes('"name": "briefing_diario"') &&
          habilidades.includes("o que tem pra mim hoje?"),
          'FALHA: roteador não conhece o pedido de briefing diário');
assert.ok(pensar.includes('"briefing_diario": briefing.consultar') &&
          pensar.includes('nome_funcao == "briefing_diario"'),
          'FALHA: briefing não possui executor e tratamento de persona próprios');
for (const fonte of ['obter_previsao_tempo', 'ler_agenda_google', 'animes.consultar',
                     'acompanhamentos.estado_interface', '_ler_nota("Novidades")',
                     '_ler_nota("Promocoes")']) {
    assert.ok(briefing.includes(fonte), 'FALHA: fonte ausente do briefing: ' + fonte);
}
assert.ok(!briefing.includes('salvar_vistos') && !briefing.includes('registrar_pergunta'),
          'FALHA: consultar o briefing pode consumir um aviso proativo');
assert.ok(pensar.includes('UMA pergunta curta e específica'),
          'FALHA: briefing perdeu o gancho conversacional específico');
assert.ok(pensar.includes('Clima é informação, não pretexto para cobrar foco'),
          'FALHA: briefing pode transformar previsão do tempo em cobrança de produtividade');

console.log('PASSOU — briefing agrega fontes sem consumir proativos e abre continuação');
