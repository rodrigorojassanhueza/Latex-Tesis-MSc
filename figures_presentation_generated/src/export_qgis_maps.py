from __future__ import annotations

import csv
import json
import math
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
from osgeo import gdal, osr
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsLayout,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemShape,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRectangle,
    QgsRendererCategory,
    QgsRendererRange,
    QgsSimpleFillSymbolLayer,
    QgsSimpleLineSymbolLayer,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer,
    QgsSymbol,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
    QgsColorRampShader,
)
from qgis.PyQt.QtCore import QVariant

from presentation_scientific_style import (
    AALR_10,
    ACCENT_RED,
    CAPTION_GRAY,
    FSR_MAP_TRACE,
    FSR_RED,
    GRID_GRAY_QGIS as GRID_GRAY,
    INTER_BLUE,
    INTRA_GOLD,
    QGIS_STYLE,
    SATELLITE_XYZ,
    SOFT_GRAY,
    TEXT_GRAY,
    TRACE_DARK,
    UCHILE_BLUE,
    VIRIDIS_10,
)


NODATA = -9999.0


def rel(root: Path, *parts: str) -> Path:
    return root.joinpath(*parts)


def mm(x: float) -> QgsUnitTypes.LayoutUnit:
    return QgsUnitTypes.LayoutMillimeters


def add_label(
    layout: QgsLayout,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    size: float = 8.0,
    bold: bool = False,
    color: str = TEXT_GRAY,
    align: Qt.AlignmentFlag = Qt.AlignLeft,
) -> QgsLayoutItemLabel:
    item = QgsLayoutItemLabel(layout)
    item.setText(text)
    item.attemptMove(QgsLayoutPoint(x, y, mm(x)))
    item.attemptResize(QgsLayoutSize(w, h, mm(w)))
    fmt = item.textFormat()
    font = QFont(QGIS_STYLE["font_family"])
    font.setPointSizeF(size)
    font.setBold(bold)
    fmt.setFont(font)
    fmt.setColor(QColor(color))
    item.setTextFormat(fmt)
    item.setHAlign(align)
    item.setVAlign(Qt.AlignVCenter)
    layout.addLayoutItem(item)
    return item


def add_shape_rect(
    layout: QgsLayout,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str = "transparent",
    outline: str = "transparent",
    outline_width: float = 0.0,
) -> QgsLayoutItemShape:
    item = QgsLayoutItemShape(layout)
    item.setShapeType(QgsLayoutItemShape.Rectangle)
    item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    item.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    symbol = QgsFillSymbol.createSimple(
        {
            "color": fill,
            "outline_color": outline,
            "outline_width": str(outline_width),
            "outline_width_unit": "MM",
        }
    )
    item.setSymbol(symbol)
    layout.addLayoutItem(item)
    return item


def export_layout(layout: QgsLayout, out_stem: Path, *, png_dpi: int = 300) -> None:
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".pdf", ".svg", ".png"):
        out_path = out_stem.with_suffix(suffix)
        if out_path.exists():
            out_path.unlink()
    exporter = QgsLayoutExporter(layout)

    pdf_settings = QgsLayoutExporter.PdfExportSettings()
    pdf_settings.exportMetadata = False
    pdf_result = exporter.exportToPdf(str(out_stem.with_suffix(".pdf")), pdf_settings)
    if pdf_result != QgsLayoutExporter.Success:
        raise RuntimeError(f"QGIS PDF export failed for {out_stem.name}: {pdf_result}")

    svg_settings = QgsLayoutExporter.SvgExportSettings()
    svg_settings.exportMetadata = False
    svg_result = exporter.exportToSvg(str(out_stem.with_suffix(".svg")), svg_settings)
    if svg_result != QgsLayoutExporter.Success:
        raise RuntimeError(f"QGIS SVG export failed for {out_stem.name}: {svg_result}")

    png_settings = QgsLayoutExporter.ImageExportSettings()
    png_settings.dpi = png_dpi
    png_result = exporter.exportToImage(str(out_stem.with_suffix(".png")), png_settings)
    if png_result != QgsLayoutExporter.Success:
        raise RuntimeError(f"QGIS PNG export failed for {out_stem.name}: {png_result}")


def add_grid(
    map_item: QgsLayoutItemMap,
    interval_x: float,
    interval_y: float,
    *,
    precision: int = 2,
    annotations: bool = True,
) -> None:
    grid = QgsLayoutItemMapGrid("graticule", map_item)
    map_item.grids().addGrid(grid)
    grid.setEnabled(True)
    grid.setIntervalX(interval_x)
    grid.setIntervalY(interval_y)
    grid.setAnnotationEnabled(annotations)
    grid.setAnnotationPrecision(precision)
    annotation_font = QFont(QGIS_STYLE["font_family"])
    annotation_font.setPointSizeF(QGIS_STYLE["grid_annotation_size"])
    grid.setAnnotationFont(annotation_font)
    grid.setAnnotationFontColor(QColor(CAPTION_GRAY))
    grid.setAnnotationFrameDistance(2.0)
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


