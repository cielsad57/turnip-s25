# patches/experimental — NÃO aplicados no build

O CI só aplica arquivos `patches/*.patch` (raiz). Tudo aqui fica fora do build.

## 0001-turnip-a8xx-fc26-workarounds.patch

Mantido como referência, mas **desativado** por dois motivos:

1. **Não aplica no Mesa real.** Os hashes `index` são fictícios e o código usa
   campos/APIs que não existem no Turnip (`device->info->chip == 830`,
   `nir_options.lower_fp16` dentro de `tu_pipeline.c`, `instance->app_info`
   lido em `tu_physical_device_init`). `git apply --check` falharia.
2. **Vai contra o objetivo de desempenho sustentado.**
   - Forçar FP32 em todos os shaders de vértice/geometria aumenta o trabalho da ALU.
   - Desligar UBWC em depth/stencil aumenta o tráfego de memória.
   Os dois geram mais calor → o celular reduz o clock da GPU mais cedo → FPS cai.

Só reative algo parecido se um bug visual for **confirmado** com captura
(RenderDoc / `TU_DEBUG`), e restrito ao shader/recurso afetado, não ao jogo inteiro.
