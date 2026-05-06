"""
atlite-based VRE (variable renewable energy) trace builder for Timor-Leste.

Provides per-bus hourly capacity-factor traces for solar PV and onshore wind,
computed from an ERA5 cutout via the atlite library. One trace per bus
coordinate (9 substations + 2 power-plant buses = 11 traces).

If the model horizon exceeds the cutout weather window (default 15 years
starting 2010), the weather pattern is repeated from the start (wrap-around).

The CDS API key is required to download a fresh cutout. See the project
README for setup instructions.
"""

import os
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

# atlite is imported lazily inside the cutout function so the rest of the
# project still imports cleanly when atlite is uninstalled (Renewables Ninja
# mode does not need it).


# ============================================================================
# Bus coordinate helpers
# ============================================================================

def bus_coords_for_atlite() -> Dict[str, Tuple[float, float]]:
    """
    Return a dict of bus_name → (longitude, latitude) for every bus that should
    receive an atlite-derived VRE trace.

    Combines the 9 substation coordinates and 2 power-plant coordinates from
    ``timor_leste_config``.

    Returns
    -------
    dict[str, tuple[float, float]]
        ``{"Dili": (125.61, -8.56), "Betano": (125.73, -9.15), ...}``
    """
    from timor_leste_config import SUBSTATIONS, POWER_PLANTS

    coords: Dict[str, Tuple[float, float]] = {}
    for name, (lat, lon, _v) in SUBSTATIONS.items():
        coords[name] = (float(lon), float(lat))
    for name, plant in POWER_PLANTS.items():
        lat, lon = plant["coordinates"]
        coords[name] = (float(lon), float(lat))
    return coords


# ============================================================================
# Cutout management
# ============================================================================

def compute_cutout_year_range(
    model_start_year: int,
    model_end_year_exclusive: int,
    weather_start_year: int,
    weather_max_years: int,
) -> Tuple[int, int]:
    """
    Decide which calendar years the cutout should cover.

    The weather window starts at ``weather_start_year`` and spans at most
    ``weather_max_years`` years OR the model horizon, whichever is shorter.
    A model horizon longer than the cutout window is handled later by tiling
    the weather trace with a wrap-around.

    Parameters
    ----------
    model_start_year, model_end_year_exclusive : int
        Model horizon (inclusive start, exclusive end).
    weather_start_year : int
        First year of weather data the cutout should cover.
    weather_max_years : int
        Maximum span of the cutout in years.

    Returns
    -------
    (cutout_start, cutout_end_inclusive) : tuple[int, int]
    """
    horizon_years = model_end_year_exclusive - model_start_year
    span = min(horizon_years, weather_max_years)
    span = max(span, 1)
    cutout_start = weather_start_year
    cutout_end_inclusive = cutout_start + span - 1
    return cutout_start, cutout_end_inclusive


def get_or_create_cutout(
    cutout_start_year: int,
    cutout_end_year_inclusive: int,
    config_dict: dict,
):
    """
    Load a cached atlite cutout if present, otherwise create + prepare one.

    The cutout filename is derived from the weather year range and stored
    under ``config_dict["cutout_dir"]``. Re-runs reuse the cache.

    Returns
    -------
    atlite.Cutout
    """
    try:
        import atlite
    except ImportError as exc:
        raise ImportError(
            "atlite is not installed. Install it with `pip install atlite cdsapi`."
        ) from exc

    cutout_dir = config_dict["cutout_dir"]
    os.makedirs(cutout_dir, exist_ok=True)
    fname = config_dict["cutout_name_template"].format(
        year_start=cutout_start_year,
        year_end=cutout_end_year_inclusive,
    )
    path = os.path.join(cutout_dir, fname)

    bbox = config_dict["bbox"]
    time_slice = slice(f"{cutout_start_year}-01-01", f"{cutout_end_year_inclusive}-12-31")

    cutout_kwargs = dict(
        path=path,
        module=config_dict.get("module", "era5"),
        x=slice(bbox["x_min"], bbox["x_max"]),
        y=slice(bbox["y_min"], bbox["y_max"]),
        time=time_slice,
    )

    cutout = atlite.Cutout(**cutout_kwargs)

    if not os.path.exists(path):
        print(f"  [atlite] Cutout not cached - preparing {path}")
        print(f"  [atlite] Range: {time_slice.start} -> {time_slice.stop}")
        print(f"  [atlite] BBox:  x=[{bbox['x_min']}, {bbox['x_max']}], y=[{bbox['y_min']}, {bbox['y_max']}]")
        print(f"  [atlite] Downloading ERA5 from CDS - first request may sit in CDS queue for several minutes...")

        prepare_kwargs = {}
        for key in ("data_format", "monthly_requests", "concurrent_requests", "show_progress"):
            if key in config_dict:
                prepare_kwargs[key] = config_dict[key]

        try:
            cutout.prepare(**prepare_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"atlite cutout preparation failed. Common causes:\n"
                f"  1. Missing CDS API key — create ~/.cdsapirc per the README.\n"
                f"  2. CDS server queue / network error — try again later.\n"
                f"  3. data_format='grib' requires the ecCodes C library; on Windows\n"
                f"     prefer data_format='netcdf' (set in config.ATLITE_CONFIG).\n"
                f"  4. Disk space exhausted at {path}.\n"
                f"Original error: {exc}"
            ) from exc
    else:
        print(f"  [atlite] Reusing cached cutout: {path}")

    return cutout


