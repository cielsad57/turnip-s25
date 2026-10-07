#!/usr/bin/env python3
"""
Orquestrador de Cross-Compilation para Mesa Turnip no Android (A8XX)
Gera o crossfile meson configurado com o NDK especificado e executa o build.
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

def resolve_ndk_path(provided_ndk: str = None) -> Path:
    if provided_ndk:
        p = Path(provided_ndk)
        if p.exists():
            return p.resolve()

    env_ndk = os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_ROOT")
    if env_ndk and Path(env_ndk).exists():
        return Path(env_ndk).resolve()

    print("[ERRO] Android NDK não localizado! Defina ANDROID_NDK_HOME ou use o parâmetro --ndk.")
    sys.exit(1)

def find_toolchain_bin(ndk_path: Path) -> Path:
    # No Windows é 'windows-x86_64', no Linux 'linux-x86_64', no Mac 'darwin-x86_64'
    host_tag = "windows-x86_64" if sys.platform == "win32" else "linux-x86_64"
    prebuilt_bin = ndk_path / "toolchains" / "llvm" / "prebuilt" / host_tag / "bin"
    if not prebuilt_bin.exists():
        # Fallback de busca caso o nome da pasta varie
        candidates = list((ndk_path / "toolchains" / "llvm" / "prebuilt").glob("*/bin"))
        if candidates:
            return candidates[0]
        print(f"[ERRO] Diretório binário do toolchain LLVM não encontrado em {ndk_path}")
        sys.exit(1)
    return prebuilt_bin

def generate_crossfile(template_path: Path, output_path: Path, ndk_bin: Path, api_level: int):
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Formatar o caminho usando barras normais para compatibilidade Meson
    ndk_bin_str = str(ndk_bin).replace("\\", "/")
    content = content.replace("@NDK_BIN@", ndk_bin_str)
    content = content.replace("@API_LEVEL@", str(api_level))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[*] Cross-file Meson gerado em: {output_path}")

def run_command(cmd, cwd=None):
    print(f"\n[EXEC] {' '.join(str(c) for c in cmd)}")
    res = subprocess.run(cmd, cwd=cwd)
    if res.returncode != 0:
        print(f"[ERRO] Comando falhou com código de retorno: {res.returncode}")
        sys.exit(res.returncode)

def main():
    parser = argparse.ArgumentParser(description="Script de Build Meson Turnip NDK")
    parser.add_argument("--mesa-dir", type=str, default="../mesa", help="Diretório raiz do código-fonte do Mesa")
    parser.add_argument("--build-dir", type=str, default="build-a830", help="Diretório de build")
    parser.add_argument("--ndk", type=str, default=None, help="Caminho raiz do Android NDK")
    parser.add_argument("--api", type=int, default=31, help="Nível da API Android (Padrão: 31 / Android 12)")
    parser.add_argument("--configure-only", action="store_true", help="Apenas configura o meson sem compilar")

    args = parser.parse_args()

    ndk_path = resolve_ndk_path(args.ndk)
    print(f"[*] Utilizando Android NDK: {ndk_path}")

    ndk_bin = find_toolchain_bin(ndk_path)
    print(f"[*] Toolchain binário: {ndk_bin}")

    script_dir = Path(__file__).parent.resolve()
    template_path = script_dir / "ndk-android-aarch64.ini.template"
    crossfile_path = script_dir / "generated_crossfile.ini"

    generate_crossfile(template_path, crossfile_path, ndk_bin, args.api)

    mesa_path = Path(args.mesa_dir).resolve()
    build_path = (script_dir.parent / args.build_dir).resolve()

    if not (mesa_path / "meson.build").exists():
        print(f"[AVISO] meson.build não encontrado em {mesa_path}.")
        print("[INFO] Certifique-se de clonar o repositório Mesa antes de executar a compilação completa.")
        print(f"[EXEMPLO] git clone --depth 1 https://gitlab.freedesktop.org/mesa/mesa.git {mesa_path}")
        return

    # Comandos padrão para build do Turnip Vulkan
    meson_cmd = [
        "meson", "setup", str(build_path), str(mesa_path),
        f"--cross-file={str(crossfile_path)}",
        "-Dbuildtype=release",
        "-Dplatforms=android",
        "-Dplatform-sdk-version=31",
        "-Dgallium-drivers=",
        "-Dvulkan-drivers=freedreno",
        "-Dfreedreno-kmds=kgsl",
        "-Db_lto=true"
    ]

    run_command(meson_cmd)

    if not args.configure_only:
        ninja_cmd = ["ninja", "-C", str(build_path), "src/freedreno/vulkan/libvulkan_freedreno.so"]
        run_command(ninja_cmd)
        print(f"\n[SUCESSO] Compilação concluída! Binário disponível no diretório: {build_path}")

if __name__ == "__main__":
    main()
