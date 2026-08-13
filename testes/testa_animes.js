#!/usr/bin/env node
// Contrato da consulta reativa: compartilha o AniList com o proativo sem consumir avisos.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const raiz = path.join(__dirname, '..');
const anime = fs.readFileSync(path.join(raiz, 'modulos', 'animes.py'), 'utf8');
const proativa = fs.readFileSync(path.join(raiz, 'modulos', 'proativa.py'), 'utf8');
const pensar = fs.readFileSync(path.join(raiz, 'modulos', 'pensar.py'), 'utf8');
const habilidades = fs.readFileSync(path.join(raiz, 'modulos', 'habilidades.py'), 'utf8');

assert.ok(habilidades.includes('"name": "consultar_animes"'),
          'FALHA: a consulta de animes não está exposta ao roteador');
assert.ok(pensar.includes('"consultar_animes": animes.consultar'),
          'FALHA: a ferramenta não tem executor registrado');
assert.ok(proativa.includes('animes.temporada_no_ar(nome)') &&
          proativa.includes('animes.ultimo_episodio(media_id)'),
          'FALHA: proativo e reativo deixaram de compartilhar a consulta do AniList');
assert.ok(anime.includes('obsidian.ler_lista_animes()[:10]') &&
          anime.includes('JANELA_RECENTES_H = 72'),
          'FALHA: consulta geral não respeita a lista e a janela do radar');
assert.ok(!anime.includes('salvar_vistos') && !anime.includes('carregar_vistos'),
          'FALHA: uma pergunta reativa pode consumir o aviso proativo');
assert.ok(anime.includes('if temporada is False:') &&
          anime.includes('if temporada is None:') &&
          anime.includes('if falhas == len(lista):'),
          'FALHA: ausência de temporada voltou a ser confundida com falha do AniList');

console.log('PASSOU — animes podem ser consultados sem interferir no radar');