# ============================================================================
# Per-bus VRE trace builders
# ============================================================================

def _one_hot_layout_at_point(cutout, x: float, y: float):
    """
    Build a 0/1 atlite layout DataArray with 1.0 at the nearest grid cell to
    (x, y) and 0.0 everywhere else.

    Used so ``cutout.pv(..., layout=layout, per_unit=True)`` returns a
    capacity-factor time series sampled at the bus location.
    """
    import xarray as xr

    x_coords = cutout.coords["x"].values
    y_coords = cutout.coords["y"].values

    ix = int(np.argmin(np.abs(x_coords - x)))
    iy = int(np.argmin(np.abs(y_coords - y)))

    grid_shape = (len(y_coords), len(x_coords))
    arr = np.zeros(grid_shape, dtype=float)
    arr[iy, ix] = 1.0

    return xr.DataArray(
        arr,
        dims=("y", "x"),
        coords={"y": y_coords, "x": x_coords},
    )


def _series_from_atlite_result(result) -> pd.Series:
    """Convert an atlite per_unit time-series result into a clean float series."""
    s = result.to_pandas()
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s = s.astype(float).clip(lower=0.0, upper=1.0)
    s.index.name = "time"
    return s


def build_atlite_solar_traces(
    cutout,
    bus_coords: Dict[str, Tuple[float, float]],
    config_dict: dict,
) -> pd.DataFrame:
    """
    Compute per-bus solar PV capacity factors for the cutout window.

    Uses one ``cutout.pv()`` call per bus with a 0/1 layout indicator at the
    bus's nearest grid cell and ``per_unit=True``.

    Returns
    -------
    pd.DataFrame
        Hourly UTC index × one column per bus.
    """
    panel = config_dict.get("solar_panel", "CSi")
    orientation = config_dict.get("solar_orientation", {"slope": 30.0, "azimuth": 180.0})

    series_by_bus: Dict[str, pd.Series] = {}
    for bus, (x, y) in bus_coords.items():
        layout = _one_hot_layout_at_point(cutout, x, y)
        result = cutout.pv(
            panel=panel,
            orientation=orientation,
            layout=layout,
            per_unit=True,
        )
        series_by_bus[bus] = _series_from_atlite_result(result)

    df = pd.DataFrame(series_by_bus)
    df.index.name = "time"
    return df


def build_atlite_wind_traces(
    cutout,
    bus_coords: Dict[str, Tuple[float, float]],
    config_dict: dict,
) -> pd.DataFrame:
    """
    Compute per-bus onshore-wind capacity factors for the cutout window.

    Uses one ``cutout.wind()`` call per bus with a 0/1 layout indicator at the
    bus's nearest grid cell and ``per_unit=True``.

    Returns
    -------
    pd.DataFrame
        Hourly UTC index × one column per bus.
    """
    turbine = config_dict.get("wind_turbine", "Vestas_V112_3MW")

    series_by_bus: Dict[str, pd.Series] = {}
    for bus, (x, y) in bus_coords.items():
        layout = _one_hot_layout_at_point(cutout, x, y)
        result = cutout.wind(
            turbine=turbine,
            layout=layout,
            per_unit=True,
        )
        series_by_bus[bus] = _series_from_atlite_result(result)

    df = pd.DataFrame(series_by_bus)
    df.index.name = "time"
    return df


# ============================================================================
# Tile to model snapshots (matches the Renewables Ninja workflow)
# ============================================================================

