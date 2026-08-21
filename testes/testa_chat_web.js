#!/usr/bin/env node
// Garante que a conversa principal continue rolável, copiável e sem executar HTML da LLM.

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

assert.ok(/#historico-panel\s*\{[^}]*position:\s*static/s.test(html),
          'FALHA: histórico deixou de ser a conversa principal');
assert.ok(/#historico-panel\s*\{[^}]*background:\s*transparent;\s*border:\s*0;\s*border-radius:\s*0/s.test(html),
          'FALHA: recipiente visual voltou a separar a conversa da página');
assert.ok(/\.historico-header\s*\{\s*display:\s*none;\s*\}/.test(html) &&
          /<div class="config-secao-titulo">💬 Conversa<\/div>[\s\S]*?id="btn-historico-limpar"/.test(html),
          'FALHA: título voltou ao chat ou limpeza saiu das configurações');
assert.ok(!/#config-panel #btn-historico-limpar\s*\{[^}]*display:\s*block/s.test(html),
          'FALHA: botão limpar voltou a furar o recolhimento da seção');
assert.ok(html.includes('presencaStatus.appendChild(statusCabecalho)') &&
          html.includes("classList.toggle('tem-ferramenta'") &&
          /#presenca:hover #status-luna\.tem-ferramenta\s*\{[^}]*opacity:\s*1/s.test(html) &&
          /#presenca #status-luna\s*\{[^}]*left:\s*calc\(50% \+ 120px\)/s.test(html) &&
          /body\.widget #status-luna\s*\{\s*display:\s*none\s*!important/s.test(html),
          'FALHA: diagnóstico da ferramenta deixou de aparecer só no hover do mascote web');
assert.ok(/#historico-lista\s*\{[^}]*user-select:\s*text/s.test(html),
          'FALHA: texto da conversa deixou de ser selecionável');
assert.ok(/#historico-lista\s*\{[^}]*display:\s*flex;[^}]*flex-direction:\s*column/s.test(html) &&
          /#historico-lista::before\s*\{[^}]*flex:\s*1 0 auto/s.test(html),
          'FALHA: conversa curta voltou a crescer do topo para baixo');
assert.ok(/@keyframes balao-entra\s*\{[^}]*translateY\(13px\)/s.test(html) &&
          html.includes("balaoUsuario.classList.add('balao-entrando')") &&
          html.includes("luna.className = 'turno-luna balao-entrando'"),
          'FALHA: balões novos deixaram de entrar suavemente de baixo para cima');
