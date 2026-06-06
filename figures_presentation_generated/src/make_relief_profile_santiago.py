from __future__ import annotations

import argparse
import math
from pathlib import Path
from urllib.request import urlretrieve

import h5py
import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "figures_presentation_generated"
CACHE_DIR = GEN / "src" / "tile_cache" / "gmt_earth_relief"
DATA_DIR = GEN / "data" / "processed"
PDF_DIR = GEN / "pdf"
PNG_DIR = GEN / "png"

SANTIAGO_LON = -70.66246
SANTIAGO_LAT = -33.45891

GMT_DATA_BASE = "https://fct-gmt.ualg.pt/gmt/data"
GMT_RESOLUTION_BYTES = {
    "15s": 3_100_000_000,
    "30s": 864_000_000,
    "01m": 238_000_000,
    "02m": 65_000_000,
    "03m": 30_000_000,
    "04m": 17_000_000,
    "05m": 11_000_000,
    "06m": 8_000_000,
    "10m": 3_000_000,
}


def haversine_km(lon0: np.ndarray, lat0: np.ndarray, lon1: np.ndarray, lat1: np.ndarray) -> np.ndarray:
    radius_km = 6371.0
    lon0_rad = np.radians(lon0)
    lat0_rad = np.radians(lat0)
    lon1_rad = np.radians(lon1)
    lat1_rad = np.radians(lat1)
    dlon = lon1_rad - lon0_rad
    dlat = lat1_rad - lat0_rad
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat0_rad) * np.cos(lat1_rad) * np.sin(dlon / 2.0) ** 2
    return 2.0 * radius_km * np.arcsin(np.sqrt(a))


