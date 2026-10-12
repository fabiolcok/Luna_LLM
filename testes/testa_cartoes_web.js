// Exercita os cartões reais e as ações sobre o estado atual, inclusive em mensagens antigas.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

class Elemento {
    constructor(tag) {
        this.tagName = tag; this.children = []; this.dataset = {}; this.className = ''; this._texto = '';
        this.style = {setProperty(nome, valor) {this[nome] = valor;}};
    }
    set textContent(texto) { this._texto = String(texto); this.children = []; }
    get textContent() { return this._texto + this.children.map(e => e.textContent).join(''); }
    appendChild(el) { this.children.push(el); el.parentNode = this; return el; }
    append(...els) { els.forEach(el => this.appendChild(el)); }
    remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(el => el !== this); }
    setAttribute(nome, valor) { this[nome] = valor; }
    addEventListener(nome, callback) { this['on' + nome] = callback; }
    querySelectorAll(seletor) {
        const combina = el => seletor[0] === '.' ? el.className.split(' ').includes(seletor.slice(1)) : el.tagName === seletor;
        return this.children.flatMap(el => [...(combina(el) ? [el] : []), ...el.querySelectorAll(seletor)]);
    }
    scrollIntoView() { this.rolou = true; }
}
const raizes = Object.fromEntries(['historico-lista', 'fontes-lista', 'acompanhamentos-lista', 'sopro-painel', 'btn-repetir']
    .map(id => [id, new Elemento('div')]));
const criados = [];
const document = { getElementById: id => raizes[id], createElement: tag => {
    const el = new Elemento(tag); criados.push(el); return el;
} };
const envios = [];
const socket = {readyState: 1, send: s => envios.push(JSON.parse(s))}, acoes = [], paineis = [], feedback = [], copias = [], perguntas = [];
const consultas = [], referencias = [], ampliacoes = [];
const markdown = html.slice(html.indexOf('function escaparHtml('), html.indexOf('function copiarMensagem('));
const componentes = html.slice(html.indexOf('function linkNovidade('), html.indexOf('function anexarDetalhesAoTurno('));
const api = new Function('document', 'socket', 'abrirPainelLateral', 'acaoFonte', 'acaoSopro',
    'mostrarFeedbackAcompanhamento', 'copiarMensagem', 'enviarPedidoTexto',
    'abrirBiblioteca', 'selecionarResposta', 'abrirImagem',
    'let acompanhamentoEstado = {}; let cartoesEstadoRecebido = false;\n' + markdown + componentes +
    html.slice(html.indexOf("document.getElementById('btn-repetir').onclick ="), html.indexOf('const volumeSlider =')) + `
    return {criarCartaoWeb, criarTurnoEl, estadoCartaoAcompanhamento,
        receber(estado) { acompanhamentoEstado = estado; cartoesEstadoRecebido = true; atualizarCartoesAcompanhamento(); },
        desconectar() {cartoesEstadoRecebido = false; atualizarCartoesAcompanhamento();},
        receberEstadoAudio, receberFeedbackPropostaFonte, ouvirUltimaResposta, atualizarOuvirUltimaResposta};`)(
    document, socket, (...args) => paineis.push(args), (...args) => acoes.push(['fonte', ...args]),
    (...args) => acoes.push(['sopro', ...args]), texto => feedback.push(texto), texto => copias.push(texto),
    (...args) => perguntas.push(args), tipo => consultas.push(tipo),
    (...args) => referencias.push(args), (...args) => ampliacoes.push(args));

const titulo = '<img src=x onerror=alert(1)>', trecho = '<script>alert(1)</script>';
const noticia = {tipo: 'noticia', titulo, fonte: '<b>Feed</b>', url: 'https://example.org/n', mais: 2};
const turno = api.criarTurnoEl({luna: '**Fala** intacta.', cartoes_web: [noticia],
    links_novidades: {noticia: noticia.url, nota: 'obsidian://open?path=Novidades.md'}});
