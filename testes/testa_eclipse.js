// O eclipse precisa continuar raro, diurno e atrás da cabeça. Este teste trava as decisões
// visuais e as proteções que impedem o passageiro de atropelar conversa ou outro evento.
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

let ok = true;
function diz(cond, msg) {
  if (!cond) ok = false;
  console.log((cond ? '  OK   ' : '  FALHA') + '  ' + msg);
}

diz(html.includes('id="eclipse"') && !html.includes('m-atras-cabeca'),
    'o Sol permanece redondo, sem máscara recortando suas bordas');
diz(html.includes('id="nucleo-eclipse"') &&
    html.indexOf('id="eclipse"') < html.indexOf('id="nucleo-eclipse"') &&
    html.indexOf('id="nucleo-eclipse"') < html.indexOf('id="halo"'),
    'há um disco lunar opaco entre o Sol e o halo, antes do rosto');
diz(html.includes('#presenca.eclipse #nucleo-eclipse { opacity: 1; }'),
    'o núcleo opaco só aparece durante o eclipse');
diz(html.includes('<circle cx="0" cy="0" r="78" fill="url(#g-eclipse)"/>'),
    'o disco do sol é maior que a cabeça da Luna');
diz(html.includes('duration: 20000'), 'a travessia rara acontece lentamente por vinte segundos');
diz(html.includes('borda * borda * (3 - 2 * borda)') && html.includes("opacidade.toFixed(3)"),
    'fade in e fade out usam uma curva suave e contínua');
diz(html.includes('Math.hypot(x - 100, y - 100) <= 155') &&
    html.includes("pres.classList.toggle('eclipse', ativar)"),
    'cor e óculos reagem à proximidade do Sol, não à duração inteira do evento');
diz(html.includes("if (pres.classList.contains('est-dormindo')) trocarRosto(ROSTO_ECLIPSE)"),
    'os óculos entram pela mesma transição suave usada para sair');
diz(html.includes('-100 + pos.p * 400') && html.includes('300 - pos.p * 400'),
    'o sol maior entra e sai completamente pelas bordas');
diz(html.includes('const arco = 2 * pos.p - 1') && html.includes('92 + arco * arco * 178'),
    'a trajetória nasce embaixo, sobe em arco e desce na outra ponta');
diz(html.includes("const ROSTO_ECLIPSE = '⌐■_■'") && html.includes('ROSTO_ECLIPSE,'),
    'a cara do eclipse existe e tem decisão explícita de não piscar');
diz(html.includes('h >= 6 && h < 20'), 'o sorteio só aceita o período diurno');
diz(html.includes("pres.classList.contains('est-dormindo')") &&
    html.includes("!pres.classList.contains('com-ferramenta')") &&
    html.includes("!pres.classList.contains('proat-radar')") && html.includes('!_afagando && !_desistiu'),
    'não começa durante conversa, ferramenta ou proativo');
diz(html.includes('2700000 + Math.random() * 2700000') && html.includes('Math.random() < 0.25'),
    'tenta em 45–90 minutos e somente uma em quatro tentativas acontece');
diz(html.includes('chaveHoraEclipse(agora) !== _ultimaHoraEclipse'),
    'não repete dentro da mesma hora');
diz(html.includes("else if (_rostoAtual === ROSTO_ECLIPSE && pres.classList.contains('est-dormindo'))"),
    'ao terminar não escreve por cima de uma conversa que começou durante a passagem');
diz(html.includes('eclipse:  function () { eclipse(true); }'),
    'o laboratório consegue disparar o eclipse sem esperar o sorteio');
diz(/#luna-bloco\s*\{[^}]*position:\s*relative;[^}]*z-index:\s*2;/.test(html),
    'a caixa da fala fica em uma camada acima do Sol quando ele desce');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