def cumulative_distance_km(lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
    try:
        from pyproj import Geod

        geod = Geod(ellps="WGS84")
        _, _, dist_m = geod.inv(lons[:-1], lats[:-1], lons[1:], lats[1:])
        steps = np.asarray(dist_m, dtype=float) / 1000.0
    except Exception:
        steps = haversine_km(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return np.concatenate([[0.0], np.cumsum(steps)])


def local_x_from_santiago_km(lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
    radius_km = 6371.0
    return radius_km * math.cos(math.radians(SANTIAGO_LAT)) * np.radians(lons - SANTIAGO_LON)


def requested_resolution_chain(resolution: str) -> list[str]:
    chain = [resolution, "30s", "01m", "02m", "03m", "06m", "10m"]
    seen: set[str] = set()
    return [item for item in chain if not (item in seen or seen.add(item))]


def download_gmt_relief_grid(resolution: str, *, max_direct_download_mb: int = 300) -> Path:
    estimated = GMT_RESOLUTION_BYTES.get(resolution)
    if estimated is not None and estimated > max_direct_download_mb * 1024 * 1024:
        raise RuntimeError(
            f"GMT earth_relief_{resolution}_g.grd pesa ~{estimated / 1024**2:.0f} MB; "
            f"se omite en fallback directo."
        )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    grid_path = CACHE_DIR / f"earth_relief_{resolution}_g.grd"
    if grid_path.exists() and grid_path.stat().st_size > 0:
        return grid_path
    url = f"{GMT_DATA_BASE}/earth_relief_{resolution}_g.grd"
    print(f"Descargando {url}")
    urlretrieve(url, grid_path)
    return grid_path


def sample_hdf5_grid(grid_path: Path, lons: np.ndarray, lats: np.ndarray) -> np.ndarray:
    with h5py.File(grid_path, "r") as handle:
        lon_grid = np.asarray(handle["lon"][:], dtype=float)
        lat_grid = np.asarray(handle["lat"][:], dtype=float)
        z_dataset = handle["z"]
        fill_value = float(z_dataset.attrs.get("_FillValue", [-32768])[0])
        scale_factor = float(z_dataset.attrs.get("scale_factor", [1.0])[0])

        row_float = np.interp(lats, lat_grid, np.arange(lat_grid.size))
        col_float = np.interp(lons, lon_grid, np.arange(lon_grid.size))
        row0 = np.floor(row_float).astype(int)
        col0 = np.floor(col_float).astype(int)
        row1 = np.clip(row0 + 1, 0, lat_grid.size - 1)
        col1 = np.clip(col0 + 1, 0, lon_grid.size - 1)
        row0 = np.clip(row0, 0, lat_grid.size - 1)
        col0 = np.clip(col0, 0, lon_grid.size - 1)

        r_min, r_max = int(row0.min()), int(row1.max())
        c_min, c_max = int(col0.min()), int(col1.max())
        z = np.asarray(z_dataset[r_min : r_max + 1, c_min : c_max + 1], dtype=float)
        z[z == fill_value] = np.nan
        z *= scale_factor

        rr0 = row0 - r_min
        rr1 = row1 - r_min
        cc0 = col0 - c_min
        cc1 = col1 - c_min
        wy = row_float - row0
        wx = col_float - col0
        z00 = z[rr0, cc0]
        z01 = z[rr0, cc1]
        z10 = z[rr1, cc0]
        z11 = z[rr1, cc1]
        return (1 - wy) * ((1 - wx) * z00 + wx * z01) + wy * ((1 - wx) * z10 + wx * z11)


def build_relief_profile(
    lat: float = SANTIAGO_LAT,
    lon_min: float = -80.0,
    lon_max: float = -64.0,
    sample_km: float = 2.0,
    resolution: str = "15s",
) -> pd.DataFrame:
    total_km = float(haversine_km(np.array([lon_min]), np.array([lat]), np.array([lon_max]), np.array([lat]))[0])
    n_points = max(int(math.ceil(total_km / sample_km)) + 1, 101)
    lons = np.linspace(lon_min, lon_max, n_points)
    lats = np.full(n_points, lat, dtype=float)

    last_error: Exception | None = None
    used_resolution: str | None = None
    relief_m: np.ndarray | None = None
    for candidate in requested_resolution_chain(resolution):
        try:
            grid_path = download_gmt_relief_grid(candidate)
            relief_m = sample_hdf5_grid(grid_path, lons, lats)
            used_resolution = candidate
            break
        except Exception as exc:
            print(f"No se pudo usar GMT earth_relief {candidate}: {exc}")
            last_error = exc
    if relief_m is None or used_resolution is None:
        raise RuntimeError("No se pudo construir el perfil de relieve GMT.") from last_error

    nan_count = int(np.count_nonzero(~np.isfinite(relief_m)))
    if nan_count:
        if nan_count / relief_m.size > 0.03:
            raise RuntimeError(f"Perfil de relieve con demasiados NaN: {nan_count}/{relief_m.size}")
        relief_m = pd.Series(relief_m).interpolate(limit_direction="both").to_numpy()

    profile = pd.DataFrame(
        {
            "lon": lons,
            "lat": lats,
            "distance_km": cumulative_distance_km(lons, lats),
            "x_santiago_km": local_x_from_santiago_km(lons, lats),
            "relief_m": relief_m,
            "resolution": used_resolution,
        }
    )
    if len(profile) <= 100:
        raise RuntimeError("El perfil debe tener mas de 100 puntos.")
    if float(profile["relief_m"].min()) > -500:
        print("WARNING: el perfil no muestra batimetria oceánica profunda.")
    if float(profile["relief_m"].max()) < 1000:
        print("WARNING: el perfil no muestra topografia andina significativa.")
    print(
        f"Resolucion usada: {used_resolution}; "
        f"relief_m min={profile['relief_m'].min():.1f}, max={profile['relief_m'].max():.1f}"
    )
    return profile


def plot_relief_profile(ax: mpl.axes.Axes, profile_df: pd.DataFrame, *, x: str = "distance_km", show_zero: bool = True) -> None:
    x_values = profile_df[x].to_numpy(dtype=float)
    relief = profile_df["relief_m"].to_numpy(dtype=float)
    ax.fill_between(x_values, 0, relief, where=relief < 0, color="#8DB7D8", alpha=0.50, linewidth=0)
    ax.fill_between(x_values, 0, relief, where=relief >= 0, color="#D7C39A", alpha=0.62, linewidth=0)
    ax.plot(x_values, relief, color="#30343A", linewidth=1.0)
    if show_zero:
        ax.axhline(0.0, color="#6F7780", linewidth=0.7)
    ax.set_ylabel("Relieve [m]")
    ax.set_xlabel("Distancia desde 80°W [km]" if x == "distance_km" else "Distancia E-O [km]")


def output_stem(lat: float, lon_min: float, lon_max: float) -> str:
    lat_token = f"{abs(lat):.3f}".replace(".", "p")
    return f"relief_profile_latS{lat_token}_lon{int(abs(lon_min))}W_{int(abs(lon_max))}W"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=SANTIAGO_LAT)
    parser.add_argument("--lon-min", type=float, default=-80.0)
    parser.add_argument("--lon-max", type=float, default=-64.0)
    parser.add_argument("--sample-km", type=float, default=2.0)
    parser.add_argument("--resolution", default="15s")
    parser.add_argument("--x-axis", choices=["distance_km", "lon", "x_santiago_km"], default="distance_km")
    args = parser.parse_args()

    profile = build_relief_profile(args.lat, args.lon_min, args.lon_max, args.sample_km, args.resolution)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    stem = output_stem(args.lat, args.lon_min, args.lon_max)
    csv_path = DATA_DIR / f"{stem}.csv"
    profile.to_csv(csv_path, index=False)

    fig, ax = plt.subplots(figsize=(6.4, 2.1))
    plot_relief_profile(ax, profile, x=args.x_axis)
    ax.set_title(f"Perfil de relieve a latitud de Santiago ({args.lat:.3f}°)")
    ax.grid(color="#DDE3EA", linewidth=0.6, alpha=0.8)
    fig.tight_layout()
    fig.savefig(PDF_DIR / f"{stem}.pdf")
    fig.savefig(PNG_DIR / f"{stem}.png", dpi=300)
    print(csv_path.as_posix())


if __name__ == "__main__":
    main()