raizes['historico-lista'].appendChild(turno);
assert.equal(turno.querySelectorAll('.cartao-web-titulo')[0].textContent, titulo);
assert.equal(turno.querySelectorAll('.cartao-web-fonte')[0].textContent, '<b>Feed</b>');
assert.equal(turno.querySelectorAll('a').filter(a => a.href === noticia.url).length, 1, 'Não duplicar o link do cartão');
assert.equal(turno.querySelectorAll('a').at(-1).href, 'obsidian://open?path=Novidades.md');
const cartaoNoticia = turno.querySelectorAll('.cartao-noticia')[0];
const todas = turno.querySelectorAll('.cartao-noticia-todas')[0];
assert.equal(todas.textContent, 'Ver todas');
assert.equal(todas['aria-label'], 'Ver todas as notícias na Luna');
todas.onclick({preventDefault() {}});
assert.deepEqual(consultas, ['noticia'], 'Ver todas deve abrir a biblioteca local');
assert.equal(todas.parentNode, cartaoNoticia.querySelectorAll('.cartao-web-acoes')[0], 'A nota pertence às ações da notícia');
assert.equal(cartaoNoticia.querySelectorAll('.cartao-web-mais').length, 0, 'O link da nota substitui a contagem solta');
assert.equal(turno.querySelectorAll('a').filter(a => a.href === todas.href).length, 1, 'A nota não aparece de novo após a fala');
assert.equal(cartaoNoticia.querySelectorAll('.cartao-web-fonte')[0].parentNode,
    cartaoNoticia.querySelectorAll('.cartao-web-cabecalho')[0], 'A fonte fica junto ao cabeçalho');
assert.equal(turno.querySelectorAll('.mensagem-conteudo')[0].innerHTML, '<p><strong>Fala</strong> intacta.</p>');
const balao = turno.querySelectorAll('.turno-luna')[0];
assert.equal(balao.children[0].className, 'cartao-web cartao-noticia');
turno.querySelectorAll('.mensagem-copiar')[0].onclick();
assert.deepEqual(copias, ['**Fala** intacta.']);
const comSugestoes = api.criarTurnoEl({id: 'rss-antigo', origem_proativa: 'radar_rss', luna: 'Comentário.',
    cartoes_web: [{...noticia, sugestoes: ['Como fizeram esse teste?', 'OLED ainda vale a pena?']}]});
const sugestoes = comSugestoes.querySelectorAll('.novidade-sugestoes')[0];
assert.equal(sugestoes.children.length, 2);
assert.equal(sugestoes['aria-label'], 'Continuar sobre esta notícia');
assert.equal(sugestoes.children[1].textContent, 'OLED ainda vale a pena?');
sugestoes.children[1].onclick();
assert.deepEqual(perguntas, [['OLED ainda vale a pena?', null, {turno_id: 'rss-antigo', indice: 1}]]);
const balaoSugestoes = comSugestoes.querySelectorAll('.turno-luna')[0];
const controlesNoticia = balaoSugestoes.querySelectorAll('.novidade-controles')[0];
const continuar = controlesNoticia.children[0];
assert.equal(continuar.className, 'novidade-continuacao');
assert.ok(!continuar.open, 'As perguntas começam recolhidas');
assert.equal(continuar.querySelectorAll('summary')[0].textContent, 'Continuar assunto');
assert.ok(balaoSugestoes.children.indexOf(controlesNoticia) >
    balaoSugestoes.children.findIndex(el => el.className === 'mensagem-conteudo'), 'As perguntas vêm após o comentário');