def tile_atlite_trace_to_snapshots(
    weather_df: pd.DataFrame,
    snapshots: pd.Index,
    target_timezone: str = "Asia/Dili",
) -> Dict[str, pd.Series]:
    """
    Convert UTC weather DataFrame to local time and tile/wrap to model snapshots.

    Mirrors ``model_builder.prepare_vre_trace_for_snapshots`` but for atlite
    output: timestamps are converted to local time, leap-day rows dropped,
    and the resulting array is tiled to the snapshot length (numpy tile).

    Parameters
    ----------
    weather_df : pd.DataFrame
        Hourly UTC index × one column per bus.
    snapshots : pd.Index
        Network snapshots (DatetimeIndex or MultiIndex with 'timestep' level).
    target_timezone : str
        IANA tz name. Default ``Asia/Dili`` (UTC+9).

    Returns
    -------
    dict[str, pd.Series]
        ``{bus_name: pd.Series indexed by snapshots}``
    """
    # Localize UTC → target tz, drop tzinfo to align with naive model snapshots
    if weather_df.index.tz is None:
        utc_index = weather_df.index.tz_localize("UTC")
    else:
        utc_index = weather_df.index
    local_index = utc_index.tz_convert(target_timezone).tz_localize(None)
    df = weather_df.copy()
    df.index = local_index
    df = df.sort_index()

    # Drop Feb 29 to match the model snapshot calendar
    feb29_mask = (df.index.month == 2) & (df.index.day == 29)
    df = df.loc[~feb29_mask]

    # Drop any duplicate timestamps that may arise from DST or boundary effects
    df = df[~df.index.duplicated(keep="first")]

    if isinstance(snapshots, pd.MultiIndex):
        timestep_index = snapshots.get_level_values("timestep")
    else:
        timestep_index = pd.DatetimeIndex(snapshots)
    n_snapshots = len(timestep_index)

    if df.empty:
        raise ValueError("atlite trace is empty after tz conversion / leap-day removal.")

    n_repeat = int(np.ceil(n_snapshots / len(df)))

    out: Dict[str, pd.Series] = {}
    for bus in df.columns:
        tiled = np.tile(df[bus].to_numpy(), n_repeat)[:n_snapshots]
        out[bus] = pd.Series(tiled, index=snapshots, name=bus)
    return out


# ============================================================================
# Top-level helper used by model_builder
# ============================================================================

def build_atlite_vre_traces(
    snapshots: pd.Index,
    model_start_year: int,
    model_end_year_exclusive: int,
    config_dict: dict,
    target_timezone: str = "Asia/Dili",
) -> Tuple[Dict[str, pd.Series], Dict[str, pd.Series], pd.DataFrame, pd.DataFrame]:
    """
    Build per-bus atlite solar and wind capacity-factor traces.

    Combines all the steps:
      1. Decide cutout year range (capped at ``weather_max_years``).
      2. Load or download the cutout.
      3. Compute per-bus solar PV and wind capacity factors.
      4. Tile the resulting series to the model snapshot index, wrapping
         around if the horizon exceeds the cutout window.

    Returns
    -------
    (solar_per_bus, wind_per_bus, raw_solar_df, raw_wind_df)
        Two dicts (bus → series indexed by ``snapshots``) plus the raw
        cutout-window DataFrames (UTC index) for the run record export.
    """
    cutout_start, cutout_end = compute_cutout_year_range(
        model_start_year=model_start_year,
        model_end_year_exclusive=model_end_year_exclusive,
        weather_start_year=config_dict.get("weather_start_year", 2010),
        weather_max_years=config_dict.get("weather_max_years", 15),
    )

    cutout = get_or_create_cutout(cutout_start, cutout_end, config_dict)

    coords = bus_coords_for_atlite()
    print(f"  [atlite] Computing solar PV traces for {len(coords)} buses...")
    solar_df = build_atlite_solar_traces(cutout, coords, config_dict)
    print(f"  [atlite] Computing onshore-wind traces for {len(coords)} buses...")
    wind_df = build_atlite_wind_traces(cutout, coords, config_dict)

    solar_per_bus = tile_atlite_trace_to_snapshots(solar_df, snapshots, target_timezone)
    wind_per_bus = tile_atlite_trace_to_snapshots(wind_df, snapshots, target_timezone)

    return solar_per_bus, wind_per_bus, solar_df, wind_df


# ============================================================================
# Run-record export
# ============================================================================

