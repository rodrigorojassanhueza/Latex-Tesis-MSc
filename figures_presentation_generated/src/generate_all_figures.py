from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import matplotlib.patheffects as pe
from matplotlib.ticker import LogFormatterMathtext, LogLocator
from matplotlib import image as mpimg
from scipy.io import loadmat

from presentation_scientific_style import (
    ACCENT_RED,
    CAPTION_GRAY,
    FSR_MAP_TRACE,
    FSR_RED,
    GRID_GRAY,
    INTER_BLUE,
    INTRA_GOLD,
    NO_FSR_GRAY,
    PRESENTATION_FONT_STACK,
    SATELLITE_XYZ,
    SOFT_GRAY,
    STYLE_SOURCE,
    TEAL,
    TEXT_GRAY,
    UCHILE_BLUE,
    apply_matplotlib_presentation_style,
)


REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "figures_presentation_generated"
PDF_DIR = GEN / "pdf"
SVG_DIR = GEN / "svg"
PNG_DIR = GEN / "png"
SRC_DIR = GEN / "src"
WRAPPER_DIR = SRC_DIR / "wrappers"
WRAPPER_BUILD = SRC_DIR / "_wrapper_build"
TILE_CACHE_DIR = SRC_DIR / "tile_cache"
RELIEF_PROFILE_CSV = GEN / "data" / "processed" / "relief_profile_latS33p459_lon80W_64W.csv"

ASSETS_PRESENTATION = REPO / "assets" / "figures" / "presentation"
ASSETS_TEMPLATE = REPO / "assets" / "figures" / "template" / "departamentos"

MODELOS = Path(os.environ.get("TESIS_MODELOS_DIR", REPO.parent / "Modelos_v2025"))
RESULTS = Path(os.environ.get("TESIS_RESULTS_DIR", MODELOS / "resultados_finales"))
PSHA_CLASSICAL = MODELOS / "hazard" / "psha" / "resultados" / "classical" / "analysis_out"
MODELOS_ACTUALES = REPO.parent / "Modelos" / "Actuales"

INKSCAPE = Path(os.environ.get("INKSCAPE_EXE", r"C:\Program Files\Inkscape\bin\inkscape.exe"))
QGIS_PYTHON = Path(os.environ.get("QGIS_PYTHON_BAT", r"C:\Program Files\QGIS 3.40.8\bin\python-qgis-ltr.bat"))
QGIS_PROJECT = MODELOS_ACTUALES / "Qgis_traza_FSR" / "Modelo_FSR_v2.qgz"
QGIS_LAYOUT_NAME = "Composici\u00f3n 2"
QGIS_HELPER = SRC_DIR / "export_qgis_trazas.py"
QGIS_MAP_HELPER = SRC_DIR / "export_qgis_maps.py"
QGIS_DATA_DIR = SRC_DIR / "qgis_data"
COLORMAP_DIR = SRC_DIR / "colormaps"
BATLOW_CMAP_FILE = COLORMAP_DIR / "batlow.txt"
HCURVE_RAW = MODELOS / "hazard" / "psha" / "resultados" / "disagg" / "curvas_amenaza_apoyo" / "datos_crudos"
HCURVE_ZIPS = {
    "poisson": HCURVE_RAW / "output-520-hcurves-csv.zip",
    "bpt": HCURVE_RAW / "output-524-hcurves-csv.zip",
    "inter": HCURVE_RAW / "output-512-hcurves-csv.zip",
    "intra": HCURVE_RAW / "output-516-hcurves-csv.zip",
}
SUBDUCTION_NOTEBOOK = (
    MODELOS_ACTUALES
    / "Amenaza"
    / "Procesadores_datos"
    / "Amenaza"
    / "generar_plano_subduccion.ipynb"
)
SUBDUCTION_NRML_DIR = MODELOS_ACTUALES / "Amenaza" / "Modelos_base" / "PSHA_MODELO_SUBDUCCION_CORTO" / "INTERPLACA"
SUBDUCTION_MAT = (
    MODELOS_ACTUALES
    / "Amenaza"
    / "Informaci\u00f3n previa"
    / "Modelos de ejemplo"
    / "subduccion"
    / "Subduccion.mat"
)
FSR_RUPTURE_XML = MODELOS / "hazard" / "scenario" / "geometrias" / "NT_75_34.xml"
SUBDUCTION_MODEL_OUTPUT = "modelo_subduccion_zonas_centradas.pdf"


@dataclass
class ManifestRow:
    original_path: str
    new_path: str
    slide: str
    original_type: str
    new_type: str
    change: str
    source_data: str
    script_or_source: str
    limitation: str


MANIFEST: list[ManifestRow] = []


def as_posix(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        try:
            return Path(os.path.relpath(path, REPO)).as_posix()
        except ValueError:
            return path.as_posix()


def ensure_dirs() -> None:
    for path in (PDF_DIR, SVG_DIR, PNG_DIR, SRC_DIR, WRAPPER_DIR, WRAPPER_BUILD, QGIS_DATA_DIR, TILE_CACHE_DIR):
        path.mkdir(parents=True, exist_ok=True)
    for path in GEN.rglob("desktop.ini"):
        if path.is_file():
            path.unlink()
    for path in (PDF_DIR, SVG_DIR, PNG_DIR):
        for child in path.iterdir():
            if child.is_file():
                try:
                    child.unlink()
                except PermissionError:
                    print(f"Skipping locked generated file: {child}", file=sys.stderr)
    shutil.rmtree(WRAPPER_BUILD, ignore_errors=True)
    WRAPPER_BUILD.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(QGIS_DATA_DIR, ignore_errors=True)
    QGIS_DATA_DIR.mkdir(parents=True, exist_ok=True)


def style_matplotlib() -> None:
    apply_matplotlib_presentation_style(mpl)


def load_batlow_light_start() -> mpl.colors.ListedColormap:
    if not BATLOW_CMAP_FILE.exists():
        raise FileNotFoundError(f"No se encontro la tabla local batlow: {as_posix(BATLOW_CMAP_FILE)}")
    colors = np.loadtxt(BATLOW_CMAP_FILE, dtype=float)
    if colors.ndim != 2 or colors.shape[1] != 3:
        raise RuntimeError(f"Tabla batlow invalida: {as_posix(BATLOW_CMAP_FILE)}")
    return mpl.colors.ListedColormap(colors[::-1], name="batlow_light_start")


def add_manifest(
    *,
    original_path: str,
    new_path: Path,
    slide: str,
    original_type: str,
    new_type: str,
    change: str,
    source_data: str,
    script_or_source: str,
    limitation: str = "",
) -> None:
    MANIFEST.append(
        ManifestRow(
            original_path=original_path,
            new_path=as_posix(new_path),
            slide=slide,
            original_type=original_type,
            new_type=new_type,
            change=change,
            source_data=source_data,
            script_or_source=script_or_source,
            limitation=limitation,
        )
    )


def save_plot(
    fig: mpl.figure.Figure,
    name: str,
    *,
    original_path: str,
    slide: str,
    change: str,
    source_data: str,
    limitation: str = "",
    png_dpi: int = 300,
) -> Path:
    pdf = PDF_DIR / name
    svg = SVG_DIR / f"{Path(name).stem}.svg"
    png = PNG_DIR / f"{Path(name).stem}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    fig.savefig(png, bbox_inches="tight", dpi=png_dpi)
    plt.close(fig)
    add_manifest(
        original_path=original_path,
        new_path=pdf,
        slide=slide,
        original_type=Path(original_path).suffix.lstrip(".") or "tikz",
        new_type="pdf/svg/png",
        change=change,
        source_data=source_data,
        script_or_source=as_posix(Path(__file__)),
        limitation=limitation,
    )
    return pdf


def set_four_sided_axis(
    ax: mpl.axes.Axes,
    *,
    linewidth: float = 0.75,
    color: str = TEXT_GRAY,
    zorder: float = 30.0,
) -> None:
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(linewidth)
        spine.set_edgecolor(color)
        spine.set_zorder(zorder)
    for axis in (ax.xaxis, ax.yaxis):
        for tick in list(axis.get_major_ticks()) + list(axis.get_minor_ticks()):
            tick.tick1line.set_zorder(zorder)
            tick.tick2line.set_zorder(zorder)


def remove_overlapping_texts(fig: mpl.figure.Figure, texts: list[mpl.text.Text], *, pad_x: float = 1.02, pad_y: float = 1.08) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    kept: list[mpl.transforms.Bbox] = []
    for text in texts:
        if not text.get_visible():
            continue
        bbox = text.get_window_extent(renderer=renderer).expanded(pad_x, pad_y)
        if any(bbox.overlaps(previous) for previous in kept):
            text.remove()
            continue
        kept.append(bbox)


def finish_axis(ax: mpl.axes.Axes) -> None:
    ax.grid(True, axis="y")
    ax.tick_params(
        axis="both",
        which="major",
        length=3.0,
        width=0.8,
        pad=2.0,
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        direction="out",
    )
    set_four_sided_axis(ax, linewidth=0.75)


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")
    return pd.read_csv(path)


def plot_exposure() -> None:
    source = RESULTS / "risk_exposicion" / "Tablas" / "Global" / "exposicion_por_tipologia.csv"
    df = read_csv_required(source)
    labels = {
        "Albanileria": "Alban.",
        "Albañilería": "Alban.",
        "Hormigón armado (1–3 pisos)": "RC 1-3",
        "Hormigón armado (4–7 pisos)": "RC 4-7",
        "Hormigón armado (8+ pisos)": "RC 8+",
        "Madera": "Madera",
        "Adobe": "Adobe",
    }
    df["label"] = df["Categoria"].map(labels).fillna(df["Categoria"])
    df["frac_count"] = df["Frac_Cantidad"].str.rstrip("%").astype(float)
    df["frac_value"] = df["Frac_Valor"].str.rstrip("%").astype(float)

    order = df.sort_values("frac_value", ascending=True)
    y = np.arange(len(order))
    colors = [UCHILE_BLUE, INTER_BLUE, "#6E9DC8", "#9DBDD8", TEAL, ACCENT_RED]

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.8), sharey=True)
    for ax, col, title in [
        (axes[0], "frac_count", "Roles"),
        (axes[1], "frac_value", "Valor fiscal"),
    ]:
        bars = ax.barh(y, order[col], color=colors[: len(order)], edgecolor="white", linewidth=0.5)
        ax.set_yticks(y, order["label"])
        ax.set_xlim(0, max(58, order[col].max() * 1.18))
        ax.set_xlabel("% del portafolio")
        ax.set_title(title, color=UCHILE_BLUE, fontweight="bold", pad=6)
        finish_axis(ax)
        for bar, value in zip(bars, order[col]):
            ax.text(
                value + 1.0,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}%",
                va="center",
                fontsize=9.4,
                color=TEXT_GRAY,
            )
    axes[0].set_ylabel("Tipologia estructural")
    fig.suptitle("Composicion del inventario expuesto", color=UCHILE_BLUE, fontweight="bold", y=1.02)
    fig.tight_layout(w_pad=1.0)
    save_plot(
        fig,
        "exposicion_composicion.pdf",
        original_path="assets/figures/presentation/exposicion_composicion.pdf",
        slide="9",
        change="Redibujada como dos barras horizontales con porcentajes directos y tipografia de presentacion.",
        source_data=as_posix(source),
    )


