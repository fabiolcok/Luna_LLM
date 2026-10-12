// Consulta e envio reais; só transporte HTTP/WebSocket e DOM são substituídos.
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');
class Elemento {
    constructor(tag='div') {
        this.tagName=tag; this.children=[]; this.dataset={}; this.style={}; this.events={};
        this.value=''; this.hidden=false; this.open=false; this.textContent=''; this.className='';
        this.classList = {
            add: nome => this.className += ' '+nome,
            remove: nome => this.className=this.className.replace(nome,''),
            toggle: (nome, valor) => valor ? this.classList.add(nome) : this.classList.remove(nome)
        };
    }
    append(...els) { for(const el of els) this.appendChild(el); }
    appendChild(el) { this.children.push(el); el.parentNode=this; return el; }
    insertBefore(el, outro) { this.children.splice(this.children.indexOf(outro),0,el); el.parentNode=this; }
    get firstChild() { return this.children[0]; }
    replaceChildren() { this.children=[]; }
    remove() { this.parentNode.children=this.parentNode.children.filter(el=>el!==this); }
    addEventListener(nome, fn) { (this.events[nome] ||= []).push(fn); }
    setAttribute(nome, valor) { this[nome]=valor; }
    removeAttribute(nome) { delete this[nome]; }
    focus() { this.foco=true; }
    scrollIntoView() { this.rolou=true; }
    showModal() { this.open=true; }
    close() { this.open=false; for(const fn of this.events.close || []) fn(); }
    querySelector(seletor) {
        for(const el of this.children) {
            if (seletor.startsWith('.') ? el.className.split(' ').includes(seletor.slice(1)) : el.tagName===seletor) return el;
            const achou=el.querySelector(seletor); if(achou) return achou;
        }
        return null;
    }
}
const elementos={}, documentoEventos={}, pedidos=[], envios=[];
const document={createElement: tag=>new Elemento(tag),
    getElementById: id=>elementos[id] ||=new Elemento(),
    addEventListener: (nome,fn)=> (documentoEventos[nome] ||= []).push(fn)};
