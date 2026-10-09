// Exercita os cartões reais e as ações sobre o estado atual, inclusive em mensagens antigas.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

class Elemento {
    constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.className = ''; this._texto = ''; }
    set textContent(texto) { this._texto = String(texto); this.children = []; }
    get textContent() { return this._texto + this.children.map(e => e.textContent).join(''); }
    appendChild(el) { this.children.push(el); el.parentNode = this; return el; }
    append(...els) { els.forEach(el => this.appendChild(el)); }
    remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(el => el !== this); }
    setAttribute(nome, valor) { this[nome] = valor; }
    querySelectorAll(seletor) {
        const combina = el => seletor[0] === '.' ? el.className.split(' ').includes(seletor.slice(1)) : el.tagName === seletor;
        return this.children.flatMap(el => [...(combina(el) ? [el] : []), ...el.querySelectorAll(seletor)]);
    }
    scrollIntoView() { this.rolou = true; }
}
const raizes = Object.fromEntries(['historico-lista', 'fontes-lista', 'acompanhamentos-lista', 'sopro-painel']
    .map(id => [id, new Elemento('div')]));
const criados = [];
const document = { getElementById: id => raizes[id], createElement: tag => {
    const el = new Elemento(tag); criados.push(el); return el;
} };
const socket = {readyState: 1}, acoes = [], paineis = [], feedback = [], copias = [];
const markdown = html.slice(html.indexOf('function escaparHtml('), html.indexOf('function copiarMensagem('));
const componentes = html.slice(html.indexOf('function linkNovidade('), html.indexOf('function anexarDetalhesAoTurno('));
const api = new Function('document', 'socket', 'abrirPainelLateral', 'acaoFonte', 'acaoSopro',
    'mostrarFeedbackAcompanhamento', 'copiarMensagem',
    'let acompanhamentoEstado = {}; let cartoesEstadoRecebido = false;\n' + markdown + componentes + `
    return {criarCartaoWeb, criarTurnoEl, estadoCartaoAcompanhamento,
        receber(estado) { acompanhamentoEstado = estado; cartoesEstadoRecebido = true; atualizarCartoesAcompanhamento(); },
        desconectar() {cartoesEstadoRecebido = false; atualizarCartoesAcompanhamento();}};`)(
    document, socket, (...args) => paineis.push(args), (...args) => acoes.push(['fonte', ...args]),
    (...args) => acoes.push(['sopro', ...args]), texto => feedback.push(texto), texto => copias.push(texto));

const titulo = '<img src=x onerror=alert(1)>', trecho = '<script>alert(1)</script>';
const noticia = {tipo: 'noticia', titulo, fonte: '<b>Feed</b>', url: 'https://example.org/n', mais: 2};
const turno = api.criarTurnoEl({luna: '**Fala** intacta.', cartoes_web: [noticia],
    links_novidades: {noticia: noticia.url, nota: 'obsidian://open?path=Novidades.md'}});
raizes['historico-lista'].appendChild(turno);
assert.equal(turno.querySelectorAll('.cartao-web-titulo')[0].textContent, titulo);
assert.equal(turno.querySelectorAll('.cartao-web-fonte')[0].textContent, '<b>Feed</b>');
assert.equal(turno.querySelectorAll('a').filter(a => a.href === noticia.url).length, 1, 'Não duplicar o link do cartão');
assert.equal(turno.querySelectorAll('a').at(-1).href, 'obsidian://open?path=Novidades.md');
assert.equal(turno.querySelectorAll('.mensagem-conteudo')[0].innerHTML, '<p><strong>Fala</strong> intacta.</p>');
const balao = turno.querySelectorAll('.turno-luna')[0];
assert.equal(balao.children[0].className, 'cartao-web cartao-noticia');
turno.querySelectorAll('.mensagem-copiar')[0].onclick();
assert.deepEqual(copias, ['**Fala** intacta.']);
for (const bruto of [null, {}, {...noticia, url: 'javascript:alert(1)'}, {...noticia, url: 'https://['},
    {tipo: 'html', titulo: 'X'}, {tipo: 'acompanhamento', titulo: 'X', origem: 'fontes', id: 'a b'},
    {tipo: 'acompanhamento', titulo: 'X', origem: 'sopro', id: 'outro'}]) assert.equal(api.criarCartaoWeb(bruto), null);
const legado = api.criarTurnoEl({luna: 'Fala antiga.', links_novidades: {noticia: noticia.url,
    ofertas: [{url: 'https://t.me/canal/123', rotulo: 'Oferta'}]}});
assert.equal(legado.querySelectorAll('.cartao-web').length, 0);
assert.equal(legado.querySelectorAll('a').length, 2);

const urlImagem = 'https://example.org/imagem-da-noticia.jpg';
const comImagem = api.criarTurnoEl({luna: 'Fala intacta.', cartoes_web: [{...noticia, imagem: urlImagem}]});
const imagem = comImagem.querySelectorAll('img')[0];
assert.equal(imagem.src, urlImagem); assert.equal(imagem.loading, 'lazy');
assert.equal(imagem.decoding, 'async'); assert.equal(imagem.referrerPolicy, 'no-referrer');
assert.equal(imagem.alt, '');
assert.equal(comImagem.querySelectorAll('a').length, 1);
imagem.onerror();
assert.equal(comImagem.querySelectorAll('img').length, 0, 'Imagem indisponível não deixa ícone quebrado');
assert.equal(comImagem.querySelectorAll('.cartao-web-titulo')[0].textContent, titulo);
assert.equal(comImagem.querySelectorAll('a')[0].href, noticia.url);
assert.equal(turno.querySelectorAll('img').length, 0, 'Notícia sem miniatura continua com texto');
for (const invalida of [null, {}, '', 'data:image/png;base64,ABC', 'javascript:alert(1)', 'file:///foto.jpg',
    'obsidian://open?path=foto', 'https://[', 'https://example.org/imagem com espaco.jpg']) {
    const semImagem = api.criarCartaoWeb({...noticia, imagem: invalida});
    assert.equal(semImagem.querySelectorAll('img').length, 0);
    assert.equal(semImagem.querySelectorAll('.cartao-web-titulo')[0].textContent, titulo);
}

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
assert.ok(criados.filter(el => el.tagName === 'img').every(el => el.className === 'cartao-web-imagem' && el.src === urlImagem),
    'Apenas o campo de miniatura validado cria uma imagem; título e trecho continuam sendo texto');
console.log('PASSOU: cartões, links, estado atual e reconexão');
