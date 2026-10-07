#!/usr/bin/env python3
"""
Monitor térmico/clock para Galaxy S25 (Snapdragon 8 Elite / Adreno 830) via adb.

Objetivo: provar SE e QUANDO o celular começa a reduzir o clock da GPU
(thermal throttling) enquanto o FC 26 roda no emulador — que é o sintoma
"começa bem e vai caindo depois de alguns minutos".

Uso:
    python scripts/thermal_monitor.py                 # amostra a cada 2s até Ctrl+C
    python scripts/thermal_monitor.py --interval 1 --minutes 20 --out logs/teste1.csv

Não precisa de root. Campos que o sistema bloquear aparecem como "-".
"""

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

KGSL = "/sys/class/kgsl/kgsl-3d0"

# Um único "adb shell" por amostra -> overhead mínimo no celular.
# Obs.: "r" é alias interno do mksh do Android (fc -e -), por isso a função chama "rd".
# No S25 (Android 16) o SELinux bloqueia gpuclk e power_supply/*/temp, mas libera
# clock_mhz, devfreq/cur_freq, gpu_busy_percentage e temp.
PROBE = (
    "rd(){ v=$(cat \"$2\" 2>/dev/null) && echo \"$1=$v\"; }; "
    f"rd gpumhz {KGSL}/clock_mhz; "
    f"rd gpuclk {KGSL}/gpuclk; "
    f"rd gpuclk_df {KGSL}/devfreq/cur_freq; "
    f"rd gpumaxmhz {KGSL}/max_clock_mhz; "
    f"rd gpubusy {KGSL}/gpu_busy_percentage; "
    f"rd gputemp {KGSL}/temp; "
    "for p in /sys/devices/system/cpu/cpufreq/policy*; do "
    "rd cpu${p##*policy} $p/scaling_cur_freq; done; "
    "dumpsys battery 2>/dev/null | grep -m1 '^  temperature' | sed 's/.*: */batt=/'; "
    "dumpsys thermalservice 2>/dev/null | grep -m1 'Thermal Status'; "
    "dumpsys thermalservice 2>/dev/null | grep -m1 'mName=SKIN' | sed 's/.*mValue=\\([0-9.]*\\).*/skin=\\1/'"
)

THERMAL_NAMES = {0: "none", 1: "light", 2: "moderate", 3: "severe",
                 4: "critical", 5: "emergency", 6: "shutdown"}


def find_adb() -> str:
    adb = shutil.which("adb")
    if adb:
        return adb
    sdk = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    if sdk.exists():
        return str(sdk)
    sys.exit("[ERRO] adb não encontrado. Instale o Android platform-tools.")


def to_int(s):
    m = re.search(r"-?\d+", s or "")
    return int(m.group()) if m else None


