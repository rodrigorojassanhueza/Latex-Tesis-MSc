from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(r"G:\Mi unidad\Tesis\Tesis Rodrigo Rojas")
LATEX = ROOT / "LATEX_TESIS"
RESULTS = ROOT / "Modelos_v2025" / "resultados_finales"
RISK = RESULTS / "risk_event_based"
MAPS = RESULTS / "mapas_AAL_AALR_duckdb_FSR_vs_noFSR"
DEST = LATEX / "figuras_tesis" / "resultados_perdida"
WORK = LATEX / "_graph_generation_work" / "processed_svgs"
INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape.exe")

ALL_LABEL = "(Inter. + Intra. + FSR)"
NO_ASC_LABEL = "(Inter. + Intra.)"


def hide_group(svg: str, group_id: str) -> str:
    pattern = re.compile(
        rf'(<g\b(?=[^>]*\bid="{re.escape(group_id)}")[^>]*)(>)',
        flags=re.S,
    )

    def repl(match: re.Match[str]) -> str:
        tag = match.group(1)
        if re.search(r"\bdisplay\s*=", tag):
            return match.group(0)
        return f'{tag} display="none"{match.group(2)}'

    updated, count = pattern.subn(repl, svg, count=1)
    if count != 1:
        raise ValueError(f"No se encontro el grupo {group_id}")
    return updated


def replace_text(svg: str, old: str, new: str) -> str:
    updated = svg.replace(f">{old}<", f">{new}<")
    if updated == svg:
        raise ValueError(f"No se encontro el texto {old!r}")
    return updated


def shrink_group_font(svg: str, group_id: str, font_size: str) -> str:
    pattern = re.compile(
        rf'(<g\b(?=[^>]*\bid="{re.escape(group_id)}")[^>]*>.*?</g>)',
        flags=re.S,
    )

    def repl(match: re.Match[str]) -> str:
        block = match.group(1)
        return re.sub(r"font-size:\s*[\d.]+px", f"font-size: {font_size}px", block)

    updated, count = pattern.subn(repl, svg, count=1)
    if count != 1:
        raise ValueError(f"No se encontro el grupo {group_id} para ajustar fuente")
    return updated


def add_rotated_labels(svg: str, labels: list[tuple[str, float, float, float]]) -> str:
    additions = [
        '  <g id="codex_row_labels" style="fill:#222222; font-family:Arial, Helvetica, sans-serif; font-weight:700">\n'
    ]
    for label, x, y, size in labels:
        additions.append(
            f'    <text x="{x:.3f}" y="{y:.3f}" font-size="{size:.2f}px" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'transform="rotate(-90 {x:.3f} {y:.3f})">{label}</text>\n'
        )
    additions.append("  </g>\n")
    return svg.replace("</svg>", "".join(additions) + "</svg>")


def process_fig_a(svg: str) -> str:
    for group_id in ("text_13", "text_14"):
        svg = hide_group(svg, group_id)
    replacements = {
        "Nacional (All)": f"Nacional {ALL_LABEL}",
        "Nacional (No-ASC)": f"Nacional {NO_ASC_LABEL}",
        "HAZUS (All)": f"HAZUS {ALL_LABEL}",
        "HAZUS (No-ASC)": f"HAZUS {NO_ASC_LABEL}",
    }
    for old, new in replacements.items():
        svg = replace_text(svg, old, new)
    for group_id in ("text_15", "text_16", "text_17", "text_18"):
        svg = shrink_group_font(svg, group_id, "8.2")
    return svg


def process_fig_4cols(svg: str) -> str:
    for group_id in ("text_45", "text_46"):
        svg = hide_group(svg, group_id)
    return add_rotated_labels(
        svg,
        [
            (ALL_LABEL, 60.466, 131.752, 10.8),
            (NO_ASC_LABEL, 60.466, 268.434, 10.8),
        ],
    )


def process_fig_material(svg: str) -> str:
    for group_id in ("text_53", "text_54"):
        svg = hide_group(svg, group_id)
    return add_rotated_labels(
        svg,
        [
            (ALL_LABEL, 126.954, 119.954, 9.6),
            (NO_ASC_LABEL, 126.954, 230.754, 9.6),
        ],
    )


