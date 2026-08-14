#!/usr/bin/env node
// Scroll sobre a Luna gira a órbita com inércia sem sequestrar a página inteira.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'templates', 'Index.html'), 'utf8');

assert.ok(html.includes('id="orbita-fidget"') &&
          html.includes("fidget.setAttribute('transform'") &&
          html.includes('rotate(${angulo.toFixed(2)})'),
          'FALHA: fidget não possui canal SVG independente para girar');
assert.ok(html.includes("pres.addEventListener('wheel'") && html.includes('{ passive: false }'),
          'FALHA: rodinha não controla a órbita');
assert.ok(html.includes("pres.classList.contains('est-dormindo')") &&
          html.includes('Math.hypot(dx, dy) > r.width * .48'),
          'FALHA: scroll fora da Luna ou durante atividade pode ser capturado');
assert.ok(html.includes('velocidade + direcao * impulso') &&
          html.includes('velocidade *= Math.pow(0.975'),
          'FALHA: órbita não acumula embalo e desaceleração');
assert.ok(html.includes('id="fidget-rastros"') &&
          html.includes("copia.setAttribute('fill', '#ffffff')") &&
          html.includes("copia.setAttribute('opacity', '.9')") &&
          html.includes("classList.toggle('fidget-rapido', modulo > 1.0)"),
          'FALHA: velocidade alta não cria brilho e rastros de cometa');
assert.ok(html.includes('filter: brightness(2.15) drop-shadow'),
          'FALHA: órbita principal perde luminosidade quando gira rápido');
assert.ok(html.includes("rastro.style.opacity = (intensidade * (.34 - i * .08)).toFixed(2)") &&
          html.includes('atraso = -Math.sign(velocidade)'),
          'FALHA: caudas não acompanham intensidade e direção do giro');
assert.ok(html.includes("classList.toggle('fidget-girando', modulo > .03)") &&
          html.includes('#presenca.fidget-girando #orbita rect'),
          'FALHA: o primeiro movimento da rodinha não ganha leitura visual');
assert.ok(html.includes('Math.min(.18, Math.max(.06') &&
          html.includes('Math.max(-1.5, Math.min(1.5'),
          'FALHA: poucos passos da rodinha voltaram a alcançar a velocidade máxima');
assert.ok(html.includes('Math.max(0, (modulo - .30) / 1.20)') &&
          html.includes('const escalaCentrifuga = 1 + forcaCentrifuga * .08') &&
          html.includes('scale(${escalaCentrifuga.toFixed(3)})'),
          'FALHA: velocidade nao afasta a orbita com zona morta e limite de 8%');
assert.ok(html.includes('<g id="orbita-escala"><g id="orbita-fidget">'),
          'FALHA: forca centrifuga deixou de ser independente das animacoes de entrar e sair');
assert.ok(!/ligarFidgetOrbita[\s\S]*?pintarRosto\(/.test(html.slice(html.indexOf('function ligarFidgetOrbita'), html.indexOf("const PRES_ESTADOS"))),
          'FALHA: primeiro rascunho do fidget não deve mudar o rosto');

console.log('PASSOU — órbita funciona como fidget com embalo');
