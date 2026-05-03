"""
Scenario utilities for the Timor-Leste PyPSA model.
Provides VRE trace extension, fuel price volatility, demand growth,
and scenario application helpers.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Union, Dict


def extended_vre_trace(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    freq: str,
    trace_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extend a VRE capacity factor trace by tiling the original year across a new date range.

    Parameters
    ----------
    start_date : pd.Timestamp
        Start of the extended range.
    end_date : pd.Timestamp
        End of the extended range (inclusive).
    freq : str
        Pandas frequency string (e.g. "1h").
    trace_df : pd.DataFrame
        Original single-year VRE trace with DatetimeIndex (8760 rows for hourly data).

    Returns
    -------
    pd.DataFrame
        Extended DataFrame with tiled VRE patterns indexed by the new date range.
    """
    target_range = pd.date_range(start=start_date, end=end_date, freq=freq)

    original_length = len(trace_df)
    if original_length == 0:
        raise ValueError("trace_df is empty")

    result_df = pd.DataFrame(index=target_range, columns=trace_df.columns, dtype=float)

    for i, _ in enumerate(target_range):
        result_df.iloc[i] = trace_df.iloc[i % original_length]

    return result_df


def apply_fuel_price_volatility(
    fuel_cost_series: pd.Series,
    periods_to_modify: Optional[Union[List[int], str]] = "all",
    min_increase_factor: float = 1.0,
    max_increase_factor: float = 2.0,
    volatility_type: str = "uniform",
    resolution: str = "timestep",
    random_seed: Optional[int] = None,
) -> pd.Series:
    """
    Apply stochastic price volatility to a MultiIndex fuel cost series.

    Parameters
    ----------
    fuel_cost_series : pd.Series
        Series with MultiIndex (period, timestep) containing fuel costs.
    periods_to_modify : list[int] or "all"
        Investment periods to modify. "all" applies to every period.
    min_increase_factor : float
        Minimum price multiplier (>= 1.0).
    max_increase_factor : float
        Maximum price multiplier.
    volatility_type : str
        Distribution: "uniform", "normal", or "lognormal".
    resolution : str
        Granularity: "timestep", "monthly", "quarterly", or "annually".
    random_seed : int, optional
        Seed for reproducibility.

    Returns
    -------
    pd.Series
        Modified series with same structure.
    """
    if min_increase_factor < 1.0:
        raise ValueError("min_increase_factor must be >= 1.0")
    if max_increase_factor <= min_increase_factor:
        raise ValueError("max_increase_factor must be > min_increase_factor")

    valid_resolutions = ["timestep", "monthly", "quarterly", "annually"]
    if resolution not in valid_resolutions:
        raise ValueError(f"resolution must be one of {valid_resolutions}")

    if random_seed is not None:
        np.random.seed(random_seed)

    modified_series = fuel_cost_series.copy()

    if periods_to_modify is None or (isinstance(periods_to_modify, list) and len(periods_to_modify) == 0):
        return modified_series

    if periods_to_modify == "all":
        periods_to_modify = fuel_cost_series.index.get_level_values("period").unique().tolist()
    elif not isinstance(periods_to_modify, list):
        periods_to_modify = [periods_to_modify]

    def _random_factors(size, dist, lo, hi):
        if dist == "uniform":
            return np.random.uniform(lo, hi, size=size)
        elif dist == "normal":
            mean = (lo + hi) / 2
            std = (hi - lo) / 6
            return np.clip(np.random.normal(mean, std, size=size), lo, hi)
        else:
            mean_log = np.log((lo + hi) / 2)
            return np.clip(np.random.lognormal(mean_log, 0.2, size=size), lo, hi)

    for period in periods_to_modify:
        if period not in fuel_cost_series.index.get_level_values("period"):
            continue

        period_mask = fuel_cost_series.index.get_level_values("period") == period
        period_data = fuel_cost_series[period_mask]
        period_timestamps = period_data.index.get_level_values("timestep")

        if resolution == "timestep":
            factors = _random_factors(len(period_data), volatility_type, min_increase_factor, max_increase_factor)

        elif resolution == "monthly":
            factors = np.zeros(len(period_data))
            for month in period_timestamps.to_series().dt.to_period("M").unique():
                mask = period_timestamps.to_series().dt.to_period("M") == month
                factors[mask.values] = _random_factors(1, volatility_type, min_increase_factor, max_increase_factor)[0]

        elif resolution == "quarterly":
            factors = np.zeros(len(period_data))
            for quarter in period_timestamps.to_series().dt.to_period("Q").unique():
                mask = period_timestamps.to_series().dt.to_period("Q") == quarter
                factors[mask.values] = _random_factors(1, volatility_type, min_increase_factor, max_increase_factor)[0]

        else:  # annually
            factors = np.full(len(period_data), _random_factors(1, volatility_type, min_increase_factor, max_increase_factor)[0])

        modified_series[period_mask] = period_data * factors

    return modified_series


def build_demand_growth_profile(
    base_load_series: pd.Series,
    years: List[int],
    annual_growth_rate: float,
) -> pd.Series:
    """
    Extend a single-year hourly load profile across multiple years with compound growth.

    The load profile shape is preserved; only the magnitude scales year-on-year.
    February 29 is excluded so every year has exactly 8760 hourly timesteps.

    Parameters
    ----------
    base_load_series : pd.Series
        8760-row hourly load for the base year (index ignored, values used cyclically).
    years : list[int]
        Ordered list of calendar years to cover.
    annual_growth_rate : float
        Compound annual growth rate (e.g. 0.03 for 3%).

    Returns
    -------
    pd.Series
        Multi-year load profile with DatetimeIndex, Feb 29 excluded.
    """
    base_year = years[0]
    base_values = base_load_series.values

    all_series = []
    for year in years:
        year_range = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31 23:00", freq="1h")
        # Remove Feb 29
        year_range = year_range[~((year_range.month == 2) & (year_range.day == 29))]

        growth_factor = (1 + annual_growth_rate) ** (year - base_year)
        n_hours = len(year_range)

        # Tile/trim base values to exactly n_hours
        tiled = np.tile(base_values, int(np.ceil(n_hours / len(base_values))))[:n_hours]
        scaled = tiled * growth_factor

        all_series.append(pd.Series(scaled, index=year_range))

    return pd.concat(all_series)


def apply_scenario_config(network, scenario_dict: dict) -> None:
    """
    Apply a scenario configuration dict to an assembled network.

    Modifies in-place:
    - Removes generators whose carrier is not in ``allowed_generators``.
    - Applies diesel price factor to diesel generator marginal costs.

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

    # Apply diesel price factor to diesel generator marginal costs (scalar or series)
    diesel_factor = scenario_dict.get("diesel_price_factor", 1.0)
    if diesel_factor != 1.0:
        diesel_gens = network.generators.index[network.generators.carrier == "diesel"]
        for gen in diesel_gens:
            mc = network.generators.at[gen, "marginal_cost"]
            if isinstance(mc, (int, float)):
                network.generators.at[gen, "marginal_cost"] = mc * diesel_factor
