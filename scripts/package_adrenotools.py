#!/usr/bin/env python3
"""
Script utilitário para empacotar o driver Turnip compilado no formato Adrenotools (.zip).
Suporta validação de integridade do arquivo .so e geração automática do meta.json.
"""

import os
import sys
import json
import zipfile
import argparse
from pathlib import Path

def create_adrenotools_package(
    so_file_path: Path,
    output_zip_path: Path,
    driver_name: str,
    description: str,
    author: str,
    version: str,
    driver_version: str,
    min_api: int
):
    if not so_file_path.exists():
        print(f"[ERRO] O arquivo binário '{so_file_path}' não foi encontrado.")
        sys.exit(1)

    lib_name = so_file_path.name
    print(f"[*] Validando binário do driver: {lib_name} ({so_file_path.stat().st_size / (1024*1024):.2f} MB)")

    meta_content = {
        "schemaVersion": 1,
        "name": driver_name,
        "description": description,
        "author": author,
        "packageVersion": version,
        "vendor": "Mesa/Freedreno",
        "driverVersion": driver_version,
        "minApi": min_api,
        "libraryName": lib_name
    }

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Criando arquivo ZIP: {output_zip_path}")
    with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Escrever meta.json
        meta_json_bytes = json.dumps(meta_content, indent=2, ensure_ascii=False).encode("utf-8")
        zf.writestr("meta.json", meta_json_bytes)
        print("  -> meta.json adicionado com sucesso.")

        # Escrever a biblioteca do driver (.so)
        zf.write(so_file_path, arcname=lib_name)
        print(f"  -> {lib_name} adicionado com sucesso.")

    print(f"[SUCESSO] Pacote Adrenotools gerado com êxito em:\n  {output_zip_path.resolve()}\n")

def main():
    parser = argparse.ArgumentParser(description="Empacotador Adrenotools para Mesa Turnip (Adreno 830)")
    parser.add_argument("--so", type=str, required=True, help="Caminho para o arquivo vulkan.adreno.so compilado")
    parser.add_argument("--out", type=str, default="build/turnip-a830-fc26.zip", help="Caminho de saída para o pacote .zip")
    parser.add_argument("--name", type=str, default="Turnip A830 FC26 Experimental", help="Nome de exibição no emulador")
    parser.add_argument("--desc", type=str, default="Custom Mesa Turnip for Adreno 830 optimized for EA Sports FC 26", help="Descrição do pacote")
    parser.add_argument("--author", type=str, default="Marciel Leal de Moura", help="Autor do pacote")
    parser.add_argument("--ver", type=str, default="1.0", help="Versão do pacote")
    parser.add_argument("--driver-ver", type=str, default="Mesa 25.1-devel", help="Versão da base do Mesa")
    parser.add_argument("--min-api", type=int, default=31, help="Nível mínimo da API Android (ex: 31=Android 12, 34=Android 14)")

    args = parser.parse_args()

    create_adrenotools_package(
        so_file_path=Path(args.so),
        output_zip_path=Path(args.out),
        driver_name=args.name,
        description=args.desc,
        author=args.author,
        version=args.ver,
        driver_version=args.driver_ver,
        min_api=args.min_api
    )

if __name__ == "__main__":
    main()