assert.equal(controlesNoticia.children.at(-1).className, 'radar-interesse', 'Afinar radar fica junto das opções da notícia');
const afinar = controlesNoticia.children.at(-1);
assert.ok(!afinar.open, 'Ajuste de interesse começa recolhido');
afinar.querySelectorAll('input')[0].value = 'OLED';
afinar.querySelectorAll('button')[1].onclick();
assert.deepEqual(envios.pop(), {comando:'radar_interesse', acao:'menos', assunto:'OLED', turno_id:'rss-antigo'});
const ouvir = comSugestoes.querySelectorAll('.mensagem-ouvir')[0];
comSugestoes.querySelectorAll('.mensagem-responder')[0].onclick();
assert.deepEqual(referencias, [[{turno_id: 'rss-antigo'}, 'Comentário.']]);
const barraOuvir = raizes['btn-repetir'];
api.atualizarOuvirUltimaResposta();
assert.equal(barraOuvir.disabled, true, 'Sem resposta com id, a barra não pode repetir um áudio antigo');
barraOuvir.onclick(); assert.equal(envios.length, 0);
raizes['historico-lista'].appendChild(comSugestoes);
api.atualizarOuvirUltimaResposta();
assert.equal(barraOuvir.disabled, false);
barraOuvir.onclick();
const audio = envios.pop();
assert.equal(audio.comando, 'ouvir_resposta'); assert.equal(audio.turno_id, 'rss-antigo');
assert.equal(audio.texto, undefined, 'O navegador não escolhe o texto que será lido');
assert.equal(ouvir.dataset.requestId, audio.request_id, 'Os dois botões compartilham a mesma leitura');
assert.equal(barraOuvir.textContent, '⏹️');
api.receberEstadoAudio({turno_id:'rss-antigo', request_id:audio.request_id, estado:'falando'});
assert.equal(ouvir.textContent, '■');
barraOuvir.onclick();
assert.deepEqual(envios.pop(), {comando:'parar_leitura', request_id:audio.request_id});
ouvir.receberEstado({request_id:audio.request_id, estado:'fim'});
assert.equal(ouvir.textContent, '▷');
assert.equal(barraOuvir.textContent, '▶️');
ouvir.onclick();
const audioDireto = envios.pop();
assert.equal(barraOuvir.textContent, '⏹️', 'Ouvir pelo balão também atualiza o controle da barra');
barraOuvir.onclick(); assert.equal(envios.pop().request_id, audioDireto.request_id);
ouvir.receberEstado({request_id:audioDireto.request_id, estado:'fim'});
const respostaNova = api.criarTurnoEl({id:'resposta-nova', luna:'Texto sem áudio anterior.'});
raizes['historico-lista'].appendChild(respostaNova);
api.atualizarOuvirUltimaResposta(); barraOuvir.onclick();
const audioNovo = envios.pop();
assert.equal(audioNovo.turno_id, 'resposta-nova', 'A barra segue a última resposta, inclusive sem áudio já gerado');
api.receberEstadoAudio({turno_id:'rss-antigo', request_id:audioDireto.request_id, estado:'fim'});
assert.equal(barraOuvir.textContent, '⏹️', 'Fim de uma leitura antiga não altera a atual');
socket.readyState = 3;
api.receberEstadoAudio({estado:'desconectado'});
assert.equal(barraOuvir.disabled, true);
barraOuvir.onclick(); assert.equal(envios.length, 0, 'Sem conexão não tenta ouvir');
socket.readyState = 1;
api.atualizarOuvirUltimaResposta(); assert.equal(barraOuvir.disabled, false);
api.receberEstadoAudio({turno_id:'resposta-nova', request_id:audioNovo.request_id, estado:'fim'});
comSugestoes.querySelectorAll('.mensagem-copiar')[0].onclick();
assert.equal(copias.at(-1), 'Comentário.', 'Copiar a fala não inclui botões');
for (const origem of ['dark_souls_morte', 'radar_promocoes', undefined]) {
    assert.equal(api.criarTurnoEl({id: 'outro', origem_proativa: origem, luna: 'Fala.',
        cartoes_web: [{...noticia, sugestoes: ['Como fizeram esse teste?']}]}).querySelectorAll('.novidade-sugestoes').length, 0);
}
const inseguro = api.criarTurnoEl({id: 'rss', origem_proativa: 'radar_rss', luna: 'Fala.',
    cartoes_web: [{...noticia, sugestoes: ['<script>Como assim?</script>', {}, 'https://exemplo.org?', 'Por quê?']}]});