def add_map(
    layout: QgsLayout,
    layers: list,
    extent: tuple[float, float, float, float],
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    grid_interval: tuple[float, float] | None = None,
    precision: int = 2,
    rotation: float = 0.0,
    item_rotation: float = 0.0,
    item_rotation_adjust: bool = True,
    grid_annotations: bool = True,
) -> QgsLayoutItemMap:
    item = QgsLayoutItemMap(layout)
    item.attemptMove(QgsLayoutPoint(x, y, QgsUnitTypes.LayoutMillimeters))
    item.attemptResize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(item)
    xmin, xmax, ymin, ymax = extent
    rect = QgsRectangle(xmin, ymin, xmax, ymax)
    item.setLayers(layers)
    item.setExtent(rect)
    item.zoomToExtent(rect)
    if rotation:
        item.setMapRotation(rotation)
    item.setFrameEnabled(True)
    item.setFrameStrokeColor(QColor("#5B616A"))
    item.setFrameStrokeWidth(QgsLayoutMeasurement(QGIS_STYLE["frame_line_mm"], QgsUnitTypes.LayoutMillimeters))
    if item_rotation:
        item.setItemRotation(item_rotation, item_rotation_adjust)
    if grid_interval is not None:
        add_grid(item, grid_interval[0], grid_interval[1], precision=precision, annotations=grid_annotations)
    return item


def satellite_layer(name: str = "Esri World Imagery", *, opacity: float = 0.92) -> QgsRasterLayer | None:
    uri = f"type=xyz&url={SATELLITE_XYZ}"
    layer = QgsRasterLayer(uri, name, "wms")
    if not layer.isValid():
        return None
    layer.setOpacity(opacity)
    return layer


def with_satellite(science_layers: list, *, opacity: float = 0.92) -> list:
    sat = satellite_layer(opacity=opacity)
    valid_layers = [layer for layer in science_layers if layer is not None]
    ordered_top_to_bottom = list(reversed(valid_layers))
    return [layer for layer in [*ordered_top_to_bottom, sat] if layer is not None]


def style_line_layer(layer: QgsVectorLayer, color: str, width_mm: float, *, white_casing: bool = False) -> None:
    symbol = QgsLineSymbol()
    while symbol.symbolLayerCount():
        symbol.deleteSymbolLayer(0)
    if white_casing:
        casing = QgsSimpleLineSymbolLayer()
        casing.setColor(QColor("#FFFFFF"))
        casing.setWidth(width_mm + 0.45)
        casing.setWidthUnit(QgsUnitTypes.RenderMillimeters)
        symbol.appendSymbolLayer(casing)
    line = QgsSimpleLineSymbolLayer()
    line.setColor(QColor(color))
    line.setWidth(width_mm)
    line.setWidthUnit(QgsUnitTypes.RenderMillimeters)
    symbol.appendSymbolLayer(line)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def style_point_layer(layer: QgsVectorLayer, color: str, size_mm: float, *, shape: str = "circle") -> None:
    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": shape,
            "color": color,
            "outline_color": "#FFFFFF",
            "outline_width": "0.35",
            "outline_width_unit": "MM",
            "size": str(size_mm),
            "size_unit": "MM",
        }
    )
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def style_site_points(layer: QgsVectorLayer) -> None:
    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": UCHILE_BLUE,
            "outline_color": "#FFFFFF",
            "outline_width": "0.45",
            "outline_width_unit": "MM",
            "size": "3.1",
            "size_unit": "MM",
        }
    )
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    text_format = QgsTextFormat()
    font = QFont(QGIS_STYLE["font_family"])
    font.setPointSizeF(QGIS_STYLE["site_label_size"])
    font.setBold(True)
    text_format.setFont(font)
    text_format.setColor(QColor(TEXT_GRAY))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.0)
    buffer.setColor(QColor("#FFFFFF"))
    text_format.setBuffer(buffer)
    settings = QgsPalLayerSettings()
    settings.fieldName = "label"
    settings.placement = QgsPalLayerSettings.AroundPoint
    settings.dist = 1.2
    settings.setFormat(text_format)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)


def style_raster(layer: QgsRasterLayer, bounds: list[float], colors: list[str], *, opacity: float = 0.60) -> None:
    provider = layer.dataProvider()
    shader = QgsRasterShader()
    ramp = QgsColorRampShader()
    ramp.setColorRampType(QgsColorRampShader.Interpolated)
    items = []
    for value, color in zip(bounds, interpolate_colors(colors, len(bounds))):
        items.append(QgsColorRampShader.ColorRampItem(float(value), QColor(color), f"{value:.2f}"))
    ramp.setColorRampItemList(items)
    shader.setRasterShaderFunction(ramp)
    renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
    renderer.setOpacity(opacity)
    layer.setRenderer(renderer)


def interpolate_colors(colors: list[str], n: int) -> list[str]:
    if n <= 1:
        return colors[:1]
    if len(colors) == n:
        return colors
    out = []
    xs = np.linspace(0.0, len(colors) - 1, n)
    rgbs = np.array([[QColor(c).red(), QColor(c).green(), QColor(c).blue()] for c in colors], dtype=float)
    for x in xs:
        lo = int(math.floor(x))
        hi = min(len(colors) - 1, lo + 1)
        t = x - lo
        rgb = (1.0 - t) * rgbs[lo] + t * rgbs[hi]
        out.append("#%02X%02X%02X" % tuple(np.round(rgb).astype(int)))
    return out


def style_polygon_layer(layer: QgsVectorLayer, attr: str, bounds: list[float], colors: list[str], *, opacity: float = 0.68) -> None:
    ranges = []
    class_colors = interpolate_colors(colors, max(1, len(bounds) - 1))
    for lo, hi, color in zip(bounds[:-1], bounds[1:], class_colors):
        symbol = QgsFillSymbol.createSimple(
            {
                "color": color,
                "outline_color": "#50545A",
                "outline_width": "0.045",
                "outline_width_unit": "MM",
            }
        )
        symbol.setOpacity(opacity)
        ranges.append(QgsRendererRange(float(lo), float(hi), symbol, f"{lo:.2g}-{hi:.2g}"))
    renderer = QgsGraduatedSymbolRenderer(attr, ranges)
    renderer.setMode(QgsGraduatedSymbolRenderer.Custom)
    layer.setRenderer(renderer)


