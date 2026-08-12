// Regressão visual: ouvir precisa ter assinatura própria, não só girar mais rápido que idle.
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

function diz(ok, msg) {
    if (!ok) { console.error('  FALHOU:', msg); process.exitCode = 1; }
}

diz(html.includes('#presenca.est-ouvindo #orbita rect:nth-child(4n+1)'),
    'as quatro bolas grandes funcionam como sensores durante a escuta');
diz(html.includes('animation: escuta-sensor .85s ease-in-out infinite alternate'),
    'os sensores pulsam enquanto o microfone está aberto');
diz(html.includes('animation: escuta-membrana 1.35s ease-in-out infinite alternate'),
    'os arcos respiram como uma membrana durante a escuta');
diz(html.includes('#presenca.est-ouvindo { --cor-halo: #9edcff; }'),
    'o halo de escuta tem cor distinta do repouso');
