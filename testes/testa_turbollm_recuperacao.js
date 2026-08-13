#!/usr/bin/env node
// Contrato de integração: chamadas de conversa precisam passar pelo recuperador de cold-start.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const pensar = fs.readFileSync(path.join(__dirname, '..', 'modulos', 'pensar.py'), 'utf8');

assert.ok(pensar.includes('def _chamar_llm(**parametros):'),
          'FALHA: pensar.py perdeu o ponto único de recuperação do modelo frio');
assert.ok(pensar.includes('if not erro_modelo_descarregado(erro):'),
          'FALHA: a recuperação deixou de distinguir o idle-unload de outros erros');
assert.ok(pensar.includes('Não adota w.model'),
          'FALHA: o warm-up pode voltar a trocar a chave estável pelo caminho do GGUF');
assert.ok(pensar.includes('config_env.texto("MODELO_THINKING", "desligado")'),
          'FALHA: a escolha do modo de pensamento saiu do .env');
assert.ok(!pensar.includes('extra_body=THINK_OFF'),
          'FALHA: uma chamada ainda está presa à configuração antiga do Gemma');

for (const chamada of ['r = _chamar_llm(', 'resposta = _chamar_llm(',
                        'resposta_ferramenta = _chamar_llm(']) {
    assert.ok(pensar.includes(chamada),
              `FALHA: chamada normal não usa a recuperação: ${chamada}`);
}

// Quatro chamadas diretas são seleção/warm-up (incluindo validar uma troca pelo painel);
// a quinta vive dentro do próprio wrapper.
// Se aparecer outra, alguma rota provavelmente voltou a ignorar a recuperação.
const diretas = pensar.match(/cliente\.chat\.completions\.create\(/g) || [];
assert.strictEqual(diretas.length, 5,
                   'FALHA: surgiu chamada direta ao TurboLLM fora do contrato esperado');

console.log('PASSOU — chamadas da Luna usam recuperação de modelo frio');
