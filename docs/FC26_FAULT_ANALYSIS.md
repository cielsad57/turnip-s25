# Análise de Falhas: EA Sports FC 26 na Adreno 830 (A8XX)

## 1. Engine & Arquitetura Gráfica do Jogo
O **EA Sports FC 26** utiliza a engine **Frostbite** adaptada para a plataforma Nintendo Switch (NVN/Vulkan). 

Diferente de versões legadas de gerações anteriores que utilizavam uma engine simplificada (Legacy Edition), as versões recentes adotaram a Frostbite completa com:
* **Forward+ / Clustered Deferred Lighting** para iluminação de estádios.
* **Compute Shaders dedicados para tesselação e deformação do gramado** (Pitch Shells & Fins / Grass Instancing).
* **Cloth & Hair Simulation** rodando via compute shaders antes dos render passes de geometria.
* **Subpasses Vulkan e Dynamic State** para sombras em cascata (Cascaded Shadow Maps - CSM).

---

## 2. Pontos Críticos de Falha no Turnip / Adreno 830

### A. Renderização do Gramado (Pitch Glitches & Artefatos Pretos/Verdes)
* **Sintoma:** O gramado aparece inteiramente preto, com linhas piscando, ou com plano verde liso sem detalhamento de relevo/lâminas de grama.
* **Causa Raiz em Drivers Móveis:**
  1. **Precisão de Ponto Flutuante (FP16 vs FP32):** Shaders de interpolação de normais e coordenadas de textura da grama sofrem perda de precisão ou overflow/NaN ao operar em FP16. No compilador IR3 (`ir3_compiler_nir.c`), a otimização de compactação para meias-precisões pode quebrar cálculos de tangente.
  2. **Depth Bias / Polygon Offset Clamping:** Diferenças na interpretação de `depthBiasClamp` e `slopeScaledDepthBias` entre a arquitetura A7xx e A8xx geram z-fighting violento entre o plano do campo e as lâminas de grama.
  3. **UBWC (Universal Bandwidth Compression):** A Adreno 830 introduz formatos UBWC atualizados. Texturas de splatting do gramado descompactadas incorretamente resultam em planos pretos ou com faixas diagonais de corrompimento.

### B. Artefatos em Cutscenes e Iluminação
* **Sintoma:** Rostos dos jogadores com sombreamento estourado (manchas brancas ou pretas) e sombras quebradas em close-ups.
* **Causa Raiz:**
  1. **Subpass Input e Barriers:** Barreiras de memória (`VkSubpassDependency` / pipeline barriers) com flags de transição de layout incompletas no Turnip para o pipeline GMEM/Bypass da A8xx.
  2. **Descriptor Buffers / Uniform Buffers desbalanceados:** Shaders de iluminação usam buffers dinâmicos de uniformes que exigem alinhamentos de offset estritos (128 ou 256 bytes) na A8xx.

### C. Instabilidade e Crashes em Transições de Menus para Partida
* **Sintoma:** O jogo congela ou o emulador encerra silenciosamente ao carregar o estádio.
* **Causa Raiz:**
  1. **Device Memory Over-Allocation:** Exaustão de GMEM ao tentar renderizar render targets de alta resolução (1080p docked) em modo GMEM direto sem fallback para SysMem (Bypass).
  2. **Compute Pipeline Barriers:** Dessincronização entre compute de física de tecido e vertex fetch subsequente.

---

## 3. Matriz de Patches & Workarounds Planejados

| ID | Área no Mesa/Turnip | Arquivo Alvo | Estratégia do Patch |
|---|---|---|---|
| **WA-01** | Compiler (IR3) | `src/freedreno/ir3/ir3_nir.c` | Forçar FP32 para shaders de tesselação/geometry e normais quando o app for identificado como FC 26 |
| **WA-02** | Device Quirks | `src/freedreno/vulkan/tu_device.c` | Adicionar detecção de app/engine e forçar `disable_ubwc` em texturas de profundidade de campo |
| **WA-03** | Depth/Stencil | `src/freedreno/vulkan/tu_pipeline.c` | Ajustar tolerância de depth bias e clamp para evitar z-fighting de gramado |
| **WA-04** | GMEM Management | `src/freedreno/vulkan/tu_cmd_buffer.c` | Forçar modo SysMem (Bypass) em render targets com attachments de formato incompatível |
