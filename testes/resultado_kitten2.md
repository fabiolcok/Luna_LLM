# KittenTTS 2 x Kokoro — 03/10/2026

O KittenTTS 2 gerou as seis amostras em português na CPU. A instalação ficou em um ambiente
isolado, sem trocar a voz da Luna. No runtime Python testado, demorou entre 55 e 68 segundos
para produzir cada frase. O Kokoro levou entre 3 e 5 segundos para os mesmos quatro textos.

[Ouvir a comparação local](../logs/bancada_tts/kitten2-20261003/amostras/ouvir.html).

A página não toca automaticamente. Seus controles usam cópias com RMS aproximado de 0,049
e limite de pico 0,95; há links para os WAVs brutos. A normalização não altera timbre ou ritmo
e não equivale a uma medição rigorosa de volume percebido.

## Avaliação do usuário — 03/10/2026

Após ouvir a comparação, o usuário avaliou: **“kokoro tá melhor ainda”**.
A preferência auditiva permanece com o Kokoro. Não foram dadas notas individuais
para sotaque, ritmo ou emoção, então não atribuímos motivos específicos à preferência.

**Decisão: manter o Kokoro na Luna e registrar o KittenTTS 2 como experimento avaliado,
sem integração aprovada.** A versão C++ continua sem medição; o teste atual não
justificou a troca de voz.

## Ambiente e configuração

- Windows 11, Ryzen 5 5600, 6 núcleos / 12 threads, 32 GB de RAM.
- Ambos os motores com 6 threads de PyTorch. Processos separados, sem inferências simultâneas.
- KittenML 0.9.3, PyTorch/torchaudio 2.6.0+cpu, transformers 4.57.6, NumPy 2.2.6.
- KittenTTS 2: pesos packed (lossless), voz Portuguese, decoder default, BF16, CPU.
- Snapshot do modelo: baa41e5d2c5f64be0095365672a7858542261271.
- Vocoder s3gen_meanflow: ResembleAI/chatterbox-turbo, snapshot
  749d1c1a46eb10492095d68fbcf55691ccf137cd.
- normalize=False, seed 42, orçamento de 750 tokens por chunk.
- Quatro amostras stable; duas adicionais expressive, com [stern] na morte e [joyful] na conquista.
- Kokoro 0.9.4, Nicole/af_nicole, português, speed=0.9; PyTorch 2.11.0+cpu.
- Não houve reprodução automática, geração de respostas por LLM ou execução da Luna.

A RAM estava muito ocupada durante a preparação. Após a liberação observada, havia cerca de
9 GB livres antes do Kitten. Durante a geração, seu processo chegou a aproximadamente
6,1 GiB residentes e 7,3 GiB de memória privada. Ainda havia pressão sobre o limite de memória
virtual do Windows. Não é medição em uma máquina dedicada, nem teste de FPS durante o jogo.

## Resultados

| Frase | Kokoro: geração | Áudio Kokoro | Kitten stable: geração | Áudio Kitten | RTF Kitten |
|---|---:|---:|---:|---:|---:|
| Saudação | 3,22 s | 6,85 s | 67,52 s | 3,80 s | 17,77 |
| Morte | 3,58 s | 9,65 s | 55,35 s | 5,32 s | 10,40 |
| Conquista | 4,38 s | 11,05 s | 61,26 s | 6,32 s | 9,69 |
| Números/preço | 5,05 s | 13,55 s | 64,42 s | 6,68 s | 9,64 |

| Kitten expressive | Geração | Áudio | RTF |
|---|---:|---:|---:|
| Morte + [stern] | 68,10 s | 6,04 s | 11,27 |
| Conquista + [joyful] | 55,90 s | 6,12 s | 9,13 |

RTF é o tempo para gerar dividido pela duração do áudio: abaixo de 1 significa geração
mais rápida que a reprodução. O Kokoro ficou entre 0,37 e 0,47; o Kitten entre 9,13 e 17,77.