def add_colorbar(
    layout: QgsLayout,
    x: float,
    y: float,
    w: float,
    h: float,
    bounds: list[float],
    colors: list[str],
    label: str,
    *,
    fmt: str = "{:.2g}",
) -> None:
    class_colors = interpolate_colors(colors, max(1, len(bounds) - 1))
    n = len(class_colors)
    seg_h = h / n
    for i, color in enumerate(reversed(class_colors)):
        add_shape_rect(layout, x, y + i * seg_h, w, seg_h + 0.02, fill=color, outline=color)
    add_shape_rect(layout, x, y, w, h, fill="transparent", outline="#5B616A", outline_width=0.16)
    add_label(layout, label, x - 0.4, y - 10.0, 24.0, 10.0, size=QGIS_STYLE["colorbar_label_size"], bold=True, color=TEXT_GRAY)
    tick_values = [bounds[0], bounds[len(bounds) // 2], bounds[-1]]
    tick_y = [y + h, y + h / 2.0, y]
    for val, ty in zip(tick_values, tick_y):
        add_label(layout, fmt.format(val), x + w + 1.6, ty - 2.9, 19.0, 5.8, size=QGIS_STYLE["colorbar_tick_size"], color=CAPTION_GRAY)


def add_colorbar_horizontal(
    layout: QgsLayout,
    x: float,
    y: float,
    w: float,
    h: float,
    bounds: list[float],
    colors: list[str],
    label: str,
    *,
    fmt: str = "{:.2g}",
) -> None:
    class_colors = interpolate_colors(colors, max(1, len(bounds) - 1))
    n = len(class_colors)
    seg_w = w / n
    for i, color in enumerate(class_colors):
        add_shape_rect(layout, x + i * seg_w, y, seg_w + 0.02, h, fill=color, outline=color)
    add_shape_rect(layout, x, y, w, h, fill="transparent", outline="#5B616A", outline_width=0.16)
    add_label(layout, label, x, y - 7.0, w, 5.8, size=QGIS_STYLE["colorbar_label_size"] - 0.4, bold=True, color=TEXT_GRAY, align=Qt.AlignCenter)
    tick_values = [bounds[0], bounds[len(bounds) // 2], bounds[-1]]
    tick_x = [x, x + w / 2.0, x + w]
    for val, tx in zip(tick_values, tick_x):
        add_label(layout, fmt.format(val), tx - 5.0, y + h + 1.0, 10.0, 4.8, size=QGIS_STYLE["colorbar_tick_size"] - 0.5, color=CAPTION_GRAY, align=Qt.AlignCenter)


def load_bounds(path: Path) -> list[float]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [float(row["value"]) for row in reader]


def read_kmz_lines(path: Path) -> list[list[tuple[float, float]]]:
    if not path.exists():
        return []
    with zipfile.ZipFile(path, "r") as zf:
        kml_names = [name for name in zf.namelist() if name.lower().endswith(".kml")]
        if not kml_names:
            return []
        raw = zf.read(kml_names[0])
    root = ET.fromstring(raw)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    lines: list[list[tuple[float, float]]] = []
    for coords in root.findall(".//kml:coordinates", ns):
        pts = []
        text = coords.text or ""
        for token in text.replace("\n", " ").replace("\t", " ").split():
            parts = token.split(",")
            if len(parts) < 2:
                continue
            try:
                pts.append((float(parts[0]), float(parts[1])))
            except ValueError:
                continue
        if len(pts) >= 2:
            lines.append(pts)
    return lines


def line_bounds(lines: list[list[tuple[float, float]]]) -> tuple[float, float, float, float] | None:
    pts = [pt for line in lines for pt in line]
    if not pts:
        return None
    xs = [pt[0] for pt in pts]
    ys = [pt[1] for pt in pts]
    return min(xs), max(xs), min(ys), max(ys)


def make_line_layer(name: str, lines: list[list[tuple[float, float]]], color: str, width: float) -> QgsVectorLayer:
    layer = QgsVectorLayer("LineString?crs=EPSG:4326&field=name:string", name, "memory")
    provider = layer.dataProvider()
    feats = []
    for i, line in enumerate(lines):
        feat = QgsFeature(layer.fields())
        feat.setAttributes([f"{name}_{i}"])
        feat.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in line]))
        feats.append(feat)
    provider.addFeatures(feats)
    layer.updateExtents()
    style_line_layer(layer, color, width, white_casing=True)
    return layer


def make_extent_anchor_layer(name: str, extent: tuple[float, float, float, float]) -> QgsVectorLayer:
    xmin, xmax, ymin, ymax = extent
    layer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=name:string", name, "memory")
    provider = layer.dataProvider()
    feat = QgsFeature(layer.fields())
    feat.setAttributes([name])
    ring = [
        QgsPointXY(xmin, ymin),
        QgsPointXY(xmax, ymin),
        QgsPointXY(xmax, ymax),
        QgsPointXY(xmin, ymax),
        QgsPointXY(xmin, ymin),
    ]
    feat.setGeometry(QgsGeometry.fromPolygonXY([ring]))
    provider.addFeature(feat)
    layer.updateExtents()
    symbol = QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "0,0,0,0"})
    layer.renderer().setSymbol(symbol)
    return layer


def load_dem_layer(path: Path) -> QgsRasterLayer | None:
    if not path.exists():
        return None
    layer = QgsRasterLayer(str(path), "DEM")
    if not layer.isValid():
        return None
    layer.setOpacity(0.18)
    return layer


def qgis_csv_uri(path: Path, *, x: str = "lon", y: str = "lat") -> str:
    return f"file:///{path.as_posix()}?delimiter=,&xField={x}&yField={y}&crs=EPSG:4326"


