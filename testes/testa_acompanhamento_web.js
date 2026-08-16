/** Card de acompanhamento existe e envia ações identificadas ao backend. */
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
const servidor = fs.readFileSync(path.join(__dirname, '..', 'servidor.py'), 'utf8');
const main = fs.readFileSync(path.join(__dirname, '..', 'main.py'), 'utf8');
const pensar = fs.readFileSync(path.join(__dirname, '..', 'modulos', 'pensar.py'), 'utf8');
const exigidos = [
    'id="acompanhamento-card"',
    "comando: 'acompanhamento_acao'",
    "comando: 'acompanhamento_cancelar'",
    "dados.tipo === 'acompanhamentos'",
    "'Acompanhar resultado'",
    "'Só comentei'",
    "'Resolvido'",
    "'Semana que vem'",
];

for (const trecho of exigidos) {
    if (!html.includes(trecho)) {
        console.log('FALHA: faltou contrato do acompanhamento web:', trecho);
        process.exit(1);
    }
}

const continuidade = [
    [servidor, 'registrar_handler_acompanhamento_web'],
    [main, 'responder_clique_acompanhamento'],
    [pensar, 'ACOMPANHAMENTO_CONFIRMADO:'],
    [pensar, 'ACOMPANHAMENTO_DESCARTADO:'],
];
for (const [fonte, trecho] of continuidade) {
    if (!fonte.includes(trecho)) {
        console.log('FALHA: clique resolve estado, mas não continua a conversa:', trecho);
        process.exit(1);
    }
}

console.log('PASSOU: card resolve o estado e entrega o clique de volta à conversa');
