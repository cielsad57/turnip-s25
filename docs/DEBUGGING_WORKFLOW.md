# Guia de Debugging & Captura de Logs (Galaxy S25 / Adreno 830)

Este documento estabelece o fluxo prático para capturar logs detalhados, dumps de shaders e traces gráficos no Samsung Galaxy S25 durante a execução do EA Sports FC 26 via emuladores Android (Yuzu, Sudachi, Citron, etc.).

---

## 1. Conexão e Configuração Inicial (ADB)

Certifique-se de que a depuração USB está ativada no Galaxy S25 e execute:

```bash
# Verificar dispositivo conectado
adb devices

# Ativar permissões de depuração de GPU (se necessário)
adb shell settings put global enable_gpu_debug_layers 1
adb shell settings put global gpu_debug_app <package_name_do_emulador>
# Exemplo de package: org.yuzu.yuzu_emu ou org.sudachi.sudachi_emu
```

---

## 2. Variáveis de Ambiente do Turnip (`TU_DEBUG`)

O Turnip aceita variáveis de ambiente para despejar instruções, desativar recursos problemáticos e emitir logs de validação interna. No Android, podemos injetar essas variáveis via propriedades de sistema ou arquivos de configuração do emulador.

### Flags Essenciais de Diagnóstico:
* `TU_DEBUG=startup`: Imprime na inicialização as capacidades detectadas do chip A830 e limites de GMEM.
* `TU_DEBUG=nir`: Despeja o código intermediário NIR dos shaders antes e depois das passagens de otimização.
* `TU_DEBUG=ir3`: Imprime o disassembly do assembly nativo da Adreno gerado pelo compilador IR3.
* `TU_DEBUG=sysmem`: Força a renderização em SysMem (Bypass), desativando o tiled rendering GMEM. Essencial para verificar se o bug do gramado é decorrente de tiling/binning incorreto.
* `TU_DEBUG=noblit`: Desativa aceleração de cópias via blit engine 3D.
* `TU_DEBUG=noubwc`: Desativa compressão UBWC universalmente. Crucial para isolar corrupção de texturas e faixas pretas.
* `TU_DEBUG=syncdraw`: Força sincronização a cada draw call (útil para detectar em qual comando específico ocorre o crash).

### Configurando no Android via Shell:
```bash
# Definir propriedade do Turnip (se o emulador suportar leitura de props de sistema)
adb shell setprop debug.mesa.tu_debug startup,ir3,noubwc

# Ou criar o arquivo de configuração de redirecionamento no armazenamento do emulador
# (Dependendo da implementação do Adrenotools, variáveis podem ser passadas via config de driver)
```

---

## 3. Captura Contínua de Logcat Filtrado

Para capturar erros específicos do Turnip, falhas de assert e mensagens de compilação de shader:

```bash
# Monitorar apenas saídas do Mesa / Turnip e do emulador
adb logcat -c
adb logcat -v time | grep -E "(MESA-LOADER|freedreno|turnip|vulkan|IR3|NIR)" > logs/turnip_session.log
```

No PowerShell (Windows):
```powershell
adb logcat -c
adb logcat -v time | Select-String -Pattern "(MESA-LOADER|freedreno|turnip|vulkan|IR3|NIR)" | Tee-Object -FilePath "logs/turnip_session.log"
```

---

## 4. Rastreamento e Isolamento de Shaders Quebrados

Quando o gramado ou uma cutscene apresentar falha visual:
1. Ative `TU_DEBUG=nir,ir3` direcionado para a pasta de logs.
2. Identifique no log o hash do shader em questão (ex: `IR3: compiling shader 0x7a3f...`).
3. Verifique se o shader contém instruções complexas de interpolação (`bary.f`), operações trigonométricas ou carregamento de uniformes com desalinhamento.
4. Teste a regra de substituição de shader ou desativação de otimizações de peephole no IR3.