As frases têm menos de 380 caracteres e o Kitten devolveu um único chunk em cada amostra.
Assim, o primeiro áudio ficou pronto praticamente no final da síntese. A chamada
generate_stream não trouxe ganho de início nestas frases curtas.

Carga com pesos já baixados: aproximadamente 47 segundos no Kitten e 65 segundos no Kokoro.
Isso é separado dos tempos de geração e não inclui a criação do ambiente. Tempos de uma
rodada só não estimam estabilidade em sessões longas. As versões de PyTorch diferem.

## Checagem do texto e avaliação auditiva

O faster-whisper-small local, CPU/int8, transcreveu os dez arquivos brutos.
As saudações e conquistas vieram quase completas em português. Nos comentários de morte do
Kitten, apareceram reconhecimentos como “pagar em salubridade” e “apagar em salubridade”.
A versão com emoção também trouxe uma palavra inicial inesperada na transcrição.
Isso pode ser erro de reconhecimento ou da síntese; precisa ser conferido ouvindo.

O preço com R$ 51,95 também merece escuta nos dois motores: o Kitten voltou como 51.95
e o Kokoro teve reconhecimento estranho do símbolo monetário. A normalização inglesa foi
desligada como orienta a documentação do Kitten; não foi acrescentado normalizador PT-BR.

As transcrições não provam naturalidade, sotaque brasileiro ou expressividade.
A comparação expressive muda o preset e acrescenta a tag ao mesmo tempo; não isola a
contribuição de cada opção. A decisão sobre qual voz combina com a Luna fica para a escuta.

## Limite importante do teste em CPU

Foi testada a versão Python/PyTorch. A implementação C++ oficial usa llama.cpp/GGML e kernels
para pesos ternários, além de LibTorch para o decoder. Ela não foi compilada nem medida aqui.
Portanto, estes tempos não demonstram a velocidade máxima do KittenTTS 2 na CPU.

Pelos tempos desta instalação, a versão Python não é uma troca prática para comentários
durante a jogatina. Após a escuta, o usuário preferiu manter o Kokoro; a integração
do Kitten não foi aprovada. O runtime C++ permanece sem medição.

Fontes consultadas:
- [API Python e recomendações de CPU](https://github.com/KittenML/KittenTTS/blob/main/docs/api.md).
- [Português, vozes e limitações da emoção](https://github.com/KittenML/KittenTTS/blob/main/docs/voices-and-expression.md).
- [Runtime C++ oficial](https://github.com/KittenML/kitten-tts-2-cpp).

## Artefatos e reprodução

- testes/bancada_kitten2.py — gera os mesmos textos nos dois ambientes e salva medições por arquivo.
- testes/requirements_kitten2.txt — dependências opcionais do ambiente separado.
- logs/bancada_tts/kitten2-20261003/amostras/ — dez WAVs, JSONs, transcrições e página para escuta.
- logs/bancada_tts/kitten2-20261003/amostras/normalizados/ — cópias e ganhos aplicados.
- logs/bancada_tts/kitten2-20261003/bancada_usada.py — código executado na comparação.
- logs/bancada_tts/kitten2-20261003/modelo.json — snapshot exato dos pesos.
- logs/bancada_tts/kitten2-20261003/torch-kokoro.json — confirma runtime CPU do Kokoro.
- logs/ambientes/kitten2/ — ambiente virtual isolado.
- logs/cache_kitten2/ — pesos e caches locais.

A versão atual da bancada fixa device=cpu também no Kokoro; a rodada original usou a seleção
automática em uma instalação PyTorch CPU-only, verificada separadamente.
A voz em produção, dependências principais e configuração da Luna continuam iguais.

Validação: instalação sem dependências quebradas (pip check), arquivos não vazios e finitos,
CLI/compilação Python e 39 arquivos de testes Node aprovados. Uma execução curta valida
também o caminho com seleção explícita de CPU do Kokoro. Não houve teste da integração,
pois nenhum motor foi integrado à Luna.

Instruções de instalação e comandos: [README dos testes](README.md#kittentts-2--bancada-isolada-em-cpu).
