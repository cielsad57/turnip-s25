# Especificação Técnica: Adreno 830 (A8XX) no Driver Mesa Turnip

## 1. Visão Geral da Arquitetura
A **Adreno 830** (integrada no Snapdragon 8 Elite / SM8750) introduz mudanças fundamentais na microarquitetura gráfica da Qualcomm:

* **Família de Arquitetura:** Qualcomm Adreno 8xx (A8XX).
* **Processo:** TSMC 3nm (N3E).
* **Configuração de Núcleos:** Dois blocos de GPU (Slice 0 e Slice 1), operando em frequências de até 1.1 GHz.
* **Memória Gráfica Dedicada:** 12 MB de cache dedicado (High-Speed Memory / Slice Cache), atuando em conjunto com a GMEM tradicional.
* **Suporte à API:** Vulkan 1.3 / Vulkan 1.4 features, Shader Model 6.7 equivalente, Ray Tracing por hardware avançado.

---

## 2. Diferenças Chave: A7XX vs A8XX no Mesa Freedreno/Turnip

| Recurso / Componente | Adreno 7xx (Ex: A750 - Gen 3) | Adreno 830 (A8XX - Elite) | Impacto no Turnip |
|---|---|---|---|
| **Formato de Registradores** | `a7xx.xml` (CP / VPC / SP) | `a8xx.xml` / Novos opcodes | Novos pacotes de comando CP_DRAW e novos bits de estado de pipeline |
| **Arquitetura de Slices** | 1 cluster unificado | 2 Slices independentes | Sincronização entre slices em compute e render passes |
| **Instruções IR3 (ISA)** | Conjunto A7xx ISA | Novos opcodes para wave32/wave64 e novas instruções de conversão | Compilador IR3 precisa emitir sequências válidas para a nova ALU |
| **UBWC Versão** | UBWC 4.0 / 5.0 | UBWC 5.x com novos layouts de tile | Cálculos de pitch, offset e alinhamento de tiles modificados |
| **GMEM / GMEM Tile Layout** | GMEM tradicional particionada | GMEM com alinhamento aumentado | Cálculo de binning e GMEM size em `tu_device.c` |

---

## 3. Arquivos Principais do Mesa Afetados

No código-fonte do Mesa (`src/freedreno/` e `src/qcom/`):

1. **`src/freedreno/common/freedreno_devices.py` & `freedreno_dev_info.c`:**
   - Definição do ID do chip (ex: `FD_CHIP_ID(8, 3, 0)`), número de SPs, tamanho de GMEM (geralmente dimensionado por slice), limites de registradores de ponto flutuante.
2. **`src/freedreno/vulkan/tu_device.c`:**
   - Criação da instância de hardware, seleção de extensões Vulkan suportadas na A830, alocação de memória do host e do dispositivo.
3. **`src/freedreno/ir3/`:**
   - `ir3_compiler_nir.c`: Tradução de NIR para IR3.
   - `ir3_legalize.c`: Inserção de `nop`s e stalls para hazard avoidance (mudanças nas latências da pipeline na Adreno 830).
   - `ir3_shader.c`: Geração do binário final executável pela GPU.
4. **`src/freedreno/registers/adreno/a8xx.xml.h`:**
   - Mapeamento direto dos registradores de controle da GPU (gerado a partir das definições XML do Enna/Freedreno).

---

## 4. Pontos de Atenção na A830 para Emuladores Switch

1. **Transform Feedback / Stream Output:** Jogos de Switch usam transform feedback intensamente. Na A830, o suporte a streamout deve garantir que os buffers de saída mantenham coerência de cache.
2. **Dynamic Rendering:** A transição completa para `VK_KHR_dynamic_rendering` pode exigir barreiras explícitas antes de disparar draw calls em modo SysMem.
3. **Descriptor Indexing:** O FC 26 usa grandes arrays de descritores de texturas para renderizar uniformes de times, placas de publicidade e torcida.
