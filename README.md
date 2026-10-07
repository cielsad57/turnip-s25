# Turnip Driver Optimization & Reverse Engineering for Adreno 830 (FC 26 Scope)

Este repositório é dedicado à pesquisa, engenharia reversa, desenvolvimento de patches e compilação do driver Vulkan **Mesa Turnip (Freedreno)** para a GPU **Adreno 830 (Snapdragon 8 Elite / A8XX)**, com foco específico na resolução de falhas gráficas, otimização de shaders e estabilidade no **EA Sports FC 26** em emuladores de Nintendo Switch no Android.

---

## 🏗️ Estrutura do Repositório

```plaintext
d:/drive turnip/
├── .github/workflows/
│   └── build-turnip.yml           # Build na nuvem (GitHub Actions) -> .zip Adrenotools
├── docs/
│   ├── PERFORMANCE_THERMAL.md     # FPS caindo com o tempo: como medir e resolver
│   ├── A8XX_ARCHITECTURE.md       # Características e registradores da arquitetura Adreno 830
│   ├── FC26_FAULT_ANALYSIS.md     # Mapeamento de falhas conhecidas (gramado, shaders, crashes)
│   ├── DEBUGGING_WORKFLOW.md      # Procedimentos de logcat, RenderDoc, GFXReconstruct e NIR dumps
│   └── ADRENOTOOLS_SPEC.md        # Especificação de empacotamento para Android (meta.json)
├── patches/
│   ├── *.patch                    # Aplicados no build (validados com git apply --check)
│   └── experimental/              # NÃO aplicados (ver README da pasta)
├── scripts/
│   ├── ci_build.sh                # Build Linux: clona Mesa, aplica patches, compila, empacota
│   ├── thermal_monitor.py         # Mede clock/temperatura da GPU do S25 via adb
│   ├── package_adrenotools.py     # Gerador do pacote .zip compatível com Adrenotools
│   ├── build_turnip_ndk.py        # (legado) build local via Meson + NDK
│   └── ndk-android-aarch64.ini.template
└── README.md
```

---

## 🚀 Uso rápido

### 1. Gerar o driver (nuvem)
1. Suba este repositório para o GitHub.
2. Aba **Actions → Build Turnip (Adrenotools) → Run workflow**.
3. Baixe o artefato `turnip-a830-perf` e instale o `.zip` no emulador
   (Configurações → GPU Driver → Instalar).

### 2. Medir se a queda de FPS é térmica
```powershell
python scripts/thermal_monitor.py --minutes 15 --out logs/teste.csv
```
Detalhes e o que fazer com o resultado: [docs/PERFORMANCE_THERMAL.md](docs/PERFORMANCE_THERMAL.md).

---

## 🎯 Objetivos

1. **Desempenho sustentado (prioridade):** FPS estável em partidas longas no S25.
   - Driver em release+LTO, sem workarounds globais que aumentem consumo (FP32 forçado, UBWC off).
   - Medir throttling com `thermal_monitor.py` antes/depois de cada mudança.
2. **Correções visuais pontuais:** só com bug confirmado em captura (RenderDoc / `TU_DEBUG`),
   restritas ao shader/recurso afetado.
3. **Dump & Inspeção de Shaders (NIR / IR3):**
   - `TU_DEBUG=nir,ir3,startup` nos shaders de iluminação e gramado do FC 26.
