// Easter egg em duas camadas: insistir durante a encarada aumenta a cara por 10 segundos.
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

let ok = true;
function diz(cond, msg) {
  if (!cond) ok = false;
  console.log((cond ? '  OK   ' : '  FALHA') + '  ' + msg);
}

diz(html.includes('ENCARADA_CLIQUES = 10') && html.includes('ENCARADA_JANELA = 3000'),
    'exige dez cutucadas deliberadas em até três segundos durante a encarada');
diz(html.includes('ENCARADA_GIGANTE_MS = 10000'), 'a encarada gigante dura dez segundos');
diz(html.includes('#presenca.encarada-gigante #rosto-txt'), 'somente o rosto cresce');
diz(html.includes('transform: scale(2.65)'), 'o rosto ocupa quase toda a lua');
diz(html.includes('if (_encaradaGigante) return;'), 'cliques extras não reiniciam o efeito');
diz(html.includes("pres.classList.remove('encarada-gigante');       // encolhe ainda encarando"),
    'primeiro volta ao tamanho normal ainda com ≖_≖');
diz(html.includes("rostoDireto('• _ •');                       // alivia antes de voltar ao repouso"),
    'depois da encarada normal passa por • _ •');
diz(html.includes('ENCARADA_GIGANTE_MS + ENCARADA_NORMAL_MS + ENCARADA_ALIVIO_MS'),
    'só depois do alívio retorna ao idle');
diz(html.includes("if (_encaradaGigante) limparReacaoClique();") &&
    html.includes("if (pres) pres.classList.remove('encarada-gigante');"),
    'arrastar durante a encarada desfaz o zoom antes de trocar o rosto');
diz(/function limparReacaoClique\(\)[\s\S]*?_encaradaGigante = false;/.test(html),
    'cancelar os timers também encerra o estado gigante');
diz(html.includes("if (estado !== 'dormindo' && _encaradaGigante) limparReacaoClique();"),
    'ouvir, pensar ou falar interrompe a encarada gigante');
diz(/function aplicarFerramenta\(statusTxt\)[\s\S]*?if \(_encaradaGigante\) limparReacaoClique\(\);/.test(html),
    'ferramentas e proativos interrompem a encarada gigante');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