assert.equal(inseguro.querySelectorAll('.novidade-sugestoes').length, 0);
for (const bruto of [null, {}, {...noticia, url: 'javascript:alert(1)'}, {...noticia, url: 'https://['},
    {tipo: 'html', titulo: 'X'}, {tipo: 'acompanhamento', titulo: 'X', origem: 'fontes', id: 'a b'},
    {tipo: 'acompanhamento', titulo: 'X', origem: 'sopro', id: 'outro'}]) assert.equal(api.criarCartaoWeb(bruto), null);
const legado = api.criarTurnoEl({luna: 'Fala antiga.', links_novidades: {noticia: noticia.url,
    ofertas: [{url: 'https://t.me/canal/123', rotulo: 'Oferta'}]}});
assert.equal(legado.querySelectorAll('.cartao-web').length, 0);
assert.equal(legado.querySelectorAll('a').length, 2);

const agenda = {tipo: 'agenda', titulo: 'Agenda', total: 4, inicio_periodo: '2026-10-09T00:00:00-03:00',
    fim_periodo: '2026-10-12T00:00:00-03:00', eventos: [
        {titulo: 'Reunião', inicio: '2026-10-10T14:00:00-03:00', fim: '2026-10-10T15:00:00-03:00',
            local: 'Sala de teste', url: 'https://calendar.google.com/event?eid=teste'},
        {titulo: 'Viagem', inicio: '2026-10-10', fim: '2026-10-12', dia_inteiro: true},
        {titulo: '<script>Literal</script>', inicio: '2026-10-09T23:00:00-03:00', fim: '2026-10-10T01:00:00-03:00',
            local: '<img src=x>', url: 'javascript:alert(1)'},
        {titulo: 'Sem término', inicio: '2026-10-10T17:30:00-03:00'}]};
const turnoAgenda = api.criarTurnoEl({luna: 'Olhei sua agenda.', cartoes_web: [agenda]});
const cardAgenda = turnoAgenda.querySelectorAll('.cartao-agenda')[0];
assert.equal(turnoAgenda.querySelectorAll('.turno-luna')[0].children[0].className, 'mensagem-conteudo');
assert.equal(cardAgenda.querySelectorAll('.agenda-dia').length, 0, 'Datas não ficam fora do bloco de compromisso');
assert.equal(cardAgenda.querySelectorAll('.agenda-eventos').length, 1);
assert.equal(cardAgenda.querySelectorAll('.agenda-evento').length, 4);
assert.equal(cardAgenda.querySelectorAll('.agenda-periodo')[0].textContent, 'Próximos 3 dias');
assert.ok(cardAgenda.querySelectorAll('.agenda-periodo')[0].title.includes('11'), 'O detalhe do período respeita a meia-noite exclusiva');
assert.equal(cardAgenda.querySelectorAll('.cartao-web-fonte').length, 0, 'O intervalo longo deixa de disputar atenção com as datas dos eventos');
for (const linha of cardAgenda.querySelectorAll('.agenda-evento')) {
    assert.equal(linha.children[0].className, 'agenda-evento-info');
    assert.equal(linha.querySelectorAll('.agenda-data').length, 1);
    assert.equal(linha.querySelectorAll('.agenda-horario').length, 1);
}
assert.ok(cardAgenda.querySelectorAll('.agenda-data')[0].textContent.includes('9'));
assert.ok(cardAgenda.querySelectorAll('.agenda-data')[1].textContent.includes('10'));
const agenda30 = api.criarCartaoWeb({...agenda, fim_periodo: '2026-11-08T00:00:00-03:00'});
assert.equal(agenda30.querySelectorAll('.agenda-periodo')[0].textContent, 'Próximos 30 dias');
const hoje = api.criarCartaoWeb({...agenda, titulo: 'Agenda de hoje', fim_periodo: '2026-10-10T00:00:00-03:00'});
assert.equal(hoje.querySelectorAll('.agenda-periodo').length, 0, 'Agenda de hoje não repete o período do título');
assert.equal(cardAgenda.querySelectorAll('.agenda-evento-titulo')[0].textContent, '<script>Literal</script>');
const horarios = cardAgenda.querySelectorAll('.agenda-horario').map(e => e.textContent);
assert.match(horarios[0], /^23:00 – 01:00\n/);
assert.match(horarios[1], /^Dia inteiro\naté /);
assert.ok(horarios[1].includes('11'), 'Data final de dia inteiro é exclusiva');
assert.equal(horarios[2], '14:00 – 15:00'); assert.equal(horarios[3], '17:30');
assert.equal(cardAgenda.querySelectorAll('a').length, 1);
assert.equal(cardAgenda.querySelectorAll('button').length, 0);
assert.equal(cardAgenda.querySelectorAll('img').length, 0);
turnoAgenda.querySelectorAll('.mensagem-copiar')[0].onclick();
assert.equal(copias.at(-1), 'Olhei sua agenda.', 'Metadados não se misturam à fala copiada');
assert.equal(api.criarCartaoWeb({...agenda, eventos: [] , total: 0}).querySelectorAll('.agenda-vazia')[0].textContent,
    'Sem compromissos neste período.');