def rasterize_dsha_csv(csv_path: Path, tif_path: Path, *, nx: int = 600, ny: int = 600) -> None:
    from scipy.interpolate import LinearNDInterpolator
    from scipy.ndimage import gaussian_filter

    df = pd.read_csv(csv_path)
    lon = df["lon"].to_numpy(float)
    lat = df["lat"].to_numpy(float)
    val = df["value"].to_numpy(float)
    ok = np.isfinite(lon) & np.isfinite(lat) & np.isfinite(val)
    lon, lat, val = lon[ok], lat[ok], val[ok]
    if len(val) < 3:
        raise RuntimeError(f"Not enough DSHA points in {csv_path}")

    xmin, xmax = float(lon.min()), float(lon.max())
    ymin, ymax = float(lat.min()), float(lat.max())
    gx = np.linspace(xmin, xmax, nx)
    gy = np.linspace(ymin, ymax, ny)
    cx = (gx[:-1] + gx[1:]) * 0.5
    cy = (gy[:-1] + gy[1:]) * 0.5
    xx, yy = np.meshgrid(cx, cy)
    interp = LinearNDInterpolator(np.c_[lon, lat], val, fill_value=np.nan)
    img = interp(xx, yy).astype("float32")
    nanmask = ~np.isfinite(img)
    tmp = img.copy()
    tmp[nanmask] = 0.0
    tmp = gaussian_filter(tmp, sigma=1.0, truncate=3.0)
    tmp[nanmask] = np.nan
    img = tmp.astype("float32")

    tif_path.parent.mkdir(parents=True, exist_ok=True)
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(tif_path), img.shape[1], img.shape[0], 1, gdal.GDT_Float32, ["COMPRESS=LZW"])
    if ds is None:
        raise RuntimeError(f"Could not create {tif_path}")
    dx = (xmax - xmin) / img.shape[1]
    dy = (ymax - ymin) / img.shape[0]
    ds.SetGeoTransform((xmin, dx, 0.0, ymax, 0.0, -dy))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    out = np.where(np.isfinite(img), img, NODATA)
    band.WriteArray(np.flipud(out))
    band.FlushCache()
    ds = None


def export_single_dsha_map(
    project: QgsProject,
    repo: Path,
    name: str,
    title: str,
    csv_path: Path,
    bounds: list[float],
    dem_path: Path,
    trace_path: Path,
) -> None:
    data_dir = repo / "figures_presentation_generated" / "src" / "qgis_data"
    tif_path = data_dir / "rasters" / f"{name}.tif"
    rasterize_dsha_csv(csv_path, tif_path)

    raster = QgsRasterLayer(str(tif_path), title)
    if not raster.isValid():
        raise RuntimeError(f"Invalid raster: {tif_path}")
    style_raster(raster, bounds, VIRIDIS_10, opacity=1.0)
    dem = load_dem_layer(dem_path)
    if dem is not None:
        dem.setOpacity(0.08)
    fsr = make_line_layer("FSR", read_kmz_lines(trace_path), FSR_MAP_TRACE, 0.64)

    layers = with_satellite([dem, raster, fsr], opacity=0.24)
    for layer in layers:
        project.addMapLayer(layer)

    layout = QgsLayout(project)
    layout.initializeDefaults()
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(112, 98, QgsUnitTypes.LayoutMillimeters))
    add_label(layout, title, 6.0, 3.0, 76.0, 7.0, size=8.2, bold=True, color=UCHILE_BLUE)
    add_map(layout, layers, (-71.01, -70.43, -33.81, -33.28), 14.0, 15.0, 70.0, 71.0, grid_interval=(0.20, 0.20), precision=2)
    add_colorbar(layout, 91.0, 24.0, 3.8, 48.0, bounds, VIRIDIS_10, "PGA p50\n[g]", fmt="{:.2f}")
    export_layout(layout, repo / "figures_presentation_generated" / "pdf" / name)


def export_dsha_maps(project: QgsProject, repo: Path) -> None:
    data_dir = repo / "figures_presentation_generated" / "src" / "qgis_data"
    bounds = load_bounds(data_dir / "dsha_pga_bounds.csv")
    dem_path = repo.parent / "Modelos" / "Actuales" / "Amenaza" / "Geometrias_base" / "output_SRTMGL1.tif"
    trace_path = repo.parent / "Modelos" / "Actuales" / "Amenaza" / "Geometrias_base" / "FSR completo.kmz"
    specs = [
        ("dsha_inter_pga", "Interplaca Mw 9.3", data_dir / "dsha_inter_pga.csv"),
        ("dsha_fsr_pga", "FSR Mw 7.5", data_dir / "dsha_fsr_pga.csv"),
        ("dsha_intra_pga", "Intraplaca Mw 8.0", data_dir / "dsha_intra_pga.csv"),
    ]
    for name, title, csv_path in specs:
        export_single_dsha_map(project, repo, name, title, csv_path, bounds, dem_path, trace_path)


def _read_poslist(text: str) -> np.ndarray:
    nums = [float(x) for x in text.strip().split()]
    return np.asarray(nums, dtype=float).reshape((-1, 3))


def _trace_from_shallow(llz: np.ndarray) -> list[tuple[float, float]]:
    shallow = llz[llz[:, 2] <= np.nanmin(llz[:, 2]) + 0.05]
    if len(shallow) < 2:
        shallow = llz
    xy = shallow[:, :2]
    _, idx = np.unique(np.round(xy, 7), axis=0, return_index=True)
    xy = xy[np.sort(idx)]
    if len(xy) < 2:
        return []
    center = xy.mean(axis=0)
    cov = (xy - center).T @ (xy - center)
    eigvals, eigvecs = np.linalg.eigh(cov)
    direction = eigvecs[:, np.argmax(eigvals)]
    order = np.argsort((xy - center) @ direction)
    return [(float(x), float(y)) for x, y in xy[order]]