def export_atlite_traces(
    solar_per_bus: Dict[str, pd.Series],
    wind_per_bus: Dict[str, pd.Series],
    output_dir: str,
    scenario_name: str = "",
) -> None:
    """
    Persist per-bus VRE traces to ``{output_dir}/inputs/`` for the run record.

    Writes:
      - ``vre_solar.csv`` / ``vre_wind.csv`` — wide-form CSVs (one column per bus).
      - ``vre_solar_overview.png`` / ``vre_wind_overview.png`` — overlaid traces.
      - ``vre_solar/<bus>.png`` / ``vre_wind/<bus>.png`` — full-horizon plots.
    """
    if not solar_per_bus and not wind_per_bus:
        return

    inputs_dir = os.path.join(output_dir, "inputs")
    os.makedirs(inputs_dir, exist_ok=True)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for tech_name, profiles in [("solar", solar_per_bus), ("wind", wind_per_bus)]:
        if not profiles:
            continue

        sample_index = next(iter(profiles.values())).index
        df = pd.DataFrame(
            {bus: s.values for bus, s in profiles.items()},
            index=sample_index,
        )
        csv_path = os.path.join(inputs_dir, f"vre_{tech_name}.csv")
        df.to_csv(csv_path)

        if isinstance(sample_index, pd.MultiIndex):
            timesteps = sample_index.get_level_values("timestep")
        else:
            timesteps = pd.DatetimeIndex(sample_index)

        # Overview plot — first week + mean daily shape
        week_n = min(168, len(timesteps))
        x_week = timesteps[:week_n]

        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        for bus, s in profiles.items():
            axes[0].plot(x_week, s.values[:week_n], label=bus, linewidth=0.8)
        title = f"{tech_name.capitalize()} capacity factor — first week"
        if scenario_name:
            title = f"{title} — {scenario_name}"
        axes[0].set_title(title)
        axes[0].set_ylabel("Capacity factor")
        axes[0].set_ylim(0, 1)
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc="best", ncol=3, fontsize=8)

        hours = timesteps.hour
        for bus, s in profiles.items():
            avg_by_hour = pd.Series(s.values).groupby(hours).mean()
            axes[1].plot(avg_by_hour.index, avg_by_hour.values, label=bus, linewidth=1.0)
        axes[1].set_title(f"Average daily {tech_name} capacity factor (mean across all days)")
        axes[1].set_xlabel("Hour of day")
        axes[1].set_ylabel("Mean CF")
        axes[1].set_xticks(range(0, 24, 2))
        axes[1].set_ylim(0, 1)
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc="best", ncol=3, fontsize=8)

        fig.autofmt_xdate()
        fig.tight_layout()
        overview_png = os.path.join(inputs_dir, f"vre_{tech_name}_overview.png")
        fig.savefig(overview_png, dpi=150)
        plt.close(fig)

        # Per-bus full-horizon plots
        per_bus_dir = os.path.join(inputs_dir, f"vre_{tech_name}")
        os.makedirs(per_bus_dir, exist_ok=True)
        for bus, s in profiles.items():
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.plot(timesteps, s.values, linewidth=0.4, color="tab:orange" if tech_name == "solar" else "tab:blue")

            bus_title = f"{tech_name.capitalize()} capacity factor — {bus}"
            if scenario_name:
                bus_title = f"{bus_title} — {scenario_name}"
            ax.set_title(bus_title)
            ax.set_xlabel("Date")
            ax.set_ylabel("Capacity factor")
            ax.set_ylim(0, 1)
            ax.grid(True, alpha=0.3)

            stats = (
                f"peak: {s.max():.2f}\n"
                f"mean: {s.mean():.2f}\n"
                f"CF (annual avg): {s.mean() * 100:.1f}%"
            )
            ax.text(
                0.99, 0.97, stats,
                transform=ax.transAxes,
                ha="right", va="top",
                fontsize=9,
                bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "0.6"},
            )

            fig.autofmt_xdate()
            fig.tight_layout()
            fig.savefig(os.path.join(per_bus_dir, f"{bus}.png"), dpi=150)
            plt.close(fig)

        print(f"  Exported {tech_name} VRE traces to: {inputs_dir}")
        print(f"    vre_{tech_name}.csv ({len(df)} rows × {len(df.columns)} buses)")
        print(f"    vre_{tech_name}_overview.png")
        print(f"    vre_{tech_name}/  ({len(profiles)} per-bus PNG plots)")