assert.equal(api.criarCartaoWeb({...agenda, eventos: null}), null);
const invalidaAgenda = api.criarCartaoWeb({...agenda, eventos: [{titulo: 'Data impossível', inicio: '2026-02-31'},
    {titulo: 'Sem fuso', inicio: '2026-10-10T17:30:00'}, null]});
assert.equal(invalidaAgenda.querySelectorAll('.agenda-evento').length, 0);
assert.equal(invalidaAgenda.querySelectorAll('.agenda-vazia')[0].textContent, 'Não foi possível mostrar os compromissos.');
const cheia = api.criarCartaoWeb({...agenda, eventos: Array.from({length: 60}, () => agenda.eventos[0]), total: 60});
assert.equal(cheia.querySelectorAll('.agenda-evento').length, 50);
assert.equal(cheia.querySelectorAll('.agenda-limite').length, 1);

const urlImagem = 'https://example.org/imagem-da-noticia.jpg';
const comImagem = api.criarTurnoEl({luna: 'Fala intacta.', cartoes_web: [{...noticia, imagem: urlImagem}]});
const imagem = comImagem.querySelectorAll('img')[0];
assert.equal(imagem.src, urlImagem); assert.equal(imagem.loading, 'lazy');
assert.equal(imagem.decoding, 'async'); assert.equal(imagem.referrerPolicy, 'no-referrer');
assert.equal(imagem.alt, '');
imagem.onclick();
assert.equal(ampliacoes.at(-1)[0], imagem, 'Ampliar deve reaproveitar o arquivo já apresentado');
assert.equal(imagem['role'], 'button');
const midiaNoticia = comImagem.querySelectorAll('.cartao-noticia-midia')[0];
assert.equal(imagem.parentNode, midiaNoticia);
assert.equal(midiaNoticia.style['--imagem-noticia'], undefined, 'O fundo não antecipa a carga da imagem lazy');
imagem.onload();
assert.equal(midiaNoticia.style['--imagem-noticia'], 'url("' + urlImagem + '")', 'O fundo reaproveita a fonte carregada');
assert.equal(comImagem.querySelectorAll('a').length, 1);
imagem.onerror();
assert.equal(comImagem.querySelectorAll('img').length, 0, 'Imagem indisponível não deixa ícone quebrado');
assert.equal(comImagem.querySelectorAll('.cartao-noticia-midia').length, 0, 'Falha na imagem também remove a moldura vazia');
assert.equal(comImagem.querySelectorAll('.cartao-web-titulo')[0].textContent, titulo);
assert.equal(comImagem.querySelectorAll('a')[0].href, noticia.url);
assert.equal(turno.querySelectorAll('img').length, 0, 'Notícia sem miniatura continua com texto');
for (const invalida of [null, {}, '', 'data:image/png;base64,ABC', 'javascript:alert(1)', 'file:///foto.jpg',
    'obsidian://open?path=foto', 'https://[', 'https://example.org/imagem com espaco.jpg']) {
    const semImagem = api.criarCartaoWeb({...noticia, imagem: invalida});
    assert.equal(semImagem.querySelectorAll('img').length, 0);
    assert.equal(semImagem.querySelectorAll('.cartao-web-titulo')[0].textContent, titulo);
}

