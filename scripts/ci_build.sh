#!/usr/bin/env bash
# =============================================================================
# Build do Mesa Turnip (Vulkan / Adreno) para Android + pacote Adrenotools.
# Pensado para rodar no GitHub Actions (ubuntu-latest), mas funciona em
# qualquer Linux/WSL com: git, python3, meson, ninja, patchelf, glslang, flex, bison.
#
# Variáveis (todas opcionais):
#   MESA_REF       branch/tag do Mesa       (padrão: main)
#   API_LEVEL      API Android alvo         (padrão: 34 = Android 14)
#   APPLY_PATCHES  aplica patches/*.patch   (padrão: true)
#   PKG_NAME       nome exibido no emulador (padrão: "Turnip A830 Perf")
#   ANDROID_NDK_HOME / ANDROID_NDK_LATEST_HOME  caminho do NDK
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/work}"
OUT="${OUT:-$ROOT/out}"
MESA_REF="${MESA_REF:-main}"
API_LEVEL="${API_LEVEL:-34}"
APPLY_PATCHES="${APPLY_PATCHES:-true}"
PKG_NAME="${PKG_NAME:-Turnip A830 Perf}"
MESA_DIR="$WORK/mesa"
BUILD_DIR="$WORK/build-android-aarch64"

log() { echo -e "\n\033[1;36m==> $*\033[0m"; }

# ---------------------------------------------------------------- NDK
NDK="${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:-}}"
if [[ -z "$NDK" || ! -d "$NDK" ]]; then
  log "NDK não encontrado, baixando r27c"
  mkdir -p "$WORK"
  curl -sSL -o "$WORK/ndk.zip" https://dl.google.com/android/repository/android-ndk-r27c-linux.zip
  unzip -q "$WORK/ndk.zip" -d "$WORK"
  NDK="$WORK/android-ndk-r27c"
fi
NDK_BIN="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin"
[[ -x "$NDK_BIN/aarch64-linux-android${API_LEVEL}-clang" ]] || {
  echo "[ERRO] Compilador para API $API_LEVEL não existe em $NDK_BIN"; exit 1; }
log "NDK: $NDK (API $API_LEVEL)"

# ---------------------------------------------------------------- Mesa
mkdir -p "$WORK" "$OUT"
if [[ ! -d "$MESA_DIR/.git" ]]; then
  log "Clonando Mesa ($MESA_REF)"
  git clone --depth 1 --branch "$MESA_REF" https://gitlab.freedesktop.org/mesa/mesa.git "$MESA_DIR"
fi
MESA_COMMIT="$(git -C "$MESA_DIR" rev-parse --short HEAD)"
MESA_VERSION="$(cat "$MESA_DIR/VERSION" 2>/dev/null || echo unknown)"
log "Mesa $MESA_VERSION @ $MESA_COMMIT"

# ---------------------------------------------------------------- Patches
# Só patches na raiz de patches/ são aplicados. patches/experimental/ é ignorado.
if [[ "$APPLY_PATCHES" == "true" ]]; then
  shopt -s nullglob
  for p in "$ROOT"/patches/*.patch; do
    log "Aplicando $(basename "$p")"
    if ! git -C "$MESA_DIR" apply --check "$p"; then
      echo "[ERRO] $(basename "$p") não aplica no Mesa $MESA_COMMIT."
      echo "       Atualize o patch ou mova-o para patches/experimental/."
      exit 1
    fi
    git -C "$MESA_DIR" apply "$p"
  done
  shopt -u nullglob
fi

# ---------------------------------------------------------------- Cross-file
CROSS="$WORK/android-aarch64.ini"
cat >"$CROSS" <<EOF
[binaries]
ar = '$NDK_BIN/llvm-ar'
c = ['$NDK_BIN/aarch64-linux-android${API_LEVEL}-clang']
cpp = ['$NDK_BIN/aarch64-linux-android${API_LEVEL}-clang++', '-fno-exceptions', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '--start-no-unused-arguments', '-static-libstdc++', '--end-no-unused-arguments']
c_ld = 'lld'
cpp_ld = 'lld'
strip = '$NDK_BIN/llvm-strip'
# Impede o pkg-config de achar libs do host (x86) e linkar coisa errada.
pkg-config = ['env', 'PKG_CONFIG_LIBDIR=/nonexistent', '/usr/bin/pkg-config']

[host_machine]
system = 'android'
cpu_family = 'aarch64'
cpu = 'armv8'
endian = 'little'

[built-in options]
# armv8.2-a é suportado por todo Snapdragon com Adreno 6xx/7xx/8xx.
c_args = ['-march=armv8.2-a']
cpp_args = ['-march=armv8.2-a']
EOF

# Adiciona uma opção do meson só se ela existir nessa versão do Mesa
OPTS_FILE="$MESA_DIR/meson.options"; [[ -f "$OPTS_FILE" ]] || OPTS_FILE="$MESA_DIR/meson_options.txt"
has_opt() { grep -q "option('$1'" "$OPTS_FILE"; }
EXTRA=()
has_opt android-libbacktrace && EXTRA+=("-Dandroid-libbacktrace=disabled")
has_opt valgrind             && EXTRA+=("-Dvalgrind=disabled")
has_opt egl                  && EXTRA+=("-Degl=disabled")

# ---------------------------------------------------------------- Build
log "meson setup"
rm -rf "$BUILD_DIR"
meson setup "$BUILD_DIR" "$MESA_DIR" \
  --cross-file "$CROSS" \
  -Dbuildtype=release \
  -Db_lto=false \
  -Db_ndebug=true \
  -Dstrip=true \
  -Dplatforms=android \
  -Dplatform-sdk-version="$API_LEVEL" \
  -Dandroid-stub=true \
  -Dgallium-drivers= \
  -Dvulkan-drivers=freedreno \
  -Dvulkan-beta=true \
  -Dfreedreno-kmds=kgsl \
  -Dopengl=false \
  -Dgles1=disabled \
  -Dgles2=disabled \
  -Dglx=disabled \
  -Degl=disabled \
  "${EXTRA[@]}"

log "ninja"
ninja -C "$BUILD_DIR" src/freedreno/vulkan/libvulkan_freedreno.so

# ---------------------------------------------------------------- Pacote
SO_SRC="$BUILD_DIR/src/freedreno/vulkan/libvulkan_freedreno.so"
SO_OUT="$WORK/vulkan.ad08XX.so"
cp "$SO_SRC" "$SO_OUT"
patchelf --set-soname vulkan.adreno.so "$SO_OUT"

STAMP="$(date -u +%Y%m%d)"
ZIP="$OUT/turnip-a830-perf-${STAMP}-${MESA_COMMIT}.zip"
log "Empacotando $ZIP"
python3 "$ROOT/scripts/package_adrenotools.py" \
  --so "$SO_OUT" \
  --out "$ZIP" \
  --name "$PKG_NAME ($STAMP)" \
  --desc "Mesa Turnip $MESA_VERSION ($MESA_COMMIT) - release+LTO, sem workarounds que custam desempenho" \
  --ver "$STAMP" \
  --driver-ver "Mesa $MESA_VERSION ($MESA_COMMIT)" \
  --min-api "$API_LEVEL"

echo "MESA_COMMIT=$MESA_COMMIT" >"$OUT/build-info.txt"
echo "MESA_VERSION=$MESA_VERSION" >>"$OUT/build-info.txt"
echo "API_LEVEL=$API_LEVEL" >>"$OUT/build-info.txt"
log "Pronto: $ZIP"