let retorno={itens:[],total:0,mais:false,nao_lidas:0};
let falha=false, pendentes=null;
const contexto=vm.createContext({document, URLSearchParams, Date, console, encodeURIComponent,
    setTimeout: ()=>1,clearTimeout:()=>{},
    socket:{readyState:1,send: s=>envios.push(JSON.parse(s)),reconectar(){}},
    fetch: async (url,opcoes)=> {
        pedidos.push({url,opcoes});
        if (pendentes) return new Promise(resolve=>pendentes.push(resolve));
        return {ok:!falha,json:async()=>retorno};
    },
    renderizarMarkdownSeguro: t=>'<p>'+t+'</p>',
    criarCartaoWeb: dados=>{
        const card=new Elemento('article'), acoes=new Elemento(); acoes.className='cartao-web-acoes';
        const link=new Elemento('a'); link.href=dados.url;
        const todas=new Elemento('button'); todas.className='cartao-noticia-todas';
        acoes.append(link,todas); card.appendChild(acoes); return card;
    }
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'..','static','consulta-web.js'),'utf8'),contexto);
const inicio=html.indexOf('// --- Caixa de texto'),fim=html.indexOf('// --- Acompanhamentos:',inicio);
vm.runInContext(html.slice(inicio,fim),contexto);
contexto.iniciarConsultaWeb();
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
    contexto.abrirBiblioteca('promocao'); await flush();
    assert.equal(elementos['consulta-web'].open,true);
    assert.ok(elementos['consulta-web'].className.includes('consulta-biblioteca'));
    assert.equal(elementos['consulta-fechar'].textContent,'← Voltar à conversa');
    assert.ok(pedidos.at(-1).url.includes('tipo=promocao'));
    assert.equal(elementos['consulta-status'].textContent,'Nenhum resultado por aqui.');
    assert.equal(envios.length,0,'Abrir a biblioteca chamou o modelo');
    assert.ok(!pedidos.some(p=>p.opcoes),'Abrir a biblioteca marcou tudo como lido');

    retorno={itens:[{id:'item',tipo:'noticia',titulo:'Uma notícia',url:'https://example.org/n',lido:false}],total:31,mais:true};
    await contexto.carregarConsultaWeb();
    assert.equal(elementos['consulta-lista'].children.length,1);
    assert.equal(elementos['consulta-mais'].hidden,false);
    const card=elementos['consulta-lista'].children[0];
    assert.equal(card.querySelector('.cartao-noticia-todas'),null,'Ver todas reapareceu dentro da biblioteca');
    const botoes=card.querySelector('.cartao-web-acoes').children.filter(el=>el.tagName==='button');
    await botoes[0].onclick();
    const leitura=pedidos.find(p=>p.opcoes);
    assert.equal(leitura.url,'/api/biblioteca/item/leitura');
    assert.deepEqual(JSON.parse(leitura.opcoes.body),{lido:true});
    await contexto.carregarConsultaWeb(true);
    assert.equal(elementos['consulta-lista'].children.length,2,'Carregar mais apagou a página anterior');

    // Um retorno atrasado não pode substituir a pesquisa atual.
    pendentes=[];
    const antiga=contexto.carregarConsultaWeb();
    elementos['consulta-busca'].value='OLED';
    const nova=contexto.carregarConsultaWeb();
    pendentes[1]({ok:true,json:async()=>({itens:[],total:0,mais:false})}); await nova;
    pendentes[0]({ok:true,json:async()=>retorno}); await antiga;
    assert.equal(elementos['consulta-lista'].children.length,0);
    assert.ok(pedidos.at(-1).url.includes('busca=OLED'));
    pendentes=null;
    falha=true; await contexto.carregarConsultaWeb();
    assert.ok(elementos['consulta-status'].textContent.includes('Tente novamente'));
    assert.equal(elementos['consulta-busca'].value,'OLED'); falha=false;

    const naTela=new Elemento();naTela.dataset.turnoId='turno';document.getElementById('historico-lista').appendChild(naTela);
    contexto.abrirConsultaWeb('historico'); await flush();
    assert.ok(!elementos['consulta-web'].className.includes('consulta-biblioteca'));
    assert.ok(pedidos.at(-1).url.startsWith('/api/historico?'));
    assert.ok(elementos['consulta-dica'].textContent.includes('conversas anteriores'));
    const antigaSalva=contexto.criarResultadoConversa({id:'antiga',data:'2026-08-22T10:00:00',usuario:'Pergunta antiga',
        luna:'Resposta recuperada',incompleto:true});
    assert.ok(antigaSalva.children[0].textContent.includes('Trecho recuperado do log'));
    assert.equal(antigaSalva.querySelector('details'),null,'A busca não duplica a resposta em um bloco expansível');
    assert.equal(antigaSalva.querySelector('.mensagem-conteudo').innerHTML,'<p>Resposta recuperada</p>');
    assert.equal(antigaSalva.querySelector('.consulta-acoes').children.length,1,'Uma mensagem fora da sessão só oferece responder');
    antigaSalva.querySelector('.consulta-acoes').children[0].onclick();
    assert.equal(contexto.obterRespostaSelecionada().turno_id,'antiga');
    contexto.limparRespostaSelecionada();
    const respostaLonga='Uma resposta longa. '.repeat(20)+'Fim da resposta.';
    const resultado=contexto.criarResultadoConversa({id:'turno',data:'2026-10-11T10:00:00',usuario:'Pergunta',luna:respostaLonga});
    assert.equal(resultado.querySelector('.mensagem-conteudo').innerHTML,'<p>'+respostaLonga+'</p>',
        'A resposta aparece inteira, sem o corte da prévia de 240 caracteres');
    assert.equal(resultado.children.length,4,'A resposta aparece uma única vez entre pergunta e ações');
    resultado.querySelector('.consulta-acoes').children[1].onclick();
    assert.equal(naTela.rolou,true);assert.equal(elementos['consulta-web'].open,false);

    const input=elementos['texto-input']; input.value='Meu rascunho';
    contexto.selecionarResposta({turno_id:'turno'},'Resposta escolhida');
    assert.equal(input.value,'Meu rascunho','Escolher referência apagou o rascunho');
    contexto.enviarTexto();
    let pedido=envios.at(-1);
    assert.deepEqual(JSON.parse(JSON.stringify(pedido.resposta_a)),{turno_id:'turno'});
    assert.equal(pedido.texto,'Meu rascunho');assert.equal(pedido.luna,undefined);
    contexto.receberConfirmacaoTexto({...pedido,ok:false,erro:'Referência expirada'});
    assert.equal(input.value,'Meu rascunho');assert.equal(elementos['resposta-selecionada'].hidden,false);
    contexto.enviarTexto();pedido=envios.at(-1);
    contexto.selecionarResposta({turno_id:'outro'},'Outra referência');
    contexto.receberConfirmacaoTexto({...pedido,ok:true});
    assert.equal(contexto.obterRespostaSelecionada().turno_id,'outro','ACK apagou a nova referência');
    input.value='Agora sim';contexto.enviarTexto();pedido=envios.at(-1);
    contexto.receberConfirmacaoTexto({...pedido,ok:true});
    assert.equal(contexto.obterRespostaSelecionada(),null);assert.equal(input.value,'');

    const antes=envios.length;
    contexto.abrirImagem({currentSrc:'https://example.org/capa.jpg',src:'outra'},'Título');
    assert.equal(elementos['imagem-ampliada'].open,true);
    assert.equal(elementos['imagem-ampliada-arquivo'].src,'https://example.org/capa.jpg');
    elementos['imagem-ampliada-fechar'].onclick();
    assert.equal(elementos['imagem-ampliada-arquivo'].src,undefined);
    assert.equal(envios.length,antes,'Ampliar a imagem chamou o modelo');
    console.log('testa_consulta_web ok');
})().catch(erro=>{console.error(erro);process.exitCode=1;});