def parse_rupture_xml(path: Path) -> tuple[list[list[tuple[float, float]]], list[tuple[float, float]], tuple[float, float] | None]:
    ns = {"nrml": "http://openquake.org/xmlns/nrml/0.5", "gml": "http://www.opengis.net/gml"}
    root = ET.parse(path).getroot()
    rup = list(root)[0]
    hypocenter = rup.find(".//nrml:hypocenter", ns)
    if hypocenter is None:
        hypocenter = rup.find(".//hypocenter")
    hypo = None
    if hypocenter is not None:
        try:
            hypo = (float(hypocenter.attrib["lon"]), float(hypocenter.attrib["lat"]))
        except Exception:
            hypo = None
    top = rup.find(".//nrml:faultTopEdge/gml:LineString/gml:posList", ns)
    bot = rup.find(".//nrml:faultBottomEdge/gml:LineString/gml:posList", ns)
    if top is not None and bot is not None:
        top_pts = _read_poslist(top.text)
        bot_pts = _read_poslist(bot.text)
        ring = [(float(x), float(y)) for x, y, _ in top_pts] + [(float(x), float(y)) for x, y, _ in bot_pts[::-1]]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        trace = [(float(x), float(y)) for x, y, _ in top_pts]
        return [ring], trace, hypo

    polys = []
    shallow = []
    for ks in rup.findall(".//nrml:kiteSurface", ns):
        profiles = ks.findall(".//nrml:profile", ns)
        if len(profiles) < 2:
            continue
        a = _read_poslist(profiles[0].find(".//gml:posList", ns).text)
        b = _read_poslist(profiles[1].find(".//gml:posList", ns).text)
        a_sh, a_dp = a[np.argmin(a[:, 2])], a[np.argmax(a[:, 2])]
        b_sh, b_dp = b[np.argmin(b[:, 2])], b[np.argmax(b[:, 2])]
        shallow.extend([a_sh[:2], b_sh[:2]])
        ring = [(a_sh[0], a_sh[1]), (b_sh[0], b_sh[1]), (b_dp[0], b_dp[1]), (a_dp[0], a_dp[1]), (a_sh[0], a_sh[1])]
        polys.append([(float(x), float(y)) for x, y in ring])
    if polys:
        shallow_arr = np.c_[np.asarray(shallow, dtype=float), np.zeros(len(shallow))]
        return polys, _trace_from_shallow(shallow_arr), hypo

    all_pts = np.vstack([_read_poslist(pl.text) for pl in rup.findall(".//gml:posList", ns)])
    trace = _trace_from_shallow(all_pts)
    return [], trace, hypo


def make_scenario_layers(repo: Path) -> tuple[list, list[tuple[str, str]], tuple[float, float]]:
    geom_dir = repo.parent / "Modelos_v2025" / "hazard" / "scenario" / "geometrias"
    specs = [
        ("FSR Mw 7.5", "NT_75_34.xml", FSR_MAP_TRACE),
        ("Intraplaca Mw 8.0", "rupture_intra_80.xml", INTRA_GOLD),
        ("Interplaca Mw 9.3", "rupture_inter_93.xml", INTER_BLUE),
    ]
    layers = []
    legend = []
    hypo_points = []
    fsr_trace = []
    for label, file_name, color in specs:
        polys, trace, hypo = parse_rupture_xml(geom_dir / file_name)
        poly_layer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=label:string", f"{label} superficie", "memory")
        feats = []
        for ring in polys:
            feat = QgsFeature(poly_layer.fields())
            feat.setAttributes([label])
            feat.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in ring]]))
            feats.append(feat)
        poly_layer.dataProvider().addFeatures(feats)
        poly_layer.updateExtents()
        is_fsr = "FSR" in label
        symbol = QgsFillSymbol.createSimple(
            {
                "color": color,
                "outline_color": "transparent" if is_fsr else color,
                "outline_width": "0.00" if is_fsr else "0.16",
                "outline_width_unit": "MM",
            }
        )
        symbol.setOpacity(0.18 if is_fsr else 0.16)
        poly_layer.setRenderer(QgsSingleSymbolRenderer(symbol))

        line_layer = make_line_layer(f"{label} traza", [trace], color, 0.82 if is_fsr else 0.58)
        layers.extend([poly_layer, line_layer])
        legend.append((label, color))
        if is_fsr:
            fsr_trace = trace
        if hypo is not None:
            hypo_points.append((label, color, hypo[0], hypo[1]))

    fsr_hypo_lon = -70.5354949075
    if fsr_trace:
        lat_target = -33.5767391157
        closest_lon = min(fsr_trace, key=lambda p: abs(p[1] - lat_target))[0]
        dlon = (1.0 / math.tan(math.radians(34.0))) / (111.32 * math.cos(math.radians(lat_target)))
        fsr_hypo_lon = closest_lon + dlon
    hypo_points = [
        ("Epicentro interplaca", INTER_BLUE, -72.0, -33.4),
        ("Epicentro intraplaca", INTRA_GOLD, -70.6373168, -33.4858633),
        ("Epicentro FSR", FSR_MAP_TRACE, fsr_hypo_lon, -33.5767391157),
    ]
    pts_layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string&field=kind:string", "Epicentros", "memory")
    feats = []
    for name, color, lon, lat in hypo_points:
        feat = QgsFeature(pts_layer.fields())
        feat.setAttributes([name, name])
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        feats.append(feat)
    pts_layer.dataProvider().addFeatures(feats)
    pts_layer.updateExtents()
    categories = []
    marker_specs = [
        ("Epicentro interplaca", INTER_BLUE, "star"),
        ("Epicentro intraplaca", INTRA_GOLD, "diamond"),
        ("Epicentro FSR", FSR_MAP_TRACE, "triangle"),
    ]
    for name, color, shape in marker_specs:
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": shape,
                "color": color,
                "outline_color": "#1E1E1E",
                "outline_width": "0.18",
                "outline_width_unit": "MM",
                "size": "4.0",
                "size_unit": "MM",
            }
        )
        categories.append(QgsRendererCategory(name, symbol, name))
    pts_layer.setRenderer(QgsCategorizedSymbolRenderer("kind", categories))
    layers.append(pts_layer)

    zoom_ring = [(-70.95, -33.82), (-70.22, -33.82), (-70.22, -33.00), (-70.95, -33.00), (-70.95, -33.82)]
    zoom_layer = make_line_layer("Recuadro zoom", [zoom_ring], "#1E1E1E", 0.42)
    symbol = zoom_layer.renderer().symbol()
    symbol.symbolLayer(0).setPenStyle(Qt.DashLine)
    layers.append(zoom_layer)
    return layers, legend, (fsr_hypo_lon, -33.5767391157)