def curve_columns(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    cols = [c for c in df.columns if c.startswith("poe-")]
    imls = np.array([float(c.replace("poe-", "")) for c in cols])
    return imls, cols


def nearest_curve_row(df: pd.DataFrame, lon: float, lat: float) -> pd.Series:
    dist2 = (df["lon"] - lon) ** 2 + (df["lat"] - lat) ** 2
    return df.loc[dist2.idxmin()]


def plot_hazard_curves(scheme: str) -> None:
    total_case = "Poisson_completo" if scheme == "Poisson" else "BPT_completo"
    total = read_csv_required(PSHA_CLASSICAL / total_case / "hazard_curve_percentile_p50.csv")
    no_fsr = read_csv_required(PSHA_CLASSICAL / "Sin_FSR" / "hazard_curve_percentile_p50.csv")
    table = read_csv_required(
        RESULTS
        / "hazard_curvas_y_desagg"
        / "tables"
        / "contribuciones"
        / "PGA"
        / scheme
        / f"tabla_contribuciones_PGA_{scheme}.csv"
    )
    imls, cols = curve_columns(total)

    fig, axes = plt.subplots(2, 3, figsize=(8.2, 4.75), sharex=True, sharey=True)
    axes = axes.ravel()
    for i, (_, site) in enumerate(table.iterrows()):
        ax = axes[i]
        total_row = nearest_curve_row(total, site["lon"], site["lat"])
        no_row = nearest_curve_row(no_fsr, site["lon"], site["lat"])
        total_y = total_row[cols].to_numpy(dtype=float)
        no_y = no_row[cols].to_numpy(dtype=float)
        ax.plot(imls, no_y, color=NO_FSR_GRAY, linestyle="--", label="Sin FSR")
        ax.plot(imls, total_y, color=UCHILE_BLUE, label=f"Total {scheme}")
        ax.fill_between(imls, no_y, total_y, where=total_y >= no_y, color=ACCENT_RED, alpha=0.13, linewidth=0)
        ax.axhline(0.10, color=GRID_GRAY, linewidth=0.65)
        ax.axhline(0.02, color=GRID_GRAY, linewidth=0.65)
        ax.set_title(f"Sitio {int(site['site_idx'])}", loc="left", color=UCHILE_BLUE, fontweight="bold")
        ax.set_xlim(0.05, 1.45)
        ax.set_ylim(0.001, 1.0)
        ax.set_yscale("log")
        ax.grid(True, which="major", axis="both")
        ax.tick_params(axis="both", which="both", top=True, right=True, labeltop=False, labelright=False)
        set_four_sided_axis(ax, linewidth=0.75)
    axes[-1].axis("off")
    handles, labels = axes[0].get_legend_handles_labels()
    axes[-1].legend(handles, labels, loc="center", frameon=False)
    fig.text(0.52, 0.03, "PGA [g]", ha="center", fontsize=9.4)
    fig.text(0.03, 0.52, "Probabilidad de excedencia en 50 anos", va="center", rotation=90, fontsize=9.4)
    fig.suptitle(
        f"Curvas de amenaza PGA: total vs. modelo sin FSR ({scheme})",
        color=UCHILE_BLUE,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=[0.06, 0.07, 1.0, 0.93], w_pad=0.8, h_pad=0.9)
    old = (
        "assets/figures/presentation/fig_5_18_psha_curvas_pga_poisson.pdf"
        if scheme == "Poisson"
        else "assets/figures/presentation/fig_5_19_psha_curvas_pga_bpt.pdf"
    )
    name = "fig_5_18_psha_curvas_pga_poisson.pdf" if scheme == "Poisson" else "fig_5_19_psha_curvas_pga_bpt.pdf"
    slide = "17" if scheme == "Poisson" else "Anexo"
    save_plot(
        fig,
        name,
        original_path=old,
        slide=slide,
        change="Redibujada desde CSV p50 como small multiples de cinco sitios, mostrando total y sin FSR con banda de diferencia.",
        source_data=f"{as_posix(PSHA_CLASSICAL / total_case / 'hazard_curve_percentile_p50.csv')}; {as_posix(PSHA_CLASSICAL / 'Sin_FSR' / 'hazard_curve_percentile_p50.csv')}",
        limitation="Los CSV disponibles no separan curvas interplaca e intraplaca; esa separacion queda representada en las figuras de desagregacion.",
    )


def contribution_columns(imt_key: str, poe_suffix: str) -> list[str]:
    return [
        f"frac_rate_inter@{imt_key}{poe_suffix}",
        f"frac_rate_intra@{imt_key}{poe_suffix}",
        f"frac_rate_FSR@{imt_key}{poe_suffix}",
    ]


def plot_disaggregation(imt: str, scheme: str, output_name: str, old: str, slide: str) -> None:
    imt_dir = "PGA" if imt == "PGA" else "SA1_0"
    imt_key = "PGA" if imt == "PGA" else "SA1p0"
    table = read_csv_required(
        RESULTS
        / "hazard_curvas_y_desagg"
        / "tables"
        / "contribuciones"
        / imt_dir
        / scheme
        / f"tabla_contribuciones_{imt_dir}_{scheme}.csv"
    )

    x = np.arange(len(table))
    labels = [f"S{int(i)}" for i in table["site_idx"]]
    source_labels = ["Interplaca", "Intraplaca", "FSR"]
    source_colors = [INTER_BLUE, INTRA_GOLD, FSR_RED]

    fig, axes = plt.subplots(1, 2, figsize=(8.25, 3.75), sharey=True)
    for ax, suffix, title in zip(axes, ["10", "02"], ["PoE 10% / 50 anos", "PoE 2% / 50 anos"]):
        bottom = np.zeros(len(table))
        for col, label, color in zip(contribution_columns(imt_key, suffix), source_labels, source_colors):
            vals = table[col].to_numpy(dtype=float) * 100.0
            ax.bar(x, vals, bottom=bottom, label=label, color=color, edgecolor="white", linewidth=0.45)
            if label == "FSR":
                for xi, yi, bi in zip(x, vals, bottom):
                    if yi >= 0.25:
                        ax.text(xi, bi + yi + 1.0, f"{yi:.1f}%", ha="center", fontsize=9.0, color=FSR_RED)
            bottom += vals
        ax.set_xticks(x, labels)
        ax.set_ylim(0, 103)
        ax.set_title(title, color=UCHILE_BLUE, fontweight="bold")
        ax.set_xlabel("Sitio de control")
        finish_axis(ax)
    axes[0].set_ylabel("Contribucion a la tasa [%]")
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    fig.suptitle(f"Desagregacion por fuente: {imt}, modelo {scheme}", color=UCHILE_BLUE, fontweight="bold", y=1.02)
    fig.tight_layout(rect=[0, 0.10, 1, 0.94], w_pad=1.0)
    save_plot(
        fig,
        output_name,
        original_path=old,
        slide=slide,
        change="Redibujada desde tabla de contribuciones como barras apiladas por sitio y nivel de excedencia.",
        source_data=as_posix(
            RESULTS
            / "hazard_curvas_y_desagg"
            / "tables"
            / "contribuciones"
            / imt_dir
            / scheme
            / f"tabla_contribuciones_{imt_dir}_{scheme}.csv"
        ),
    )


def plot_deterministic_losses() -> None:
    # Source: thesis table and text in tex/chapters/cap5_resultados.tex.
    scenarios = ["Interplaca", "Intraplaca", "FSR"]
    nac = np.array([3.84e10, 7.02e10, 8.29e10]) / 1e11
    haz = np.array([2.98e11, 4.54e11, 4.57e11]) / 1e11
    nac_lr = [3.70, 6.77, 7.98]
    haz_lr = [28.67, 43.78, 44.03]
    x = np.arange(len(scenarios))
    width = 0.34

    fig, ax = plt.subplots(figsize=(7.3, 3.75))
    b1 = ax.bar(x - width / 2, nac, width, label="Nacional", color=UCHILE_BLUE, edgecolor="white")
    b2 = ax.bar(x + width / 2, haz, width, label="HAZUS", color=ACCENT_RED, edgecolor="white")
    ax.set_xticks(x, scenarios)
    ax.set_ylabel(r"Perdida p50 [$10^{11}$ CLP]")
    ax.set_ylim(0, 5.05)
    finish_axis(ax)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    for bars, lrs in [(b1, nac_lr), (b2, haz_lr)]:
        for bar, lr in zip(bars, lrs):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.08,
                f"{lr:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9.5,
            )
    ax.text(
        0.02,
        0.93,
        "Etiqueta superior: perdida relativa del portafolio",
        transform=ax.transAxes,
        fontsize=9.4,
        color=CAPTION_GRAY,
    )
    fig.suptitle("Perdidas deterministas por escenario y modelo de vulnerabilidad", color=UCHILE_BLUE, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_plot(
        fig,
        "fig_5_30_perdidas_comuna_materialidad.pdf",
        original_path="assets/figures/presentation/fig_5_30_perdidas_comuna_materialidad.pdf",
        slide="16",
        change="Simplificada desde figura multicolumna a sintesis de perdida p50 y perdida relativa por escenario.",
        source_data="tex/chapters/cap5_resultados.tex, Tabla perdida_total_escenarios y texto asociado.",
        limitation="Se omite el detalle por comuna/materialidad de la figura de tesis para mejorar legibilidad en slide; no cambia los totales reportados.",
    )


def plot_nlt_convergence(im: str, output_name: str, old: str) -> None:
    source = RESULTS / "hazard_psha_sensibilidad_N_ramas" / "04_tables" / "fraction_converged_vs_n_ALLPCTS.csv"
    df = read_csv_required(source)
    sub = df[df["IM"].eq(im)].copy()
    if sub.empty:
        raise ValueError(f"No convergence rows for IM={im}")
    fig, ax = plt.subplots(figsize=(7.0, 3.3))
    for tol, color in [(2, ACCENT_RED), (5, UCHILE_BLUE)]:
        part = sub[sub["tolerance_pct"].eq(tol)]
        if not part.empty:
            ax.plot(part["n"], part["fraction_converged"] * 100, color=color, label=f"Tolerancia {tol}%")
    ax.axvline(310, color=TEXT_GRAY, linestyle="--", linewidth=1.0)
    ax.text(314, 8, r"$N_{LT}=310$", rotation=90, va="bottom", fontsize=9.6, color=TEXT_GRAY)
    ax.set_xlabel("Numero de ramas del arbol logico")
    ax.set_ylabel("Sitios convergidos [%]")
    ax.set_ylim(-2, 102)
    ax.set_xlim(0, max(320, sub["n"].max() * 1.02))
    finish_axis(ax)
    ax.legend(frameon=False, loc="lower right")
    fig.suptitle(f"Convergencia PSHA por ramas: {im}", color=UCHILE_BLUE, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    save_plot(
        fig,
        output_name,
        original_path=old,
        slide="Anexo",
        change="Redibujada desde CSV como curva compacta de fraccion de sitios convergidos.",
        source_data=as_posix(source),
    )


def plot_gmf_convergence(threshold: str, output_name: str, old: str) -> None:
    source = RESULTS / "hazard_sensibilidad_N_GMF" / "csv_caseB" / f"caseB_Tu_delta_obs_and_errband_thr_{threshold}.csv"
    df = read_csv_required(source)
    fig, ax = plt.subplots(figsize=(4.5, 3.35))
    ax.plot(df["u"], df["T_full"], color=UCHILE_BLUE, label="Referencia")
    ax.plot(df["u"], df["T_small_ref"], color=ACCENT_RED, label="Muestra usada")
    ax.plot(df["u"], df["T_nocorr"], color=NO_FSR_GRAY, linestyle="--", label="Sin correccion")
    ax.fill_between(df["u"], df["T_small_ref_lo"], df["T_small_ref_hi"], color=ACCENT_RED, alpha=0.14, linewidth=0)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(r"Umbral normalizado \(u\)")
    ax.set_ylabel(r"Probabilidad excedente")
    finish_axis(ax)
    ax.legend(frameon=False, loc="upper right")
    title = "PGA = 0.20 g" if threshold == "0p20g" else "PGA = 0.40 g"
    fig.suptitle(f"Convergencia GMF: {title}", color=UCHILE_BLUE, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    save_plot(
        fig,
        output_name,
        original_path=old,
        slide="Anexo",
        change="Redibujada desde CSV con lineas de referencia, muestra usada y banda de incertidumbre.",
        source_data=as_posix(source),
    )


def rel_from_wrapper(path: Path) -> str:
    return Path(os.path.relpath(path, WRAPPER_DIR)).as_posix()


def copy_source_to_png(src: Path, dest_name: str) -> Path:
    dest = PNG_DIR / dest_name
    if not src.exists():
        raise FileNotFoundError(src)
    shutil.copy2(src, dest)
    return dest


def write_wrapper_tex(tex_path: Path, source: Path, include_options: str) -> None:
    source_rel = rel_from_wrapper(source)
    tex = textwrap.dedent(
        rf"""
        \documentclass[border=0pt]{{standalone}}
        \usepackage{{graphicx}}
        \usepackage[x11names]{{xcolor}}
        \begin{{document}}
        \includegraphics[{include_options}]{{{source_rel}}}
        \end{{document}}
        """
    ).strip() + "\n"
    tex_path.write_text(tex, encoding="utf-8", newline="\n")


def run_checked(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        cmd,
        cwd=str(cwd or REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + completed.stdout
            + "\n\nSTDERR:\n"
            + completed.stderr
        )


def remove_manifest_for_output(output_name: str) -> None:
    new_path = as_posix(PDF_DIR / output_name)
    MANIFEST[:] = [row for row in MANIFEST if row.new_path != new_path]


def replace_or_add_style(style: str, key: str, value: str) -> str:
    declarations = [part.strip() for part in style.split(";") if part.strip()]
    replaced = False
    cleaned: list[str] = []
    for declaration in declarations:
        if ":" not in declaration:
            cleaned.append(declaration)
            continue
        name, _old_value = declaration.split(":", 1)
        if name.strip().lower() == key.lower():
            if not replaced:
                cleaned.append(f"{key}: {value}")
                replaced = True
            continue
        cleaned.append(declaration)
    if not replaced:
        cleaned.append(f"{key}: {value}")
    return "; ".join(cleaned)


def scale_font_sizes(svg: str, *, scale: float, min_px: float, max_px: float) -> str:
    def scaled(value: str) -> float:
        size = float(value)
        return min(max(size * scale, min_px), max_px)

    def repl_style(match: re.Match[str]) -> str:
        size = float(match.group(1))
        new_size = min(max(size * scale, min_px), max_px)
        return f"font-size: {new_size:.2f}px"

    def repl_attr(match: re.Match[str]) -> str:
        return f'{match.group(1)}"{scaled(match.group(2)):.2f}"'

    svg = re.sub(r"font-size:\s*([\d.]+)px", repl_style, svg)
    return re.sub(r'(font-size=)"([\d.]+)"', repl_attr, svg)


def style_font_attrs(svg: str) -> str:
    attr_stack = "Arial, Helvetica, DejaVu Sans, Liberation Sans, sans-serif"
    return re.sub(r'font-family="[^"]*"', f'font-family="{attr_stack}"', svg)


def raise_stroke_widths(svg: str, *, min_width: float) -> str:
    def repl_style(match: re.Match[str]) -> str:
        width = float(match.group(1))
        if width <= 0:
            return match.group(0)
        return f"stroke-width: {max(width, min_width):.3f}"

    def repl_attr(match: re.Match[str]) -> str:
        width = float(match.group(2))
        if width <= 0:
            return match.group(0)
        return f'{match.group(1)}"{max(width, min_width):.3f}"'

    svg = re.sub(r"stroke-width:\s*([\d.]+)", repl_style, svg)
    return re.sub(r'(stroke-width=)"([\d.]+)"', repl_attr, svg)


def style_text_tags(svg: str) -> str:
    def repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        style_match = re.search(r'style="([^"]*)"', tag)
        if style_match:
            style = style_match.group(1)
            style = replace_or_add_style(style, "font-family", PRESENTATION_FONT_STACK)
            style = replace_or_add_style(style, "fill", TEXT_GRAY)
            return tag[: style_match.start(1)] + style + tag[style_match.end(1) :]
        return tag.replace("<text", f'<text style="font-family: {PRESENTATION_FONT_STACK}; fill: {TEXT_GRAY}"', 1)

    return re.sub(r"<text\b[^>]*>", repl, svg)


def apply_presentation_svg_style(
    svg: str,
    *,
    font_scale: float = 1.15,
    min_font_px: float = 10.0,
    max_font_px: float = 17.0,
    min_stroke_width: float = 0.45,
) -> str:
    svg = svg.replace("Times New Roman", "Arial")
    svg = svg.replace("'Times'", "'Helvetica'")
    svg = svg.replace("DejaVu Serif", "DejaVu Sans")
    svg = scale_font_sizes(svg, scale=font_scale, min_px=min_font_px, max_px=max_font_px)
    svg = style_font_attrs(svg)
    svg = style_text_tags(svg)
    return raise_stroke_widths(svg, min_width=min_stroke_width)


def hide_group(svg: str, group_id: str) -> str:
    pattern = re.compile(rf'(<g\b(?=[^>]*\bid="{re.escape(group_id)}")[^>]*)(>)', flags=re.S)
    return pattern.sub(r'\1 display="none"\2', svg, count=1)


def replace_text(svg: str, old: str, new: str) -> str:
    return svg.replace(f">{old}<", f">{new}<")


def set_text_group_font_size(svg: str, group_id: str, font_size_px: float) -> str:
    pattern = re.compile(
        rf'(<g\b(?=[^>]*\bid="{re.escape(group_id)}")[\s\S]*?</g>)',
        flags=re.S,
    )

    def repl(match: re.Match[str]) -> str:
        return re.sub(
            r"font-size:\s*[\d.]+px",
            f"font-size: {font_size_px:.2f}px",
            match.group(1),
        )

    return pattern.sub(repl, svg, count=1)


def process_exposure_svg(svg: str) -> str:
    for group_id in [f"text_{idx}" for idx in range(26, 34)]:
        svg = set_text_group_font_size(svg, group_id, 9.6)
    return svg


def process_oep_svg(svg: str) -> str:
    for group_id in ("text_13", "text_14"):
        svg = hide_group(svg, group_id)
    replacements = {
        "Nacional (All)": "Nacional (con FSR)",
        "Nacional (No-ASC)": "Nacional (sin FSR)",
        "HAZUS (All)": "HAZUS (con FSR)",
        "HAZUS (No-ASC)": "HAZUS (sin FSR)",
    }
    for old, new in replacements.items():
        svg = replace_text(svg, old, new)
    return svg


def process_delta_lambda_svg(svg: str) -> str:
    return hide_group(svg, "text_13")


def process_lambda_svg(svg: str) -> str:
    return hide_group(svg, "text_12")


def process_map_fsr_svg(svg: str) -> str:
    return hide_group(svg, "text_27")


def export_svg_to_pdf(svg_path: Path, pdf_path: Path, png_path: Path | None = None) -> None:
    if not INKSCAPE.exists():
        raise FileNotFoundError(f"No se encontro Inkscape en {INKSCAPE}")
    run_checked([str(INKSCAPE), str(svg_path), f"--export-filename={pdf_path}"], cwd=REPO)
    if png_path is not None:
        run_checked([str(INKSCAPE), str(svg_path), f"--export-filename={png_path}", "--export-dpi=180"], cwd=REPO)


def styled_pdf_source(
    *,
    source: Path,
    output_name: str,
    original_path: str,
    slide: str,
    change: str,
    source_data: str,
    limitation: str = "",
    font_scale: float = 1.12,
    min_font_px: float = 10.0,
    max_font_px: float = 17.0,
    min_stroke_width: float = 0.45,
) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    raw_svg = WRAPPER_BUILD / f"{Path(output_name).stem}_pdf_raw.svg"
    run_checked([str(INKSCAPE), str(source), f"--export-filename={raw_svg}"], cwd=REPO)
    svg = raw_svg.read_text(encoding="utf-8", errors="ignore")
    svg = apply_presentation_svg_style(
        svg,
        font_scale=font_scale,
        min_font_px=min_font_px,
        max_font_px=max_font_px,
        min_stroke_width=min_stroke_width,
    )
    styled = SVG_DIR / f"{Path(output_name).stem}.svg"
    styled.write_text(svg, encoding="utf-8", newline="\n")
    pdf = PDF_DIR / output_name
    png = PNG_DIR / f"{Path(output_name).stem}.png"
    export_svg_to_pdf(styled, pdf, png)
    remove_manifest_for_output(output_name)
    if svg.count("<text") == 0:
        limitation = (
            (limitation + " " if limitation else "")
            + "El PDF importado no expone texto editable; se conserva el contenido exacto y se normalizan salida vectorial, escala y grosores cuando Inkscape los expone."
        )
    add_manifest(
        original_path=original_path,
        new_path=pdf,
        slide=slide,
        original_type="pdf",
        new_type="pdf/svg/png",
        change=change,
        source_data=source_data,
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(styled)}",
        limitation=limitation,
    )


def read_kml_lines(path: Path) -> list[list[tuple[float, float]]]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".kmz":
        with zipfile.ZipFile(path, "r") as zf:
            kml_names = [name for name in zf.namelist() if name.lower().endswith(".kml")]
            if not kml_names:
                return []
            raw = zf.read(kml_names[0])
        root = ET.fromstring(raw)
    else:
        root = ET.parse(path).getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    nodes = root.findall(".//kml:LineString/kml:coordinates", ns) + root.findall(".//LineString/coordinates")
    lines: list[list[tuple[float, float]]] = []
    for coords in nodes:
        line: list[tuple[float, float]] = []
        for token in (coords.text or "").replace("\n", " ").replace("\t", " ").split():
            parts = token.split(",")
            if len(parts) < 2:
                continue
            try:
                line.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
        if len(line) >= 2:
            lines.append(line)
    return lines


def line_collection_bounds(lines: list[list[tuple[float, float]]]) -> tuple[float, float, float, float]:
    points = [point for line in lines for point in line]
    if not points:
        raise RuntimeError("La coleccion de lineas no contiene coordenadas.")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), max(xs), min(ys), max(ys)


def read_shapefile_polygon_parts(path: Path) -> list[list[tuple[float, float]]]:
    if not path.exists():
        raise FileNotFoundError(path)
    parts_out: list[list[tuple[float, float]]] = []
    with path.open("rb") as fh:
        header = fh.read(100)
        if len(header) < 100:
            return parts_out
        xmin, ymin, xmax, ymax = struct.unpack("<4d", header[36:68])
        is_web_mercator = max(abs(xmin), abs(ymin), abs(xmax), abs(ymax)) > 1000.0
        while True:
            record_header = fh.read(8)
            if len(record_header) < 8:
                break
            _record_number, content_words = struct.unpack(">2i", record_header)
            content = fh.read(content_words * 2)
            if len(content) < 44:
                continue
            shape_type = struct.unpack("<i", content[:4])[0]
            if shape_type == 0:
                continue
            if shape_type not in {5, 15, 25, 31}:
                continue
            num_parts, num_points = struct.unpack("<2i", content[36:44])
            parts_offset = 44
            points_offset = parts_offset + 4 * num_parts
            expected = points_offset + 16 * num_points
            if num_parts <= 0 or num_points <= 0 or len(content) < expected:
                continue
            starts = list(struct.unpack(f"<{num_parts}i", content[parts_offset:points_offset]))
            starts.append(num_points)
            raw_points = [
                struct.unpack("<2d", content[points_offset + 16 * idx : points_offset + 16 * (idx + 1)])
                for idx in range(num_points)
            ]
            for start, end in zip(starts[:-1], starts[1:]):
                ring = [web_mercator_to_lonlat(x, y) if is_web_mercator else (float(x), float(y)) for x, y in raw_points[start:end]]
                if len(ring) >= 3:
                    parts_out.append(ring)
    return parts_out


def web_mercator_to_lonlat(x: float, y: float) -> tuple[float, float]:
    radius = 6378137.0
    lon = math.degrees(x / radius)
    lat = math.degrees(2.0 * math.atan(math.exp(y / radius)) - math.pi / 2.0)
    return lon, lat


def draw_santiago_context(ax: mpl.axes.Axes, extent: tuple[float, float, float, float]) -> None:
    xmin, xmax, ymin, ymax = extent
    satellite = satellite_mosaic(xmin, xmax, ymin, ymax, zoom=13, require_complete=False)
    if satellite is not None:
        img, img_extent = satellite
        img_pil = Image.fromarray(img).filter(ImageFilter.SHARPEN)
        img_pil = ImageEnhance.Contrast(img_pil).enhance(1.08)
        img_pil = ImageEnhance.Color(img_pil).enhance(1.04)
        img_pil = ImageEnhance.Brightness(img_pil).enhance(0.88)
        img = np.asarray(img_pil)
        ax.imshow(img, extent=img_extent, origin="upper", zorder=0.0, interpolation="bilinear")
        ax.set_facecolor("#1F252A")
        return

    comuna_path = MODELOS_ACTUALES / "Amenaza" / "Geometrias_base" / "Comunas_reparado.shp"
    try:
        rings = read_shapefile_polygon_parts(comuna_path)
    except FileNotFoundError:
        rings = []
    ax.set_facecolor("#F3F5F6")
    for ring in rings:
        xs = np.asarray([point[0] for point in ring], dtype=float)
        ys = np.asarray([point[1] for point in ring], dtype=float)
        if xs.size == 0 or ys.size == 0:
            continue
        if xs.max() < xmin or xs.min() > xmax or ys.max() < ymin or ys.min() > ymax:
            continue
        ax.fill(xs, ys, facecolor=FIG3_MAP_LAND, edgecolor="#7D858C", linewidth=0.42, zorder=0.5)


def generate_qgis_trazas() -> None:
    trace_path = MODELOS_ACTUALES / "Amenaza" / "Geometrias_base" / "FSR completo.kmz"
    lines = read_kml_lines(trace_path)
    if not lines:
        raise RuntimeError(f"No se encontraron lineas FSR en {trace_path}")

    fxmin, fxmax, fymin, fymax = line_collection_bounds(lines)
    urban_extent = (-70.88, -70.35, -33.84, -33.25)
    xmin = min(urban_extent[0], fxmin) - 0.015
    xmax = max(urban_extent[1], fxmax) + 0.015
    ymin = min(urban_extent[2], fymin) - 0.015
    ymax = max(urban_extent[3], fymax) + 0.015
    extent = (xmin, xmax, ymin, ymax)

    fig, ax = plt.subplots(figsize=(4.10, 4.25), constrained_layout=True)
    draw_santiago_context(ax, extent)

    for idx, line in enumerate(lines):
        xs = [point[0] for point in line]
        ys = [point[1] for point in line]
        ax.plot(
            xs,
            ys,
            color="#FF0A7A",
            linewidth=1.65,
            solid_capstyle="butt",
            solid_joinstyle="round",
            label="FSR" if idx == 0 else None,
            zorder=5.0,
            path_effects=[
                pe.Stroke(linewidth=3.20, foreground="#14171A", alpha=0.78),
                pe.Stroke(linewidth=2.45, foreground="white", alpha=0.96),
                pe.Normal(),
            ],
        )

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect(1.0 / math.cos(math.radians((ymin + ymax) / 2.0)))
    ax.set_xlabel("Longitud", fontsize=9.2, labelpad=2.0)
    ax.set_ylabel("Latitud", fontsize=9.2, labelpad=2.0)
    ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(0.20))
    ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(0.20))
    degree = "\N{DEGREE SIGN}"
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda value, _pos: f"{abs(value):.1f}{degree}W"))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda value, _pos: f"{abs(value):.1f}{degree}S"))
    ax.tick_params(
        axis="both",
        which="major",
        labelsize=8.0,
        length=3.2,
        width=0.75,
        pad=2.0,
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        direction="out",
    )
    set_four_sided_axis(ax, linewidth=0.82, zorder=20.0)
    ax.grid(False)
    legend = ax.legend(
        loc="lower left",
        fontsize=8.4,
        frameon=True,
        facecolor="white",
        edgecolor="none",
        framealpha=0.92,
        borderpad=0.35,
        handlelength=1.7,
        labelspacing=0.25,
    )
    for text in legend.get_texts():
        text.set_color(TEXT_GRAY)

    remove_manifest_for_output("trazas_fsr.pdf")
    save_plot(
        fig,
        "trazas_fsr.pdf",
        original_path="assets/figures/presentation/trazas_fsr.png",
        slide="2",
        change="Redibujada como mapa unico para presentacion: usa la capa operacional mas completa identificada en Modelos/Actuales, FSR completo.kmz, con todos sus segmentos cartograficos; elimina los paneles y modelos de ruptura del layout QGIS original, incorpora vista satelital de mayor resolucion en los mismos limites del mapa, aplica nitidez/contraste suave al raster y refuerza la FSR con nucleo magenta y doble contorno oscuro/blanco para mejorar contraste proyectado.",
        source_data=(
            f"{as_posix(trace_path)} (200 LineStrings, 1660 vertices; incluye segmentos observados, interpretados e inferidos); contexto urbano: "
            f"{as_posix(MODELOS_ACTUALES / 'Amenaza' / 'Geometrias_base' / 'Comunas_reparado.shp')}; "
            f"tiles satelitales Esri World Imagery zoom 13: {SATELLITE_XYZ}; "
            f"layout QGIS original identificado: {as_posix(QGIS_PROJECT)} / {QGIS_LAYOUT_NAME}"
        ),
        limitation="El mapa se redibuja desde los datos vectoriales disponibles; el fondo satelital se descarga en cache local desde el servicio XYZ configurado y, si no esta disponible, el script cae al fondo vectorial de comunas sin cambiar la traza ni los limites.",
        png_dpi=600,
    )


