"""
Scenario utilities for the Timor-Leste PyPSA model.
Provides VRE trace extension, fuel price trajectories, demand growth,
and scenario application helpers.
"""

import os
import numpy as np
import pandas as pd
from typing import List, Optional, Union, Dict


def extended_vre_trace(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    freq: str,
    trace_df: pd.DataFrame,
    inclusive: str = "both",
) -> pd.DataFrame:
    """
    Extend a VRE capacity factor trace by tiling the original year across a new date range.

    Parameters
    ----------
    start_date : pd.Timestamp
        Start of the extended range.
    end_date : pd.Timestamp
        End of the extended range.
    freq : str
        Pandas frequency string (e.g. "1h").
    trace_df : pd.DataFrame
        Original single-year VRE trace with DatetimeIndex (8760 rows for hourly data).
    inclusive : str
        Passed to pd.date_range. Use "left" with an exclusive end boundary.

    Returns
    -------
    pd.DataFrame
        Extended DataFrame with tiled VRE patterns indexed by the new date range.
    """
    target_range = pd.date_range(start=start_date, end=end_date, freq=freq, inclusive=inclusive)

    original_length = len(trace_df)
    if original_length == 0:
        raise ValueError("trace_df is empty")

    result_df = pd.DataFrame(index=target_range, columns=trace_df.columns, dtype=float)

    for i, _ in enumerate(target_range):
        result_df.iloc[i] = trace_df.iloc[i % original_length]

    return result_df


