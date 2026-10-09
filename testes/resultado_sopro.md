# Sopro v2 Turbo x Kokoro — 04/10/2026

O Sopro funcionou localmente em Python/PyTorch CPU. Foram geradas oito amostras:
quatro frases, cada uma em geração completa e streaming. Os WAVs estão em
`logs/bancada_tts/sopro-20261004/amostras/`, com uma página `ouvir.html` para
comparação. O usuário gostou do resultado, mas considerou ruim o sotaque PT-PT;
o Sopro fica como candidato para reavaliar em futuras atualizações.

A Luna continua usando Kokoro. O ambiente Sopro, cache, modelo e demo ficam separados
em `logs/`. Não houve alteração no motor de voz, no venv principal ou nos prompts.

## Avaliação do usuário — 04/10/2026

Após ouvir, o usuário gostou do Sopro e destacou a “respiração” diferente da voz
do Kokoro. Confirmou que o teste local funcionou e que o problema percebido foi
o sotaque PT-PT: “funcionou sim, só o sotaque que foi ruim”.

Não foi declarada uma preferência geral sobre o Kokoro nem dadas notas por categoria.
A observação sobre respiração é avaliação auditiva do usuário, não uma métrica
automática ou identificação técnica da causa.

**Decisão: manter o Kokoro por enquanto e acompanhar futuras atualizações do Sopro,
especialmente suporte ou melhorias para português brasileiro.** Quando houver
mudança relevante, repetir os mesmos textos com a referência fornecida e comparar
sotaque, respiração, clareza e latência antes de considerar a integração.

Na consulta de 04/10/2026, o autor mencionava expansão de idiomas e controle
de emoção, sem roadmap público específico ou previsão para PT-BR.

## Ambiente e referência

- Windows 11, Python 3.12.10; Ryzen 5 5600; 32 GB de RAM.
- Sopro 2.2.0, torch/torchaudio 2.6.0+cpu, NumPy 2.2.6, soundfile 0.13.1.
- Modelo: `samuel-vitorino/sopro-v2-turbo`.
- Revisão: `6c4aa6bba196ea3c8ee8e3e8b5dabe7a715fac92`.
- CPU explícita, seis threads; sem CUDA/HIP; sem quantização int8.
- Seed 42, idioma pt, dois passos acústicos, temperature 0.8, top-p 0.9, top-k 25.
- Teto de 20 segundos por segmento; chunk_frames 64.
- Referência sintética: Kokoro/Nicole, `kokoro_conquista_stable.wav`, 11,05 s.
  O modelo usa até aproximadamente 10 s pela configuração ref_seconds.
- As quatro amostras Kokoro foram reaproveitadas de 03/10/2026. Seus tempos não
  representam uma nova execução simultânea ou controlada com o Sopro.

A referência brasileira não garante sotaque brasileiro: o treinamento do Sopro
prioriza português europeu. A frase de conquista também aparece na referência;
as outras três frases são mais úteis para avaliar a generalização.

## Medições

Carga incluindo o primeiro download: 16,98 s. Preparo da referência: 0,16 s
no modo completo e 0,66 s com preparo de streaming. Aquecimento separado:
2,16 s completo e 2,09 s streaming. Carga, preparo e aquecimento não entram
nos tempos por frase abaixo.

| Frase | Completo: geração | Áudio completo | Streaming: primeiro chunk | Streaming: geração total | Áudio streaming |
|---|---:|---:|---:|---:|---:|
| Conversa | 2,56 s | 3,96 s | 0,48 s | 2,34 s | 3,79 s |
| Morte | 3,24 s | 5,06 s | 0,82 s | 3,07 s | 5,00 s |
| Chefe | 3,61 s | 5,22 s | 0,94 s | 3,34 s | 5,05 s |
| Tempo/preço | 3,98 s | 6,67 s | 0,79 s | 3,66 s | 6,35 s |

RTF completo: 0,60–0,69; streaming: 0,58–0,66. A geração ficou mais rápida
que a duração do áudio. O primeiro chunk foi medido na biblioteca, com referência
preparada; não é o instante de reprodução audível no navegador. Buffering, transporte
e processamento da referência podem aumentar esse tempo.

As durações do Sopro são menores que as do Kokoro/Nicole nesta comparação;
igual duração ou ritmo não foi imposto. Tempo total menor não prova maior naturalidade.

## Checagem de texto

