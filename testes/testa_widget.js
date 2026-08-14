// O widget usa o mesmo Index para não duplicar o motor visual. Este teste trava o contrato
// entre o botão da página, a janela transparente do pywebview e o menu de botão direito.
const fs = require('fs');
const path = require('path');
const raiz = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(raiz, 'templates', 'Index.html'), 'utf8');
const main = fs.readFileSync(path.join(raiz, 'main.py'), 'utf8');
const servidor = fs.readFileSync(path.join(raiz, 'servidor.py'), 'utf8');
const widget = fs.readFileSync(path.join(raiz, 'widget.py'), 'utf8');
const requirements = fs.readFileSync(path.join(raiz, 'requirements.txt'), 'utf8');

let ok = true;
function diz(cond, msg) {
  if (!cond) ok = false;
  console.log((cond ? '  OK   ' : '  FALHA') + '  ' + msg);
}

diz(html.includes("request.args.get('widget') == '1'") &&
    html.includes('body.widget .container > :not(#presenca)'),
    'a mesma página ganha um modo que deixa somente o mascote');
diz(html.includes('html:has(body.widget), body.widget, body.widget .container') &&
    html.includes('background: rgba(0, 0, 0, 0) !important'),
    'a página do widget não pinta um retângulo atrás do mascote');
diz(html.includes('body.widget #presenca::before') &&
    html.includes('border-radius: 50%') &&
    html.includes('@keyframes cintila-widget'),
    'o widget ganha contraste circular e estrelas mais legíveis sem perder o fundo transparente');
diz(html.includes('#presenca svg { width: 230px; height: 230px;') &&
    html.includes('body.widget #presenca svg {'),
    'o mascote da janela principal tem os mesmos 230 px do widget');
diz(widget.includes('frameless=True') && widget.includes('transparent=True') &&
    widget.includes('on_top=config["sempre_no_topo"]'),
    'o processo visual abre transparente, sem moldura e respeita a preferência de topo');
diz(widget.includes('os.environ["QT_API"] = "pyside6"') &&
    widget.includes('webview.start(gui="qt")') &&
    !widget.includes('System.Windows.Forms'),
    'o widget força Qt e não volta ao remendo WinForms que deixava um fundo sólido');
diz(requirements.includes('PySide6==6.11.1') && requirements.includes('QtPy==2.4.3'),
    'uma instalação nova também recebe o backend transparente do widget');
diz(widget.includes('easy_drag=False') && html.includes("'pywebviewMoveWindow'") &&
    html.includes('distancia < 4') && html.includes('_arrastou = true'),
    'arrasto global fica desligado e só começa sobre a Luna após um pequeno limiar');
diz(widget.includes('focus=True, js_api=api'),
    'a janela do widget aceita clique, arrasto e menu de contexto');
diz(html.includes("document.addEventListener('contextmenu'") &&
    html.includes('id="btn-widget-retornar"'),
    'o botão de retornar aparece pelo clique direito');
diz(widget.includes('janela.events.moved += api.registrar_posicao') && widget.includes('widget_posicao.json'),
    'a posição do widget é lembrada entre execuções');
diz(widget.includes('def definir_sempre_no_topo') && widget.includes('self._janela.on_top = ativo') &&
    html.includes('id="btn-widget-topo"'),
    'o menu alterna sempre no topo e persiste a decisão');
diz(widget.includes('_TAMANHOS = {"pequeno": 240, "normal": 320, "grande": 460}') &&
    widget.includes('def definir_tamanho') &&
    ['pequeno', 'normal', 'grande'].every(t => html.includes(`data-tamanho="${t}"`)),
    'o menu oferece três tamanhos que redimensionam a janela nativa');
diz(html.includes('--widget-svg: 165px; --widget-nucleo: 120px') &&
    html.includes('--widget-svg: 350px; --widget-nucleo: 256px') &&
    html.includes('font-size: var(--widget-rosto)') &&
    html.includes('width: var(--widget-nucleo)'),
    'corpo, halo e rosto escalam juntos em vez de deixar uma borda desproporcional');
diz(widget.includes('def cursor_relativo') && widget.includes('QCursor.pos()') &&
    html.includes('window.pywebview.api.cursor_relativo()') && html.includes('d <= 430'),
    'o widget acompanha o cursor global quando ele se aproxima');
diz(html.includes("body.classList.toggle('mascote-solto'") &&
    html.includes('body.mascote-solto:not(.widget) #presenca'),
    'o mascote original some enquanto a cópia desktop está solta');
diz(html.includes('html.arrastando-luna, html.arrastando-luna body { overflow-x: clip; }') &&
    html.includes("classList.add('arrastando-luna')") &&
    html.includes("classList.remove('arrastando-luna')"),
    'arrastar na janela bloqueia a barra horizontal somente durante o gesto');
diz(!main.includes('TransparencyKey') && !main.includes('SetLayeredWindowAttributes'),
    'não restou chave de cor que deixe o widget preto ou sem clique');
diz(widget.includes('time.sleep(0.75)') && widget.includes('janela.destroy()'),
    'retornar espera a ponte JS responder antes de descartar a janela');
diz(main.includes('[sys.executable, caminho]') && main.includes('self._processo_widget = processo'),
    'a Luna principal cria somente um processo visual auxiliar');
diz(html.includes("window.pywebview.api.recolher_mascote()") &&
    html.includes("document.body.classList.contains('mascote-solto')"),
    'o botão da interface também alterna entre soltar e retornar');
diz(servidor.includes("'estado': _ultimo_estado_rosto") && servidor.includes("'kaomoji': _ultimo_kaomoji"),
    'uma janela recém-aberta já recebe o estado e a expressão atuais');

console.log(ok ? '\nTUDO PASSOU' : '\nTEM FALHA');
process.exit(ok ? 0 : 1);
