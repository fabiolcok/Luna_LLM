/** Card de acompanhamento existe e envia ações identificadas ao backend. */
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
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

console.log('PASSOU: card e ações de acompanhamento estão ligados ao WebSocket');
