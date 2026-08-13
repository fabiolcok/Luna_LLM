// Os eventos precisam seguir o mascote visível sem criar dois sorteios nem zerar os relógios
// quando a interface troca do WebView2 principal para o widget Qt.
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(raiz, 'templates', 'Index.html'), 'utf8');
const main = fs.readFileSync(path.join(raiz, 'main.py'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');

let ok = true;
function diz(cond, msg) {
  if (!cond) ok = false;
  console.log((cond ? '  OK   ' : '  FALHA') + '  ' + msg);
}

const eventos = ['cometa', 'ovni', 'foguete', 'satelites', 'sujeira',
                  'chuva', 'cometao', 'invasao', 'eclipse'];
diz(eventos.every(nome => servidor.includes(`"${nome}": (`)),
    'todos os nove eventos possuem intervalo no relógio central');
diz(servidor.includes('time.monotonic()') &&
    servidor.includes('threading.Thread(target=_relogio_eventos_visuais, daemon=True)'),
    'um único relógio leve preserva os próximos disparos durante a troca de janela');
diz(!/function agendar(?:Eclipse|Ovni|Foguete|Satelites|Invasao|Chuva|Sujeira|Cometao|Cometa)/.test(html),
    'as páginas não mantêm mais sorteios concorrentes ou invisíveis');
diz(main.includes('atualizar_mascote_solto(solto)') &&
    servidor.includes('"widget" if _mascote_solto else "principal"'),
    'o servidor sabe qual janela está exibindo o mascote');
diz(html.includes("const PAPEL_MASCOTE = document.body.classList.contains('widget')") &&
    html.includes("dados.destino === PAPEL_MASCOTE") &&
    html.includes('executarEventoVisual(dados.evento)'),
    'somente o destino visível aceita o evento transmitido');
diz(eventos.every(nome => html.includes(`case '${nome}':`)),
    'o cliente sabe executar cada evento recebido do servidor');
diz(html.includes('if (!mascoteClienteAtivo() || !g || !TEM_ANIME) return;'),
    'efeitos ligados a respostas também ignoram a cópia escondida');
diz(servidor.includes("dados.get('comando') == 'laboratorio_visual'") &&
    servidor.includes('"tipo": "laboratorio_visual"') &&
    html.includes("executarLaboratorio(dados.acao, dados.valor)"),
    'o laboratório usa o mesmo destino central dos eventos automáticos');
diz(html.includes("enviarLaboratorio('rosto', cara)") &&
    html.includes("if (acao === 'rosto')"),
    'até as caras escolhidas no laboratório chegam ao widget visível');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
