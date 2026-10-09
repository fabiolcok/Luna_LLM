const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
const elementos = {};
function el() {
    return { children: [], dataset: {}, value: '', textContent: '', hidden: false, open: false,
        disabled: false, focus() {}, setAttribute(k,v) { this[k]=v; },
        appendChild(c) { this.children.push(c); return c; },
        set innerHTML(v) { this.children=[]; this.html=v; }, get innerHTML() { return this.html||''; } };
}
const document = { getElementById: id => elementos[id] || (elementos[id]=el()), createElement: el };
const envios = [], socket = {readyState:1, send:s=>envios.push(JSON.parse(s))};
document.getElementById('fontes-form').reset = () =>
    ['fonte-id','fonte-assunto','fonte-interesse','fonte-situacao','fonte-urls'].forEach(id=>document.getElementById(id).value='');
const inicio = html.indexOf('let fontesItens =');
const fim = html.indexOf('function acaoSopro(',inicio);
const il = html.indexOf('function linkNovidade('), fl=html.indexOf('function criarTurnoEl(',il);
const ii=html.indexOf('function atualizarIndicadorAcompanhamentos('), fi=html.indexOf('function renderAcompanhamentos(',ii);
const api = new Function('document','socket','quandoAcompanhamento',
    html.slice(inicio,fim)+html.slice(il,fl)+html.slice(ii,fi)+
    ';return {renderAcompanhamentoFontes,editarFonte,salvarFonte,receberFeedbackFonte,acaoFonte,interromperCadastroFonte,atualizarIndicadorAcompanhamentos};')(document,socket,()=> '07/10 12:00');
const item={id:'a', assunto:'<img onerror=alert(1)>', interesse:'Suporte brasileiro', situacao:'Meu teste',
            status:'ativo',fontes:['https://example.com/feed','javascript:alert(1)'],
            novidades:[{id:'n',etapa:'plano',resumo:'Plano futuro',evidencia:'PT-BR planned',url:'https://example.com/new',lido:false}]};
api.renderAcompanhamentoFontes({itens:[item]});
const card = elementos['fontes-lista'].children[0];
assert.equal(card.children[0].children[0].textContent,item.assunto);
assert.equal(card.children[card.children.length-1].children.length,1,'Link inseguro foi renderizado');
card.open=true;
api.editarFonte('a');
elementos['fonte-interesse'].value='Meu rascunho alterado';
api.renderAcompanhamentoFontes({itens:[{...item,interesse:'Estado do servidor',verificando:true}]});
assert.equal(elementos['fonte-interesse'].value,'Meu rascunho alterado');
assert.equal(elementos['fontes-lista'].children[0].open,true);
const botao=elementos['fontes-lista'].children[0].children.find(e=>e.className==='fonte-acoes').children;
assert.equal(botao.find(b=>b.textContent==='Verificar agora').disabled,true);
api.salvarFonte({preventDefault(){}});
let pedido=envios.pop();
assert.equal(pedido.acao,'editar'); assert.equal(pedido.cadastro.interesse,'Meu rascunho alterado');
api.receberFeedbackFonte({ok:false,request_id:pedido.request_id,texto:'Erro de cadastro'});
assert.equal(elementos['fonte-interesse'].value,'Meu rascunho alterado');
assert.equal(elementos['fonte-salvar'].disabled,false);
api.salvarFonte({preventDefault(){}}); pedido=envios.pop();
elementos['fonte-interesse'].value='Texto novo durante o salvamento';
api.receberFeedbackFonte({ok:true,request_id:pedido.request_id,texto:'Salvo'});
assert.equal(elementos['fonte-interesse'].value,'Texto novo durante o salvamento');
api.salvarFonte({preventDefault(){}}); pedido=envios.pop();
api.receberFeedbackFonte({ok:true,request_id:'antiga',texto:'Outro salvamento'});
assert.equal(elementos['fonte-salvar'].disabled,true,'Confirmação antiga liberou outro pedido');
api.receberFeedbackFonte({ok:true,request_id:pedido.request_id,texto:'Salvo'});
assert.equal(elementos['fonte-interesse'].value,'');
api.editarFonte('a');
api.salvarFonte({preventDefault(){}});
envios.pop();
api.interromperCadastroFonte();
assert.equal(elementos['fonte-salvar'].disabled,false);
assert.equal(elementos['fonte-assunto'].value,item.assunto);
socket.readyState=3;
api.acaoFonte('verificar','a');
assert.equal(envios.length,0); assert.match(elementos['fontes-feedback'].textContent,/Sem conexão/);
api.atualizarIndicadorAcompanhamentos({fontes:{itens:[item,{...item,id:'b',status:'encerrado'}]}});
assert.equal(elementos['acompanhamentos-badge'].textContent,'1');
assert.equal(elementos['acompanhamentos-badge'].hidden,false);
console.log('PASSOU — cadastro, rascunhos, ações, fontes e indicador de novidades');
