# Desempenho sustentado: FC 26 no Galaxy S25 (Adreno 830)

**Sintoma:** o jogo começa bem e o FPS cai depois de alguns minutos.

Esse padrão quase sempre é **thermal throttling**. O celular esquenta, o sistema
reduz o clock da GPU/CPU (no S25 a GPU vai de 1200 MHz até 160 MHz) e o FPS cai junto.

> [!IMPORTANT]
> Nenhum driver impede o celular de esquentar. O que o driver pode fazer é **gastar
> menos energia por frame**: assim a temperatura sobe mais devagar e o clock fica alto
> por mais tempo. As configurações do emulador ajudam muito mais que qualquer patch.

---

## 1. Primeiro meça (5 min)

```powershell
python scripts/thermal_monitor.py --minutes 15 --out logs/antes.csv
```

Jogue uma partida enquanto ele roda. No fim aparece:

- `THROTTLING detectado em ~X:XX` → é térmico. Siga as seções 2 e 3.
- `Sem throttling forte de GPU` → o gargalo é CPU (emulação) ou compilação de shaders.
  Veja a seção 4.

Repita com `--out logs/depois.csv` após cada mudança para comparar.

---

## 2. O que este driver faz pela temperatura

| Escolha | Por quê |
|---|---|
| Mesa recente (`main` ou tag) | O suporte e o desempenho do A8xx no Turnip melhoram a cada versão |
| `release` + LTO + `-march=armv8.2-a` + `strip` | Menos CPU gasta no driver por draw call |
| **Sem** forçar FP32 global | FP16 consome menos energia na ALU |
| **Sem** desligar UBWC | A compressão UBWC reduz o tráfego de memória, que gasta muita energia |

O patch antigo (`patches/experimental/`) fazia o contrário nos dois últimos itens,
por isso está fora do build. Veja [patches/experimental/README.md](../patches/experimental/README.md).

---

## 3. Configurações que mais reduzem calor (na ordem do impacto)

1. **Limite de FPS fixo** no emulador (ex.: 30). Um FPS estável e mais baixo é
   melhor que 60 que cai pra 25. A GPU para de trabalhar entre os frames e esfria.
2. **Resolução 1x (720p/docked) ou 0.75x.** Renderizar 2x gasta cerca de 4x mais pixels.
3. **Filtro de escala simples** (Bilinear) em vez de FSR, se a imagem estiver aceitável.
4. **Anisotropia** em Automático/2x em vez de 16x.
5. **Não jogar carregando**, principalmente com carregador rápido: o carregamento aquece
   a bateria e o sistema reduz o clock mais cedo.
6. **Game Booster (Samsung):** use o perfil "Equilibrado"/"Desempenho padrão". O modo
   "Desempenho máximo" esquenta mais rápido e costuma ficar *pior* depois de 10 min.
7. Tire a capinha ou use um cooler de celular (Peltier). Isso faz mais diferença do que parece.

---

## 4. Se NÃO for térmico

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Travadinhas quando aparece algo novo | Compilação de shaders | Ative shaders assíncronos e o cache de pipeline no emulador; a 2ª partida fica mais lisa |
| FPS baixo constante, GPU `busy%` baixo | CPU (emulação) | Desligue opções de precisão de CPU, use o modo de CPU "Nativo/Dynarmic" padrão |
| FPS baixo constante, GPU `busy%` ~100% | GPU no limite | Reduza a resolução (seção 3) |
