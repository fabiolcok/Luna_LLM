# Voz da Luna no Discord (opcional)

O bot transmite a voz Kokoro diretamente a um canal de voz de servidor. Não usa
placa de som virtual, não captura microfone e não lê mensagens do Discord.
Cada instalação usa seu próprio bot e token. Sem configuração, a Luna funciona
normalmente e não importa a biblioteca Discord nem abre conexão com o serviço.

## Instalar

Na raiz do projeto, no mesmo ambiente da Luna:

```powershell
.\venv\Scripts\python.exe -m pip install -r integracoes/discord/requirements.txt
.\venv\Scripts\python.exe -m discord --version
```

É necessário Python compatível com discord.py e seus extras de voz, incluindo
PyNaCl e davey. O requirements fixa discord.py 2.7.1 e davey na série 0.1:
a API de transições mudou na davey 0.2 e não é compatível com essa versão do
discord.py. Instale pelo requirements também para corrigir uma instalação anterior
e reinicie completamente a Luna. Não é necessário FFmpeg: o PCM do Kokoro é convertido para 48 kHz estéreo
usando NumPy/SciPy já presentes na Luna. Windows usa o carregamento de Opus da
biblioteca; em outros sistemas pode ser necessário instalar libopus.

## Criar o bot e escolher o canal

1. Abra https://discord.com/developers/applications e crie uma aplicação.
2. Na seção Bot, obtenha o token do bot. Não use token de conta pessoal.
3. Em OAuth2 / URL Generator, selecione o escopo `bot` e as permissões
   **View Channels**, **Connect** e **Speak**. Convide para seu servidor.
   Não precisa de Administrator nem intents privilegiadas.
4. No Discord, ative Modo Desenvolvedor em Avançado. Clique com o botão direito
   no canal de voz e copie seu ID. O bot precisa ter acesso a esse canal, inclusive
   nas permissões específicas dele. Use canal de voz comum; não DM nem Stage.
5. Preencha no `.env` local (não publique nem envie seu token em conversas):

```dotenv
DISCORD_BOT_TOKEN=
DISCORD_VOICE_CHANNEL_ID=
```

Reinicie a Luna após instalar e configurar. O token nunca é enviado à interface.

## Usar

- Menu da Luna → **Discord** → **Entrar no canal**. A conexão é manual a cada sessão.
- Quando conectada, as respostas recentes ganham **Falar no Discord**. Esse botão
  sintetiza a resposta existente, sem nova consulta ao LLM e sem tocar no fone local.
  Você e seus amigos ouvem o bot pelo Discord.
- Opcionalmente ative **Compartilhar comentários dos jogos**. Somente falas
  marcadas internamente como `comentario_jogo` seguem automaticamente para o bot.
  Agenda, notícias e outras falas pessoais não são encaminhadas automaticamente.
  A fala automática de jogo toca no PC e também é enviada ao Discord.
- **Sair do canal** encerra transmissão e descarta a fila. Ao interromper um
  comentário de jogo na Luna, sua transmissão também é interrompida.
- A interface informa erros de conexão e transmissão. Há no máximo quatro falas
  aguardando; falas que esperam mais de 60 segundos são descartadas.

Controle disponível somente pelo PC local (`localhost`/`127.0.0.1`). Os amigos
ajustam o volume do bot pelo Discord; o microfone pessoal segue independente.
A opção de jogos é desligada ao sair e não persiste entre sessões.
O estado pode levar até três segundos para atualizar no painel.

## Limites e validação

Não há comandos de chat, escuta, reconhecimento de voz ou reprodução de música.
Respostas textuais são compartilhadas por escolha explícita; não é um espelho
automático de todas as conversas. A síntese compartilha a trava do Kokoro com a
voz local, evitando duas gerações simultâneas no mesmo motor.

Testes locais usam cliente Discord simulado. Conexão DAVE, permissões e qualidade
de áudio precisam ser confirmadas em um servidor real com o bot configurado.

Fontes: https://discordpy.readthedocs.io/en/latest/whats_new.html e
https://discordpy.readthedocs.io/en/latest/api.html#discord.VoiceClient