def _bounds_from_values(values: np.ndarray, *, lo: float = 2.0, hi: float = 100.0, n: int = 10) -> np.ndarray:
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return np.linspace(0.0, 1.0, n + 1)
    vmin, vmax = np.nanpercentile(vals, [lo, hi])
    vmin = max(0.0, float(vmin))
    vmax = float(vmax)
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin = max(0.0, float(np.nanmin(vals)))
        vmax = float(np.nanmax(vals))
    if vmax <= vmin:
        vmax = vmin + 1e-6
    return np.linspace(vmin, vmax, n + 1)


def write_bounds_csv(path: Path, bounds: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["index", "value"])
        writer.writeheader()
        for idx, value in enumerate(np.asarray(bounds, dtype=float)):
            writer.writerow({"index": idx, "value": f"{value:.12g}"})


def discover_dsha_sites_from_sitemesh(zip_paths: list[Path]) -> pd.DataFrame:
    best: pd.DataFrame | None = None
    for zip_path in zip_paths:
        if not zip_path.exists():
            continue
        with zipfile.ZipFile(zip_path) as zf:
            members = [name for name in zf.namelist() if "sitemesh" in name.lower() and name.lower().endswith(".csv")]
            for member in members:
                with zf.open(member, "r") as fh:
                    df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8"), comment="#")
                lower = {str(col).lower(): col for col in df.columns}
                id_col = lower.get("custom_site_id")
                lon_col = lower.get("lon") or lower.get("longitude") or lower.get("x")
                lat_col = lower.get("lat") or lower.get("latitude") or lower.get("y")
                if not (id_col and lon_col and lat_col):
                    continue
                out = (
                    df[[id_col, lon_col, lat_col]]
                    .rename(columns={id_col: "custom_site_id", lon_col: "lon", lat_col: "lat"})
                    .dropna(subset=["lon", "lat"])
                    .drop_duplicates(subset=["custom_site_id"])
                )
                out["custom_site_id"] = out["custom_site_id"].astype(str)
                out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
                out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
                out = out.dropna(subset=["lon", "lat"])
                if best is None or len(out) > len(best):
                    best = out
    if best is None or best.empty:
        raise RuntimeError("No se encontraron coordenadas sitemesh para DSHA en los ZIP.")
    return best


def prepare_dsha_qgis_inputs() -> None:
    raw_dir = MODELOS / "hazard" / "scenario" / "resultados" / "resultados_crudos"
    zip_paths = [
        raw_dir / name
        for name in [
            "output-518-gmf_data-csv.zip",
            "output-523-gmf_data-csv.zip",
            "output-528-gmf_data-csv.zip",
            "output-533-gmf_data-csv.zip",
            "output-538-gmf_data-csv.zip",
            "output-543-gmf_data-csv.zip",
            "output-548-gmf_data-csv.zip",
            "output-513-gmf_data-csv.zip",
        ]
    ]
    sites = discover_dsha_sites_from_sitemesh(zip_paths)
    tables_dir = MODELOS / "hazard" / "scenario" / "resultados" / "resultados_procesados" / "out_gmf_maps_single_DEMhillshade" / "tables"
    model_to_output = {
        149: "dsha_inter_pga.csv",
        147: "dsha_fsr_pga.csv",
        150: "dsha_intra_pga.csv",
    }
    all_values: list[np.ndarray] = []
    for csv_path in sorted(tables_dir.glob("percentiles_model_*.csv")):
        df = pd.read_csv(csv_path)
        if "PGA_p50" in df.columns:
            all_values.append(pd.to_numeric(df["PGA_p50"], errors="coerce").to_numpy(float))
    bounds = _bounds_from_values(np.concatenate(all_values), lo=2.0, hi=100.0, n=10)
    write_bounds_csv(QGIS_DATA_DIR / "dsha_pga_bounds.csv", bounds)

    for model_id, output_name in model_to_output.items():
        source = tables_dir / f"percentiles_model_{model_id}.csv"
        df = pd.read_csv(source)
        df["custom_site_id"] = df["custom_site_id"].astype(str)
        merged = sites.merge(df[["custom_site_id", "PGA_p50"]], on="custom_site_id", how="inner")
        merged = merged.rename(columns={"PGA_p50": "value"})
        merged[["custom_site_id", "lon", "lat", "value"]].to_csv(QGIS_DATA_DIR / output_name, index=False)


def prepare_control_sites_qgis_input() -> None:
    source = (
        RESULTS
        / "hazard_curvas_y_desagg"
        / "tables"
        / "contribuciones"
        / "PGA"
        / "Poisson"
        / "tabla_contribuciones_PGA_Poisson.csv"
    )
    df = pd.read_csv(source)
    out = df[["site_idx", "lon", "lat"]].copy()
    out["label"] = out["site_idx"].map(lambda value: f"S{int(value)}")
    out.to_csv(QGIS_DATA_DIR / "control_sites.csv", index=False)