assert.ok(/\.turno-luna\s*\{[^}]*color:\s*#c1ccd5/s.test(html) &&
          /\.mensagem-conteudo h1[^\{]*\{[^}]*color:\s*#d5dbe1/s.test(html),
          'FALHA: texto da Luna voltou ao ciano neon cansativo');
assert.ok(html.includes('#historico-lista.fade-topo.fade-fundo') &&
          html.includes("classList.toggle('fade-topo', acima)") &&
          html.includes("classList.toggle('fade-fundo', abaixo)"),
          'FALHA: conversa perdeu o fade ligado à posição da rolagem');
assert.ok(/max-width:\s*1040px/.test(html) &&
          /#historico-panel\s*\{[^}]*height:\s*clamp\(440px,\s*58vh,\s*760px\)/s.test(html),
          'FALHA: conversa principal voltou ao tamanho compacto');
assert.ok(/\.zona-divisor\s*\{\s*display:\s*none;\s*\}/.test(html),
          'FALHA: divisor antigo voltou a ocupar espaço');
assert.ok(/#acompanhamento-feedback\s*\{[^}]*display:\s*none/s.test(html) &&
          /#acompanhamento-feedback:not\(\.ativo\)[^\{]*\{\s*margin-top:\s*-16px/s.test(html),
          'FALHA: espaço vazio voltou entre avaliação e entrada');
assert.ok(/<summary>Detalhes<\/summary>[\s\S]*?<div id="metricas-bar">[\s\S]*?<\/details>/.test(html),
          'FALHA: detalhes e métricas deixaram de compartilhar o expansível');
assert.ok(html.includes('balao.appendChild(detailsEl)') &&
          html.includes('anexarDetalhesAoTurno(turnoEl)'),
          'FALHA: detalhes deixaram de acompanhar a fala mais recente da Luna');
assert.ok(/<div id="avaliacao-bar">[\s\S]*?id="btn-repetir"[\s\S]*?id="btn-interromper"[\s\S]*?data-rating="bom"[\s\S]*?data-rating="ruim"[\s\S]*?class="avaliacao-espaco"[\s\S]*?id="btn-toggle-proativo"[\s\S]*?<\/div>/.test(html),
          'FALHA: controles de fala, avaliação e proativo deixaram a barra compacta');
assert.ok(/#avaliacao-bar #btn-interromper\s*\{[^}]*opacity:\s*\.45/s.test(html) &&
          /#avaliacao-bar #btn-interromper:hover\s*\{[^}]*opacity:\s*1/s.test(html),
          'FALHA: parar fala voltou a ter destaque maior que os controles vizinhos');
assert.ok(html.includes("conteudo.innerHTML = renderizarMarkdownSeguro(turno.luna)"),
          'FALHA: resposta não passa pelo renderizador seguro');
assert.ok(html.includes("if (dados.tipo === 'resposta_stream')") &&
          html.includes('mostrarRespostaStream(dados.texto') &&
          /function mostrarRespostaStream\(texto\)[\s\S]*?animarBraileStream\(\)/.test(html) &&
          /function animarBraileStream\(\)[\s\S]*?quadroBraile\(_braileStreamAlvo/.test(html),
          'FALHA: resposta parcial deixou de atualizar o balão seguro da conversa');
assert.ok(!html.includes('`<div class="turno-usuario">${turno.usuario}</div>`'),
          'FALHA: texto do usuário voltou a entrar como HTML cru');

const inicio = html.indexOf('function escaparHtml(');
const fim = html.indexOf('function copiarMensagem(', inicio);
assert.ok(inicio >= 0 && fim > inicio, 'FALHA: funções do Markdown não encontradas');
const contexto = {};
vm.createContext(contexto);
vm.runInContext(html.slice(inicio, fim), contexto);

const inicioBraile = html.indexOf('const BRAILE =');
const fimBraile = html.indexOf('function typewriter(', inicioBraile);
const contextoBraile = {};
vm.createContext(contextoBraile);
vm.runInContext(html.slice(inicioBraile, fimBraile), contextoBraile);
const quadro = contextoBraile.quadroBraile('Luna escreve', 4, 6);
assert.strictEqual(quadro.slice(0, 4), 'Luna',
                   'FALHA: braille alterou caracteres que já deveriam estar resolvidos');
assert.ok([...quadro.slice(4)].some(c => c >= '\u2801' && c <= '\u2840'),
          'FALHA: animação da conversa deixou de gerar ruído braille');

const ataque = contexto.renderizarMarkdownSeguro('<img src=x onerror=alert(1)>');
assert.ok(ataque.includes('&lt;img') && !ataque.includes('<img'),
          'FALHA: HTML cru atravessou o renderizador');

const tabela = contexto.renderizarMarkdownSeguro(
    '| Nome | Volume |\n| --- | --- |\n| Silksong | 2 |');
assert.ok(tabela.includes('<table>') && tabela.includes('<th>Nome</th>') &&
          tabela.includes('<td>Silksong</td>'),
          'FALHA: tabela Markdown não foi renderizada');

const codigo = contexto.renderizarMarkdownSeguro('```py\nprint("Luna")\n```');
assert.ok(codigo.includes('<pre><code>') && codigo.includes('print(&quot;Luna&quot;)'),
          'FALHA: bloco de código perdeu formatação segura');

console.log('PASSOU — conversa web renderiza e copia texto com segurança');
