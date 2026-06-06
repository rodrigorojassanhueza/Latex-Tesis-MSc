from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter, MultipleLocator


ROOT = Path(__file__).resolve().parents[2]
CSV_IN = (
    ROOT.parent
    / "Modelos"
    / "Actuales"
    / "Riesgo"
    / "Bases de datos"
    / "BD_Struct_FSR.csv"
)
PDF_OUT = ROOT / "figures_presentation_generated" / "pdf" / "fig_valor_expuesto_tipologia_heatmap.pdf"
PNG_OUT = ROOT / "figures_presentation_generated" / "png" / "fig_valor_expuesto_tipologia_heatmap.png"
SVG_OUT = ROOT / "figures_presentation_generated" / "svg" / "fig_valor_expuesto_tipologia_heatmap.svg"

VALUE_COL = "AVAL_FISC"
MAT_COL = "COD_MAT"
DEST_COL = "DEST_BI"
H_COL = "height"
LON_COL = "longitude_b"
LAT_COL = "latitude_b"
DEST_HAB_CODE = "H"

CODMAT_DESCRIPCION = {
    "A": "Acero",
    "B": "Hormigón armado",
    "C": "Albañilería",
    "E": "Madera",
    "F": "Adobe",
    "G": "Perfiles metálicos",
    "K": "Prefabricados",
    "GA": "Galpón acero",
    "GB": "Galpón hormigón",
    "GC": "Galpón albañilería",
    "GE": "Galpón madera",
    "GL": "Galpón madera laminada",
    "GF": "Galpón adobe",
    "OA": "Obra civil acero",
    "OB": "Obra civil hormigón",
    "OE": "Obra civil madera",
    "M": "Marquesina",
    "P": "Pavimento",
    "W": "Piscina",
}
MATERIALES_EXCLUIDOS_DETALLE = ["K", "G", "A", "P", "GE"]

PISOS_POR_ID = {
    1817: 4,
    2615: 17,
    2616: 17,
    2620: 11,
    2621: 11,
    2628: 17,
    2629: 17,
    2630: 17,
    2632: 11,
    2633: 11,
    3014: 2,
    3068: 5,
    3194: 15,
    3557: 4,
    3691: 4,
    4128: 5,
    4377: 3,
    4379: 5,
    4480: 5,
    4501: 4,
    4695: 4,
    4704: 4,
    4815: 5,
    4819: 5,
    4832: 5,
    4912: 5,
    4966: 4,
    5342: 5,
    5366: 5,
    5552: 2,
    5640: 2,
    5920: 2,
    6034: 2,
    6889: 3,
    6998: 2,
    7201: 3,
    7351: 5,
    7472: 4,
    7522: 2,
    7559: 2,
    7689: 3,
    7748: 2,
    7771: 4,
    7880: 5,
    7897: 5,
    7902: 2,
}

CATEGORY_ORDER = [
    "Albañilería",
    "Adobe",
    "Madera",
    "HA 1–3",
    "HA 4–7",
    "HA 8–9",
    "HA 10–24",
]

TYPE_TO_SHORT = {
    "Albañilería": "Albañilería",
    "Adobe": "Adobe",
    "Madera": "Madera",
    "Hormigón armado (1–3 pisos)": "HA 1–3",
    "Hormigón armado (4–7 pisos)": "HA 4–7",
    "Hormigón armado (8–9 pisos)": "HA 8–9",
    "Hormigón armado (10–24 pisos)": "HA 10–24",
    "Hormigón armado (>24 pisos)": "HA >24",
}