def export_scenario_geometry(project: QgsProject, repo: Path) -> None:
    layers, legend, _ = make_scenario_layers(repo)
    layers = with_satellite(layers, opacity=0.92)
    for layer in layers:
        project.addMapLayer(layer)
    layout = QgsLayout(project)
    layout.initializeDefaults()
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(166, 112, QgsUnitTypes.LayoutMillimeters))
    add_label(layout, "Geometria de escenarios deterministas", 6, 3, 124, 7, size=QGIS_STYLE["title_size"], bold=True, color=UCHILE_BLUE)
    add_map(layout, layers, (-81.0, -68.2, -36.0, -25.0), 14, 17, 84, 71, grid_interval=(3.0, 2.5), precision=1)
    add_map(layout, layers, (-70.95, -70.22, -33.82, -33.00), 110, 17, 48, 71, grid_interval=(0.35, 0.40), precision=1)
    add_label(layout, "(a) Vista regional", 15, 10, 54, 6, size=QGIS_STYLE["panel_title_size"], bold=True, color=TEXT_GRAY)
    add_label(layout, "(b) Zoom: Santiago", 111, 10, 46, 6, size=QGIS_STYLE["panel_title_size"], bold=True, color=TEXT_GRAY)
    export_layout(layout, repo / "figures_presentation_generated" / "pdf" / "fig_4_2_escenarios_simulados")


def prepare_aalr_gpkg(repo: Path) -> tuple[Path, tuple[float, float, float, float], list[float]]:
    import geopandas as gpd

    data_dir = repo / "figures_presentation_generated" / "src" / "qgis_data"
    csv_path = data_dir / "aalr_effect_objectid.csv"
    bounds_path = data_dir / "aalr_effect_bounds.csv"
    shp_path = repo.parent / "Modelos" / "Actuales" / "Riesgo" / "Bases de datos" / "Valores comerciales" / "Valores comerciales" / "Manzanas_VC_UFm2_DS.shp"
    out_path = data_dir / "aalr_effect_objectid.gpkg"
    if out_path.exists():
        out_path.unlink()
    gdf = gpd.read_file(shp_path).to_crs("EPSG:4326")
    obj_col = next((c for c in gdf.columns if str(c).lower() == "objectid"), None)
    if obj_col is None:
        raise RuntimeError("OBJECTID field not found in manzanas shapefile")
    gdf["OBJECTID_INT"] = pd.to_numeric(gdf[obj_col], errors="coerce").astype("Int64")
    df = pd.read_csv(csv_path)
    merged = gdf.merge(df, on="OBJECTID_INT", how="inner")
    merged = merged[np.isfinite(pd.to_numeric(merged["dFSR_AALR_NAC_pct"], errors="coerce")) & np.isfinite(pd.to_numeric(merged["dFSR_AALR_HAZ_pct"], errors="coerce"))].copy()
    for col in list(merged.columns):
        if str(col).lower() == "fid":
            merged = merged.drop(columns=[col])
    merged.to_file(out_path, layer="aalr_effect", driver="GPKG", index=False)
    bounds = load_bounds(bounds_path)
    win = merged.cx[-70.57:-70.47, :]
    if win.empty:
        win = merged
    xmin, ymin, xmax, ymax = win.total_bounds
    pad = (ymax - ymin) * 0.03 if ymax > ymin else 0.01
    return out_path, (-70.57, -70.47, float(ymin - pad), float(ymax + pad)), bounds


def export_aalr_panel_png(project: QgsProject, layers: list, extent: tuple[float, float, float, float], out_png: Path) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    if out_png.exists():
        out_png.unlink()
    xmin, xmax, ymin, ymax = extent
    map_h_mm = 118.0
    map_ratio = max(0.16, min(0.34, (xmax - xmin) / max(ymax - ymin, 1e-9)))
    map_w_mm = map_h_mm * map_ratio
    page_margin_mm = 1.0
    layout = QgsLayout(project)
    layout.initializeDefaults()
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(map_w_mm + 2 * page_margin_mm, map_h_mm + 2 * page_margin_mm, QgsUnitTypes.LayoutMillimeters))
    add_map(layout, layers, extent, page_margin_mm, page_margin_mm, map_w_mm, map_h_mm, grid_interval=(0.03, 0.06), precision=2, grid_annotations=False)
    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = 600
    result = exporter.exportToImage(str(out_png), settings)
    if result != QgsLayoutExporter.Success:
        raise RuntimeError(f"QGIS AALR panel export failed for {out_png.name}: {result}")


