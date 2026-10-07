# Especificação Adrenotools: Estrutura do Pacote Customizado

Para que o driver compilado seja reconhecido pelo gerenciador de drivers customizados dos emuladores de Switch no Android (baseados na biblioteca **Adrenotools** de Bylaws/Kimuyu), o arquivo `.zip` final precisa atender rigorosamente à estrutura de metadados.

---

## 1. Estrutura do Arquivo ZIP

```plaintext
turnip-a830-fc26-v1.zip
├── meta.json
└── vulkan.adreno.so
```

*(Opcionalmente, se houver bibliotecas dependentes compiladas estaticamente ou dinamicamente, podem ser adicionadas na raiz ou na pasta `lib/` conforme a versão do Adrenotools).*

---

## 2. Esquema do `meta.json`

```json
{
  "schemaVersion": 1,
  "name": "Turnip v25.x-A830-FC26-Opt",
  "description": "Mesa Turnip customizado para Adreno 830 (Snapdragon 8 Elite) com patches e workarounds para EA Sports FC 26.",
  "author": "Marciel Leal de Moura",
  "packageVersion": "1.0",
  "vendor": "Mesa/Freedreno",
  "driverVersion": "Mesa 25.1.0-devel",
  "minApi": 31,
  "libraryName": "vulkan.adreno.so"
}
```

### Explicação dos Campos:
* **`schemaVersion`**: Deve ser `1`.
* **`name`**: Nome legível exibido na lista de drivers do emulador.
* **`description`**: Breve resumo das otimizações ou versão base.
* **`author`**: Nome do desenvolvedor responsável pela compilação/patch.
* **`packageVersion`**: Versão sequencial do pacote (ex: "1.0", "1.1").
* **`vendor`**: Fornecedor do driver ("Mesa/Freedreno" ou "Qualcomm").
* **`driverVersion`**: Versão da base do Mesa utilizada.
* **`minApi`**: Versão mínima da API do Android (31 = Android 12, 34/35 = Android 14/15 do Galaxy S25).
* **`libraryName`**: O nome exato do arquivo `.so` compartilhado contido no ZIP (geralmente `vulkan.adreno.so` ou `libvulkan_freedreno.so`).
