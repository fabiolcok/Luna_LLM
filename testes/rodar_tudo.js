#!/usr/bin/env node
/** Suíte completa: preserva o runner rápido e acrescenta os testes Python puros. */

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const testesDir = __dirname;
const raiz = path.join(testesDir, '..');
const pythonSite = process.platform === 'win32'
    ? path.join(raiz, 'venv', 'Lib', 'site-packages')
    : path.join(raiz, 'venv', 'lib');
const envPython = { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' };
const caminhosPython = [raiz];
if (fs.existsSync(pythonSite)) caminhosPython.push(pythonSite);
if (envPython.PYTHONPATH) caminhosPython.push(envPython.PYTHONPATH);
envPython.PYTHONPATH = caminhosPython.join(path.delimiter);

function candidatosPython() {
    const locais = process.platform === 'win32'
        ? [path.join(raiz, 'venv', 'Scripts', 'python.exe')]
        : [path.join(raiz, 'venv', 'bin', 'python')];
    const sistema = process.platform === 'win32'
        ? [{ comando: 'py', prefixo: ['-3.12'] }, { comando: 'python', prefixo: [] }]
        : [{ comando: 'python3', prefixo: [] }, { comando: 'python', prefixo: [] }];
    return locais.filter(fs.existsSync).map(comando => ({ comando, prefixo: [] })).concat(sistema);
}

function acharPython() {
    for (const candidato of candidatosPython()) {
        const teste = spawnSync(candidato.comando, [...candidato.prefixo, '-c',
            'import sys; print(sys.version_info[:2])'], {
            cwd: raiz, env: envPython, encoding: 'utf8', windowsHide: true,
        });
        if (teste.status === 0) return candidato;
    }
    return null;
}

console.log('── JavaScript / interface ──');
const rapido = spawnSync(process.execPath, [path.join(testesDir, 'rodar.js')], {
    cwd: raiz, encoding: 'utf8', stdio: 'inherit', windowsHide: true,
});
let falhou = rapido.status === 0 ? 0 : 1;

const arquivosJs = fs.readdirSync(testesDir)
    .filter(nome => nome === 'checa.js' || (nome.startsWith('testa_') && nome.endsWith('.js')));
const arquivosPy = fs.readdirSync(testesDir)
    .filter(nome => nome.startsWith('testa_') && nome.endsWith('.py'))
    .sort();

console.log('\n── Python / backend ──');
const python = acharPython();
if (!python) {
    console.log('  FALHOU: Python 3 não foi encontrado (venv, py -3.12, python3 ou python).');
    falhou++;
} else {
    console.log(`  intérprete: ${python.comando}${python.prefixo.length ? ' ' + python.prefixo.join(' ') : ''}`);
    for (const arquivo of arquivosPy) {
        const nome = arquivo.replace(/\.py$/, '');
        process.stdout.write('  ' + nome.padEnd(30));
        const execucao = spawnSync(python.comando,
            [...python.prefixo, '-m', `testes.${nome}`], {
                cwd: raiz, env: envPython, encoding: 'utf8', windowsHide: true,
            });
        if (execucao.status === 0) {
            console.log('ok');
            continue;
        }
        falhou++;
        console.log('FALHOU');
        const saida = `${execucao.stdout || ''}\n${execucao.stderr || ''}`.trim().split(/\r?\n/);
        const relevantes = saida.filter(linha => /FAIL|ERROR|Error|Traceback|Assertion/.test(linha));
        (relevantes.length ? relevantes : saida.slice(-8)).slice(0, 8)
            .forEach(linha => console.log('       ' + linha.trim()));
    }
}

console.log();
const total = arquivosJs.length + arquivosPy.length;
if (falhou) {
    console.log(`❌ suíte completa falhou em ${falhou} etapa(s)`);
    process.exit(1);
}
console.log(`✅ suíte completa: ${total} arquivos (${arquivosJs.length} JS + ${arquivosPy.length} Python)`);