def compose_aalr_stacked_figure(
    repo: Path,
    nac_png: Path,
    haz_png: Path,
    bounds: list[float],
    extent: tuple[float, float, float, float],
) -> None:
    import base64
    from io import BytesIO

    from PIL import Image, ImageColor, ImageDraw, ImageFont

    def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
        candidates = [
            Path(r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size)
        return ImageFont.load_default()

    def fit_panel(path: Path, size: tuple[int, int]) -> Image.Image:
        img = Image.open(path).convert("RGB").rotate(90, expand=True)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        panel = Image.new("RGB", size, "white")
        panel.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
        return panel

    def add_geo_labels(x0: int, y0: int, size: tuple[int, int]) -> None:
        xmin, xmax, ymin, ymax = extent
        w, h = size
        small_font = font(31)
        axis_color = ImageColor.getrgb("#4D535C")
        degree = "\N{DEGREE SIGN}"
        lat_ticks = [(ymax, x0), ((ymax + ymin) * 0.5, x0 + w // 2), (ymin, x0 + w)]
        lon_ticks = [(xmax, y0), ((xmax + xmin) * 0.5, y0 + h // 2), (xmin, y0 + h)]
        for value, tx in lat_ticks:
            draw.text((tx, y0 + h + 27), f"{value:.2f}{degree}", fill=axis_color, font=small_font, anchor="mm")
        for value, ty in lon_ticks:
            draw.text((x0 - 12, ty), f"{abs(value):.2f}{degree}W", fill=axis_color, font=small_font, anchor="rm")

    rotated_probe = Image.open(nac_png).convert("RGB").rotate(90, expand=True)
    panel_w = 2200
    panel_h = max(360, int(round(panel_w / (rotated_probe.width / rotated_probe.height))))
    panel_size = (panel_w, panel_h)
    left_margin, right_margin = 150, 80
    canvas_w = left_margin + panel_w + right_margin
    title_y = 48
    nac_title_y = 136
    nac_y = 172
    inter_panel_gap = 110
    haz_title_y = nac_y + panel_h + inter_panel_gap
    haz_y = haz_title_y + 36
    cbar_y = haz_y + panel_h + 120
    canvas_h = cbar_y + 160
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(canvas)
    blue = ImageColor.getrgb(UCHILE_BLUE)
    text = ImageColor.getrgb(TEXT_GRAY)
    caption = ImageColor.getrgb(CAPTION_GRAY)

    draw.text((55, title_y), "Cambio relativo de AALR al incorporar la FSR", fill=blue, font=font(46, bold=True))
    draw.text((canvas_w - 300, title_y + 2), "N", fill=caption, font=font(42, bold=True))
    draw.text((canvas_w - 232, title_y), "\u2190", fill=caption, font=font(42, bold=True))
    draw.text((canvas_w // 2, nac_title_y), "Nacional", fill=text, font=font(42, bold=True), anchor="mm")
    draw.text((canvas_w // 2, haz_title_y), "HAZUS", fill=text, font=font(42, bold=True), anchor="mm")

    nac_pos = (left_margin, nac_y)
    haz_pos = (left_margin, haz_y)
    canvas.paste(fit_panel(nac_png, panel_size), nac_pos)
    canvas.paste(fit_panel(haz_png, panel_size), haz_pos)
    add_geo_labels(*nac_pos, panel_size)
    add_geo_labels(*haz_pos, panel_size)

    cbar_w, cbar_h = 650, 54
    cbar_x = (canvas_w - cbar_w) // 2
    draw.text((cbar_x + cbar_w // 2, cbar_y - 54), "Incremento relativo [%]", fill=text, font=font(38, bold=True), anchor="mm")
    colors = interpolate_colors(AALR_10, max(1, len(bounds) - 1))
    seg_w = cbar_w / len(colors)
    for i, color in enumerate(colors):
        x0 = round(cbar_x + i * seg_w)
        x1 = round(cbar_x + (i + 1) * seg_w)
        draw.rectangle([x0, cbar_y, x1, cbar_y + cbar_h], fill=ImageColor.getrgb(color))
    draw.rectangle([cbar_x, cbar_y, cbar_x + cbar_w, cbar_y + cbar_h], outline=ImageColor.getrgb("#5B616A"), width=3)
    ticks = [(bounds[0], cbar_x), (bounds[len(bounds) // 2], cbar_x + cbar_w // 2), (bounds[-1], cbar_x + cbar_w)]
    for val, tx in ticks:
        draw.text((tx, cbar_y + cbar_h + 50), f"{val:.1f}", fill=caption, font=font(36), anchor="mm")

    out_stem = repo / "figures_presentation_generated" / "pdf" / "fig_5_41_aalr_cambio_rel_pct"
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    png_path = out_stem.with_suffix(".png")
    pdf_path = out_stem.with_suffix(".pdf")
    svg_path = out_stem.with_suffix(".svg")
    for path in (png_path, pdf_path, svg_path):
        if path.exists():
            path.unlink()
    canvas.save(png_path, dpi=(300, 300))
    canvas.save(pdf_path, "PDF", resolution=300.0)
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    svg_path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">'
        f'<image href="data:image/png;base64,{encoded}" width="{canvas_w}" height="{canvas_h}"/></svg>\n',
        encoding="utf-8",
    )


def export_aalr_map(project: QgsProject, repo: Path) -> None:
    gpkg, extent, bounds = prepare_aalr_gpkg(repo)
    dem_path = repo.parent / "Modelos" / "Actuales" / "Amenaza" / "Geometrias_base" / "output_SRTMGL1.tif"
    trace_path = repo.parent / "Modelos" / "Actuales" / "Amenaza" / "Geometrias_base" / "FSR completo.kmz"
    dem = load_dem_layer(dem_path)
    if dem is not None:
        dem.setOpacity(0.08)
    fsr_lines = read_kmz_lines(trace_path)
    fsr_bounds = line_bounds(fsr_lines)
    if fsr_bounds is not None:
        xmin, xmax, ymin, ymax = extent
        fxmin, fxmax, fymin, fymax = fsr_bounds
        uxmin, uxmax = min(xmin, fxmin), max(xmax, fxmax)
        uymin, uymax = min(ymin, fymin), max(ymax, fymax)
        xpad = max((uxmax - uxmin) * 0.10, 0.010)
        ypad = max((uymax - uymin) * 0.18, 0.065)
        extent = (uxmin - xpad, uxmax + xpad, uymin - ypad, uymax + ypad)
    fsr = make_line_layer("FSR", fsr_lines, FSR_MAP_TRACE, 0.46)
    extent_anchor = make_extent_anchor_layer("AALR extent", extent)

    nac = QgsVectorLayer(f"{gpkg.as_posix()}|layername=aalr_effect", "Nacional", "ogr")
    haz = QgsVectorLayer(f"{gpkg.as_posix()}|layername=aalr_effect", "HAZUS", "ogr")
    if not nac.isValid() or not haz.isValid():
        raise RuntimeError("Could not load AALR GeoPackage")
    style_polygon_layer(nac, "dFSR_AALR_NAC_pct", bounds, AALR_10, opacity=1.0)
    style_polygon_layer(haz, "dFSR_AALR_HAZ_pct", bounds, AALR_10, opacity=1.0)
    nac_layers = with_satellite([extent_anchor, dem, fsr, nac], opacity=0.18)
    haz_layers = with_satellite([extent_anchor, dem, fsr, haz], opacity=0.18)
    added_layer_ids = set()
    for layer in [*nac_layers, *haz_layers]:
        if layer is not None:
            if layer.id() in added_layer_ids:
                continue
            added_layer_ids.add(layer.id())
            project.addMapLayer(layer)

    panel_dir = repo / "figures_presentation_generated" / "src" / "qgis_data" / "aalr_panels"
    nac_png = panel_dir / "nacional.png"
    haz_png = panel_dir / "hazus.png"
    export_aalr_panel_png(project, nac_layers, extent, nac_png)
    export_aalr_panel_png(project, haz_layers, extent, haz_png)
    compose_aalr_stacked_figure(repo, nac_png, haz_png, bounds, extent)


def export_site_map(project: QgsProject, repo: Path) -> None:
    data_dir = repo / "figures_presentation_generated" / "src" / "qgis_data"
    csv_path = data_dir / "control_sites.csv"
    trace_path = repo.parent / "Modelos" / "Actuales" / "Amenaza" / "Geometrias_base" / "FSR completo.kmz"
    dem_path = repo.parent / "Modelos" / "Actuales" / "Amenaza" / "Geometrias_base" / "output_SRTMGL1.tif"
    pts = QgsVectorLayer(qgis_csv_uri(csv_path), "Sitios", "delimitedtext")
    if not pts.isValid():
        raise RuntimeError(f"Invalid site CSV: {csv_path}")
    style_site_points(pts)
    dem = load_dem_layer(dem_path)
    fsr = make_line_layer("FSR", read_kmz_lines(trace_path), FSR_MAP_TRACE, 0.56)
    layers = with_satellite([dem, fsr, pts], opacity=0.92)
    for layer in layers:
        if layer is not None:
            project.addMapLayer(layer)
    df = pd.read_csv(csv_path)
    xmin, xmax = df["lon"].min() - 0.07, df["lon"].max() + 0.07
    ymin, ymax = df["lat"].min() - 0.07, df["lat"].max() + 0.07
    extent = (float(min(xmin, -70.72)), float(max(xmax, -70.42)), float(min(ymin, -33.70)), float(max(ymax, -33.34)))

    layout = QgsLayout(project)
    layout.initializeDefaults()
    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(82, 74, QgsUnitTypes.LayoutMillimeters))
    add_label(layout, "Sitios de control", 5, 3, 50, 7, size=8.0, bold=True, color=UCHILE_BLUE)
    add_map(layout, layers, extent, 12, 12, 58, 55, grid_interval=(0.12, 0.12), precision=1)
    export_layout(layout, repo / "figures_presentation_generated" / "pdf" / "qgis_site_map_control_sites")


def copy_qgis_outputs(repo: Path) -> None:
    gen = repo / "figures_presentation_generated"
    for pdf in (gen / "pdf").glob("*.pdf"):
        stem = pdf.stem
        svg = pdf.with_suffix(".svg")
        png = pdf.with_suffix(".png")
        if svg.exists():
            (gen / "svg" / svg.name).write_bytes(svg.read_bytes())
            if svg != gen / "svg" / svg.name:
                try:
                    svg.unlink()
                except OSError:
                    pass
        if png.exists():
            (gen / "png" / png.name).write_bytes(png.read_bytes())
            if png != gen / "png" / png.name:
                try:
                    png.unlink()
                except OSError:
                    pass


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: export_qgis_maps.py REPO_ROOT", file=sys.stderr)
        return 2
    repo = Path(sys.argv[1]).resolve()
    QgsApplication.setPrefixPath(r"C:\Program Files\QGIS 3.40.8\apps\qgis-ltr", True)
    app = QgsApplication([], False)
    app.initQgis()
    try:
        project = QgsProject.instance()
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        export_dsha_maps(project, repo)
        export_scenario_geometry(project, repo)
        export_aalr_map(project, repo)
        export_site_map(project, repo)
        copy_qgis_outputs(repo)
    finally:
        app.exitQgis()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
