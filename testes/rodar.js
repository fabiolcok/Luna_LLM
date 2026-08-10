#!/usr/bin/env node
/**
 * Roda a suíte inteira da presença.
 *
 *     node testes/rodar.js
 *
 * Sem dependência nenhuma — só Node. Cada teste extrai o <script> do Index.html na hora e
 * EXECUTA com um DOM falso. É isso que pega o erro que mais dói aqui: usar `let`/`const` antes
 * da declaração derruba o script INTEIRO e a interface abre em branco, sem mensagem nenhuma.
 * `node --check` não vê isso (a sintaxe é válida); só executando.
 */
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const testes = fs.readdirSync(__dirname)
    .filter(f => f.startsWith('testa_') && f.endsWith('.js'))
    .sort();
testes.unshift('checa.js');            // o de carga vem primeiro: se ele falha, o resto é ruído

let falhou = 0;
for (const t of testes) {
    process.stdout.write('  ' + t.replace(/\.js$/, '').padEnd(18));
    try {
        const saida = execFileSync(process.execPath, [path.join(__dirname, t)],
                                   { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
        const ultima = saida.trim().split('\n').pop();
        console.log(ultima.includes('PASSOU') || ultima.includes('sem ReferenceError')
                    ? 'ok' : ultima);
    } catch (e) {
        falhou++;
        console.log('FALHOU');
        // só as linhas que interessam, pra saída não virar um muro
        const txt = ((e.stdout || '') + (e.stderr || '')).trim();
        txt.split('\n').filter(l => /FALHA|QUEBROU|Error/.test(l))
           .slice(0, 8).forEach(l => console.log('       ' + l.trim()));
    }
}

console.log();
if (falhou) { console.log('❌ ' + falhou + ' de ' + testes.length + ' falharam'); process.exit(1); }
console.log('✅ ' + testes.length + ' arquivos, tudo passou');