def build_fuel_price_trajectory(
    snapshots: pd.Index,
    base_price: float,
    modifiers: Optional[List[Dict]] = None,
) -> pd.Series:
    """
    Build a time-indexed fuel price (USD/MWh) series for a generator.

    Starts from a flat base_price and applies optional date-range modifiers.
    Each modifier multiplies the price across the inclusive date range it
    specifies. Multiple modifiers compound (multiplicative); overlapping
    modifiers stack — e.g. two overlapping modifiers with multipliers 2.0
    and 1.5 give a combined multiplier of 3.0 in the overlap.

    Parameters
    ----------
    snapshots : pd.Index
        Network snapshots — either a DatetimeIndex or a MultiIndex with
        levels (period, timestep). The returned series shares this index.
    base_price : float
        Base fuel price in USD/MWh, applied uniformly before modifiers.
    modifiers : list[dict], optional
        Each entry is ``{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD",
        "multiplier": float}``. ``start`` and ``end`` are inclusive at
        whole-day resolution: ``end`` extends through 23:59:59 of that day.
        ``multiplier`` may be any positive float.

    Returns
    -------
    pd.Series
        Fuel price series indexed by ``snapshots``, named ``marginal_cost``.

    Examples
    --------
    >>> # Diesel doubles between 2030 and 2035, then 1.5x onwards
    >>> modifiers = [
    ...     {"start": "2030-01-01", "end": "2034-12-31", "multiplier": 2.0},
    ...     {"start": "2035-01-01", "end": "2045-12-31", "multiplier": 1.5},
    ... ]
    >>> series = build_fuel_price_trajectory(snapshots, 250.0, modifiers)
    """
    if isinstance(snapshots, pd.MultiIndex):
        timesteps = snapshots.get_level_values("timestep")
    else:
        timesteps = pd.DatetimeIndex(snapshots)

    values = np.full(len(snapshots), float(base_price), dtype=float)

    if modifiers:
        for spec in modifiers:
            try:
                start = pd.Timestamp(spec["start"])
                # end is inclusive — extend through end of that day
                end = pd.Timestamp(spec["end"]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                multiplier = float(spec["multiplier"])
            except KeyError as exc:
                raise KeyError(
                    f"Fuel price modifier missing required key: {exc}. "
                    f"Each modifier needs 'start', 'end', and 'multiplier'."
                ) from exc

            mask = (timesteps >= start) & (timesteps <= end)
            values[mask] *= multiplier

    return pd.Series(values, index=snapshots, name="marginal_cost")


def export_fuel_price_series(
    series_by_carrier: Dict[str, pd.Series],
    output_dir: str,
    scenario_name: str = "",
) -> None:
    """
    Persist custom fuel price (marginal cost) series for the run record.

    Writes ``{output_dir}/inputs/fuel_price_trajectories.csv`` with one column
    per carrier and ``fuel_price_trajectories.png`` showing all carriers on a
    single matplotlib axis. The ``inputs/`` subdirectory is created if absent.

    Skips silently when ``series_by_carrier`` is empty so callers don't need
    to guard against scenarios without trajectories.

    Parameters
    ----------
    series_by_carrier : dict[str, pd.Series]
        Carrier name → fuel price time series. All series must share the same
        index (DatetimeIndex or MultiIndex with a 'timestep' level).
    output_dir : str
        Scenario output directory (e.g. ``results/high_diesel``). The
        ``inputs/`` subdirectory is created underneath.
    scenario_name : str, optional
        Used only as the plot title.
    """
    if not series_by_carrier:
        return

    inputs_dir = os.path.join(output_dir, "inputs")
    os.makedirs(inputs_dir, exist_ok=True)

    # Combine series into a single dataframe sharing one index
    sample_index = next(iter(series_by_carrier.values())).index
    combined = pd.DataFrame(
        {carrier: series.values for carrier, series in series_by_carrier.items()},
        index=sample_index,
    )
    csv_path = os.path.join(inputs_dir, "fuel_price_trajectories.csv")
    combined.to_csv(csv_path)

    # Headless matplotlib plot
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if isinstance(sample_index, pd.MultiIndex):
        x = sample_index.get_level_values("timestep")
    else:
        x = sample_index

    fig, ax = plt.subplots(figsize=(12, 5))
    for carrier, series in series_by_carrier.items():
        ax.plot(x, series.values, label=carrier, linewidth=1.0)

    title = "Fuel price trajectories"
    if scenario_name:
        title = f"{title} — {scenario_name}"
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Marginal cost (USD/MWh)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()

    png_path = os.path.join(inputs_dir, "fuel_price_trajectories.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    print(f"  Exported fuel price inputs to: {inputs_dir}")
    print(f"    {os.path.basename(csv_path)} ({len(combined)} rows × {len(combined.columns)} carriers)")
    print(f"    {os.path.basename(png_path)}")


_MONTH_TO_SEASON = {
    12: "DJF", 1: "DJF", 2: "DJF",
    3: "MAM", 4: "MAM", 5: "MAM",
    6: "JJA", 7: "JJA", 8: "JJA",
    9: "SON", 10: "SON", 11: "SON",
}


def _build_typical_daily_template(
    peak_mw: float,
    min_mw: float,
    morning_peak_window,
    evening_peak_window,
    morning_peak_fraction: float,
    evening_peak_fraction: float,
) -> np.ndarray:
    """
    Build a 24-hour load template — two cosine bumps over a min_mw baseline.

    Each bump uses a sin² envelope so the load ramps smoothly up to the peak
    at the midpoint of the window and back down to baseline at the window
    boundaries. Outside both windows the template equals min_mw.

    Returns
    -------
    np.ndarray of length 24 (MW), indexed by hour of day 0–23.
    """
    template = np.full(24, float(min_mw))

    morning_peak = min_mw + morning_peak_fraction * (peak_mw - min_mw)
    evening_peak = min_mw + evening_peak_fraction * (peak_mw - min_mw)

    for (start, end, peak_value) in [
        (morning_peak_window[0], morning_peak_window[1], morning_peak),
        (evening_peak_window[0], evening_peak_window[1], evening_peak),
    ]:
        width = end - start
        if width <= 0:
            continue
        for h in range(int(start), int(end) + 1):
            t = (h - start) / width  # 0 → 1 across the window
            envelope = np.sin(np.pi * t) ** 2  # 0 → 1 at midpoint → 0
            val = min_mw + envelope * (peak_value - min_mw)
            if val > template[h]:
                template[h] = val

    return template


def build_random_load_profiles(
    snapshots: pd.Index,
    load_distribution: Dict[str, float],
    config_dict: Dict,
) -> Dict[str, pd.Series]:
    """
    Build per-bus randomised hourly load profiles from a typical-shape template.

    All buses share the same daily template (morning + evening peaks) by
    default; buses listed in ``config_dict["fully_random_buses"]`` get a
    24-hour fully random template instead. Every bus then receives:
      1. Tiling of its 24-hour template across all snapshot timesteps.
      2. A seasonal multiplier per timestep (DJF/MAM/JJA/SON).
      3. Gaussian noise scaled by ``noise_std × peak_mw``.
      4. Multiplication by ``load_distribution[bus]`` (population share).
      5. Clipping below at zero.

    The same daily profile is applied to every day — there is no inter-day
    or year-on-year demand growth in this mode.

    Reproducibility: a single ``seed`` integer in ``config_dict`` drives a
    ``SeedSequence`` whose spawned children give each bus its own
    deterministic ``np.random.default_rng``.

    Parameters
    ----------
    snapshots : pd.Index
        DatetimeIndex or MultiIndex with a 'timestep' level.
    load_distribution : dict[str, float]
        Bus name → population share (e.g. ``{"Dili": 0.29, ...}``).
    config_dict : dict
        Settings — see ``config.LOAD_RANDOM_CONFIG`` for keys and defaults.

    Returns
    -------
    dict[str, pd.Series]
        Bus name → load (MW) series indexed by ``snapshots``.
    """
    peak_mw = float(config_dict["peak_mw"])
    min_mw = float(config_dict["min_mw"])
    seed = int(config_dict.get("seed", 42))
    fully_random_buses = set(config_dict.get("fully_random_buses", []))
    seasonal_factors = config_dict.get("seasonal_factors", {})
    noise_std_frac = float(config_dict.get("noise_std", 0.0))
    morning_peak_window = config_dict.get("morning_peak_window", (6, 9))
    evening_peak_window = config_dict.get("evening_peak_window", (17, 21))
    morning_peak_fraction = float(config_dict.get("morning_peak_fraction", 0.7))
    evening_peak_fraction = float(config_dict.get("evening_peak_fraction", 1.0))

    if peak_mw <= min_mw:
        raise ValueError(
            f"peak_mw ({peak_mw}) must be greater than min_mw ({min_mw})."
        )

    # Snapshot-derived hour and month arrays (one entry per timestep)
    if isinstance(snapshots, pd.MultiIndex):
        timesteps = snapshots.get_level_values("timestep")
    else:
        timesteps = pd.DatetimeIndex(snapshots)

    hours_of_day = timesteps.hour.to_numpy()
    months = timesteps.month.to_numpy()
    season_factor_array = np.array(
        [seasonal_factors.get(_MONTH_TO_SEASON[int(m)], 1.0) for m in months],
        dtype=float,
    )

    # Default typical-shape template (shared across non-random buses)
    typical_template = _build_typical_daily_template(
        peak_mw=peak_mw,
        min_mw=min_mw,
        morning_peak_window=morning_peak_window,
        evening_peak_window=evening_peak_window,
        morning_peak_fraction=morning_peak_fraction,
        evening_peak_fraction=evening_peak_fraction,
    )

    # Per-bus deterministic RNGs from a single seed
    bus_names_sorted = sorted(load_distribution.keys())
    seed_seq = np.random.SeedSequence(seed)
    child_seeds = seed_seq.spawn(len(bus_names_sorted))
    bus_rng = {bus: np.random.default_rng(child_seeds[i]) for i, bus in enumerate(bus_names_sorted)}

    profiles: Dict[str, pd.Series] = {}
    for bus, share in load_distribution.items():
        rng = bus_rng[bus]

        if bus in fully_random_buses:
            # 24 random hourly values uniform in [min_mw, peak_mw]
            bus_template = rng.uniform(min_mw, peak_mw, size=24)
        else:
            bus_template = typical_template

        # Tile by hour-of-day index
        tiled = bus_template[hours_of_day]

        # Apply seasonal factor per timestep
        seasonal = tiled * season_factor_array

        # Add Gaussian noise scaled by peak_mw
        if noise_std_frac > 0:
            noise = rng.normal(0.0, noise_std_frac * peak_mw, size=len(timesteps))
            seasonal = seasonal + noise

        # Scale by per-bus population share, then clip below at 0
        scaled = np.clip(seasonal * float(share), 0.0, None)

        profiles[bus] = pd.Series(scaled, index=snapshots, name=f"Load_{bus}")

    return profiles


def export_load_profiles(
    profiles: Dict[str, pd.Series],
    output_dir: str,
    scenario_name: str = "",
) -> None:
    """
    Persist per-bus load profile inputs for the run record.

    Writes ``{output_dir}/inputs/load_profiles.csv`` (one column per bus) and:
      - ``load_profiles.png`` — overview: first week of every bus on one axis,
        plus mean daily shape across all days.
      - ``load_profiles/<bus>.png`` — one full-horizon timeseries plot per bus.

    Skips silently when ``profiles`` is empty.
    """
    if not profiles:
        return

    inputs_dir = os.path.join(output_dir, "inputs")
    per_bus_dir = os.path.join(inputs_dir, "load_profiles")
    os.makedirs(per_bus_dir, exist_ok=True)

    sample_index = next(iter(profiles.values())).index
    df = pd.DataFrame(
        {bus: series.values for bus, series in profiles.items()},
        index=sample_index,
    )
    csv_path = os.path.join(inputs_dir, "load_profiles.csv")
    df.to_csv(csv_path)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if isinstance(sample_index, pd.MultiIndex):
        timesteps = sample_index.get_level_values("timestep")
    else:
        timesteps = pd.DatetimeIndex(sample_index)

    # ------------------------------------------------------------------
    # Overview figure (existing): first week + mean daily shape
    # ------------------------------------------------------------------
    week_n = min(168, len(timesteps))
    x_week = timesteps[:week_n]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    for bus, series in profiles.items():
        axes[0].plot(x_week, series.values[:week_n], label=bus, linewidth=0.8)
    title = "Load profiles — first week"
    if scenario_name:
        title = f"{title} — {scenario_name}"
    axes[0].set_title(title)
    axes[0].set_ylabel("Load (MW)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best", ncol=3, fontsize=8)

    hours = timesteps.hour
    for bus, series in profiles.items():
        avg_by_hour = pd.Series(series.values).groupby(hours).mean()
        axes[1].plot(avg_by_hour.index, avg_by_hour.values, label=bus, linewidth=1.0)
    axes[1].set_title("Average daily shape (mean across all days)")
    axes[1].set_xlabel("Hour of day")
    axes[1].set_ylabel("Mean load (MW)")
    axes[1].set_xticks(range(0, 24, 2))
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best", ncol=3, fontsize=8)

    fig.autofmt_xdate()
    fig.tight_layout()
    overview_png = os.path.join(inputs_dir, "load_profiles.png")
    fig.savefig(overview_png, dpi=150)
    plt.close(fig)

    # ------------------------------------------------------------------
    # Per-bus full-horizon timeseries plots
    # ------------------------------------------------------------------
    per_bus_paths = []
    for bus, series in profiles.items():
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(timesteps, series.values, linewidth=0.4, color="tab:blue")

        bus_title = f"Load profile — {bus}"
        if scenario_name:
            bus_title = f"{bus_title} — {scenario_name}"
        ax.set_title(bus_title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Load (MW)")
        ax.grid(True, alpha=0.3)

        # Annotate peak / mean / min as a small textbox
        stats = (
            f"peak: {series.max():.1f} MW\n"
            f"mean: {series.mean():.1f} MW\n"
            f"min:  {series.min():.1f} MW"
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
        bus_png = os.path.join(per_bus_dir, f"{bus}.png")
        fig.savefig(bus_png, dpi=150)
        plt.close(fig)
        per_bus_paths.append(bus_png)

    print(f"  Exported load profile inputs to: {inputs_dir}")
    print(f"    {os.path.basename(csv_path)} ({len(df)} rows × {len(df.columns)} buses)")
    print(f"    {os.path.basename(overview_png)}")
    print(f"    load_profiles/  ({len(per_bus_paths)} per-bus PNG plots)")


def build_demand_growth_profile(
    base_load_series: pd.Series,
    years: List[int],
    annual_growth_rate: float,
    freq: str = "1h",
) -> pd.Series:
    """
    Extend a single-year hourly load profile across multiple years with compound growth.

    The load profile shape is preserved; only the magnitude scales year-on-year.
    February 29 is excluded so every model year has the same number of timesteps
    for the selected frequency.

    Parameters
    ----------
    base_load_series : pd.Series
        8760-row hourly load for the base year (index ignored, values used cyclically).
    years : list[int]
        Ordered list of calendar years to cover.
    annual_growth_rate : float
        Compound annual growth rate (e.g. 0.03 for 3%).
    freq : str
        Fixed pandas frequency string. Source demand is hourly, so sub-hourly
        frequencies are not supported. Coarser frequencies are averaged.

    Returns
    -------
    pd.Series
        Multi-year load profile with DatetimeIndex, Feb 29 excluded.
    """
    offset = pd.tseries.frequencies.to_offset(freq)
    try:
        freq_delta = pd.Timedelta(offset)
    except ValueError as exc:
        raise ValueError(f"Frequency '{freq}' must be fixed-width for demand growth.") from exc

    if freq_delta < pd.Timedelta(hours=1):
        raise ValueError(
            "Sub-hourly model frequencies are not supported by the current "
            "hourly demand CSV input. Use '1h' or a coarser fixed frequency."
        )

    base_year = years[0]
    base_index = pd.date_range(
        start=pd.Timestamp(year=base_year, month=1, day=1),
        end=pd.Timestamp(year=base_year + 1, month=1, day=1),
        freq="1h",
        inclusive="left",
    )
    base_hourly = pd.Series(base_load_series.values, index=base_index)

    if freq_delta > pd.Timedelta(hours=1):
        base_profile = base_hourly.resample(freq).mean()
    else:
        base_profile = base_hourly

    all_series = []
    for year in years:
        year_range = pd.date_range(
            start=pd.Timestamp(year=year, month=1, day=1),
            end=pd.Timestamp(year=year + 1, month=1, day=1),
            freq=freq,
            inclusive="left",
        )
        # Remove Feb 29
        year_range = year_range[~((year_range.month == 2) & (year_range.day == 29))]

        growth_factor = (1 + annual_growth_rate) ** (year - base_year)
        n_hours = len(year_range)

        # Tile/trim base values to exactly n_hours
        tiled = np.tile(base_profile.values, int(np.ceil(n_hours / len(base_profile))))[:n_hours]
        scaled = tiled * growth_factor

        all_series.append(pd.Series(scaled, index=year_range))

    return pd.concat(all_series)


def apply_scenario_config(network, scenario_dict: dict) -> None:
    """
    Apply a scenario configuration dict to an assembled network.

    Modifies in-place:
    - Removes generators whose carrier is not in ``allowed_generators``.

    Fuel price trajectories are applied earlier in the build process via
    ``build_fuel_price_trajectory`` and the ``fuel_price_trajectories`` key
    of the scenario, not here.

    Parameters
    ----------
    network : pypsa.Network
        Assembled network (generators already added).
    scenario_dict : dict
        Scenario configuration from config.SCENARIOS.
    """
    allowed = scenario_dict.get("allowed_generators")
    if allowed is not None:
        # Keep existing diesel plants (capital_cost == 0) regardless of allowed list
        to_remove = [
            g for g in network.generators.index
            if network.generators.at[g, "carrier"] not in allowed
            and network.generators.at[g, "capital_cost"] != 0  # don't remove existing plants
        ]
        if to_remove:
            network.remove("Generator", to_remove)
