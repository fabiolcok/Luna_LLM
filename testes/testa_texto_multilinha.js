const fs = require('fs');
const assert = require('assert');

const html = fs.readFileSync('templates/Index.html', 'utf8');
// Os prompts sairam do pensar.py para o modulos/prompts.py (separados por eixo).
// A regra pode estar em qualquer um dos dois: o teste cobra o CONCEITO, nao o arquivo.
const pensar = fs.readFileSync('modulos/pensar.py', 'utf8')
              + fs.readFileSync('modulos/prompts.py', 'utf8');

assert.ok(
    html.includes('<textarea id="texto-input"') &&
    html.includes("if (e.key === 'Enter' && !e.shiftKey)") &&
    html.includes("textoInput.addEventListener('input', ajustarAlturaTexto)") &&
    html.includes("Math.min(textoInput.scrollHeight || 42, 132)"),
    'FALHA: a entrada web não oferece Shift+Enter e crescimento limitado'
);

assert.ok(
    /#usuario-texto[^}]*white-space:\s*pre-wrap/.test(html),
    'FALHA: as quebras de linha do usuário não são preservadas no web'
);

assert.ok(
    pensar.includes('ideias em blocos curtos com uma linha em branco') &&
    pensar.includes('não entregue uma parede de texto'),
    'FALHA: o canal de texto não orienta parágrafos legíveis em respostas longas'
);

console.log('  testa_texto_multilinha ok');