const imagemPromo = '/imagens/promocoes/canal_teste_123.jpg';
const promocao = {tipo: 'promocao', titulo: 'Batedeira', fonte: '@canal_teste',
    url: 'https://t.me/canal_teste/123', imagem: imagemPromo, mais: 1};
const turnoPromo = api.criarTurnoEl({luna: 'Olha essa promoção!', cartoes_web: [promocao],
    links_novidades: {ofertas: [{url: promocao.url, rotulo: 'Ver esta promoção no Telegram ↗'}],
        nota: 'obsidian://open?path=Promocoes.md'}});
assert.equal(turnoPromo.querySelectorAll('.cartao-promocao').length, 1);
turnoPromo.querySelectorAll('.cartao-noticia-todas')[0].onclick({preventDefault() {}});
assert.equal(consultas.at(-1), 'promocao');
assert.equal(turnoPromo.querySelectorAll('.cartao-web-rotulo')[0].textContent, 'Promoção');
assert.equal(turnoPromo.querySelectorAll('img')[0].src, imagemPromo);
assert.equal(turnoPromo.querySelectorAll('.cartao-noticia-midia').length, 0, 'O tratamento visual desta etapa é só das notícias');
assert.equal(turnoPromo.querySelectorAll('a').filter(a => a.href === promocao.url).length, 1,
    'O cartão de promoção não pode duplicar o link legado');
assert.equal(turnoPromo.querySelectorAll('a').at(-1).href, 'obsidian://open?path=Promocoes.md');
assert.equal(turnoPromo.querySelectorAll('.turno-luna')[0].children[0].className, 'cartao-web cartao-promocao');
assert.equal(turnoPromo.querySelectorAll('.cartao-web-status').length, 0,
    'Promoção não pode receber controles de acompanhamento');
const semFoto = api.criarCartaoWeb({...promocao, imagem: ''});
assert.equal(semFoto.querySelectorAll('img').length, 0);
assert.equal(semFoto.querySelectorAll('a').length, 1);
const privado = api.criarCartaoWeb({...promocao, url: ''});
assert.equal(privado.querySelectorAll('a').length, 0, 'Não inventar um link para canal privado');
assert.equal(privado.querySelectorAll('.cartao-web-fonte')[0].textContent, '@canal_teste');
for (const invalida of ['/imagens/promocoes/../segredo.jpg', '/imagens/promocoes/%2e%2e%2fsegredo.jpg',
    '/static/foto.jpg', '/imagens/promocoes/foto.svg', '/imagens/promocoes/foto.jpg?x=1']) {
    const card = api.criarCartaoWeb({...promocao, imagem: invalida});
    assert.equal(card.querySelectorAll('img').length, 0);
}
turnoPromo.querySelectorAll('img')[0].onerror();
assert.equal(turnoPromo.querySelectorAll('img').length, 0);
assert.equal(turnoPromo.querySelectorAll('.cartao-web-titulo')[0].textContent, 'Batedeira');

