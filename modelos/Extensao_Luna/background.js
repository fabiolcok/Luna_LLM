let socket = null;

function conectarWebSocket() {
    // Conecta na porta que abrimos no Python
    socket = new WebSocket("ws://127.0.0.1:8765");

    socket.onopen = () => {
        console.log("🔥 Extensão conectada à Luna com sucesso!");
    };

    socket.onmessage = (event) => {
        let dados = JSON.parse(event.data);
        executarComando(dados.acao, dados.parametro);
    };

    socket.onclose = () => {
        console.log("Conexão perdida. A Luna desligou? Tentando de novo em 3s...");
        setTimeout(conectarWebSocket, 3000);
    };
}

// Inicia a conexão assim que o navegador abre
conectarWebSocket();


function executarComando(acao, parametro) {
    if (acao === "abrir_url") {
        browser.tabs.update({ url: parametro }).then(() => {
            socket.send("Site aberto com sucesso.");
        });
    } 
    else if (acao === "obter_url") {
        browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
            socket.send(tabs[0].url);
        });
    }
    else if (acao === "obter_titulo") {
        browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
            socket.send(tabs[0].title || "");
        });
    }
    
    if (acao === "contexto_total") {
        browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
            let tab = tabs[0];
            browser.tabs.executeScript(tab.id, {
                code: `({
                    titulo: document.title,
                    url: window.location.href,
                    texto: document.body.innerText.substring(0, 2000)
                });`
            }).then((resultados) => {
                // Envia como string JSON para o Python
                socket.send(JSON.stringify(resultados[0]));
            });
        });
    }
    // NOVA: Listar todas as abas abertas no Firefox
    else if (acao === "listar_abas") {
        browser.tabs.query({ currentWindow: true }).then((tabs) => {
            let lista = tabs.map(t => ({ id: t.id, titulo: t.title }));
            socket.send(JSON.stringify(lista));
        });
    }
    // NOVA: Mudar para uma aba específica pelo ID
    else if (acao === "trocar_aba") {
        browser.tabs.update(parseInt(parametro), { active: true }).then(() => {
            socket.send("Aba trocada.");
        });
    }




    // ---------------------------------
    else {
        browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
            let tab = tabs[0];
            browser.tabs.executeScript(tab.id, {
                code: getScriptCode(acao, parametro)
            }).then((resultados) => {
                socket.send(resultados[0]);
            }).catch(err => {
                socket.send("SISTEMA: Erro na página: " + err.message);
            });
        });
    }
}

// As instruções que a extensão injeta direto na tela do site
function getScriptCode(acao, parametro) {
    if (acao === "ler_texto") {
        return `
            (function() {
                let texto = document.body.innerText.substring(0, 1500);
                return "SISTEMA: Texto capturado da tela:\\n" + texto + "\\n\\nLUNA, leia essa informação e responda ao pedido do Fábio. Mantenha seu tom sarcástico.";
            })();
        `;
    }
    
    if (acao === "rolar_baixo") {
        return `
            window.scrollBy(0, 800); 
            "SISTEMA: A página foi rolada para baixo. LUNA, faça um comentário rápido sobre a preguiça do Fábio de usar o scroll do mouse.";
        `;
    }
    
    if (acao === "clicar") {
        return `
            (function() {
                let elementos = Array.from(document.querySelectorAll("a, button"));
                let alvo = elementos.find(el => el.innerText.trim().toLowerCase() === "${parametro.toLowerCase()}");
                
                if (alvo) {
                    alvo.click();
                    return "SISTEMA: Clique realizado com sucesso em '${parametro}'. LUNA, avise o Fábio de forma debochada (ex: 'gg', 'clipado').";
                }
                return "SISTEMA: Erro. O elemento '${parametro}' não existe na tela. LUNA, zombe da visão de prata do Fábio por pedir para clicar no que não existe.";
            })();
        `;
    }

    if (acao === "digitar_texto") {
        return `
            (function() {
                let campo = document.querySelector('input[name="search_query"], input[name="q"], input[type="search"], input[type="text"], textarea');
                if (campo) {
                    campo.focus();
                    campo.value = "${parametro}";
                    campo.dispatchEvent(new Event('input', { bubbles: true }));
                    campo.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    let form = campo.closest('form');
                    if (form) {
                        form.submit();
                    } else {
                        campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13, bubbles: true }));
                    }
                    return "Texto digitado e Enter pressionado.";
                }
                return "SISTEMA: Erro. Nenhum campo de pesquisa encontrado.";
            })();
        `;
    }

    // ---- NOVO: NAVEGAÇÃO ----
    if (acao === "navegacao") {
        return `
            (function() {
                if ("${parametro}" === "voltar") { window.history.back(); return "SISTEMA: Voltando página. LUNA, avise o Fábio."; }
                if ("${parametro}" === "recarregar") { location.reload(); return "SISTEMA: Página recarregada. LUNA, avise o Fábio."; }
            })();
        `;
    }

    // ---- NOVO: CONTROLE DE MÍDIA (YOUTUBE/TWITCH) ----
    if (acao === "controle_midia") {
        return `
            (function() {
                let video = document.querySelector("video");
                
                // Função especial para pular anúncio
                if ("${parametro}" === "pular_anuncio") {
                    let btn = document.querySelector(".ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button");
                    if (btn) { 
                        btn.click(); 
                        return "SISTEMA: Anúncio do YouTube pulado. LUNA, zombe do Fábio por ser um pleb sem YouTube Premium."; 
                    }
                    return "SISTEMA: Nenhum botão de pular anúncio na tela. LUNA, diga que o Fábio vai ter que assistir o anúncio inteiro e ria dele.";
                }
                
                // Funções gerais de vídeo
                if (video) {
                    if ("${parametro}" === "play_pause") {
                        if (video.paused) { video.play(); return "SISTEMA: Vídeo rolando. LUNA, confirme com o Fábio."; }
                        else { video.pause(); return "SISTEMA: Vídeo pausado. LUNA, confirme com o Fábio."; }
                    }
                    if ("${parametro}" === "mutar") {
                        video.muted = !video.muted;
                        return "SISTEMA: Som alterado. LUNA, confirme com o Fábio.";
                    }
                }
                return "SISTEMA: Erro. Nenhum reprodutor de vídeo encontrado na tela.";
            })();
        `;
    }

    return `"SISTEMA: Comando desconhecido."`;
}