def style_matplotlib() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
            "font.size": 11.2,
            "axes.labelsize": 13.2,
            "axes.labelweight": "medium",
            "xtick.labelsize": 11.6,
            "ytick.labelsize": 12.2,
            "axes.linewidth": 0.82,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.top": False,
            "ytick.right": False,
            "figure.dpi": 180,
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def normalize_str(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def mat_code_series(df: pd.DataFrame) -> pd.Series:
    raw = df.get(MAT_COL, pd.Series([pd.NA] * len(df), index=df.index))
    return normalize_str(raw).replace({"<NA>": pd.NA})


def get_id_series(df: pd.DataFrame) -> pd.Series:
    if "id" in df.columns:
        ids = pd.to_numeric(df["id"], errors="coerce")
    elif "OBJECTID" in df.columns:
        ids = pd.to_numeric(df["OBJECTID"], errors="coerce")
    else:
        ids = pd.Series(np.arange(len(df)), index=df.index, dtype="int64")
    return ids.fillna(-1).astype("int64")


def estimate_floors(ids: pd.Series, height_m: pd.Series, m_per_storey: float = 3.0) -> pd.Series:
    known = ids.map(PISOS_POR_ID).astype("float")
    floors = known.copy()
    h = pd.to_numeric(height_m, errors="coerce").astype("float")
    missing = floors.isna()
    estimated = np.rint(h / m_per_storey)
    estimated = np.where(np.isfinite(estimated) & (estimated >= 1), estimated, 1)
    floors.loc[missing] = estimated[missing.to_numpy()]
    return floors.astype("int64")


def classify_typology(mat: str, floors: int) -> str:
    mat = (mat or "").strip()
    if mat == "B":
        if floors <= 3:
            return "Hormigón armado (1–3 pisos)"
        if floors <= 7:
            return "Hormigón armado (4–7 pisos)"
        if floors <= 9:
            return "Hormigón armado (8–9 pisos)"
        if floors <= 24:
            return "Hormigón armado (10–24 pisos)"
        return "Hormigón armado (>24 pisos)"
    if mat == "C":
        return "Albañilería"
    if mat == "E":
        return "Madera"
    if mat == "F":
        return "Adobe"
    return CODMAT_DESCRIPCION.get(mat, "Sin información")


def build_dataset() -> pd.DataFrame:
    df = pd.read_csv(CSV_IN, low_memory=False)
    for column in [VALUE_COL, H_COL, LON_COL, LAT_COL]:
        df[column] = pd.to_numeric(df.get(column, np.nan), errors="coerce")

    mat = mat_code_series(df)
    dest = normalize_str(df.get(DEST_COL, pd.Series([pd.NA] * len(df), index=df.index))).str.upper()
    mask = (
        dest.eq(DEST_HAB_CODE)
        & mat.isin(list(CODMAT_DESCRIPCION.keys()))
        & df[VALUE_COL].fillna(0).gt(0)
        & df[LON_COL].between(-180, 180)
        & df[LAT_COL].between(-90, 90)
    )

    df_typ = df[mask].copy()
    df_typ["MAT_CODE"] = mat[mask]
    df_typ = df_typ[~df_typ["MAT_CODE"].isin(MATERIALES_EXCLUIDOS_DETALLE)].copy()
    df_typ["_floors"] = estimate_floors(get_id_series(df_typ), df_typ[H_COL])
    df_typ["TIPOLOGIA"] = [
        classify_typology(mat if pd.notna(mat) else "", int(floors))
        for mat, floors in zip(df_typ["MAT_CODE"].astype("string"), df_typ["_floors"])
    ]
    df_typ["TIPO_CORTO"] = df_typ["TIPOLOGIA"].map(TYPE_TO_SHORT)
    df_typ = df_typ[df_typ["TIPO_CORTO"].isin(CATEGORY_ORDER)].copy()
    df_typ = df_typ[np.isfinite(df_typ[VALUE_COL]) & (df_typ[VALUE_COL] > 0)].copy()
    return df_typ


def format_int_dot(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", ".")


def format_decimal_comma(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def soften_axes(ax: mpl.axes.Axes, *, left: bool = True, bottom: bool = True) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    for spine in ax.spines.values():
        spine.set_color("#30363C")
        spine.set_linewidth(0.82)
    ax.tick_params(colors="#30363C", width=0.75, length=3.4)


def generate_figure() -> None:
    style_matplotlib()
    df_typ = build_dataset()
    total_n = len(df_typ)
    total_value = float(df_typ[VALUE_COL].sum())
    log10_value = np.log10(df_typ[VALUE_COL].to_numpy())

    tick_step = 0.5
    bins_per_tick = 4
    bin_width = tick_step / bins_per_tick
    x0 = np.floor(float(np.nanmin(log10_value)) / tick_step) * tick_step
    x1 = np.ceil(float(np.nanmax(log10_value)) / tick_step) * tick_step
    edges = np.arange(x0, x1 + bin_width * 1.0001, bin_width)
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    hist_counts, _ = np.histogram(log10_value, bins=edges)

    value_order = (
        df_typ.groupby("TIPO_CORTO", observed=True)[VALUE_COL]
        .sum()
        .reindex(CATEGORY_ORDER, fill_value=0.0)
        .sort_values(ascending=False, kind="mergesort")
        .index.tolist()
    )

    n_categories = len(value_order)
    heat = np.zeros((n_categories, len(edges) - 1), dtype=float)
    counts = np.zeros(n_categories, dtype=float)
    values = np.zeros(n_categories, dtype=float)
    for idx, category in enumerate(value_order):
        subset = df_typ[df_typ["TIPO_CORTO"] == category]
        counts[idx] = len(subset)
        values[idx] = float(subset[VALUE_COL].sum())
        if len(subset):
            category_log = np.log10(subset[VALUE_COL].to_numpy())
            category_values = subset[VALUE_COL].to_numpy()
            sums, _ = np.histogram(category_log, bins=edges, weights=category_values)
            heat[idx, :] = 100.0 * sums / total_value

    count_pct = 100.0 * counts / total_n
    value_bn = values / 1e9
    value_pct = 100.0 * values / total_value

    cmap = LinearSegmentedColormap.from_list(
        "fsr_exposure_blues",
        ["#F1F7FC", "#D5E8F3", "#A9D1E7", "#6DAED6", "#2C7FB8", "#084B83"],
    )
    vmax = float(np.nanmax(heat))

    fig = plt.figure(figsize=(11.8, 5.95))
    gs = fig.add_gridspec(
        nrows=2,
        ncols=5,
        height_ratios=[1.00, 1.76],
        width_ratios=[1.35, 3.35, 1.38, 0.16, 0.20],
        hspace=0.045,
        wspace=0.105,
    )

    ax_hist = fig.add_subplot(gs[0, 1])
    ax_left = fig.add_subplot(gs[1, 0])
    ax_heat = fig.add_subplot(gs[1, 1], sharex=ax_hist)
    ax_right = fig.add_subplot(gs[1, 2], sharey=ax_heat)
    ax_cbar = fig.add_subplot(gs[1, 4])

    y_positions = np.arange(n_categories)

    ax_hist.bar(
        centers,
        hist_counts,
        width=widths * 0.94,
        align="center",
        color="#C9CDD1",
        edgecolor="#9EA4AA",
        linewidth=0.45,
        zorder=2,
    )
    ax_hist.set_ylabel("Cantidad de\nocurrencias", labelpad=8, color="#30363C")
    ax_hist.grid(axis="y", color="#E5E8EB", linewidth=0.75, zorder=0)
    ax_hist.set_xlim(edges[0], edges[-1])
    ax_hist.xaxis.set_major_locator(MultipleLocator(1.0))
    ax_hist.xaxis.set_minor_locator(MultipleLocator(bin_width))
    ax_hist.tick_params(axis="x", labelbottom=False)
    soften_axes(ax_hist)

    y_edges = np.arange(n_categories + 1) - 0.5
    mesh = ax_heat.pcolormesh(
        edges,
        y_edges,
        heat,
        cmap=cmap,
        vmin=0,
        vmax=vmax,
        shading="flat",
        linewidth=0.15,
        edgecolors=(1, 1, 1, 0.42),
    )
    ax_heat.set_ylim(n_categories - 0.5, -0.5)
    ax_heat.set_yticks(y_positions)
    ax_heat.set_yticklabels([])
    ax_heat.tick_params(axis="y", length=0)
    ax_heat.set_xlabel("Valor expuesto\n(CLP)", labelpad=6, color="#30363C")
    ax_heat.xaxis.set_major_locator(MultipleLocator(1.0))
    ax_heat.xaxis.set_major_formatter(FuncFormatter(lambda x, _pos: rf"$10^{{{int(x)}}}$"))
    ax_heat.xaxis.set_minor_locator(MultipleLocator(0.25))
    ax_heat.tick_params(axis="x", labelsize=11.8, pad=3.0)
    soften_axes(ax_heat)

    bar_color = "#718493"
    ax_left.barh(y_positions, value_bn, height=0.68, color=bar_color, edgecolor="none", alpha=0.97, zorder=2)
    ax_left.set_ylim(n_categories - 0.5, -0.5)
    ax_left.set_yticks(y_positions)
    ax_left.set_yticklabels(value_order, fontsize=12.2)
    ax_left.set_xlabel("Valor total\n(10⁹ CLP)", labelpad=5, color="#30363C")
    ax_left.set_ylabel("Tipología", labelpad=8, color="#30363C")
    max_value_bn = float(max(value_bn))
    ax_left.set_xlim(0, max_value_bn * 1.34)
    ax_left.grid(axis="x", color="#ECEFF2", linewidth=0.65, zorder=0)
    for y, value, pct in zip(y_positions, value_bn, value_pct):
        is_long_bar = value > max_value_bn * 0.56
        ax_left.text(
            value - max_value_bn * 0.035 if is_long_bar else value + max_value_bn * 0.028,
            y,
            f"{format_decimal_comma(value)} ({format_decimal_comma(pct)}%)",
            ha="right" if is_long_bar else "left",
            va="center",
            fontsize=10.6,
            color="white" if is_long_bar else "#30363C",
            clip_on=True,
        )
    soften_axes(ax_left)

    ax_right.barh(y_positions, counts, height=0.68, color=bar_color, edgecolor="none", alpha=0.97, zorder=2)
    ax_right.set_ylim(n_categories - 0.5, -0.5)
    ax_right.set_yticks(y_positions)
    ax_right.set_yticklabels([])
    ax_right.tick_params(axis="y", length=0)
    ax_right.set_xlabel("Roles", labelpad=5, color="#30363C")
    max_count = float(max(counts))
    ax_right.set_xlim(0, max_count * 1.50)
    ax_right.grid(axis="x", color="#ECEFF2", linewidth=0.65, zorder=0)
    for y, count, pct in zip(y_positions, counts, count_pct):
        is_long_bar = count > max_count * 0.56
        ax_right.text(
            count - max_count * 0.035 if is_long_bar else count + max_count * 0.035,
            y,
            f"{format_int_dot(count)} ({format_decimal_comma(pct)}%)",
            ha="right" if is_long_bar else "left",
            va="center",
            fontsize=10.6,
            color="white" if is_long_bar else "#30363C",
            clip_on=True,
        )
    soften_axes(ax_right)

    cbar = fig.colorbar(mesh, cax=ax_cbar)
    cbar.set_label("Participación del valor expuesto total (%)", labelpad=8, fontsize=11.4, color="#30363C")
    cbar.set_ticks([0.0, 1.5, 3.0, 4.5, 6.0])
    cbar.ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _pos: format_decimal_comma(x)))
    cbar.ax.tick_params(labelsize=11.0, colors="#30363C", width=0.7, length=3.1)
    cbar.outline.set_linewidth(0.75)
    cbar.outline.set_edgecolor("#30363C")

    fig.subplots_adjust(left=0.064, right=0.982, top=0.982, bottom=0.285)

    PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_OUT)
    fig.savefig(PNG_OUT, dpi=600)
    fig.savefig(SVG_OUT)
    plt.close(fig)

    print(f"[OK] {PDF_OUT}")
    print(f"[OK] {PNG_OUT}")
    print(f"[OK] {SVG_OUT}")


if __name__ == "__main__":
    generate_figure()