def prepare_aalr_qgis_input() -> None:
    import duckdb

    db_path = Path(
        os.environ.get(
            "TESIS_RISK_DUCKDB",
            Path.home() / "oqdata" / "risk_final_rlz_ASC_274_275_vs_277.duckdb",
        )
    )
    if not db_path.exists():
        raise FileNotFoundError(f"No se encontro DuckDB AALR: {db_path}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        query = """
            SELECT unit_name, AALR_mean
            FROM aal_unit_stats
            WHERE model_id=? AND subset=? AND variant=? AND unit_type='objectid'
        """

        def fetch(model_id: int, subset: str, variant: str, col: str) -> pd.DataFrame:
            df = con.execute(query, [model_id, subset, variant]).fetchdf()
            df["OBJECTID_INT"] = pd.to_numeric(df["unit_name"], errors="coerce").astype("Int64")
            df = df[df["OBJECTID_INT"].notna()].copy()
            df["OBJECTID_INT"] = df["OBJECTID_INT"].astype(int)
            return df[["OBJECTID_INT", "AALR_mean"]].rename(columns={"AALR_mean": col})

        nac_all = fetch(0, "main", "all", "AALR_NAC_FSR")
        nac_no = fetch(0, "main", "nonasc", "AALR_NAC_NOFSR")
        haz_all = fetch(1, "all", "all", "AALR_HAZ_FSR")
        haz_no = fetch(1, "all", "nonasc", "AALR_HAZ_NOFSR")
    finally:
        con.close()

    merged = nac_all.merge(nac_no, on="OBJECTID_INT", how="inner")
    merged = merged.merge(haz_all, on="OBJECTID_INT", how="inner")
    merged = merged.merge(haz_no, on="OBJECTID_INT", how="inner")

    def rel_inc(all_values: pd.Series, base_values: pd.Series) -> np.ndarray:
        all_arr = pd.to_numeric(all_values, errors="coerce").to_numpy(float)
        base_arr = pd.to_numeric(base_values, errors="coerce").to_numpy(float)
        out = np.full_like(all_arr, np.nan, dtype=float)
        ok = np.isfinite(all_arr) & np.isfinite(base_arr) & (base_arr > 0)
        out[ok] = 100.0 * (all_arr[ok] - base_arr[ok]) / base_arr[ok]
        return np.where(np.isfinite(out), np.maximum(out, 0.0), out)

    merged["dFSR_AALR_NAC_pct"] = rel_inc(merged["AALR_NAC_FSR"], merged["AALR_NAC_NOFSR"])
    merged["dFSR_AALR_HAZ_pct"] = rel_inc(merged["AALR_HAZ_FSR"], merged["AALR_HAZ_NOFSR"])
    out = merged[["OBJECTID_INT", "dFSR_AALR_NAC_pct", "dFSR_AALR_HAZ_pct"]].copy()
    out.to_csv(QGIS_DATA_DIR / "aalr_effect_objectid.csv", index=False)
    vals = np.r_[
        out["dFSR_AALR_NAC_pct"].to_numpy(float),
        out["dFSR_AALR_HAZ_pct"].to_numpy(float),
    ]
    write_bounds_csv(QGIS_DATA_DIR / "aalr_effect_bounds.csv", _bounds_from_values(vals, lo=0.0, hi=98.0, n=10))


def prepare_qgis_map_inputs() -> None:
    prepare_dsha_qgis_inputs()
    prepare_control_sites_qgis_input()
    prepare_aalr_qgis_input()


def generate_qgis_maps() -> None:
    if not QGIS_PYTHON.exists():
        raise FileNotFoundError(QGIS_PYTHON)
    if not QGIS_MAP_HELPER.exists():
        raise FileNotFoundError(QGIS_MAP_HELPER)
    env = os.environ.copy()
    env.pop("QT_QPA_PLATFORM", None)
    run_checked([str(QGIS_PYTHON), str(QGIS_MAP_HELPER), str(REPO)], cwd=REPO, env=env)


def parse_nrml_fault_geometry(nrml_file: Path) -> list[np.ndarray]:
    namespaces = {
        "gml": "http://www.opengis.net/gml",
        "nrml": "http://openquake.org/xmlns/nrml/0.5",
    }
    tree = ET.parse(nrml_file)
    root = tree.getroot()
    fault_geometry: list[np.ndarray] = []
    for edge in root.findall(".//nrml:complexFaultGeometry/*", namespaces):
        line = edge.find("gml:LineString", namespaces)
        if line is None:
            continue
        pos_list = line.find("gml:posList", namespaces)
        if pos_list is None or not pos_list.text:
            continue
        points = np.array(pos_list.text.strip().split(), dtype=float).reshape(-1, 3)
        if np.all(np.isfinite(points)):
            fault_geometry.append(points)
    return fault_geometry


def load_subduction_surface() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not SUBDUCTION_MAT.exists():
        raise FileNotFoundError(SUBDUCTION_MAT)
    subduccion_data = loadmat(SUBDUCTION_MAT)
    if "Subduccion" not in subduccion_data:
        raise KeyError(f"No se encontro la variable Subduccion en {SUBDUCTION_MAT}")
    subduccion = subduccion_data["Subduccion"]
    subduccion_clean = np.array(subduccion, dtype=float, copy=True)
    subduccion_clean[~np.isfinite(subduccion_clean)] = np.nan
    sh = subduccion_clean.reshape(-1, 301 * 221)
    zh = -sh[2, :].reshape(301, 221)
    lon_range = np.linspace(-82, -60, zh.shape[1])
    lat_range = np.linspace(-15, -45, zh.shape[0])
    lon_grid, lat_grid = np.meshgrid(lon_range, lat_range)
    return lon_grid, lat_grid, zh


def lonlat_to_xyz_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2**zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def xyz_tile_bounds(x: int, y: int, zoom: int) -> tuple[float, float, float, float]:
    n = 2**zoom
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0

    def tile_y_to_lat(tile_y: int) -> float:
        merc = math.pi * (1.0 - 2.0 * tile_y / n)
        return math.degrees(math.atan(math.sinh(merc)))

    lat_max = tile_y_to_lat(y)
    lat_min = tile_y_to_lat(y + 1)
    return lon_min, lon_max, lat_min, lat_max


def fetch_xyz_tile(x: int, y: int, zoom: int) -> Image.Image | None:
    TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = TILE_CACHE_DIR / f"esri_z{zoom}_x{x}_y{y}.jpg"
    if cache_path.exists():
        return Image.open(cache_path).convert("RGB")
    url = SATELLITE_XYZ.format(z=zoom, x=x, y=y)
    request = Request(url, headers={"User-Agent": "LATEX_TESIS figure generator"})
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
    except (OSError, URLError):
        return None
    cache_path.write_bytes(raw)
    return Image.open(io.BytesIO(raw)).convert("RGB")


def satellite_mosaic(
    lon_min: float,
    lon_max: float,
    lat_min: float,
    lat_max: float,
    *,
    zoom: int = 5,
    require_complete: bool = False,
) -> tuple[np.ndarray, tuple[float, float, float, float]] | None:
    x0, y1 = lonlat_to_xyz_tile(lon_min, lat_min, zoom)
    x1, y0 = lonlat_to_xyz_tile(lon_max, lat_max, zoom)
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    tiles: dict[tuple[int, int], Image.Image] = {}
    expected_tiles = (x1 - x0 + 1) * (y1 - y0 + 1)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            tile = fetch_xyz_tile(x, y, zoom)
            if tile is not None:
                tiles[(x, y)] = tile
    if not tiles:
        return None
    if require_complete and len(tiles) < expected_tiles:
        return None

    tile_size = 256
    mosaic = Image.new("RGB", ((x1 - x0 + 1) * tile_size, (y1 - y0 + 1) * tile_size), "white")
    for (x, y), tile in tiles.items():
        mosaic.paste(tile.resize((tile_size, tile_size)), ((x - x0) * tile_size, (y - y0) * tile_size))

    west, _, _, north = xyz_tile_bounds(x0, y0, zoom)
    _, east, south, _ = xyz_tile_bounds(x1, y1, zoom)
    return np.asarray(mosaic), (west, east, south, north)


def zone_centroid(zone_geometry: list[np.ndarray]) -> tuple[float, float, float]:
    pts = np.vstack(zone_geometry)
    shallow = pts[pts[:, 2] <= np.nanmin(pts[:, 2]) + 8.0]
    if len(shallow) < 3:
        shallow = pts
    return float(np.nanmean(shallow[:, 0])), float(np.nanmean(shallow[:, 1])), float(np.nanmean(shallow[:, 2]))


def get_subduction_zone_palette() -> list[str]:
    return ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]


FIG3_MAP_OCEAN = "#8FB9C6"
FIG3_MAP_LAND = "#C4C8CB"
FIG3_MAP_LAND_EDGE = "#5B646B"


def readable_label_color(hex_color: str) -> str:
    rgb = mpl.colors.to_rgb(hex_color)
    luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return TEXT_GRAY if luminance > 0.62 else "white"


def lonlat_to_local_km(lon: np.ndarray | float, lat: np.ndarray | float, lon0: float, lat0: float) -> tuple[np.ndarray, np.ndarray]:
    radius_km = 6371.0
    x = radius_km * math.cos(math.radians(lat0)) * np.radians(np.asarray(lon, dtype=float) - lon0)
    y = radius_km * np.radians(np.asarray(lat, dtype=float) - lat0)
    return x, y


def format_lon_w(value: float, _pos: int | None = None) -> str:
    return f"{abs(value):.0f}\N{DEGREE SIGN}W"


def format_lat_s(value: float, _pos: int | None = None) -> str:
    return f"{abs(value):.0f}\N{DEGREE SIGN}S"


def natural_earth_land_geojson() -> dict | None:
    carto_dir = SRC_DIR / "cartography"
    carto_dir.mkdir(parents=True, exist_ok=True)
    cache = carto_dir / "ne_50m_land.geojson"
    if not cache.exists():
        url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson"
        request = Request(url, headers={"User-Agent": "LATEX_TESIS figure generator"})
        try:
            with urlopen(request, timeout=30) as response:
                cache.write_bytes(response.read())
        except (OSError, URLError):
            return None
    try:
        return json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def ring_intersects_bbox(ring: list, bbox: tuple[float, float, float, float]) -> bool:
    xs = [pt[0] for pt in ring]
    ys = [pt[1] for pt in ring]
    lon_min, lon_max, lat_min, lat_max = bbox
    return max(xs) >= lon_min and min(xs) <= lon_max and max(ys) >= lat_min and min(ys) <= lat_max


def plot_sober_land_background(ax: mpl.axes.Axes, bbox: tuple[float, float, float, float]) -> bool:
    ax.set_facecolor(FIG3_MAP_OCEAN)
    ax._cartographic_land_paths = []
    land = natural_earth_land_geojson()
    if land is None:
        return False
    plotted = False
    for feature in land.get("features", []):
        geometry = feature.get("geometry") or {}
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        polygons = coordinates if geom_type == "MultiPolygon" else [coordinates] if geom_type == "Polygon" else []
        for polygon in polygons:
            if not polygon:
                continue
            exterior = polygon[0]
            if not ring_intersects_bbox(exterior, bbox):
                continue
            xs = [pt[0] for pt in exterior]
            ys = [pt[1] for pt in exterior]
            ax.fill(xs, ys, facecolor=FIG3_MAP_LAND, edgecolor=FIG3_MAP_LAND_EDGE, linewidth=0.40, zorder=0.4)
            ax._cartographic_land_paths.append(mpl.path.Path(np.column_stack([xs, ys])))
            plotted = True
    return plotted


def plot_satellite_background(ax: mpl.axes.Axes, bbox: tuple[float, float, float, float]) -> bool:
    ax.set_facecolor("#EEF2F4")
    mosaic = None
    for zoom in (8, 7, 6, 5):
        mosaic = satellite_mosaic(bbox[0], bbox[1], bbox[2], bbox[3], zoom=zoom, require_complete=zoom >= 6)
        if mosaic is not None:
            break
    if mosaic is None:
        return False

    image, extent = mosaic
    img = image.astype(float) / 255.0
    gray = img @ np.array([0.299, 0.587, 0.114])
    img = 0.88 * img + 0.12 * gray[..., None]
    img = np.clip(img * 0.90 + 0.10, 0.0, 1.0)
    ax._satellite_background = (img, extent)
    ax.imshow(
        img,
        extent=extent,
        origin="upper",
        interpolation="bilinear",
        alpha=1.0,
        zorder=0.1,
        clip_on=True,
    )
    return True


def relative_luminance(rgb: tuple[float, float, float] | np.ndarray) -> float:
    arr = np.asarray(rgb, dtype=float)
    return float(0.2126 * arr[0] + 0.7152 * arr[1] + 0.0722 * arr[2])


def contrast_line_color(rgb: tuple[float, float, float] | np.ndarray) -> str:
    return "#1F2429" if relative_luminance(rgb) > 0.54 else "white"


def composite_rgb(foreground: tuple[float, float, float] | np.ndarray, background: tuple[float, float, float] | np.ndarray, alpha: float) -> np.ndarray:
    fg = np.asarray(foreground, dtype=float)
    bg = np.asarray(background, dtype=float)
    return alpha * fg + (1.0 - alpha) * bg


def satellite_rgb_at(ax: mpl.axes.Axes, lon: float, lat: float) -> np.ndarray:
    satellite = getattr(ax, "_satellite_background", None)
    if satellite is None:
        return np.array(mpl.colors.to_rgb("#EEF2F4"))
    image, extent = satellite
    west, east, south, north = extent
    if not (west <= lon <= east and south <= lat <= north):
        return np.array(mpl.colors.to_rgb("#EEF2F4"))
    height, width = image.shape[:2]
    col = int(np.clip((lon - west) / (east - west) * (width - 1), 0, width - 1))
    row = int(np.clip((north - lat) / (north - south) * (height - 1), 0, height - 1))
    return np.asarray(image[row, col, :3], dtype=float)


def map_background_rgb_at(ax: mpl.axes.Axes, lon: float, lat: float) -> np.ndarray:
    land_paths = getattr(ax, "_cartographic_land_paths", [])
    for path in land_paths:
        if path.contains_point((lon, lat)):
            return np.array(mpl.colors.to_rgb(FIG3_MAP_LAND))
    satellite = getattr(ax, "_satellite_background", None)
    if satellite is not None:
        return satellite_rgb_at(ax, lon, lat)
    return np.array(mpl.colors.to_rgb(FIG3_MAP_OCEAN))


def sample_grid_value_at(lon_grid: np.ndarray, lat_grid: np.ndarray, value_grid: np.ndarray, lon: float, lat: float) -> float:
    valid = np.isfinite(lon_grid) & np.isfinite(lat_grid) & np.isfinite(value_grid)
    if not np.any(valid):
        return float("nan")
    distances = np.where(valid, (lon_grid - lon) ** 2 + (lat_grid - lat) ** 2, np.inf)
    idx = np.unravel_index(int(np.nanargmin(distances)), distances.shape)
    if not np.isfinite(distances[idx]) or distances[idx] > 1.0:
        return float("nan")
    return float(value_grid[idx])


def plot_adaptive_horizontal_dashes(
    ax: mpl.axes.Axes,
    y: float,
    x_min: float,
    x_max: float,
    color_at: Callable[[float, float], str],
    *,
    linewidth: float,
    dash_length: float = 0.42,
    gap_length: float = 0.28,
    alpha: float = 0.92,
    zorder: float = 8.8,
) -> None:
    x0 = x_min
    while x0 < x_max:
        x1 = min(x0 + dash_length, x_max)
        mid = 0.5 * (x0 + x1)
        color = color_at(mid, y)
        ax.plot([x0, x1], [y, y], color=color, linewidth=linewidth, alpha=alpha, solid_capstyle="butt", zorder=zorder)
        x0 += dash_length + gap_length


def plot_sober_land_outlines(
    ax: mpl.axes.Axes,
    bbox: tuple[float, float, float, float],
    *,
    zorder: float = 4.6,
    linewidth: float = 0.36,
    color: str = "#3E464D",
) -> bool:
    land = natural_earth_land_geojson()
    if land is None:
        return False
    plotted = False
    for feature in land.get("features", []):
        geometry = feature.get("geometry") or {}
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []
        polygons = coordinates if geom_type == "MultiPolygon" else [coordinates] if geom_type == "Polygon" else []
        for polygon in polygons:
            if not polygon:
                continue
            exterior = polygon[0]
            if not ring_intersects_bbox(exterior, bbox):
                continue
            xs = [pt[0] for pt in exterior]
            ys = [pt[1] for pt in exterior]
            ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=0.82, zorder=zorder, clip_on=True)
            plotted = True
    return plotted


def add_south_america_locator_inset(ax: mpl.axes.Axes, map_bbox: tuple[float, float, float, float]) -> None:
    inset_bbox = (-86.0, -33.0, -58.0, 13.0)
    inset = ax.inset_axes([0.055, 0.515, 0.30, 0.30])
    has_land = plot_sober_land_background(inset, inset_bbox)
    if not has_land:
        inset.set_facecolor(FIG3_MAP_OCEAN)
        inset.axvspan(-86.0, -68.0, color=FIG3_MAP_OCEAN, zorder=0.2)
        inset.axvspan(-68.0, -33.0, color=FIG3_MAP_LAND, zorder=0.2)
    rect = Rectangle(
        (map_bbox[0], map_bbox[2]),
        map_bbox[1] - map_bbox[0],
        map_bbox[3] - map_bbox[2],
        facecolor="none",
        edgecolor="#D61C5B",
        linewidth=0.82,
        zorder=5,
    )
    inset.add_patch(rect)
    inset.set_xlim(inset_bbox[0], inset_bbox[1])
    inset.set_ylim(inset_bbox[2], inset_bbox[3])
    inset.set_aspect(1 / math.cos(math.radians(-25.0)))
    inset.set_xticks([])
    inset.set_yticks([])
    set_four_sided_axis(inset, linewidth=0.62, color="#1F2429")
    inset.set_clip_on(True)


def finish_geo_map_axis(
    ax: mpl.axes.Axes,
    bbox: tuple[float, float, float, float],
    *,
    show_ylabel: bool = True,
) -> None:
    ax.set_xlim(bbox[0], bbox[1])
    ax.set_ylim(bbox[2], bbox[3])
    ax.set_aspect(1 / math.cos(math.radians(-30.0)), adjustable="box")
    ax.set_anchor("C")
    ax.set_xlabel("Longitud", fontsize=FIG3_AXIS_LABEL_SIZE, labelpad=1.5)
    ax.set_ylabel("Latitud" if show_ylabel else "", fontsize=FIG3_AXIS_LABEL_SIZE, labelpad=1.5)
    ax.set_xticks([-80, -70])
    ax.set_yticks([-40, -30, -20])
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(format_lon_w))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(format_lat_s))
    ax.tick_params(
        axis="both",
        labelsize=FIG3_TICK_LABEL_SIZE,
        colors=TEXT_GRAY,
        length=2.8,
        width=0.72,
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        direction="out",
    )
    ax.tick_params(axis="y", labelleft=show_ylabel)
    ax.grid(False)
    set_four_sided_axis(ax, linewidth=0.65)


def synchronize_geo_map_axes(
    ax_left: mpl.axes.Axes,
    ax_right: mpl.axes.Axes,
    bbox: tuple[float, float, float, float],
) -> None:
    for ax in (ax_left, ax_right):
        ax.set_xlim(bbox[0], bbox[1])
        ax.set_ylim(bbox[2], bbox[3])
        ax.set_xticks([-80, -70])
        ax.set_yticks([-40, -30, -20])
        ax.set_aspect(1 / math.cos(math.radians(-30.0)), adjustable="box")
        ax.set_anchor("C")
    ax_left.figure.canvas.draw()
    left_pos = ax_left.get_position()
    right_pos = ax_right.get_position()
    ax_right.set_position([right_pos.x0, left_pos.y0, left_pos.width, left_pos.height])


def plot_slab_depth_map(
    ax: mpl.axes.Axes,
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    depth_grid: np.ndarray,
    bbox: tuple[float, float, float, float],
) -> None:
    plot_sober_land_background(ax, bbox)

    in_bbox = (
        (lon_grid >= bbox[0])
        & (lon_grid <= bbox[1])
        & (lat_grid >= bbox[2])
        & (lat_grid <= bbox[3])
        & np.isfinite(depth_grid)
    )
    local_depth = depth_grid[in_bbox]
    depth_upper = 700.0
    levels = np.arange(0.0, depth_upper + 50.0, 50.0)
    depth_norm = mpl.colors.Normalize(vmin=0.0, vmax=depth_upper, clip=True)
    depth_cmap = load_batlow_light_start()
    filled = ax.pcolormesh(
        lon_grid,
        lat_grid,
        depth_grid,
        cmap=depth_cmap,
        norm=depth_norm,
        shading="auto",
        alpha=0.93,
        zorder=1,
        rasterized=True,
    )
    slab_extent = np.where(np.isfinite(depth_grid), 1.0, 0.0)
    ax.contour(
        lon_grid,
        lat_grid,
        slab_extent,
        levels=[0.5],
        colors="#1F2429",
        linewidths=0.65,
        linestyles="-",
        zorder=2.7,
    )
    contours = ax.contour(
        lon_grid,
        lat_grid,
        depth_grid,
        levels=levels[1:],
        colors="#626B73",
        linewidths=0.48,
        linestyles="--",
        alpha=0.88,
        zorder=2,
    )
    label_levels = [level for level in (50.0, 100.0, 150.0) if level in levels]
    labels = ax.clabel(
        contours,
        levels=label_levels,
        fmt=lambda value: f"{int(value)}",
        fontsize=5.6,
        inline=True,
        inline_spacing=-3.0,
    )
    remove_overlapping_texts(ax.figure, labels, pad_x=1.01, pad_y=1.04)
    for text in labels:
        if text.axes is None:
            continue
        try:
            label_value = float(text.get_text())
        except ValueError:
            label_value = 0.0
        text.set_color("#E8ECEF" if label_value >= 360 else "#2F3438")
        text.set_path_effects([])

    def slab_santiago_line_color(lon: float, lat: float) -> str:
        background = map_background_rgb_at(ax, lon, lat)
        depth = sample_grid_value_at(lon_grid, lat_grid, depth_grid, lon, lat)
        if np.isfinite(depth):
            background = composite_rgb(depth_cmap(depth_norm(depth))[:3], background, 0.93)
        return contrast_line_color(background)

    plot_adaptive_horizontal_dashes(ax, SANTIAGO_LAT, bbox[0], bbox[1], slab_santiago_line_color, linewidth=0.72, alpha=0.92, zorder=8.8)
    finish_geo_map_axis(ax, bbox, show_ylabel=True)
    add_south_america_locator_inset(ax, bbox)

    cax = ax.inset_axes([0.045, 0.055, 0.040, 0.27])
    cbar = ax.figure.colorbar(filled, cax=cax, orientation="vertical")
    cbar.set_ticks([tick for tick in np.arange(0, 701, 100) if levels[0] <= tick <= levels[-1]])
    cbar.ax.tick_params(labelsize=5.4, colors="#111111", labelcolor="#111111", length=1.8, width=0.45, pad=1.0)
    cbar.set_label("km", fontsize=6.0, color="#111111", labelpad=0.5)
    for tick_label in cbar.ax.get_yticklabels():
        tick_label.set_path_effects([])
    cbar.ax.yaxis.label.set_path_effects([])
    set_four_sided_axis(cax, linewidth=0.45, color="#111111")


def plot_depth_contours(
    ax: mpl.axes.Axes,
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    depth_grid: np.ndarray,
    *,
    label: bool,
) -> tuple[mpl.contour.QuadContourSet, mpl.contour.QuadContourSet]:
    minor_levels = np.arange(200, 651, 50)
    major_levels = np.arange(200, 651, 100)
    minor = ax.contour(lon_grid, lat_grid, depth_grid, levels=minor_levels, colors="#8F969E", linewidths=0.45, alpha=0.72, zorder=1.2)
    major = ax.contour(lon_grid, lat_grid, depth_grid, levels=major_levels, colors="#30343A", linewidths=0.85, alpha=0.88, zorder=1.3)
    if label:
        labels = ax.clabel(major, levels=[100, 300, 500], fmt=lambda v: f"{int(v)} km", fontsize=6.7, inline=True)
        for text in labels:
            text.set_color("#30343A")
            text.set_path_effects([pe.withStroke(linewidth=1.6, foreground="white")])
    return minor, major


def plot_zone_label(ax: mpl.axes.Axes, lon: float, lat: float, zone_idx: int, color: str, *, size: float = 8.0) -> None:
    ax.text(
        lon,
        lat,
        str(zone_idx),
        ha="center",
        va="center",
        fontsize=size,
        fontweight="bold",
        color=readable_label_color(color),
        zorder=5,
        bbox=dict(boxstyle="circle,pad=0.22", facecolor=color, edgecolor="#1F2429", linewidth=0.55),
    )


def plot_named_source_label(ax: mpl.axes.Axes, x: float, y: float, label: str, color: str, *, size: float = 7.6) -> None:
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=size,
        fontweight="bold",
        color=readable_label_color(color),
        zorder=7,
        bbox=dict(boxstyle="round,pad=0.22,rounding_size=0.18", facecolor=color, edgecolor="#1F2429", linewidth=0.55),
    )


def add_panel_label(
    ax: mpl.axes.Axes,
    label: str,
    *,
    x: float = 0.025,
    y: float = 0.975,
    ha: str = "left",
    va: str = "top",
    color: str = TEXT_GRAY,
    boxed: bool = True,
) -> None:
    bbox = (
        dict(boxstyle="round,pad=0.12,rounding_size=0.08", facecolor="white", edgecolor="none", alpha=0.88)
        if boxed
        else None
    )
    effects = [pe.withStroke(linewidth=1.0, foreground="#1F2429")] if (not boxed and relative_luminance(mpl.colors.to_rgb(color)) > 0.70) else []
    ax.text(
        x,
        y,
        f"({label})",
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=7.8,
        fontweight="bold",
        color=color,
        zorder=40,
        bbox=bbox,
        path_effects=effects,
    )


def load_santiago_relief_profile() -> pd.DataFrame | None:
    if not RELIEF_PROFILE_CSV.exists():
        return None
    profile = pd.read_csv(RELIEF_PROFILE_CSV)
    required = {"x_santiago_km", "relief_m", "lat", "lon"}
    if not required.issubset(profile.columns):
        raise RuntimeError(f"Perfil de relieve incompleto: {as_posix(RELIEF_PROFILE_CSV)}")
    return profile


FIG3_AXIS_LABEL_SIZE = 8.8
FIG3_TICK_LABEL_SIZE = 8.0
FIG3_PROFILE_YLABEL_X = -0.115


def format_profile_depth_tick(value: float, _pos: int | None = None) -> str:
    if math.isclose(value, -0.5, abs_tol=0.05):
        return "0"
    if abs(value - round(value)) < 0.05:
        return f"{int(round(value))}"
    return f"{value:.1f}"


def format_elevation_tick(value: float, _pos: int | None = None) -> str:
    if abs(value - round(value)) < 0.05:
        return f"{int(round(value))}"
    return f"{value:.1f}"


def plot_relief_profile_panel(
    ax: mpl.axes.Axes,
    profile: pd.DataFrame,
    *,
    bottom_depth_km: float | None = None,
    show_xlabel: bool = True,
) -> None:
    x = profile["x_santiago_km"].to_numpy(dtype=float)
    elevation_km = profile["relief_m"].to_numpy(dtype=float) / 1000.0
    ax.fill_between(x, elevation_km, 0.0, where=elevation_km < 0, color=FIG3_MAP_OCEAN, alpha=0.78, linewidth=0, zorder=1)
    ax.fill_between(x, 0.0, elevation_km, where=elevation_km >= 0, color=FIG3_MAP_LAND, alpha=0.86, linewidth=0, zorder=1)
    ax.plot(x, elevation_km, color="#30343A", linewidth=0.86, zorder=2)
    ax.axhline(0.0, color="#6F7780", linewidth=0.62, zorder=3)
    ax.set_ylabel("Elevación (km)", fontsize=FIG3_AXIS_LABEL_SIZE, labelpad=1.2)
    ax.set_xlabel("Distancia E-O desde Santiago (km)" if show_xlabel else "", fontsize=FIG3_AXIS_LABEL_SIZE, labelpad=1.0)
    ax.tick_params(
        axis="both",
        labelsize=FIG3_TICK_LABEL_SIZE,
        colors=TEXT_GRAY,
        length=2.2,
        width=0.62,
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        direction="out",
    )
    ax.yaxis.set_label_coords(FIG3_PROFILE_YLABEL_X, 0.5)
    ax.grid(False)
    y_bottom = -abs(float(bottom_depth_km)) if bottom_depth_km is not None else math.floor(float(np.nanmin(elevation_km)) - 0.1)
    y_top = math.ceil(float(np.nanmax(elevation_km)) + 0.1)
    ax.set_ylim(y_bottom, y_top)
    y_ticks = [tick for tick in [-9, -6, -3, 0, 3, 6, 9] if y_bottom <= tick <= y_top]
    if bottom_depth_km is not None and not any(abs(tick - y_bottom) < 0.05 for tick in y_ticks):
        y_ticks.append(float(y_bottom))
    ax.set_yticks(sorted(y_ticks))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(format_elevation_tick))
    set_four_sided_axis(ax, linewidth=0.62)


def relief_at_x(profile: pd.DataFrame, x_target: float) -> float:
    profile_sorted = profile.sort_values("x_santiago_km")
    x = profile_sorted["x_santiago_km"].to_numpy(dtype=float)
    relief_km = profile_sorted["relief_m"].to_numpy(dtype=float) / 1000.0
    return float(np.interp(x_target, x, relief_km))


def surface_depth_at_x(profile: pd.DataFrame, x_target: float) -> float:
    return -relief_at_x(profile, x_target)


SANTIAGO_LON = -70.66246
SANTIAGO_LAT = -33.45891
SANTIAGO_SURFACE_DEPTH_KM = -0.567
SANTIAGO_PROFILE_MARKER_DEPTH_KM = -12.0
FSR_PROFILE_START_DEPTH_KM = -0.5


def slab_profile_at_latitude(
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    depth_grid: np.ndarray,
    target_lat: float,
) -> tuple[np.ndarray, np.ndarray, float]:
    lat_values = lat_grid[:, 0]
    order = np.argsort(lat_values)
    lat_sorted = lat_values[order]
    depth_sorted = depth_grid[order, :]
    profile_depth = np.array(
        [np.interp(target_lat, lat_sorted, depth_sorted[:, col]) for col in range(depth_sorted.shape[1])],
        dtype=float,
    )
    return lon_grid[0, :], profile_depth, target_lat


def segment_crossings_at_latitude(segment: np.ndarray, target_lat: float) -> list[tuple[float, float]]:
    crossings: list[tuple[float, float]] = []
    for start, end in zip(segment[:-1], segment[1:]):
        lat0, lat1 = float(start[1]), float(end[1])
        if lat0 == lat1:
            if math.isclose(lat0, target_lat, abs_tol=1e-6):
                crossings.append((float(np.nanmean([start[0], end[0]])), float(np.nanmean([start[2], end[2]]))))
            continue
        if (target_lat - lat0) * (target_lat - lat1) > 0:
            continue
        t = (target_lat - lat0) / (lat1 - lat0)
        if 0.0 <= t <= 1.0:
            lon = float(start[0] + t * (end[0] - start[0]))
            depth = float(start[2] + t * (end[2] - start[2]))
            crossings.append((lon, depth))
    return crossings


def zone_contours_at_interval(zone_geometry: list[np.ndarray], interval_km: float = 10.0) -> list[tuple[float, np.ndarray]]:
    mean_depths = np.array([float(np.nanmean(segment[:, 2])) for segment in zone_geometry])
    min_level = int(math.ceil(float(np.nanmin(mean_depths)) / interval_km) * interval_km)
    max_level = int(math.floor(float(np.nanmax(mean_depths)) / interval_km) * interval_km)
    selected: list[tuple[float, np.ndarray]] = []
    used: set[int] = set()
    for level in np.arange(min_level, max_level + interval_km * 0.5, interval_km):
        order = np.argsort(np.abs(mean_depths - level))
        for idx in order:
            idx_int = int(idx)
            if idx_int not in used:
                selected.append((float(level), zone_geometry[idx_int]))
                used.add(idx_int)
                break
    return selected


def zone_surface_polygon(zone_geometry: list[np.ndarray]) -> np.ndarray | None:
    if not zone_geometry:
        return None
    mean_depths = np.array([float(np.nanmean(segment[:, 2])) for segment in zone_geometry])
    shallow = zone_geometry[int(np.nanargmin(mean_depths))]
    deep = zone_geometry[int(np.nanargmax(mean_depths))]
    polygon = np.vstack([shallow[:, :2], deep[::-1, :2]])
    valid = np.isfinite(polygon).all(axis=1)
    polygon = polygon[valid]
    return polygon if len(polygon) >= 3 else None


def polygon_center_lon_at_lat(polygon: np.ndarray, target_lat: float, fallback_lon: float) -> float:
    crossings: list[float] = []
    closed = np.vstack([polygon, polygon[0]])
    for start, end in zip(closed[:-1], closed[1:]):
        lon0, lat0 = float(start[0]), float(start[1])
        lon1, lat1 = float(end[0]), float(end[1])
        if math.isclose(lat0, lat1, abs_tol=1e-10):
            if math.isclose(lat0, target_lat, abs_tol=1e-8):
                crossings.extend([lon0, lon1])
            continue
        if (target_lat - lat0) * (target_lat - lat1) > 0:
            continue
        t = (target_lat - lat0) / (lat1 - lat0)
        if 0.0 <= t <= 1.0:
            crossings.append(lon0 + t * (lon1 - lon0))
    if len(crossings) < 2:
        return fallback_lon
    return float((min(crossings) + max(crossings)) / 2.0)


def read_nrml_poslist(pos_list: ET.Element | None) -> np.ndarray | None:
    if pos_list is None or not pos_list.text:
        return None
    points = np.array(pos_list.text.strip().split(), dtype=float).reshape(-1, 3)
    return points if np.all(np.isfinite(points)) else None


def interpolate_point_at_latitude(a: np.ndarray, b: np.ndarray, target_lat: float) -> np.ndarray | None:
    lat0, lat1 = float(a[1]), float(b[1])
    if math.isclose(lat0, lat1, abs_tol=1e-12):
        if math.isclose(lat0, target_lat, abs_tol=1e-8):
            return (a + b) / 2.0
        return None
    if (target_lat - lat0) * (target_lat - lat1) > 0:
        return None
    t = (target_lat - lat0) / (lat1 - lat0)
    if not (-1e-9 <= t <= 1.0 + 1e-9):
        return None
    return a + t * (b - a)


def fsr_profile_at_latitude(path: Path, target_lat: float) -> list[np.ndarray]:
    if not path.exists():
        return []
    ns = {"nrml": "http://openquake.org/xmlns/nrml/0.5", "gml": "http://www.opengis.net/gml"}
    root = ET.parse(path).getroot()
    profile_segments: list[np.ndarray] = []
    for kite_surface in root.findall(".//nrml:kiteSurface", ns):
        profiles = kite_surface.findall(".//nrml:profile", ns)
        if len(profiles) < 2:
            continue
        edge_points: list[np.ndarray] = []
        for profile in profiles[:2]:
            points = read_nrml_poslist(profile.find(".//gml:posList", ns))
            if points is None or len(points) < 2:
                edge_points = []
                break
            edge_points.extend([points[0], points[-1]])
        if len(edge_points) != 4:
            continue
        top_a, bottom_a, top_b, bottom_b = edge_points
        quad = [top_a, top_b, bottom_b, bottom_a]
        crossings: list[np.ndarray] = []
        for start, end in zip(quad, quad[1:] + quad[:1]):
            point = interpolate_point_at_latitude(start, end, target_lat)
            if point is None:
                continue
            if not any(np.linalg.norm(point - existing) < 1e-7 for existing in crossings):
                crossings.append(point)
        if len(crossings) >= 2:
            segment = np.vstack(crossings[:2])
            profile_segments.append(segment[np.argsort(segment[:, 2])])
    return profile_segments


def generate_subduction_model() -> None:
    nrml_files = [SUBDUCTION_NRML_DIR / f"Zona{i}.nrml" for i in range(1, 8)]
    missing = [path for path in nrml_files if not path.exists()]
    if missing:
        raise FileNotFoundError("Faltan NRML de subduccion: " + ", ".join(as_posix(path) for path in missing))

    fault_geometries = [parse_nrml_fault_geometry(path) for path in nrml_files]
    if not all(fault_geometries):
        raise RuntimeError("No se encontraron geometrias validas en todos los NRML de subduccion.")

    lon_grid, lat_grid, depth_grid = load_subduction_surface()
    valid_mask = np.isfinite(lon_grid) & np.isfinite(lat_grid) & np.isfinite(depth_grid)
    lon_valid = lon_grid[valid_mask]
    lat_valid = lat_grid[valid_mask]
    depth_valid = depth_grid[valid_mask]

    bbox = (-80.5, -64.0, -44.8, -15.2)
    zone_colors = get_subduction_zone_palette()
    profile_lon, profile_depth, profile_lat = slab_profile_at_latitude(lon_grid, lat_grid, depth_grid, SANTIAGO_LAT)
    profile_mask = np.isfinite(profile_lon) & np.isfinite(profile_depth)
    profile_x, _ = lonlat_to_local_km(profile_lon[profile_mask], np.full(np.count_nonzero(profile_mask), profile_lat), SANTIAGO_LON, SANTIAGO_LAT)
    profile_y = profile_depth[profile_mask]
    fsr_profile_segments = fsr_profile_at_latitude(FSR_RUPTURE_XML, SANTIAGO_LAT)
    relief_profile = load_santiago_relief_profile()

    fig = plt.figure(figsize=(7.05, 3.42), constrained_layout=False)
    outer = fig.add_gridspec(1, 2, width_ratios=[1.64, 1.30], wspace=0.22)
    map_gs = outer[0, 0].subgridspec(1, 2, wspace=0.055)
    if relief_profile is None:
        ax_slab = fig.add_subplot(map_gs[0, 0])
        ax_map = fig.add_subplot(map_gs[0, 1], sharex=ax_slab, sharey=ax_slab)
        ax_profile = fig.add_subplot(outer[0, 1])
        ax_relief = None
    else:
        profile_gs = outer[0, 1].subgridspec(2, 1, height_ratios=[0.34, 0.66], hspace=0.14)
        ax_slab = fig.add_subplot(map_gs[0, 0])
        ax_map = fig.add_subplot(map_gs[0, 1], sharex=ax_slab, sharey=ax_slab)
        ax_relief = fig.add_subplot(profile_gs[0, 0])
        ax_profile = fig.add_subplot(profile_gs[1, 0], sharex=ax_relief)

    fsr_depth_profile_segments: list[tuple[np.ndarray, np.ndarray]] = []
    fsr_profile_top_depth = FSR_PROFILE_START_DEPTH_KM
    if relief_profile is not None:
        for fsr_segment in fsr_profile_segments:
            fsr_x, _ = lonlat_to_local_km(fsr_segment[:, 0], fsr_segment[:, 1], SANTIAGO_LON, SANTIAGO_LAT)
            fsr_y = fsr_segment[:, 2].astype(float).copy()
            if len(fsr_y):
                top_idx = int(np.nanargmin(fsr_y))
                fsr_y[top_idx] = FSR_PROFILE_START_DEPTH_KM
            fsr_depth_profile_segments.append((fsr_x, fsr_y))

    plot_slab_depth_map(ax_slab, lon_grid, lat_grid, depth_grid, bbox)

    plot_sober_land_background(ax_map, bbox)

    zone_polygons_for_line: list[tuple[np.ndarray, str]] = []
    for zone_idx, (zone_geometry, color) in enumerate(zip(fault_geometries, zone_colors), start=1):
        polygon = zone_surface_polygon(zone_geometry)
        if polygon is not None:
            zone_polygons_for_line.append((polygon, color))
            ax_map.fill(
                polygon[:, 0],
                polygon[:, 1],
                facecolor=color,
                edgecolor="#1F2429",
                linewidth=0.55,
                alpha=0.96,
                zorder=4,
            )
        lon_c, lat_c, dep_c = zone_centroid(zone_geometry)
        label_lat_offsets = {2: 0.95, 4: 0.35}
        label_lat = lat_c + label_lat_offsets.get(zone_idx, 0.0)
        label_lon = polygon_center_lon_at_lat(polygon, label_lat, lon_c) if polygon is not None else lon_c
        plot_zone_label(ax_map, label_lon, label_lat, zone_idx, color, size=9.8)

    def zones_santiago_line_color(lon: float, lat: float) -> str:
        background = map_background_rgb_at(ax_map, lon, lat)
        for polygon, color in zone_polygons_for_line:
            if mpl.path.Path(polygon[:, :2]).contains_point((lon, lat)):
                background = composite_rgb(mpl.colors.to_rgb(color), background, 0.96)
                break
        return contrast_line_color(background)

    plot_adaptive_horizontal_dashes(ax_map, SANTIAGO_LAT, bbox[0], bbox[1], zones_santiago_line_color, linewidth=0.82, alpha=0.94, zorder=8.8)
    ax_map.scatter(
        [SANTIAGO_LON],
        [SANTIAGO_LAT],
        marker="*",
        s=92,
        facecolor="#F2C94C",
        edgecolor="#1F2429",
        linewidth=0.85,
        zorder=9.5,
    )
    ax_map.text(
        SANTIAGO_LON,
        SANTIAGO_LAT + 0.72,
        "Santiago",
        fontsize=8.7,
        fontweight="bold",
        color=TEXT_GRAY,
        ha="center",
        va="bottom",
        path_effects=[pe.withStroke(linewidth=2.0, foreground="white")],
        zorder=8,
    )

    finish_geo_map_axis(ax_map, bbox, show_ylabel=False)

    ax_profile.axhline(0.0, color="#8B9298", linewidth=0.72, alpha=0.78, zorder=2)

    zone_profile_extents: list[tuple[float, float]] = []
    for zone_idx, (zone_geometry, color) in enumerate(zip(fault_geometries, zone_colors), start=1):
        crossings: list[tuple[float, float]] = []
        for level, segment in zone_contours_at_interval(zone_geometry, interval_km=2.0):
            crossings.extend(segment_crossings_at_latitude(segment, SANTIAGO_LAT))
        if not crossings:
            continue
        xs_profile, _ = lonlat_to_local_km(
            np.array([lon for lon, _depth in crossings]),
            np.full(len(crossings), SANTIAGO_LAT),
            SANTIAGO_LON,
            SANTIAGO_LAT,
        )
        depths = np.array([depth for _lon, depth in crossings])
        order = np.argsort(xs_profile)
        x_ordered = xs_profile[order]
        y_ordered = depths[order]
        ax_profile.plot(x_ordered, y_ordered, color=color, linewidth=1.55, zorder=4)
        if zone_idx in (2, 7):
            zone_profile_extents.append((float(np.nanmin(x_ordered)), float(np.nanmax(x_ordered))))
        if len(x_ordered) >= 2:
            label_idx = int(round(0.54 * (len(x_ordered) - 1)))
            plot_zone_label(ax_profile, float(x_ordered[label_idx]), float(y_ordered[label_idx]), zone_idx, color, size=7.3)

    if ax_relief is None or relief_profile is None:
        fsr_depth_profile_segments = []
        for fsr_segment in fsr_profile_segments:
            fsr_x, _ = lonlat_to_local_km(fsr_segment[:, 0], fsr_segment[:, 1], SANTIAGO_LON, SANTIAGO_LAT)
            fsr_depth_profile_segments.append((fsr_x, fsr_segment[:, 2].astype(float)))

    for fsr_x, fsr_y in fsr_depth_profile_segments:
        ax_profile.plot(fsr_x, fsr_y, color=FSR_MAP_TRACE, linewidth=2.1, zorder=5)
        label_idx = int(round(0.62 * (len(fsr_x) - 1)))
        plot_named_source_label(ax_profile, float(fsr_x[label_idx] + 42.0), float(fsr_y[label_idx] + 2.0), "FSR", FSR_MAP_TRACE, size=7.5)

    ax_profile.set_xlabel("Distancia E-O desde Santiago (km)", fontsize=FIG3_AXIS_LABEL_SIZE, labelpad=1.5)
    ax_profile.set_ylabel("Profundidad (km)", fontsize=FIG3_AXIS_LABEL_SIZE, labelpad=1.5)
    if zone_profile_extents:
        x_left = min(left for left, _right in zone_profile_extents)
        x_right = max(right for _left, right in zone_profile_extents)
    else:
        x_left = float(np.nanmin(profile_x))
        x_right = float(np.nanmax(profile_x))
    ax_profile.set_xlim(x_left, x_right)
    depth_limit = math.ceil((float(np.nanmax(profile_y)) + 28.0) / 25.0) * 25.0
    profile_top_depth = fsr_profile_top_depth if ax_relief is not None else FSR_PROFILE_START_DEPTH_KM
    ax_profile.set_ylim(depth_limit, profile_top_depth)
    x_range = x_right - x_left
    x_tick_step = 100 if x_range <= 520 else 150
    x_ticks = np.arange(math.ceil(x_left / x_tick_step) * x_tick_step, math.floor(x_right / x_tick_step) * x_tick_step + 0.1, x_tick_step)
    ax_profile.set_xticks(x_ticks)
    y_ticks = [profile_top_depth] + [tick for tick in np.arange(50, depth_limit + 1, 50) if profile_top_depth < tick <= depth_limit]
    ax_profile.set_yticks(y_ticks)
    ax_profile.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(format_profile_depth_tick))
    ax_profile.tick_params(
        axis="both",
        labelsize=FIG3_TICK_LABEL_SIZE,
        colors=TEXT_GRAY,
        length=2.8,
        width=0.72,
        top=True,
        right=True,
        labeltop=False,
        labelright=False,
        direction="out",
    )
    ax_profile.yaxis.set_label_coords(FIG3_PROFILE_YLABEL_X, 0.5)
    surface_depth_at_santiago = surface_depth_at_x(relief_profile, 0.0) if relief_profile is not None else 0.0
    elevation_at_santiago = relief_at_x(relief_profile, 0.0) if relief_profile is not None else 0.0
    ax_profile.vlines(0.0, ymin=surface_depth_at_santiago, ymax=depth_limit, color="#1F2429", linewidth=0.82, linestyle=(0, (4, 3)), alpha=0.72, zorder=2.5)
    ax_profile.grid(False)
    set_four_sided_axis(ax_profile, linewidth=0.65)

    if ax_relief is not None and relief_profile is not None:
        plot_relief_profile_panel(ax_relief, relief_profile, show_xlabel=False)
        ax_relief.set_xlim(x_left, x_right)
        ax_relief.set_xticks(x_ticks)
        ax_relief.tick_params(axis="x", labelbottom=False, top=True)
        ax_relief.vlines(0.0, ymin=elevation_at_santiago, ymax=ax_relief.get_ylim()[0], color="#1F2429", linewidth=0.82, linestyle=(0, (4, 3)), alpha=0.72, zorder=4)

    fig.subplots_adjust(left=0.06, right=0.99, top=0.91, bottom=0.155)
    synchronize_geo_map_axes(ax_slab, ax_map, bbox)
    add_panel_label(ax_slab, "A", color="#111111", boxed=False)
    add_panel_label(ax_map, "B", color="#111111", boxed=False)
    if ax_relief is not None:
        add_panel_label(ax_relief, "C", x=0.982, y=0.955, ha="right")
        add_panel_label(ax_profile, "D", x=0.982, y=0.955, ha="right")
    else:
        add_panel_label(ax_profile, "C", x=0.014, y=0.955)

    remove_manifest_for_output(SUBDUCTION_MODEL_OUTPUT)
    save_plot(
        fig,
        SUBDUCTION_MODEL_OUTPUT,
        original_path="assets/figures/presentation/modelo_subduccion.pdf",
        slide="8",
        change="Regenerada desde NRML, matriz de subduccion, ruptura FSR y perfil GMT Earth Relief: agrega un mapa Slab2 a la izquierda con la misma extension del mapa de zonas, colormap batlow invertido para ubicar el extremo claro al inicio de la escala de profundidad, relleno y barra de colores continuos para profundidad Slab2 cerrados entre 0 y 700 km, borde externo solido oscuro de la superficie Slab2 con el mismo lenguaje grafico de los bordes de zonas, curvas de nivel grises segmentadas cada 50 km y tres cotas principales inline sin halo, con espacio de corte minimo alrededor del numero; los mapas principales y el minimapa usan el mismo fondo cartografico: mar celeste #8FB9C6 y continente gris #C4C8CB; la barra de color usa texto negro y queda bajo la linea segmentada de Santiago para no intersectarla; las zonas Poulos 1-7 se grafican como superficies uniformes coloreadas en planta usando los bordes superficial y profundo de cada zona, sin curvas ni relleno Slab2 de fondo; ambos mapas de planta comparten el eje X/Y y usan exactamente el mismo dominio longitudinal y latitudinal; el panel C usa la misma paleta del mapa para batimetria y relieve positivo; incorpora etiquetas de panel (A)-(D) para identificar cada mapa y perfil, con A y B en negro sin fondo y C y D en la esquina superior derecha interna; las etiquetas numeradas mantienen su latitud calculada y se centran longitudinalmente dentro de cada zona, con ajustes locales de las zonas 2 y 4 para evitar superposiciones; las coordenadas del mapa quedan en multiplos de 10 y se quitan las grillas de mapa y perfiles; todos los mapas y perfiles se dibujan con cuatro bordes visibles posicionados por encima de las capas y ticks en bordes superiores/derechos; la linea segmentada de Santiago se dibuja por tramos con color adaptativo blanco/gris oscuro segun el contraste local de la capa visible, por encima de las capas salvo la estrella; el perfil E-O usa la latitud real de Santiago, mantiene la superficie topo-batimetrica en el panel superior con eje Elevacion (km) y signo positivo hacia arriba, dibuja la FSR en el panel de profundidad y hace que tanto el eje como el punto superior de FSR partan en -0.5 km, equivalente a 500 m sobre el nivel 0, pero la etiqueta del eje se presenta como 0; quita titulos internos, unifica tamanos de texto de ejes/ticks y usa una etiqueta FSR con el mismo lenguaje grafico de las etiquetas numeradas de zonas, desplazada a la derecha para mejorar legibilidad.",
        source_data=(
            f"{as_posix(SUBDUCTION_NRML_DIR / 'Zona[1-7].nrml')}; "
            f"{as_posix(SUBDUCTION_MAT)} (superficie Slab2 para mapa de profundidad y perfil); "
            f"notebook: {as_posix(SUBDUCTION_NOTEBOOK)}; "
            f"{as_posix(FSR_RUPTURE_XML)}; "
            f"{as_posix(RELIEF_PROFILE_CSV)}; GMT Earth Relief 01m; "
            f"{as_posix(BATLOW_CMAP_FILE)}; "
            "Natural Earth 1:50m land GeoJSON para fondos cartograficos e inset regional; referencia visual de composicion: Hayes et al. 2018, DOI 10.1126/science.aat4723"
        ),
        limitation="El perfil de relieve se muestrea desde GMT Earth Relief 01m porque las grillas globales 15s y 30s son demasiado pesadas para el fallback directo sin GMT/PyGMT instalado; si no hay red disponible para Natural Earth, los mapas principales caen a un fondo neutro y se preservan zonas, perfil FSR, relieve y contornos.",
        png_dpi=600,
    )


def styled_svg_pdf(
    *,
    source: Path,
    output_name: str,
    original_path: str,
    slide: str,
    original_type: str,
    change: str,
    source_data: str | None = None,
    limitation: str = "",
    processor=None,
    font_scale: float = 1.14,
    min_font_px: float = 10.0,
    max_font_px: float = 17.0,
    min_stroke_width: float = 0.45,
) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    svg = source.read_text(encoding="utf-8", errors="ignore")
    if processor is not None:
        svg = processor(svg)
    svg = apply_presentation_svg_style(
        svg,
        font_scale=font_scale,
        min_font_px=min_font_px,
        max_font_px=max_font_px,
        min_stroke_width=min_stroke_width,
    )
    styled = SVG_DIR / f"{Path(output_name).stem}.svg"
    styled.write_text(svg, encoding="utf-8", newline="\n")
    pdf = PDF_DIR / output_name
    png = PNG_DIR / f"{Path(output_name).stem}.png"
    export_svg_to_pdf(styled, pdf, png)
    remove_manifest_for_output(output_name)
    text_tags = svg.count("<text")
    if text_tags == 0:
        limitation = (
            (limitation + " " if limitation else "")
            + "El SVG fuente no contiene texto editable; el texto ya viene convertido a trazos. "
            + "Se normalizan margen, salida vectorial y grosores, pero la familia tipografica requiere regenerar desde el notebook."
        )
    add_manifest(
        original_path=original_path,
        new_path=pdf,
        slide=slide,
        original_type=original_type,
        new_type="pdf/svg/png",
        change=change,
        source_data=source_data or as_posix(source),
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(styled)}",
        limitation=limitation,
    )


def wrapper_pdf(
    *,
    source: Path,
    output_name: str,
    original_path: str,
    slide: str,
    original_type: str,
    include_options: str = "width=6.2in,keepaspectratio",
    change: str = "Normalizada en PDF nuevo desde artefacto disponible, con ruta separada para la presentacion.",
    source_data: str | None = None,
    limitation: str = "No se encontraron datos crudos suficientes para redibujar fielmente; se conserva el contenido del artefacto disponible.",
) -> None:
    WRAPPER_BUILD.mkdir(parents=True, exist_ok=True)
    tex_path = WRAPPER_DIR / f"{Path(output_name).stem}.tex"
    write_wrapper_tex(tex_path, source, include_options)
    run_checked(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={WRAPPER_BUILD}",
            str(tex_path),
        ],
        cwd=REPO,
    )
    built = WRAPPER_BUILD / f"{tex_path.stem}.pdf"
    dest = PDF_DIR / output_name
    shutil.copy2(built, dest)
    png_prefix = PNG_DIR / Path(output_name).stem
    try:
        run_checked(["pdftoppm", "-f", "1", "-singlefile", "-png", "-r", "180", str(dest), str(png_prefix)], cwd=REPO)
    except Exception:
        pass
    try:
        export_svg_to_pdf  # keep linters quiet about the helper being in this module
        run_checked([str(INKSCAPE), str(dest), f"--export-filename={SVG_DIR / (Path(output_name).stem + '.svg')}"], cwd=REPO)
    except Exception:
        pass
    add_manifest(
        original_path=original_path,
        new_path=dest,
        slide=slide,
        original_type=original_type,
        new_type="pdf",
        change=change,
        source_data=source_data or as_posix(source),
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(tex_path)}",
        limitation=limitation,
    )


def make_styled_svg_pdf_asset(
    *,
    source: Path,
    stem: str,
    font_scale: float = 1.14,
    min_font_px: float = 10.0,
    max_font_px: float = 17.0,
    min_stroke_width: float = 0.45,
    processor=None,
) -> Path:
    if not source.exists():
        raise FileNotFoundError(source)
    raw_svg = WRAPPER_BUILD / f"{stem}_raw.svg"
    styled_svg = WRAPPER_BUILD / f"{stem}.svg"
    pdf = WRAPPER_BUILD / f"{stem}.pdf"
    run_checked([str(INKSCAPE), str(source), f"--export-filename={raw_svg}"], cwd=REPO)
    svg = raw_svg.read_text(encoding="utf-8", errors="ignore")
    svg = apply_presentation_svg_style(
        svg,
        font_scale=font_scale,
        min_font_px=min_font_px,
        max_font_px=max_font_px,
        min_stroke_width=min_stroke_width,
    )
    if processor is not None:
        svg = processor(svg)
    styled_svg.write_text(svg, encoding="utf-8", newline="\n")
    export_svg_to_pdf(styled_svg, pdf)
    return pdf


def write_composite_tex(tex_path: Path, chart_pdf: Path, map_pdf: Path, *, chart_width: str = "5.05in") -> None:
    chart_rel = rel_from_wrapper(chart_pdf)
    map_rel = rel_from_wrapper(map_pdf)
    tex = textwrap.dedent(
        rf"""
        \documentclass[border=0pt]{{standalone}}
        \usepackage{{graphicx}}
        \begin{{document}}
        \includegraphics[width={chart_width},keepaspectratio]{{{chart_rel}}}\hspace{{0.08in}}%
        \raisebox{{0.04in}}{{\includegraphics[width=1.52in,keepaspectratio]{{{map_rel}}}}}
        \end{{document}}
        """
    ).strip() + "\n"
    tex_path.write_text(tex, encoding="utf-8", newline="\n")


def write_overlay_map_tex(
    tex_path: Path,
    chart_pdf: Path,
    map_pdf: Path,
    *,
    chart_width: str = "6.35in",
    map_width: str = "1.22in",
    map_x: str = "3.38in",
    map_y: str = "0.82in",
) -> None:
    chart_rel = rel_from_wrapper(chart_pdf)
    map_rel = rel_from_wrapper(map_pdf)
    tex = textwrap.dedent(
        rf"""
        \documentclass[border=0pt]{{standalone}}
        \usepackage{{graphicx}}
        \usepackage{{tikz}}
        \begin{{document}}
        \begin{{tikzpicture}}
          \node[anchor=south west,inner sep=0] at (0,0) {{\includegraphics[width={chart_width},keepaspectratio]{{{chart_rel}}}}};
          \node[anchor=south west,inner sep=0] at ({map_x},{map_y}) {{\includegraphics[width={map_width},keepaspectratio]{{{map_rel}}}}};
        \end{{tikzpicture}}
        \end{{document}}
        """
    ).strip() + "\n"
    tex_path.write_text(tex, encoding="utf-8", newline="\n")


def build_composite_pdf(
    *,
    chart_pdf: Path,
    output_name: str,
    original_path: str,
    slide: str,
    change: str,
    source_data: str,
    limitation: str = "",
    chart_width: str = "5.05in",
) -> None:
    map_pdf = PDF_DIR / "qgis_site_map_control_sites.pdf"
    if not map_pdf.exists():
        raise FileNotFoundError(map_pdf)
    remove_manifest_for_output(output_name)
    tex_path = WRAPPER_DIR / f"{Path(output_name).stem}.tex"
    write_composite_tex(tex_path, chart_pdf, map_pdf, chart_width=chart_width)
    run_checked(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={WRAPPER_BUILD}",
            str(tex_path),
        ],
        cwd=REPO,
    )
    built = WRAPPER_BUILD / f"{tex_path.stem}.pdf"
    dest = PDF_DIR / output_name
    shutil.copy2(built, dest)
    png_prefix = PNG_DIR / Path(output_name).stem
    try:
        run_checked(["pdftoppm", "-f", "1", "-singlefile", "-png", "-r", "180", str(dest), str(png_prefix)], cwd=REPO)
    except Exception:
        pass
    try:
        run_checked([str(INKSCAPE), str(dest), f"--export-filename={SVG_DIR / (Path(output_name).stem + '.svg')}"], cwd=REPO)
    except Exception:
        pass
    add_manifest(
        original_path=original_path,
        new_path=dest,
        slide=slide,
        original_type="pdf",
        new_type="pdf",
        change=change,
        source_data=source_data,
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(QGIS_MAP_HELPER)}; {as_posix(tex_path)}",
        limitation=limitation,
    )


def build_overlay_map_pdf(
    *,
    chart_pdf: Path,
    output_name: str,
    original_path: str,
    slide: str,
    change: str,
    source_data: str,
    limitation: str = "",
) -> None:
    map_pdf = PDF_DIR / "qgis_site_map_control_sites.pdf"
    if not map_pdf.exists():
        raise FileNotFoundError(map_pdf)
    remove_manifest_for_output(output_name)
    tex_path = WRAPPER_DIR / f"{Path(output_name).stem}.tex"
    write_overlay_map_tex(tex_path, chart_pdf, map_pdf)
    run_checked(
        [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={WRAPPER_BUILD}",
            str(tex_path),
        ],
        cwd=REPO,
    )
    built = WRAPPER_BUILD / f"{tex_path.stem}.pdf"
    dest = PDF_DIR / output_name
    shutil.copy2(built, dest)
    png_prefix = PNG_DIR / Path(output_name).stem
    try:
        run_checked(["pdftoppm", "-f", "1", "-singlefile", "-png", "-r", "180", str(dest), str(png_prefix)], cwd=REPO)
    except Exception:
        pass
    add_manifest(
        original_path=original_path,
        new_path=dest,
        slide=slide,
        original_type="pdf",
        new_type="pdf",
        change=change,
        source_data=source_data,
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(QGIS_MAP_HELPER)}; {as_posix(tex_path)}",
        limitation=limitation,
    )


def read_mean_hcurve_zip(role: str, imt: str = "PGA") -> pd.DataFrame:
    zip_path = HCURVE_ZIPS[role]
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    pattern = f"hazard_curve-mean-{imt}"
    with zipfile.ZipFile(zip_path) as zf:
        names = [name for name in zf.namelist() if pattern in name and name.lower().endswith(".csv")]
        if not names:
            raise FileNotFoundError(f"No {pattern} CSV in {zip_path}")
        with zf.open(names[0], "r") as fh:
            df = pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8"), comment="#")
    cols = [col for col in df.columns if col.startswith("poe-")]
    if not {"lon", "lat", "depth"}.issubset(df.columns) or not cols:
        raise ValueError(f"Estructura inesperada en {zip_path.name}::{names[0]}")
    for col in ["lon", "lat", "depth", *cols]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def hcurve_columns(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    cols = [col for col in df.columns if col.startswith("poe-")]
    imls = np.array([float(col.replace("poe-", "")) for col in cols], dtype=float)
    order = np.argsort(imls)
    return imls[order], [cols[idx] for idx in order]


def hcurve_key(df: pd.DataFrame, digits: int = 5) -> pd.Series:
    return (
        df["lon"].round(digits).astype(str)
        + "|"
        + df["lat"].round(digits).astype(str)
        + "|"
        + df["depth"].round(digits).astype(str)
    )


def align_hcurve_frames(frames: list[pd.DataFrame]) -> tuple[list[pd.DataFrame], np.ndarray, list[str]]:
    imls, cols = hcurve_columns(frames[0])
    keyed = []
    common_keys: set[str] | None = None
    for df in frames:
        imls_i, cols_i = hcurve_columns(df)
        if not np.allclose(imls, imls_i):
            raise ValueError("Las grillas IML de las curvas no coinciden.")
        if cols_i != cols:
            df = df[["lon", "lat", "depth", *cols]].copy()
        keyed_df = df.copy()
        keyed_df["_key"] = hcurve_key(keyed_df)
        keyed.append(keyed_df)
        keys = set(keyed_df["_key"].tolist())
        common_keys = keys if common_keys is None else common_keys.intersection(keys)
    if not common_keys:
        raise ValueError("No hay sitios comunes entre curvas inter/intra/FSR.")
    ordered_keys = [key for key in keyed[0]["_key"].tolist() if key in common_keys]
    aligned = [
        df.set_index("_key").loc[ordered_keys].reset_index(drop=True).drop(columns=["_key"], errors="ignore")
        for df in keyed
    ]
    return aligned, imls, cols


def union_independent_poes(*poe_arrays: np.ndarray) -> np.ndarray:
    survival = np.ones_like(np.asarray(poe_arrays[0], dtype=float), dtype=float)
    for arr in poe_arrays:
        survival *= 1.0 - np.clip(np.asarray(arr, dtype=float), 0.0, 1.0)
    return np.clip(1.0 - survival, 0.0, 1.0)


def nonincreasing(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    return np.minimum.accumulate(y)


def iml_at_poe(imls: np.ndarray, poes: np.ndarray, target: float) -> float:
    x = np.asarray(imls, dtype=float)
    y = nonincreasing(np.asarray(poes, dtype=float))
    ok = (x > 0) & np.isfinite(x) & np.isfinite(y) & (y > 0)
    x, y = x[ok], y[ok]
    if x.size < 2 or not (np.nanmin(y) <= target <= np.nanmax(y)):
        return float("nan")
    idx = np.argsort(x)
    x, y = x[idx], y[idx]
    return float(np.exp(np.interp(np.log(target), np.log(y[::-1]), np.log(x[::-1]))))


def hazard_curve_payload(scheme: str) -> tuple[list[dict], str]:
    fsr_role = "poisson" if scheme == "Poisson" else "bpt"
    inter, intra, fsr = [read_mean_hcurve_zip(role, "PGA") for role in ["inter", "intra", fsr_role]]
    (inter, intra, fsr), imls, cols = align_hcurve_frames([inter, intra, fsr])
    source_data = "; ".join(as_posix(HCURVE_ZIPS[role]) for role in ["inter", "intra", fsr_role])
    payload = []
    for idx in range(len(inter)):
        y_inter = nonincreasing(inter.iloc[idx][cols].to_numpy(dtype=float))
        y_intra = nonincreasing(intra.iloc[idx][cols].to_numpy(dtype=float))
        y_fsr = nonincreasing(fsr.iloc[idx][cols].to_numpy(dtype=float))
        y_total = nonincreasing(union_independent_poes(y_inter, y_intra, y_fsr))
        payload.append(
            {
                "site_idx": idx + 1,
                "lon": float(inter.iloc[idx]["lon"]),
                "lat": float(inter.iloc[idx]["lat"]),
                "imls": imls,
                "inter": y_inter,
                "intra": y_intra,
                "fsr": y_fsr,
                "total": y_total,
                "x10": iml_at_poe(imls, y_total, 0.10),
                "x02": iml_at_poe(imls, y_total, 0.02),
            }
        )
    return payload, source_data


def apply_hcurve_axis_style(ax: mpl.axes.Axes) -> None:
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(1e-6, 1.0)
    ax.grid(True, which="major", color=GRID_GRAY, linewidth=0.58, alpha=0.75)
    ax.grid(True, which="minor", color=GRID_GRAY, linewidth=0.28, alpha=0.35)
    ax.tick_params(axis="both", which="both", direction="in", top=True, right=True, length=3.2, width=0.75, pad=1.8)
    ax.xaxis.set_major_locator(LogLocator(base=10.0, numticks=4))
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=7))
    ax.xaxis.set_major_formatter(LogFormatterMathtext(base=10.0))
    ax.yaxis.set_major_formatter(LogFormatterMathtext(base=10.0))
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color(TEXT_GRAY)


def render_qgis_map_axis(ax: mpl.axes.Axes) -> None:
    map_png = PNG_DIR / "qgis_site_map_control_sites.png"
    if not map_png.exists():
        raise FileNotFoundError(map_png)
    img = mpimg.imread(map_png)
    ax.imshow(img)
    ax.set_axis_off()


def generate_curve_with_qgis_map(scheme: str, output_name: str, old: str, slide: str) -> None:
    payload, source_data = hazard_curve_payload(scheme)
    fig, axes = plt.subplots(2, 3, figsize=(8.8, 5.7), gridspec_kw={"wspace": 0.32, "hspace": 0.36})
    ax_list = axes.ravel()
    fsr_label = f"FSR {scheme}"
    for ax, item in zip(ax_list[:5], payload):
        x = item["imls"]
        ax.plot(x, item["inter"], color=INTER_BLUE, linewidth=2.0, label="Interplaca")
        ax.plot(x, item["intra"], color=INTRA_GOLD, linewidth=2.0, label="Intraplaca")
        ax.plot(x, item["fsr"], color=TEAL, linewidth=2.0, linestyle="--", label=fsr_label)
        ax.plot(x, item["total"], color=FSR_RED, linewidth=2.55, label="Total")
        ax.axhline(0.10, color=CAPTION_GRAY, linestyle=(0, (5, 3)), linewidth=0.9, alpha=0.75)
        ax.axhline(0.02, color=CAPTION_GRAY, linestyle=(0, (2, 2)), linewidth=0.9, alpha=0.75)
        for target, key, marker, linestyle in [(0.10, "x10", "o", (0, (6, 4))), (0.02, "x02", "s", (0, (2, 3)))]:
            x_target = item[key]
            if np.isfinite(x_target) and x_target > 0:
                ax.axvline(x_target, color=FSR_RED, linestyle=linestyle, linewidth=1.25, alpha=0.88)
                ax.plot(x_target, target, marker=marker, markersize=5.2, markerfacecolor="white", markeredgecolor=FSR_RED, markeredgewidth=1.35)
        ax.set_xlim(float(np.nanmin(x)), float(np.nanmax(x)))
        ax.set_title(f"Sitio #{item['site_idx']}", color=TEXT_GRAY, fontweight="bold", pad=3)
        ax.set_xlabel("PGA [g]")
        ax.set_ylabel("PoE (50 anos)")
        apply_hcurve_axis_style(ax)

    render_qgis_map_axis(ax_list[5])
    handles, labels = ax_list[0].get_legend_handles_labels()
    handles.extend(
        [
            Line2D([0], [0], color=FSR_RED, linestyle=(0, (6, 4)), marker="o", markerfacecolor="white", label="PGA@10%"),
            Line2D([0], [0], color=FSR_RED, linestyle=(0, (2, 3)), marker="s", markerfacecolor="white", label="PGA@2%"),
        ]
    )
    fig.legend(handles, [h.get_label() for h in handles], loc="lower center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 0.02), columnspacing=1.0, handlelength=2.0)
    fig.suptitle(f"Curvas de amenaza PGA - {scheme}", color=UCHILE_BLUE, fontweight="bold", y=0.985)
    fig.subplots_adjust(left=0.07, right=0.99, top=0.90, bottom=0.14, wspace=0.32, hspace=0.36)
    remove_manifest_for_output(output_name)
    save_plot(
        fig,
        output_name,
        original_path=old,
        slide=slide,
        change="Regenerada desde ZIP de curvas hazard_curve-mean-PGA, manteniendo series interplaca, intraplaca, FSR, total, ejes log-log y umbrales PGA@10%/PGA@2%; el mapa de sitios se inserta desde layout QGIS satelital con marco cebra.",
        source_data=f"{source_data}; {as_posix(PNG_DIR / 'qgis_site_map_control_sites.png')}; notebook: {as_posix(MODELOS / 'hazard' / 'psha' / 'codigos_apoyo' / 'curvas_amenaza_sitios_interes.ipynb')}",
        limitation="Las curvas se reconstruyen desde los ZIP mean identificados por el notebook original; no se usa el SVG de tesis porque su tipografia viene convertida a trazos.",
    )


def make_disaggregation_chart_asset(imt: str, scheme: str, stem: str) -> Path:
    imt_dir = "PGA" if imt == "PGA" else "SA1_0"
    imt_key = "PGA" if imt == "PGA" else "SA1p0"
    table_path = (
        RESULTS
        / "hazard_curvas_y_desagg"
        / "tables"
        / "contribuciones"
        / imt_dir
        / scheme
        / f"tabla_contribuciones_{imt_dir}_{scheme}.csv"
    )
    table = read_csv_required(table_path)
    x = np.arange(len(table))
    labels = [f"S{int(i)}" for i in table["site_idx"]]
    source_labels = ["Interplaca", "Intraplaca", "FSR"]
    source_colors = [INTER_BLUE, INTRA_GOLD, FSR_RED]

    fig, axes = plt.subplots(1, 2, figsize=(7.45, 3.55), sharey=True)
    for ax, suffix, title in zip(axes, ["10", "02"], ["PoE 10% / 50 anos", "PoE 2% / 50 anos"]):
        bottom = np.zeros(len(table))
        for col, label, color in zip(contribution_columns(imt_key, suffix), source_labels, source_colors):
            vals = table[col].to_numpy(dtype=float) * 100.0
            ax.bar(x, vals, bottom=bottom, label=label, color=color, edgecolor="white", linewidth=0.45)
            bottom += vals
        ax.set_xticks(x, labels)
        ax.set_ylim(0, 102)
        ax.set_title(title, color=UCHILE_BLUE, fontweight="bold")
        ax.set_xlabel("Sitio de control")
        finish_axis(ax)
    axes[0].set_ylabel("Contribucion a la tasa [%]")
    axes[1].legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=3, frameon=False)
    fig.suptitle(f"Desagregacion por fuente: {imt}, modelo {scheme}", color=UCHILE_BLUE, fontweight="bold", y=1.02)
    fig.tight_layout(rect=[0, 0.12, 1, 0.93], w_pad=1.0)
    pdf = WRAPPER_BUILD / f"{stem}.pdf"
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return pdf


def generate_disaggregation_with_qgis_map(imt: str, scheme: str, output_name: str, old: str, slide: str) -> None:
    chart_pdf = make_disaggregation_chart_asset(imt, scheme, f"{Path(output_name).stem}_chart")
    imt_dir = "PGA" if imt == "PGA" else "SA1_0"
    table_path = (
        RESULTS
        / "hazard_curvas_y_desagg"
        / "tables"
        / "contribuciones"
        / imt_dir
        / scheme
        / f"tabla_contribuciones_{imt_dir}_{scheme}.csv"
    )
    build_composite_pdf(
        chart_pdf=chart_pdf,
        output_name=output_name,
        original_path=old,
        slide=slide,
        change="Regenerada como figura mixta: barras de contribucion desde tabla original y mapa de sitios exportado desde QGIS satelital con marco cebra y formato comun.",
        source_data=f"{as_posix(table_path)}; {as_posix(QGIS_DATA_DIR / 'control_sites.csv')}; {as_posix(QGIS_MAP_HELPER)}",
        limitation="El contenido numerico de barras proviene de la tabla identificada; el mapa de ubicacion se genera en QGIS con fondo satelital XYZ.",
        chart_width="5.10in",
    )


def normalize_wrapped_figures() -> None:
    wrapper_pdf(
        source=ASSETS_TEMPLATE / "uchile2.pdf",
        output_name="uchile2.pdf",
        original_path="assets/figures/template/departamentos/uchile2.pdf",
        slide="1",
        original_type="pdf",
        include_options="height=1.25cm,keepaspectratio",
        change="Copiada a la carpeta generada para que la presentacion no dependa de rutas antiguas de figuras.",
        limitation="Logo institucional; no se redibuja ni altera por identidad visual.",
    )
    wrapper_pdf(
        source=ASSETS_PRESENTATION / "trazas_fsr.png",
        output_name="trazas_fsr.pdf",
        original_path="assets/figures/presentation/trazas_fsr.png",
        slide="2",
        original_type="png",
        include_options="width=5.0in,keepaspectratio",
        change="Convertida a PDF generado y normalizada en carpeta separada.",
        limitation="Se conserva exactamente el contenido del PNG original; no se redibujan mapas, etiquetas ni escalas.",
    )
    for name, slide, width in [
        ("exposicion_composicion.pdf", "9", "5.9in"),
        ("fig_4_2_escenarios_simulados.pdf", "12", "5.0in"),
        ("dsha_inter_pga.pdf", "15", "3.55in"),
        ("dsha_fsr_pga.pdf", "15", "3.55in"),
        ("dsha_intra_pga.pdf", "15", "3.55in"),
        ("fig_5_18_psha_curvas_pga_poisson.pdf", "17", "5.9in"),
        ("fig_5_19_psha_curvas_pga_bpt.pdf", "Anexo", "5.9in"),
        ("fig_5_22_disagg_pga_poisson.pdf", "18", "5.9in"),
        ("fig_5_23_disagg_pga_bpt.pdf", "Anexo", "5.9in"),
        ("fig_5_25_disagg_sa10_bpt.pdf", "Anexo", "5.9in"),
        ("fig_5_30_perdidas_comuna_materialidad.pdf", "16", "5.9in"),
        ("anexo_convergencia_gmf_pga020.pdf", "Anexo", "4.4in"),
        ("anexo_convergencia_gmf_pga040.pdf", "Anexo", "4.4in"),
        ("fig_5_42_oep_relativo.pdf", "21", "4.1in"),
        ("fig_5_43_delta_lambda.pdf", "21", "4.1in"),
    ]:
        wrapper_pdf(
            source=ASSETS_PRESENTATION / name,
            output_name=name,
            original_path=f"assets/figures/presentation/{name}",
            slide=slide,
            original_type="pdf",
            include_options=f"width={width},keepaspectratio",
            limitation="Se conserva exactamente el contenido del PDF original: paneles, ejes, mapas, escalas, colores y leyendas.",
        )
    wrapper_pdf(
        source=ASSETS_PRESENTATION / "fig_5_41_aalr_cambio_rel_pct.pdf",
        output_name="fig_5_41_aalr_cambio_rel_pct.pdf",
        original_path="assets/figures/presentation/fig_5_41_aalr_cambio_rel_pct.pdf",
        slide="20",
        original_type="pdf",
        include_options="trim=5 20 10 30,clip,width=3.8in,keepaspectratio",
        change="Normalizada con el recorte que antes estaba en LaTeX y movida a PDF generado.",
        limitation="Se conserva exactamente el contenido visible en la slide original; el recorte aplicado es el mismo que antes estaba en LaTeX.",
    )

    vuln_sources = [
        (
            ASSETS_PRESENTATION / "anexo_vulnerabilidad_junemann.png",
            "anexo_vulnerabilidad_junemann.pdf",
            "assets/figures/presentation/anexo_vulnerabilidad_junemann.png",
        ),
        (
            ASSETS_PRESENTATION / "anexo_vulnerabilidad_cabrera.png",
            "anexo_vulnerabilidad_cabrera.pdf",
            "assets/figures/presentation/anexo_vulnerabilidad_cabrera.png",
        ),
        (
            ASSETS_PRESENTATION / "anexo_vulnerabilidad_hazus.png",
            "anexo_vulnerabilidad_hazus.pdf",
            "assets/figures/presentation/anexo_vulnerabilidad_hazus.png",
        ),
    ]
    for src, out_name, old in vuln_sources:
        copied = copy_source_to_png(src, f"source_{Path(out_name).stem}.png")
        wrapper_pdf(
            source=copied,
            output_name=out_name,
            original_path=old,
            slide="Anexo",
            original_type="png",
            include_options="width=4.4in,keepaspectratio",
            change="Convertida a PDF generado en carpeta separada, preservando el PNG original.",
            source_data=as_posix(src),
            limitation="Se conserva exactamente el contenido del PNG original; no se redibujan curvas ni ejes.",
        )

    for name, slide, width in [
        ("anexo_convergencia_nlt_pga.png", "Anexo", "4.4in"),
        ("anexo_convergencia_nlt_sa10.png", "Anexo", "4.4in"),
    ]:
        wrapper_pdf(
            source=ASSETS_PRESENTATION / name,
            output_name=f"{Path(name).stem}.pdf",
            original_path=f"assets/figures/presentation/{name}",
            slide=slide,
            original_type="png",
            include_options=f"width={width},keepaspectratio",
            change="Convertida a PDF generado en carpeta separada, preservando el PNG original.",
            limitation="Se conserva exactamente el contenido del PNG original; no se redibujan curvas, ejes ni leyendas.",
        )


def restyle_identified_sources() -> None:
    generate_qgis_trazas()
    generate_subduction_model()
    prepare_qgis_map_inputs()
    generate_qgis_maps()

    for output_name, original_path, source_csv, title in [
        (
            "dsha_inter_pga.pdf",
            "assets/figures/presentation/dsha_inter_pga.pdf",
            "dsha_inter_pga.csv",
            "Interplaca Mw 9.3",
        ),
        (
            "dsha_fsr_pga.pdf",
            "assets/figures/presentation/dsha_fsr_pga.pdf",
            "dsha_fsr_pga.csv",
            "FSR Mw 7.5",
        ),
        (
            "dsha_intra_pga.pdf",
            "assets/figures/presentation/dsha_intra_pga.pdf",
            "dsha_intra_pga.csv",
            "Intraplaca Mw 8.0",
        ),
    ]:
        remove_manifest_for_output(output_name)
        add_manifest(
            original_path=original_path,
            new_path=PDF_DIR / output_name,
            slide="15",
            original_type="pdf",
            new_type="pdf/svg/png",
            change=f"Mapa DSHA {title} regenerado como layout QGIS, usando los mismos percentiles PGA p50, grilla, extents y traza FSR; se agrega fondo satelital, marco cebra, tipografia legible, colorbar y pesos de linea consistentes.",
            source_data=(
                f"{as_posix(MODELOS / 'hazard' / 'scenario' / 'resultados' / 'resultados_procesados' / 'out_gmf_maps_single_DEMhillshade' / 'tables')}; "
                f"{as_posix(QGIS_DATA_DIR / source_csv)}; {as_posix(QGIS_DATA_DIR / 'dsha_pga_bounds.csv')}"
            ),
            script_or_source=f"{as_posix(Path(__file__))}; {as_posix(QGIS_MAP_HELPER)}",
        )

    remove_manifest_for_output("fig_4_2_escenarios_simulados.pdf")
    add_manifest(
        original_path="assets/figures/presentation/fig_4_2_escenarios_simulados.pdf",
        new_path=PDF_DIR / "fig_4_2_escenarios_simulados.pdf",
        slide="12",
        original_type="pdf",
        new_type="pdf/svg/png",
        change="Regenerada como layout QGIS desde los XML originales de geometria DSHA, manteniendo vista regional, zoom, superficies, trazas y epicentros; se agrega fondo satelital y marco cebra.",
        source_data=(
            f"{as_posix(MODELOS / 'hazard' / 'scenario' / 'geometrias' / 'NT_75_34.xml')}; "
            f"{as_posix(MODELOS / 'hazard' / 'scenario' / 'geometrias' / 'rupture_intra_80.xml')}; "
            f"{as_posix(MODELOS / 'hazard' / 'scenario' / 'geometrias' / 'rupture_inter_93.xml')}; "
            f"notebook: {as_posix(MODELOS / 'hazard' / 'scenario' / 'codigos_apoyo' / 'graficar_geometrias_dsha.ipynb')}"
        ),
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(QGIS_MAP_HELPER)}",
        limitation="Se usa fondo satelital XYZ de Esri World Imagery desde QGIS; si no hay red disponible durante la regeneracion, QGIS puede exportar sin teselas aunque las geometrias y puntos cientificos se preservan.",
    )

    remove_manifest_for_output("fig_5_41_aalr_cambio_rel_pct.pdf")
    add_manifest(
        original_path="assets/figures/presentation/fig_5_41_aalr_cambio_rel_pct.pdf",
        new_path=PDF_DIR / "fig_5_41_aalr_cambio_rel_pct.pdf",
        slide="20",
        original_type="pdf",
        new_type="pdf/svg/png",
        change="Regenerada desde paneles QGIS producidos con DuckDB y shapefile de manzanas, conservando el calculo del incremento relativo de AALR con y sin FSR; se agrega fondo satelital tenue, resultados opacos, marco cebra, composicion vertical apilada, norte hacia la izquierda, extension ajustada con padding proporcional a la union FSR-manzanas, margen norte/sur ampliado para que los extremos de la FSR no toquen el marco, lienzo QGIS y lienzo compuesto adaptados a la proporcion real del mapa, etiquetas lat/lon y traza FSR completa bajo las manzanas AALR.",
        source_data=(
            f"{as_posix(QGIS_DATA_DIR / 'aalr_effect_objectid.csv')}; "
            f"{as_posix(QGIS_DATA_DIR / 'aalr_effect_bounds.csv')}; "
            f"{as_posix(MODELOS_ACTUALES / 'Riesgo' / 'Bases de datos' / 'Valores comerciales' / 'Valores comerciales' / 'Manzanas_VC_UFm2_DS.shp')}; "
            f"notebook: {as_posix(MODELOS / 'risk' / 'event_based' / 'codigos_apoyo' / 'base_de_datos_low_ram.ipynb')}"
        ),
        script_or_source=f"{as_posix(Path(__file__))}; {as_posix(QGIS_MAP_HELPER)}",
    )

    styled_svg_pdf(
        source=RESULTS
        / "risk_exposicion"
        / "Figuras"
        / "03_valor"
        / "fig_valor__conteos_y_aporte_por_tipologia_en_bins__paper.svg",
        output_name="exposicion_composicion.pdf",
        original_path="assets/figures/presentation/exposicion_composicion.pdf",
        slide="9",
        original_type="pdf",
        change="Regenerada desde SVG identificado, con fuente sans-serif, lineas reforzadas y leyenda compactada para evitar cortes en presentacion.",
        source_data=as_posix(
            RESULTS
            / "risk_exposicion"
            / "Figuras"
            / "03_valor"
            / "fig_valor__conteos_y_aporte_por_tipologia_en_bins__paper.svg"
        ),
        processor=process_exposure_svg,
        font_scale=1.18,
        min_font_px=10.2,
    )

    generate_curve_with_qgis_map(
        "Poisson",
        "fig_5_18_psha_curvas_pga_poisson.pdf",
        "assets/figures/presentation/fig_5_18_psha_curvas_pga_poisson.pdf",
        "17",
    )
    generate_curve_with_qgis_map(
        "BPT",
        "fig_5_19_psha_curvas_pga_bpt.pdf",
        "assets/figures/presentation/fig_5_19_psha_curvas_pga_bpt.pdf",
        "Anexo",
    )
    generate_disaggregation_with_qgis_map(
        "PGA",
        "Poisson",
        "fig_5_22_disagg_pga_poisson.pdf",
        "assets/figures/presentation/fig_5_22_disagg_pga_poisson.pdf",
        "18",
    )
    generate_disaggregation_with_qgis_map(
        "PGA",
        "BPT",
        "fig_5_23_disagg_pga_bpt.pdf",
        "assets/figures/presentation/fig_5_23_disagg_pga_bpt.pdf",
        "Anexo",
    )
    generate_disaggregation_with_qgis_map(
        "SA1_0",
        "BPT",
        "fig_5_25_disagg_sa10_bpt.pdf",
        "assets/figures/presentation/fig_5_25_disagg_sa10_bpt.pdf",
        "Anexo",
    )

    styled_svg_pdf(
        source=RESULTS / "risk_scenario" / "Comparison_Final_4Cols_Mat_FIXED_COMUNA__MAT-NAC_noAdobe.svg",
        output_name="fig_5_30_perdidas_comuna_materialidad.pdf",
        original_path="assets/figures/presentation/fig_5_30_perdidas_comuna_materialidad.pdf",
        slide="16",
        original_type="pdf",
        change="Regenerada desde SVG identificado de riesgo por escenarios, preservando las cuatro columnas y datos originales.",
        font_scale=1.16,
        min_font_px=10.0,
        min_stroke_width=0.45,
    )

    styled_svg_pdf(
        source=RESULTS / "risk_event_based" / "figA_oep_relativo_clean_square.svg",
        output_name="fig_5_42_oep_relativo.pdf",
        original_path="assets/figures/presentation/fig_5_42_oep_relativo.pdf",
        slide="21",
        original_type="pdf",
        change="Regenerada desde SVG identificado de OEP, aplicando el mismo postproceso conceptual, estilo de presentacion y leyenda compactada.",
        processor=process_oep_svg,
        font_scale=1.15,
        min_font_px=10.0,
        min_stroke_width=0.45,
    )
    styled_svg_pdf(
        source=RESULTS
        / "risk_event_based"
        / "ASC_EFFECT_LAMBDA"
        / "DELTA_LAMBDA_threshold__ConMinusSin__Nacional_vs_HAZUS__xmin1e-5__meanDiff.svg",
        output_name="fig_5_43_delta_lambda.pdf",
        original_path="assets/figures/presentation/fig_5_43_delta_lambda.pdf",
        slide="21",
        original_type="pdf",
        change="Regenerada desde SVG identificado de delta lambda, aplicando postproceso y estilo de presentacion.",
        processor=process_delta_lambda_svg,
        font_scale=1.15,
        min_font_px=10.0,
        min_stroke_width=0.45,
    )

    for source, output_name, old in [
        (
            RESULTS / "risk_vulnerabilidad" / "Figuras" / "Vulnerabilidad" / "junemann" / "vulnerabilidad_junemann_paper.svg",
            "anexo_vulnerabilidad_junemann.pdf",
            "assets/figures/presentation/anexo_vulnerabilidad_junemann.png",
        ),
        (
            RESULTS / "risk_vulnerabilidad" / "Figuras" / "Vulnerabilidad" / "cabrera" / "vulnerabilidad_cabrera_paper.svg",
            "anexo_vulnerabilidad_cabrera.pdf",
            "assets/figures/presentation/anexo_vulnerabilidad_cabrera.png",
        ),
        (
            RESULTS / "risk_vulnerabilidad" / "Figuras" / "Vulnerabilidad" / "hazus" / "vulnerabilidad_hazus_paper.svg",
            "anexo_vulnerabilidad_hazus.pdf",
            "assets/figures/presentation/anexo_vulnerabilidad_hazus.png",
        ),
    ]:
        styled_svg_pdf(
            source=source,
            output_name=output_name,
            original_path=old,
            slide="Anexo",
            original_type="png",
            change="Regenerada desde SVG identificado de vulnerabilidad, conservando curvas y ejes originales.",
            font_scale=1.15,
            min_font_px=10.0,
            min_stroke_width=0.45,
        )

    for source, output_name, old in [
        (
            RESULTS / "hazard_psha_sensibilidad_N_ramas" / "16_ppt_vertical_convergence" / "PGA_Panels_VertLines.svg",
            "anexo_convergencia_nlt_pga.pdf",
            "assets/figures/presentation/anexo_convergencia_nlt_pga.png",
        ),
        (
            RESULTS / "hazard_psha_sensibilidad_N_ramas" / "16_ppt_vertical_convergence" / "SA(1.0)_Panels_VertLines.svg",
            "anexo_convergencia_nlt_sa10.pdf",
            "assets/figures/presentation/anexo_convergencia_nlt_sa10.png",
        ),
    ]:
        styled_svg_pdf(
            source=source,
            output_name=output_name,
            original_path=old,
            slide="Anexo",
            original_type="png",
            change="Regenerada desde SVG identificado de convergencia por ramas, con fuente sans-serif y texto aumentado.",
            font_scale=1.15,
            min_font_px=10.0,
            min_stroke_width=0.45,
        )

    for source, output_name, old in [
        (
            MODELOS
            / "hazard"
            / "scenario"
            / "test_analisis_convergencia"
            / "salidas_corregidas_procesamiento"
            / "figs_paper_uaxis_v2"
            / "Tu_uaxis_sq_v2_thr0p20.svg",
            "anexo_convergencia_gmf_pga020.pdf",
            "assets/figures/presentation/anexo_convergencia_gmf_pga020.pdf",
        ),
        (
            MODELOS
            / "hazard"
            / "scenario"
            / "test_analisis_convergencia"
            / "salidas_corregidas_procesamiento"
            / "figs_paper_uaxis_v2"
            / "Tu_uaxis_sq_v2_thr0p40.svg",
            "anexo_convergencia_gmf_pga040.pdf",
            "assets/figures/presentation/anexo_convergencia_gmf_pga040.pdf",
        ),
    ]:
        styled_svg_pdf(
            source=source,
            output_name=output_name,
            original_path=old,
            slide="Anexo",
            original_type="pdf",
            change="Regenerada desde SVG identificado de convergencia GMF, conservando curvas y ejes originales.",
            font_scale=1.15,
            min_font_px=10.0,
            min_stroke_width=0.45,
        )


def add_tikz_manifest_rows() -> None:
    tikz_rows = [
        (
            "TikZ inline en tex/presentation/main.tex",
            SRC_DIR / "fig_theory_metrics.tikz",
            "7",
            "tikz inline",
            "tikz input",
            "Extraida a fuente generada y ajustada a estilos de color, linea y tipografia de la presentacion.",
        ),
        (
            "assets/figures/presentation/fig_4_3_arbol_logico_tikz.tex",
            SRC_DIR / "fig_logic_tree.tikz",
            "10",
            "tikz",
            "tikz input",
            "Redibujada como fuente TikZ generada con colores de Beamer y pesos de linea uniformes.",
        ),
        (
            "TikZ inline en tex/presentation/main.tex",
            SRC_DIR / "fig_workflow.tikz",
            "11",
            "tikz inline",
            "tikz input",
            "Extraida a fuente generada y ajustada a estilos de color, linea y tipografia de la presentacion.",
        ),
    ]
    for old, new, slide, original_type, new_type, change in tikz_rows:
        add_manifest(
            original_path=old,
            new_path=new,
            slide=slide,
            original_type=original_type,
            new_type=new_type,
            change=change,
            source_data="Contenido conceptual de tex/presentation/main.tex y figura TikZ original.",
            script_or_source=as_posix(new),
            limitation="Figura compilada directamente por Beamer desde TikZ; no requiere PDF intermedio.",
        )


def write_manifest() -> None:
    csv_path = GEN / "manifest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ManifestRow.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in MANIFEST:
            writer.writerow(row.__dict__)

    md_path = GEN / "manifest.md"
    lines = [
        "# Manifest de figuras generadas para la presentacion",
        "",
        "Generado por `figures_presentation_generated/src/generate_all_figures.py`.",
        "",
        f"Criterios de estilo adaptados de `{STYLE_SOURCE}` y centralizados en",
        "`figures_presentation_generated/src/presentation_scientific_style.py`: figuras vectoriales",
        "cuando es posible, tipografia sans-serif legible, paleta categorica accesible, colormaps",
        "perceptualmente uniformes, spines minimos y layouts multipanel alineados para presentacion.",
        "",
        "La procedencia de codigo/notebook de cada figura queda documentada en",
        "`figures_presentation_generated/source_code_inventory.md` y",
        "`figures_presentation_generated/source_code_inventory.csv`.",
        "",
        "## Regeneracion",
        "",
        "Desde la raiz del repositorio:",
        "",
        "```powershell",
        "python figures_presentation_generated/src/generate_all_figures.py",
        "```",
        "",
        "El script usa por defecto `../Modelos_v2025/resultados_finales` cuando existe. ",
        "Si los resultados estan en otra ubicacion, define `TESIS_MODELOS_DIR` o `TESIS_RESULTS_DIR`.",
        "",
        "## Mapeo",
        "",
        "| Slide | Figura original | Figura nueva | Cambio | Fuente / limitacion |",
        "|---|---|---|---|---|",
    ]
    for row in MANIFEST:
        source = row.source_data
        if row.limitation:
            source = f"{source}. Limitacion: {row.limitation}"
        lines.append(
            f"| {row.slide} | `{row.original_path}` | `{row.new_path}` | {row.change} | {source} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    ensure_dirs()
    style_matplotlib()
    normalize_wrapped_figures()
    restyle_identified_sources()
    add_tikz_manifest_rows()
    write_manifest()
    shutil.rmtree(WRAPPER_BUILD, ignore_errors=True)
    print(f"Generated {len(MANIFEST)} figure records in {as_posix(GEN)}")


if __name__ == "__main__":
    main()
