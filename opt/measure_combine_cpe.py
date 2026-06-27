#!/usr/bin/env python3
"""Measure combine1/2/3 from vec.c with ctypes and plot CPE vs n."""

from __future__ import annotations

import argparse
import ctypes
import csv
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"


def compiler_output_name() -> Path:
    if platform.system() == "Darwin":
        return BUILD / "libvec.dylib"
    return BUILD / "libvec.so"


def compile_library(opt_level: str) -> Path:
    BUILD.mkdir(exist_ok=True)
    lib_path = compiler_output_name()
    if platform.system() == "Darwin":
        cmd = [
            "cc",
            "-dynamiclib",
            "-fPIC",
            opt_level,
            "-DLONG",
            str(ROOT / "vec.c"),
            "-o",
            str(lib_path),
        ]
    else:
        cmd = [
            "cc",
            "-shared",
            "-fPIC",
            opt_level,
            "-DLONG",
            str(ROOT / "vec.c"),
            "-o",
            str(lib_path),
        ]
    subprocess.run(cmd, check=True)
    return lib_path


def detect_cpu_hz() -> int | None:
    env_value = os.environ.get("CPU_HZ")
    if env_value:
        return int(float(env_value))
    if platform.system() == "Darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "hw.cpufrequency"], text=True).strip()
            return int(out)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return None
    if platform.system() == "Linux":
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            for line in cpuinfo.read_text(errors="ignore").splitlines():
                if line.lower().startswith("cpu mhz"):
                    return int(float(line.split(":", 1)[1].strip()) * 1_000_000)
    return None


def load_vec(lib_path: Path) -> ctypes.CDLL:
    lib = ctypes.CDLL(str(lib_path))
    lib.new_vec.argtypes = [ctypes.c_long]
    lib.new_vec.restype = ctypes.c_void_p
    lib.free_vec.argtypes = [ctypes.c_void_p]
    lib.set_vec_element.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_long]
    lib.set_vec_element.restype = ctypes.c_int
    lib.set_vec_length.argtypes = [ctypes.c_void_p, ctypes.c_long]
    for name in ("combine1", "combine2", "combine3"):
        getattr(lib, name).argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_long)]
    return lib


def choose_loops(func, vec, dest, n: int, min_ns: int) -> int:
    loops = 1
    while True:
        start = time.perf_counter_ns()
        for _ in range(loops):
            func(vec, ctypes.byref(dest))
        elapsed = time.perf_counter_ns() - start
        if elapsed >= min_ns or loops >= 1 << 20:
            return loops
        loops *= 2


def measure(func, vec, dest, n: int, samples: int, min_ns: int) -> tuple[int, int, float]:
    loops = choose_loops(func, vec, dest, n, min_ns)
    best = None
    for _ in range(samples):
        start = time.perf_counter_ns()
        for _ in range(loops):
            func(vec, ctypes.byref(dest))
        elapsed = time.perf_counter_ns() - start
        best = elapsed if best is None else min(best, elapsed)
    assert best is not None
    ns_per_element = best / (loops * n)
    return loops, best, ns_per_element


def plot(rows: list[dict[str, float | int | str]], output: Path, have_cpe: bool) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        plot_svg(rows, output.with_suffix(".svg"), have_cpe)
        return

    metric = "cpe" if have_cpe else "ns_per_element"
    ylabel = "CPE (cycles/element)" if have_cpe else "ns/element"

    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=160)
    for name in ("combine1", "combine2", "combine3"):
        xs = [int(r["n"]) for r in rows if r["function"] == name]
        ys = [float(r[metric]) for r in rows if r["function"] == name]
        ax.plot(xs, ys, marker="o", linewidth=1.8, markersize=4, label=name)

    ax.set_xscale("log", base=2)
    ax.set_xlabel("n (elements)")
    ax.set_ylabel(ylabel)
    ax.set_title("combine CPE vs vector length")
    ax.grid(True, which="both", linestyle=":", linewidth=0.7)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output)