def sample(adb: str) -> dict:
    res = subprocess.run([adb, "shell", PROBE], capture_output=True, text=True, timeout=15)
    raw = {}
    thermal = None
    for line in res.stdout.splitlines():
        if "Thermal Status" in line:
            thermal = to_int(line)
        elif "=" in line:
            k, v = line.split("=", 1)
            raw[k.strip()] = v.strip()

    gpu_mhz = to_int(raw.get("gpumhz"))
    if not gpu_mhz:
        hz = to_int(raw.get("gpuclk")) or to_int(raw.get("gpuclk_df"))
        gpu_mhz = round(hz / 1e6) if hz else None
    gpu_temp = to_int(raw.get("gputemp"))
    batt = to_int(raw.get("batt"))
    try:
        skin = float(raw["skin"]) if raw.get("skin") else None
    except ValueError:
        skin = None
    cpus = {k: to_int(v) for k, v in raw.items() if re.fullmatch(r"cpu\d+", k)}

    return {
        "gpu_mhz": gpu_mhz,
        "gpu_max_mhz": to_int(raw.get("gpumaxmhz")),
        "gpu_busy": to_int(raw.get("gpubusy")),
        # kgsl reporta em milligraus na maioria dos kernels
        "gpu_temp_c": (gpu_temp / 1000 if gpu_temp and gpu_temp > 1000 else gpu_temp),
        "skin_temp_c": skin,
        "batt_temp_c": batt / 10 if batt is not None else None,
        "thermal": thermal,
        **{f"{k}_mhz": (v // 1000 if v else None) for k, v in sorted(cpus.items())},
    }


def fmt(v, w=6):
    return f"{'-' if v is None else v:>{w}}"


def summarize(rows):
    clocks = [(r["t_s"], r["gpu_mhz"]) for r in rows if r.get("gpu_mhz")]
    print("\n================ RESUMO ================")
    if len(clocks) < 10:
        print("Poucas amostras de clock da GPU (o sistema pode estar bloqueando a leitura).")
        return
    peak = max(c for _, c in clocks)
    step = max(1e-3, (clocks[-1][0] - clocks[0][0]) / len(clocks))
    win = max(3, int(30 / step))  # janela de ~30s ignora quedas de menu/loading
    throttle_at = None
    for i in range(win, len(clocks)):
        avg = sum(c for _, c in clocks[i - win:i]) / win
        if avg < 0.75 * peak:
            throttle_at = clocks[i][0]
            break
    first = sum(c for _, c in clocks[:win]) / min(win, len(clocks))
    last = sum(c for _, c in clocks[-win:]) / min(win, len(clocks))
    temps = [r["batt_temp_c"] for r in rows if r.get("batt_temp_c") is not None]
    skins = [r["skin_temp_c"] for r in rows if r.get("skin_temp_c") is not None]
    if skins:
        print(f"Pele (SKIN):             {skins[0]:.1f}°C -> {skins[-1]:.1f}°C (máx {max(skins):.1f}°C)")
    print(f"Clock GPU pico:          {peak} MHz")
    print(f"Clock GPU médio início:  {first:.0f} MHz")
    print(f"Clock GPU médio final:   {last:.0f} MHz  ({100 * last / first:.0f}% do início)")
    if temps:
        print(f"Bateria:                 {temps[0]:.1f}°C -> {temps[-1]:.1f}°C (máx {max(temps):.1f}°C)")
    if throttle_at is not None:
        print(f"THROTTLING detectado em ~{int(throttle_at)//60}:{int(throttle_at)%60:02d} "
              "(clock médio < 75% do pico).")
        print("=> A queda de FPS é térmica. Veja docs/PERFORMANCE_THERMAL.md.")
    else:
        print("Sem throttling forte de GPU. Se o FPS caiu mesmo assim, o gargalo provável")
        print("é CPU (emulação) ou compilação de shaders — veja docs/PERFORMANCE_THERMAL.md.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=2.0, help="segundos entre amostras")
    ap.add_argument("--minutes", type=float, default=0, help="duração (0 = até Ctrl+C)")
    ap.add_argument("--out", type=str, default=None, help="CSV de saída")
    args = ap.parse_args()

    adb = find_adb()
    state = subprocess.run([adb, "get-state"], capture_output=True, text=True).stdout.strip()
    if state != "device":
        sys.exit("[ERRO] Nenhum celular conectado/autorizado no adb (ative Depuração USB).")

    out = Path(args.out or f"logs/thermal_{datetime.now():%Y%m%d_%H%M%S}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Gravando em {out}  (Ctrl+C para parar)")
    print("    Abra o FC 26 e jogue uma partida normalmente.\n")
    print(f"{'tempo':>6} {'GPU MHz':>8} {'busy%':>6} {'GPU°C':>6} {'pele°C':>6} {'bat°C':>6} {'termal':>9}")

    rows, writer = [], None
    t0 = time.time()
    with open(out, "w", newline="", encoding="utf-8") as fh:
        try:
            while not (args.minutes and time.time() - t0 > args.minutes * 60):
                tick = time.time()
                try:
                    s = sample(adb)
                except subprocess.TimeoutExpired:
                    continue
                el = tick - t0
                s = {"t_s": round(el, 1), **s}
                if writer is None:
                    writer = csv.DictWriter(fh, fieldnames=list(s.keys()), extrasaction="ignore")
                    writer.writeheader()
                writer.writerow(s)
                fh.flush()
                rows.append(s)
                th = s["thermal"]
                th_txt = THERMAL_NAMES.get(th, str(th)) if th is not None else "-"
                print(f"{int(el)//60:>3}:{int(el)%60:02d} {fmt(s['gpu_mhz'], 8)} {fmt(s['gpu_busy'])} "
                      f"{fmt(s['gpu_temp_c'])} {fmt(s['skin_temp_c'])} {fmt(s['batt_temp_c'])} {th_txt:>9}")
                time.sleep(max(0.0, args.interval - (time.time() - tick)))
        except KeyboardInterrupt:
            pass

    summarize(rows)


if __name__ == "__main__":
    main()