O faster-whisper-small local (CPU/int8) transcreveu os oito WAVs. Há divergências
em trechos como “despertador”, “esse expediente” e “Demônio Touro”. A frase de
preço virou algo reconhecido como “erros ao lar cinquenta e um vírgula...”, sugerindo
problema com o símbolo R$. Isso é indício, não julgamento auditivo: erros podem
vir do TTS, do sotaque europeu ou do próprio ASR. Ouvir os originais é necessário.

A primeira rodada usou apenas referência sintética. A rodada com a gravação
humana e a avaliação do usuário estão registradas neste relatório. A quantização
int8 não foi testada.

## Erro da demo no navegador

Erro informado pelo usuário:

```text
failed to call OrtRun()
Conv: No cached or pending pipeline for deferred dispatch
```

Esse erro apareceu na demo ONNX do navegador. Não foi reproduzido nem diagnosticado
até um navegador/GPU específico. O teste local usa PyTorch CPU e outro caminho de
execução; funcionou nos oito casos.

A demo Python local foi validada por HTTP:
página, JS e info retornaram 200; preparação de referência, geração completa
e streaming devolveram áudio finito e não silencioso. O streaming usou
Transfer-Encoding: chunked. A interface do navegador não foi automatizada.

O launcher copia os recursos da demo oficial para logs, remove o importmap de
CDN/ONNX, usa o backend Python local e pré-carrega a referência Nicole. Fica
restrito a 127.0.0.1:7860. Nenhum áudio toca antes da ação do usuário.

## Artefatos e reprodução

- `logs/bancada_tts/sopro-20261004/amostras/ouvir.html`: 12 amostras, mais referência.
- `resultado_sopro.json`: parâmetros, revisão, latências e emissões de chunks.
- `baseline_kokoro_20261003.json`: metadados da execução anterior.
- `transcricoes.json`: checagem automática de inteligibilidade.
- `normalizacao.json`: ganhos das cópias; alvo RMS 0,049 com limite de pico 0,95.
- `logs/bancada_tts/sopro-20261004/validacao-http.json`: teste dos endpoints Python.
- `modelo-remoto.json` e `pacotes.txt`: revisão/tamanhos e versões instaladas.
- `bancada_usada.py`, `servir_usado.py` e `montar_comparacao.py`: fontes usadas.

[Instruções de instalação e execução](README.md#sopro--bancada-e-demo-local-em-cpu).

Fontes: [repositório](https://github.com/samuel-vitorino/sopro),
[modelo](https://huggingface.co/samuel-vitorino/sopro-v2-turbo),
[avaliações e foco em português europeu](https://research.haloneuro.ai/posts/sopro-v2).

## Verificação

39 arquivos da suite Node passaram. Os 13 players apontam para WAVs válidos.
As duas rotas de geração HTTP e o comando --parar foram verificados.
A demo foi reiniciada na porta 7860 para a avaliação do usuário.

## Segunda rodada — referência humana fornecida

Em 04/10/2026 foi usada a gravação M4A fornecida pelo usuário. O arquivo tem
23,45 s, AAC estéreo a 48 kHz. Foi convertido localmente com PyAV 17.0.1 para
WAV mono a 24 kHz; os primeiros 15 s foram selecionados, sem alterar o original.
A configuração do Sopro recorta aproximadamente 10 s dessa referência.

Foram geradas outras oito amostras, com os mesmos textos, modelo, revisão, seed,
parâmetros, CPU e seis threads. Carga com pesos em cache: 1,04 s.

| Frase | Completo: geração | Streaming: primeiro chunk | Streaming: geração total |
|---|---:|---:|---:|
| Conversa | 3,26 s | 1,05 s | 2,51 s |
| Morte | 3,72 s | 1,24 s | 3,37 s |
| Chefe | 3,42 s | 0,82 s | 3,41 s |
| Tempo/preço | 5,27 s | 1,41 s | 4,62 s |

Os RTFs ficaram abaixo de 1 nesta rodada. Isso não mede qualidade de clonagem.
O ASR reconheceu boa parte dos textos, mas houve divergências em “Demônio Touro”
e no preço com R$. Após ouvir, o usuário gostou da voz e apontou o sotaque
PT-PT como a limitação; a decisão é reavaliar o Sopro quando houver atualizações.

A página da nova rodada reúne 16 amostras: Kokoro/Nicole, Sopro com referência
Nicole no modo completo, e Sopro com a referência fornecida nos dois modos.
A comparação anterior foi preservada. O nome e os hashes da gravação estão
nos metadados locais em logs; o áudio de referência não faz parte do código.

A demo na porta 7860 foi reiniciada com essa referência. O launcher agora mostra
o nome do arquivo selecionado, sem rotular todo áudio como Nicole.