def plot_svg(rows: list[dict[str, float | int | str]], output: Path, have_cpe: bool) -> None:
    metric = "cpe" if have_cpe else "ns_per_element"
    ylabel = "CPE (cycles/element)" if have_cpe else "ns/element"
    width, height = 900, 540
    left, right, top, bottom = 86, 24, 42, 74
    plot_w = width - left - right
    plot_h = height - top - bottom
    all_x = [int(r["n"]) for r in rows]
    all_y = [float(r[metric]) for r in rows]
    min_log_x = min(x.bit_length() - 1 for x in all_x)
    max_log_x = max(x.bit_length() - 1 for x in all_x)
    min_y, max_y = 0.0, max(all_y) * 1.08
    colors = {"combine1": "#2f6fbb", "combine2": "#c4572a", "combine3": "#2f8f5b"}

    def sx(x: int) -> float:
        return left + ((x.bit_length() - 1 - min_log_x) / (max_log_x - min_log_x)) * plot_w

    def sy(y: float) -> float:
        return top + (1 - (y - min_y) / (max_y - min_y)) * plot_h

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="540" viewBox="0 0 900 540">',
        '<rect width="900" height="540" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;font-size:13px;fill:#222}.title{font-size:20px;font-weight:700}.axis{stroke:#222;stroke-width:1.2}.grid{stroke:#ddd;stroke-width:1;stroke-dasharray:2 4}.tick{stroke:#222;stroke-width:1}.label{font-size:14px}</style>',
        '<text x="450" y="26" text-anchor="middle" class="title">combine CPE vs vector length</text>',
    ]

    for i in range(6):
        y_val = min_y + (max_y - min_y) * i / 5
        y = sy(y_val)
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        lines.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end">{y_val:.2f}</text>')

    for power in range(min_log_x, max_log_x + 1):
        x_val = 2**power
        x = sx(x_val)
        lines.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" class="grid"/>')
        lines.append(f'<text x="{x:.1f}" y="{height-bottom+24}" text-anchor="middle">{x_val}</text>')

    lines.extend(
        [
            f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" class="axis"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" class="axis"/>',
            f'<text x="450" y="{height-18}" text-anchor="middle" class="label">n (elements, log2 scale)</text>',
            f'<text transform="translate(22 270) rotate(-90)" text-anchor="middle" class="label">{ylabel}</text>',
        ]
    )

    for offset, name in enumerate(("combine1", "combine2", "combine3")):
        points = [(sx(int(r["n"])), sy(float(r[metric]))) for r in rows if r["function"] == name]
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        color = colors[name]
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="{point_text}"/>')
        for x, y in points:
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}"/>')
        legend_y = top + 18 + offset * 22
        lines.append(f'<line x1="{width-158}" y1="{legend_y}" x2="{width-128}" y2="{legend_y}" stroke="{color}" stroke-width="2.2"/>')
        lines.append(f'<text x="{width-120}" y="{legend_y+4}">{name}</text>')

    lines.append("</svg>")
    output.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opt", default="-O2", help="compiler optimization level, default: -O2")
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--min-ms", type=float, default=20.0, help="minimum timing window per sample")
    parser.add_argument("--max-n", type=int, default=1 << 22)
    parser.add_argument("--csv", type=Path, default=ROOT / "combine_cpe.csv")
    parser.add_argument("--png", type=Path, default=ROOT / "combine_cpe.png")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ns = [2**k for k in range(8, args.max_n.bit_length()) if 2**k <= args.max_n]
    lib_path = compile_library(args.opt)
    lib = load_vec(lib_path)
    cpu_hz = detect_cpu_hz()
    min_ns = int(args.min_ms * 1_000_000)

    max_n = max(ns)
    vec = lib.new_vec(max_n)
    if not vec:
        raise MemoryError(f"new_vec({max_n}) failed")

    try:
        for i in range(max_n):
            lib.set_vec_element(vec, i, i & 0x7F)

        rows: list[dict[str, float | int | str]] = []
        dest = ctypes.c_long()
        for n in ns:
            lib.set_vec_length(vec, n)
            for name in ("combine1", "combine2", "combine3"):
                func = getattr(lib, name)
                func(vec, ctypes.byref(dest))
                loops, elapsed_ns, ns_per_element = measure(func, vec, dest, n, args.samples, min_ns)
                row: dict[str, float | int | str] = {
                    "function": name,
                    "n": n,
                    "loops": loops,
                    "best_ns": elapsed_ns,
                    "ns_per_element": ns_per_element,
                }
                if cpu_hz:
                    row["cpe"] = ns_per_element * cpu_hz / 1_000_000_000
                rows.append(row)
                metric = f"{row['cpe']:.3f} CPE" if cpu_hz else f"{ns_per_element:.3f} ns/element"
                print(f"{name:8s} n={n:8d} loops={loops:6d} {metric}")
    finally:
        lib.free_vec(vec)

    fieldnames = ["function", "n", "loops", "best_ns", "ns_per_element"]
    if cpu_hz:
        fieldnames.append("cpe")
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    plot(rows, args.png, cpu_hz is not None)
    svg_path = args.png.with_suffix(".svg")
    if args.png.exists():
        print(f"wrote {args.csv} and {args.png}")
    elif svg_path.exists():
        print(f"wrote {args.csv} and {svg_path}")

    if not cpu_hz:
        print("CPU frequency was not detected; set CPU_HZ=<hz> to report CPE.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
