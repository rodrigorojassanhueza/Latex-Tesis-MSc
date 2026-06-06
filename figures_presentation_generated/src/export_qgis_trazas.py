from __future__ import annotations

import sys
from pathlib import Path

from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsApplication,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLineSymbol,
    QgsMapLayerType,
    QgsProject,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsUnitTypes,
    QgsWkbTypes,
)

from presentation_scientific_style import (
    CAPTION_GRAY,
    FSR_MAP_TRACE,
    GRID_GRAY_QGIS as GRID_GRAY,
    QGIS_STYLE,
    TEXT_GRAY,
    UCHILE_BLUE,
)


def label_text(item: QgsLayoutItemLabel) -> str:
    for method_name in ("text", "currentText"):
        method = getattr(item, method_name, None)
        if callable(method):
            try:
                return str(method())
            except Exception:
                pass
    return ""


def set_label_style(item: QgsLayoutItemLabel) -> None:
    text = label_text(item)
    fmt = item.textFormat()
    font = fmt.font()
    font.setFamily(QGIS_STYLE["font_family"])
    if "Mapas de trazas" in text:
        font.setPointSizeF(23.0)
        font.setBold(False)
        fmt.setColor(QColor(UCHILE_BLUE))
    else:
        point_size = font.pointSizeF()
        if point_size <= 0:
            point_size = 10.0
        font.setPointSizeF(max(point_size, 10.0))
        fmt.setColor(QColor(TEXT_GRAY))
    fmt.setFont(font)
    item.setTextFormat(fmt)
    item.refresh()


def simple_line(color: str, width_mm: float) -> QgsSimpleLineSymbolLayer:
    symbol_layer = QgsSimpleLineSymbolLayer()
    symbol_layer.setColor(QColor(color))
    symbol_layer.setWidth(width_mm)
    symbol_layer.setWidthUnit(QgsUnitTypes.RenderMillimeters)
    return symbol_layer


def set_trace_layer_style(project: QgsProject) -> None:
    for layer in project.mapLayers().values():
        if layer.type() != QgsMapLayerType.VectorLayer:
            continue
        if layer.geometryType() != QgsWkbTypes.LineGeometry:
            continue
        symbol = QgsLineSymbol()
        while symbol.symbolLayerCount():
            symbol.deleteSymbolLayer(0)
        symbol.appendSymbolLayer(simple_line("#FFFFFF", 1.10))
        symbol.appendSymbolLayer(simple_line(FSR_MAP_TRACE, 0.66))
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        layer.triggerRepaint()


def _grid_interval_for_map(item: QgsLayoutItemMap) -> tuple[float, float, int]:
    extent = item.extent()
    width = abs(extent.xMaximum() - extent.xMinimum())
    height = abs(extent.yMaximum() - extent.yMinimum())
    interval_x = 0.10 if width < 1.0 else 0.50 if width < 4.0 else 1.0
    interval_y = 0.10 if height < 1.0 else 0.50 if height < 4.0 else 1.0
    precision = 1 if max(interval_x, interval_y) >= 0.5 else 2
    return interval_x, interval_y, precision


def set_map_grid_style(item: QgsLayoutItemMap) -> None:
    for grid in item.grids().asList():
        grid.setEnabled(False)
    interval_x, interval_y, precision = _grid_interval_for_map(item)
    grid = QgsLayoutItemMapGrid("presentation_zebra", item)
    item.grids().addGrid(grid)
    grid.setEnabled(True)
    grid.setIntervalX(interval_x)
    grid.setIntervalY(interval_y)
    grid.setAnnotationEnabled(True)
    grid.setAnnotationPrecision(precision)
    annotation_font = QFont(QGIS_STYLE["font_family"])
    annotation_font.setPointSizeF(QGIS_STYLE["grid_annotation_size"])
    grid.setAnnotationFont(annotation_font)
    grid.setAnnotationFontColor(QColor(CAPTION_GRAY))
    grid.setAnnotationFrameDistance(2.2)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Top)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.HideAll, QgsLayoutItemMapGrid.Right)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.LongitudeOnly, QgsLayoutItemMapGrid.Bottom)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.LatitudeOnly, QgsLayoutItemMapGrid.Left)
    grid.setFrameStyle(QgsLayoutItemMapGrid.Zebra)
    grid.setFrameWidth(QGIS_STYLE["zebra_width_mm"])
    grid.setFramePenSize(QGIS_STYLE["zebra_pen_mm"])
    grid.setFramePenColor(QColor("#3A3F46"))
    grid.setFrameFillColor1(QColor("#FFFFFF"))
    grid.setFrameFillColor2(QColor("#2A2E33"))
    grid.setGridLineColor(QColor(GRID_GRAY))
    grid.setGridLineWidth(QGIS_STYLE["grid_line_mm"])
    item.setFrameEnabled(True)
    item.setFrameStrokeColor(QColor("#5B616A"))


def main() -> int:
    if len(sys.argv) != 6:
        print("usage: export_qgis_trazas.py PROJECT.qgz LAYOUT_NAME OUT.svg OUT.png OUT.pdf", file=sys.stderr)
        return 2

    project_path = Path(sys.argv[1])
    layout_name = sys.argv[2]
    out_svg = Path(sys.argv[3])
    out_png = Path(sys.argv[4])
    out_pdf = Path(sys.argv[5])

    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.40.8\apps\qgis-ltr", True)
    app = QgsApplication([], False)
    app.initQgis()
    try:
        project = QgsProject.instance()
        if not project.read(str(project_path)):
            raise RuntimeError(f"Could not read QGIS project: {project_path}")
        set_trace_layer_style(project)
        layout = project.layoutManager().layoutByName(layout_name)
        if layout is None:
            names = [layout.name() for layout in project.layoutManager().layouts()]
            raise RuntimeError(f"Layout not found: {layout_name}. Available layouts: {names}")

        for item in layout.items():
            if isinstance(item, QgsLayoutItemLabel):
                set_label_style(item)
            elif isinstance(item, QgsLayoutItemMap):
                set_map_grid_style(item)

        out_svg.parent.mkdir(parents=True, exist_ok=True)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        for out_path in (out_svg, out_png, out_pdf):
            if out_path.exists():
                out_path.unlink()
        exporter = QgsLayoutExporter(layout)

        svg_settings = QgsLayoutExporter.SvgExportSettings()
        svg_settings.exportMetadata = False
        svg_result = exporter.exportToSvg(str(out_svg), svg_settings)
        if svg_result != QgsLayoutExporter.Success:
            raise RuntimeError(f"QGIS SVG export failed with code {svg_result}")

        image_settings = QgsLayoutExporter.ImageExportSettings()
        image_settings.dpi = 300
        png_result = exporter.exportToImage(str(out_png), image_settings)
        if png_result != QgsLayoutExporter.Success:
            raise RuntimeError(f"QGIS PNG export failed with code {png_result}")

        pdf_settings = QgsLayoutExporter.PdfExportSettings()
        pdf_settings.exportMetadata = False
        pdf_result = exporter.exportToPdf(str(out_pdf), pdf_settings)
        if pdf_result != QgsLayoutExporter.Success:
            raise RuntimeError(f"QGIS PDF export failed with code {pdf_result}")
    finally:
        app.exitQgis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