const dados = {tipo: 'acompanhamento', titulo: 'Projeto de teste', origem: 'fontes', id: 'tema1',
    situacao: 'Situação da mensagem original', trecho, url: 'https://example.org/atualizacao', etapa: 'plano'};
const retorno = api.criarTurnoEl({luna: 'Fui conferir o projeto.', cartoes_web: [dados]});
raizes['historico-lista'].appendChild(retorno);
const card = retorno.querySelectorAll('.cartao-acompanhamento')[0];
const badge = card.querySelectorAll('.cartao-web-status')[0];
const [ver, pausar] = card.querySelectorAll('button');
const campos = () => card.querySelectorAll('.cartao-web-campo').map(el => el.children[1].textContent);
assert.equal(pausar.disabled, true);
pausar.onclick(); assert.equal(acoes.length, 0);
assert.equal(badge.textContent, 'Atualizando estado');
assert.equal(card.querySelectorAll('.cartao-web-trecho')[0].children[1].textContent, trecho);
assert.equal(retorno.querySelectorAll('.turno-luna')[0].children[0].className, 'mensagem-conteudo');

const item = {id: 'tema1', status: 'ativo', situacao: 'Consulta mais recente',
    proximo_passo: 'Conferir a novidade.', novidades: [{etapa: 'plano', lido: false}]};
const estado = {fontes: {itens: [item]}, sopro: {id: 'sopro_ptbr', status: 'ativo',
    situacao: 'Aguardando PT-BR', proximo_passo: 'Consultar o repositório'}, ativos: [{id: 'conversa1', status: 'aguardando_resposta'}]};
api.receber(estado);
assert.equal(badge.textContent, 'Acompanhando'); assert.equal(pausar.disabled, false);
assert.deepEqual(campos(), ['Consulta mais recente', 'Aguardar a disponibilidade anunciada antes de testar.']);
item.novidades[0].lido = true; api.receber(estado);
assert.equal(campos()[1], 'Aguardar a disponibilidade anunciada antes de testar.');
item.novidades.push({etapa: 'anuncio', lido: false}); api.receber(estado);
assert.equal(campos()[1], 'Conferir a novidade.');
pausar.onclick(); assert.deepEqual(acoes.at(-1), ['fonte', 'pausar', 'tema1']);
item.status = 'pausado'; api.receber(estado);
assert.equal(badge.textContent, 'Pausado'); assert.equal(pausar.textContent, 'Retomar');
assert.equal(campos()[1], 'Retome quando quiser voltar a consultar as fontes.');
pausar.onclick(); assert.deepEqual(acoes.at(-1), ['fonte', 'retomar', 'tema1']);
const alvoFonte = new Elemento('details'); alvoFonte.dataset.id = 'tema1'; raizes['fontes-lista'].appendChild(alvoFonte);
ver.onclick(); assert.equal(paineis.at(-1)[0], 'acompanhamentos-panel'); assert.ok(alvoFonte.open && alvoFonte.rolou);
assert.equal(card.querySelectorAll('.cartao-web-trecho')[0].children[1].textContent, trecho, 'Evidência histórica não muda');

