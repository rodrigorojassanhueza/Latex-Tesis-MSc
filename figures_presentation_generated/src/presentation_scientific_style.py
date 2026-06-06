from __future__ import annotations

"""Shared scientific-presentation style for generated thesis figures.

Adapted from https://github.com/K-Dense-AI/scientific-agent-skills, especially:
- scientific-visualization/assets/presentation.mplstyle
- scientific-visualization/assets/publication.mplstyle
- scientific-visualization/assets/color_palettes.py

The values below are tuned for 16:9 Beamer slides rather than journal print:
text is larger, strokes are heavier, and palettes remain colorblind friendly.
"""

from typing import Any


STYLE_SOURCE = "https://github.com/K-Dense-AI/scientific-agent-skills (scientific-visualization)"

# Beamer palette.
UCHILE_BLUE = "#003A70"
TEXT_GRAY = "#2A2E33"
CAPTION_GRAY = "#585C62"
SOFT_GRAY = "#F6F7F9"
GRID_GRAY = "#D9DEE5"
GRID_GRAY_QGIS = "#D7DCE2"

# Okabe-Ito / Wong accessible palette.
OKABE_ORANGE = "#E69F00"
OKABE_SKY_BLUE = "#56B4E9"
OKABE_GREEN = "#009E73"
OKABE_YELLOW = "#F0E442"
OKABE_BLUE = "#0072B2"
OKABE_VERMILLION = "#D55E00"
OKABE_PURPLE = "#CC79A7"
OKABE_BLACK = "#000000"

OKABE_ITO = [
    OKABE_ORANGE,
    OKABE_SKY_BLUE,
    OKABE_GREEN,
    OKABE_YELLOW,
    OKABE_BLUE,
    OKABE_VERMILLION,
    OKABE_PURPLE,
    OKABE_BLACK,
]

# Semantic colors used consistently across the thesis figures.
INTER_BLUE = OKABE_BLUE
INTRA_GOLD = OKABE_ORANGE
FSR_RED = OKABE_VERMILLION
FSR_MAP_TRACE = "#D81B60"
ACCENT_RED = OKABE_VERMILLION
NO_FSR_GRAY = "#8A929B"
TEAL = OKABE_GREEN
TRACE_DARK = "#1E1E1E"

SLAB_ZONE_COLORS = [
    "#D81B60",
    UCHILE_BLUE,
    OKABE_GREEN,
    OKABE_ORANGE,
    "#7E57C2",
    "#00897B",
    "#C2185B",
]

PRESENTATION_FONT_FAMILY = ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"]
PRESENTATION_FONT_STACK = "'Arial', 'Helvetica', 'DejaVu Sans', 'Liberation Sans', sans-serif"

# Perceptually uniform sequential palette sampled from viridis.
VIRIDIS_10 = [
    "#440154",
    "#482878",
    "#3E4989",
    "#31688E",
    "#26828E",
    "#1F9E89",
    "#35B779",
    "#6CCE59",
    "#B4DE2C",
    "#FDE725",
]

# Low-to-high change palette used for AALR maps. It avoids red/green as a
# categorical contrast: here color is sequential and the colorbar carries value.
AALR_10 = [
    "#1F7A4A",
    "#3F9950",
    "#6DB24B",
    "#A7C94A",
    "#D9D04A",
    "#E9B844",
    "#E58E39",
    "#D95D3C",
    "#C73535",
    "#8B1A1A",
]

SATELLITE_XYZ = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"


def matplotlib_presentation_rcparams(mpl: Any) -> dict[str, Any]:
    """Return rcParams tuned for projected scientific slides."""

    return {
        "font.family": "sans-serif",
        "font.sans-serif": PRESENTATION_FONT_FAMILY,
        "font.size": 10.8,
        "axes.titlesize": 11.4,
        "axes.labelsize": 10.9,
        "xtick.labelsize": 9.6,
        "ytick.labelsize": 9.6,
        "legend.fontsize": 9.6,
        "figure.titlesize": 12.6,
        "axes.edgecolor": TEXT_GRAY,
        "axes.labelcolor": TEXT_GRAY,
        "xtick.color": TEXT_GRAY,
        "ytick.color": TEXT_GRAY,
        "text.color": TEXT_GRAY,
        "axes.linewidth": 0.9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "lines.linewidth": 2.05,
        "lines.markersize": 5.6,
        "lines.markeredgewidth": 1.0,
        "patch.linewidth": 0.75,
        "grid.color": GRID_GRAY,
        "grid.linewidth": 0.55,
        "grid.alpha": 0.70,
        "legend.frameon": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.08,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "image.cmap": "viridis",
        "axes.prop_cycle": mpl.cycler(
            color=[UCHILE_BLUE, FSR_RED, INTER_BLUE, INTRA_GOLD, TEAL, OKABE_PURPLE, NO_FSR_GRAY]
        ),
    }


def apply_matplotlib_presentation_style(mpl: Any) -> None:
    """Apply the shared style to matplotlib."""

    mpl.rcParams.update(matplotlib_presentation_rcparams(mpl))


QGIS_STYLE = {
    "font_family": "Arial",
    "title_size": 9.0,
    "panel_title_size": 7.6,
    "grid_annotation_size": 6.0,
    "site_label_size": 7.0,
    "colorbar_label_size": 6.7,
    "colorbar_tick_size": 6.2,
    "zebra_width_mm": 2.0,
    "zebra_pen_mm": 0.08,
    "grid_line_mm": 0.10,
    "frame_line_mm": 0.18,
}