def process_identity(svg: str) -> str:
    return svg


TASKS: list[tuple[Path, str, callable[[str], str]]] = [
    (
        RISK / "figA_oep_relativo_clean_square.svg",
        "figA_oep_relativo_clean_square.pdf",
        process_fig_a,
    ),
    (
        RISK / "FIG_4cols_AAL_fromDuckDB__ALL_vs_NONASC__MAT-EXACT_PISO-HAZUS__AALRlog.svg",
        "FIG_4cols_AAL_fromDuckDB__ALL_vs_NONASC__MAT-EXACT_PISO-HAZUS__AALRlog.pdf",
        process_fig_4cols,
    ),
    (
        RISK / "FIG_MATERIAL__PISOBIN_RC__SHARES__EXPO_SHARE_AAL_AALR__ALL_vs_NONASC__NOEMPTY.svg",
        "FIG_MATERIAL__PISOBIN_RC__SHARES__EXPO_SHARE_AAL_AALR__ALL_vs_NONASC__NOEMPTY.pdf",
        process_fig_material,
    ),
    (
        RISK / "ASC_EFFECT_LAMBDA" / "LAMBDA_threshold__ConFSR_vs_SinFSR__Nacional_vs_HAZUS__xmin1e-5__p16p84.svg",
        "LAMBDA_threshold__ConFSR_vs_SinFSR__Nacional_vs_HAZUS__xmin1e-5__p16p84.pdf",
        lambda svg: hide_group(svg, "text_12"),
    ),
    (
        RISK / "ASC_EFFECT_LAMBDA" / "DELTA_LAMBDA_threshold__ConMinusSin__Nacional_vs_HAZUS__xmin1e-5__meanDiff.svg",
        "DELTA_LAMBDA_threshold__ConMinusSin__Nacional_vs_HAZUS__xmin1e-5__meanDiff.pdf",
        lambda svg: hide_group(svg, "text_13"),
    ),
    (
        MAPS / "sin_fsr" / "MAP_AAL__sin_fsr.svg",
        "MAP_AAL__sin_fsr.pdf",
        lambda svg: hide_group(svg, "text_27"),
    ),
    (
        MAPS / "sin_fsr" / "MAP_AALR_pm__sin_fsr.svg",
        "MAP_AALR_pm__sin_fsr.pdf",
        lambda svg: hide_group(svg, "text_27"),
    ),
    (
        MAPS / "con_fsr" / "MAP_AALR_pm__con_fsr.svg",
        "MAP_AALR_pm__con_fsr.pdf",
        lambda svg: hide_group(svg, "text_27"),
    ),
    (
        MAPS / "con_fsr" / "MAP_AAL__con_fsr.svg",
        "MAP_AAL__con_fsr.pdf",
        lambda svg: hide_group(svg, "text_27"),
    ),
    (
        MAPS / "sin_fsr" / "MAP_dAALR_rel_pct__sin_fsr.svg",
        "MAP_dAALR_rel_pct__sin_fsr.pdf",
        lambda svg: hide_group(svg, "text_10"),
    ),
    (
        MAPS / "efecto_fsr" / "MAP_efecto_FSR_en_AALR_pct.svg",
        "MAP_efecto_FSR_en_AALR_pct.pdf",
        lambda svg: hide_group(svg, "text_27"),
    ),
]


def main() -> None:
    if not INKSCAPE.exists():
        raise FileNotFoundError(f"No se encontro Inkscape en {INKSCAPE}")
    WORK.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)

    for source, pdf_name, processor in TASKS:
        if not source.exists():
            raise FileNotFoundError(source)
        svg = source.read_text(encoding="utf-8")
        svg = processor(svg)
        processed_svg = WORK / source.name
        processed_svg.write_text(svg, encoding="utf-8", newline="\n")
        dest_pdf = DEST / pdf_name
        subprocess.run(
            [str(INKSCAPE), str(processed_svg), f"--export-filename={dest_pdf}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(f"OK {pdf_name}")


if __name__ == "__main__":
    main()