const sopro = api.criarCartaoWeb({...dados, titulo: 'Sopro — PT-BR', origem: 'sopro', id: 'sopro_ptbr'});
const conversa = api.criarCartaoWeb({...dados, titulo: 'Acesso externo', origem: 'conversa', id: 'conversa1', url: ''});
raizes['historico-lista'].append(sopro, conversa);
const pausaSopro = sopro.querySelectorAll('button')[1];
pausaSopro.onclick(); assert.deepEqual(acoes.at(-1), ['sopro', 'pausar']);
sopro.querySelectorAll('button')[0].onclick(); assert.ok(raizes['sopro-painel'].open);
assert.equal(conversa.querySelectorAll('button').length, 1, 'Conversas não têm um comando de pausa fictício');
assert.equal(conversa.querySelectorAll('.cartao-web-status')[0].textContent, 'Aguardando sua resposta');
socket.readyState = 3; pausar.onclick(); assert.match(feedback.at(-1), /Sem conexão/);
const antes = acoes.length;
api.desconectar(); assert.equal(pausar.disabled, true); assert.equal(pausaSopro.disabled, true);
pausar.onclick(); assert.equal(acoes.length, antes);
socket.readyState = 1; api.receber(estado); assert.equal(pausar.disabled, false);
api.receber({fontes: {itens: [], erro: 'Sem acesso'}, sopro: null});
assert.equal(badge.textContent, 'Estado indisponível'); assert.equal(pausar.disabled, true);
api.receber({fontes: {itens: []}, sopro: {...estado.sopro, status: 'encerrado'}, ativos: []});
assert.equal(badge.textContent, 'Não está ativo'); assert.equal(campos()[1], 'Este acompanhamento não está mais ativo.');
assert.equal(pausar.disabled, true); assert.equal(pausaSopro.disabled, true);
assert.ok(!criados.some(el => el.tagName === 'script'), 'Metadados não criam scripts');
assert.ok(criados.filter(el => el.tagName === 'img').every(el => el.className === 'cartao-web-imagem' && [urlImagem, imagemPromo].includes(el.src)),
    'Apenas o campo de miniatura validado cria uma imagem; título e trecho continuam sendo texto');
const proposta = {tipo:'proposta_fonte', id:'abcdef1234567890', titulo:'TTS', interesse:'Suporte brasileiro',
    fontes:['https://example.org/releases.atom']};
const turnoRascunho = api.criarTurnoEl({id:'rascunho', luna:'Confira o cartão.', cartoes_web:[proposta]});
raizes['historico-lista'].appendChild(turnoRascunho);
const draft = turnoRascunho.querySelectorAll('.cartao-proposta-fonte')[0];
const confirmarDraft = draft.querySelectorAll('button')[0];
assert.equal(confirmarDraft.disabled, true, 'Não salva antes de receber o estado atual');
const estadoDraft = {propostas_fontes:{itens:[{id:proposta.id, status:'pendente'}]}};
api.receber(estadoDraft);
assert.equal(confirmarDraft.disabled, false);
const interesseDraft = draft.querySelectorAll('textarea')[0];
interesseDraft.value = 'Mudanças de desempenho em CPU'; interesseDraft.oninput();
api.receber(estadoDraft);
assert.equal(interesseDraft.value, 'Mudanças de desempenho em CPU', 'Atualização de estado não apaga edições');
confirmarDraft.onclick(); confirmarDraft.onclick();
assert.equal(envios.length, 1, 'Clique duplo não confirma duas vezes');
const confirmarPedido = envios.pop();
assert.equal(confirmarPedido.cadastro.interesse, 'Mudanças de desempenho em CPU');
assert.equal(confirmarDraft.disabled, true);
api.receberFeedbackPropostaFonte({id:proposta.id, ok:false, texto:'Erro de leitura'});
assert.equal(confirmarDraft.disabled, false);
api.desconectar(); assert.equal(confirmarDraft.disabled, true);
const draftReconectado = api.criarCartaoWeb(proposta);
assert.equal(draftReconectado.querySelectorAll('textarea')[0].value, 'Mudanças de desempenho em CPU');
estadoDraft.propostas_fontes.itens[0].status = 'confirmado'; api.receber(estadoDraft);
assert.equal(confirmarDraft.hidden, true); assert.equal(interesseDraft.disabled, true);
assert.equal(api.criarCartaoWeb({...proposta, fontes:['javascript:alert(1)']}), null);
console.log('PASSOU: cartões, rascunhos, interesses, leitura, estado atual e reconexão');
