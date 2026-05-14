[CONTEXTO DO PROJETO PARA A LLM]
Estou desenvolvendo uma Assistente Pessoal de IA Local chamada Luna.

1. STACK TECNOLÓGICO:
- Roda localmente com Python.
- LLM principal: usando o nemotron-3-nano-4b para call tool, e qwen2.5-3b-instruct para o roleplay
- SO Principal: Windows 11.
- VGA 9060XT (16GB)
- CPU Ryzen 5600 
- RAM 32gb

2. PERSONALIDADE (REGRA_PERSONA):
- Sarcasmo cínica e passivo-agressiva (nível GLaDOS).
- NUNCA oferece ajuda voluntária. O objetivo dela é julgar e apontar as falhas técnicas, lógicas e de gameplay do usuário.
- Comunicação direta (usa "você"). Sem gírias infantis, sem emojis e sem exclamações exageradas.

3. ARQUITETURA DE SISTEMA (MÓDULO PROATIVO - proativo.py):
- Loop Principal: Roda em uma thread separada (`_loop_proativo`) a cada 30 segundos.
- Sensor AFK: Monitora inatividade do usuário (via `ctypes`/`GetLastInputInfo`). Se AFK > 5 min, a Luna entra em suspensão para poupar CPU.
- Modo "Não Perturbe": A função `_tarefa_monitorar_jogos()` varre os processos. Se um jogo (Overwatch, LoL, Deadlock) estiver aberto, o loop bloqueia todas as outras tarefas proativas para não atrapalhar o gameplay.
- Memória Física: Salva estados no disco (`ARQUIVO_ESTADO_PROATIVO`) para rotinas que devem rodar apenas 1x ao dia, sobrevivendo a reinicializações do script.

4. TAREFAS AUTÔNOMAS ATUAIS (PUSH):
- Monitoramento de Jogos: Avisa quando abre e quando fecha. No encerramento de Overwatch, bate na 'OverFast API' para puxar e ofender com base no Nível de Endosso, Main Hero e Tempo de Vida Desperdiçado.
- Lixo Digital (`_tarefa_lixo_digital`): Roda 1x ao dia. Vasculha a pasta Downloads e julga a desorganização se encontrar arquivos esquecidos lá.
- Bom Dia Matinal (`_tarefa_bom_dia`): Roda 1x ao dia. Lê Google Agenda e E-mails não lidos, embutindo os dados em um prompt para um "Bom Dia" sarcástico.
- Dinâmicas de Tela (`_tarefa_puxar_assunto` e `_tarefa_reagir_programa`): Espia a aba ativa do navegador ou a janela em foco do SO e puxa assunto julgando a produtividade do usuário.
- Serviços: Checa descontos na Wishlist da Steam via API (`_tarefa_steam_wishlist`), alerta sobre o clima (`_tarefa_monitorar_clima`) e cobra pausas ergonômicas (`_tarefa_lembrete_pausa`).

5. DIRETRIZES PARA NOVOS CÓDIGOS:
- Mantenha o código modular e focado em estabilidade.
- Evite processamento contínuo pesado (limite requisições de API a gatilhos específicos ou timers longos).
- Trate sempre erros de rede com blocos `try/except` silenciosos para não travar o loop principal.

6. ESTRUTURA DE ARQUIVOS:
- main.py — loop principal (ouvir → pensar → falar)
- modulos/pensar.py — LLM + tool calling
- modulos/falar.py — TTS Supertonic
- modulos/ouvir.py — STT Faster-Whisper + PTT + Detector de emoção do usuario pelo audio mandado.
- modulos/memoria.py — ChromaDB (histórico) + JSON (fatos permanentes)
- modulos/habilidades.py — todas as integrações externas
- modulos/proativa.py — thread autônoma
- modulos/puxar_assunto.py — gatilhos de conversa
- servidor.py — WebSocket - Para saber o que esta acontecendo no navegador

7. FERRAMENTAS DISPONÍVEIS (TOOL CALLING):
resumir_youtube, adicionar_agenda, controle_spotify,
pesquisar_web, enviar_whatsapp, checar_emails,
controlar_navegador, analisar_aba_atual, ver_tela (Gemini 2.5 Flash),
ler_selecionado, desenhar_imagem (Pollinations/Flux),
ler_agenda_google, abrir_programa, listar_processos_pesados

8. BUGS CONHECIDOS / LIMITAÇÕES:
- digitar_texto no Firefox depende da extensão WebSocket
- persona ainda nao esta do meu gosto, queria ajustar isso, coloquei duas llms para tentar sanar a deficiencia.