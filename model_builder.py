"""
Multi-period network assembly for the Timor-Leste PyPSA capacity expansion model.
Provides snapshot creation, investment period weighting, degradation, cost calculation,
and the main orchestrator build_multiperiod_network().
"""

import os
import numpy as np
import pandas as pd
import pypsa
from typing import List, Optional

import config
from timor_leste_config import build_timor_leste_network, add_loads_to_network
from pypsa_setup import add_solar_pv, add_wind_farm, add_battery_storage
from src.scenarios import extended_vre_trace, build_demand_growth_profile, apply_scenario_config


# ============================================================================
# Snapshot helpers
# ============================================================================

def create_multiindex_snapshots(
    start_year: int,
    end_year: int,
    freq: str = "1h",
    investment_periods: Optional[List[int]] = None,
) -> pd.MultiIndex:
    """
    Build a (period, timestep) MultiIndex covering start_year through end_year.
    February 29 is removed so every year is exactly 8760 hourly timesteps.

    Parameters
    ----------
    start_year, end_year : int
        First and last calendar years (both inclusive).
    freq : str
        Pandas frequency string.
    investment_periods : list[int], optional
        Explicit list of investment period years. Defaults to every year in range.

    Returns
    -------
    pd.MultiIndex with names ('period', 'timestep').
    """
    date_range = pd.date_range(
        start=f"{start_year}-01-01",
        end=f"{end_year}-12-31 23:00",
        freq=freq,
    )
    # Remove Feb 29
    date_range = date_range[~((date_range.month == 2) & (date_range.day == 29))]

    if investment_periods is None:
        investment_periods = sorted(date_range.year.unique())

    years = date_range.year
    periods = []
    for year in years:
        period = None
        for i, ip in enumerate(investment_periods):
            if i == len(investment_periods) - 1 or year < investment_periods[i + 1]:
                if year >= ip:
                    period = ip
                    break
        if period is None:
            period = investment_periods[0] if year < investment_periods[0] else investment_periods[-1]
        periods.append(period)

    return pd.MultiIndex.from_arrays([periods, date_range], names=["period", "timestep"])


def calculate_investment_period_weightings(
    end_year: int,
    investment_period_years: List[int],
    discount_rate: float,
) -> pd.DataFrame:
    """
    Compute PyPSA investment_period_weightings DataFrame.

    Each period's objective weight equals the sum of discount factors for each year
    the period represents: sum((1+r)^-t for t in [T, T+nyears)).

    Returns
    -------
    pd.DataFrame with columns ['objective', 'years'], indexed by period start year.
    """
    df = pd.DataFrame(index=pd.Index(investment_period_years, name="period"))

    if len(investment_period_years) == 1:
        years_in_periods = [end_year - investment_period_years[0]]
    else:
        years_diff = list(np.diff(investment_period_years))
        final_length = end_year - investment_period_years[-1]
        years_in_periods = years_diff + [final_length]

    df["years"] = years_in_periods

    r = discount_rate
    T = 0
    for period, nyears in df["years"].items():
        df.at[period, "objective"] = sum((1 / (1 + r) ** t) for t in range(T, T + nyears))
        T += nyears

    return df[["objective", "years"]]


def calc_snapshot_weightings(n: pypsa.Network) -> None:
    """Set snapshot weightings so each year sums to 8760 hours."""
    n_years = len(n.investment_periods) if hasattr(n, "investment_periods") and len(n.investment_periods) > 0 else 1
    total_snapshots = len(n.snapshots)
    weighting = 8760 / (total_snapshots / n_years) if n_years > 0 else 1.0
    n.snapshot_weightings.loc[:, :] = weighting


def calc_custom_degradation(
    network_snapshots: pd.Index,
    technology: str,
    build_year: int,
    annual_degradation_rate: float,
    lifetime: int,
    initial_max_capacity: float = 1.0,
    min_capacity: float = 0.0,
) -> pd.Series:
    """
    Compute a p_max_pu degradation trace for a VRE asset over its lifetime.

    Values are 0 before build_year, degrade from initial_max_capacity by
    annual_degradation_rate each year, and return to 0 after build_year + lifetime.

    Returns
    -------
    pd.Series indexed by network_snapshots.
    """
    trace = pd.Series(0.0, index=network_snapshots, name=f"{technology}_{build_year}", dtype=float)

    if isinstance(network_snapshots, pd.MultiIndex):
        years = network_snapshots.get_level_values("timestep").year
    else:
        years = network_snapshots.year

    end_year = build_year + lifetime

    for year in range(build_year, end_year):
        year_mask = years == year
        if not year_mask.any():
            continue
        years_since_build = year - build_year
        factor = (1 - annual_degradation_rate) ** years_since_build
        trace[year_mask] = max(factor * initial_max_capacity, min_capacity)

    return trace


# ============================================================================
# Cost helpers
# ============================================================================

def get_annualized_cost(cost: float, lifetime: int, discount_rate: float) -> float:
    """Return the annualised cost using the annuity formula."""
    r = discount_rate
    return cost * r / (1.0 - 1.0 / (1.0 + r) ** lifetime)


def _interpolate_projection_factor(technology: str, year: int) -> float:
    """
    Return the cost projection factor for a technology at a given year,
    linearly interpolating between the milestone years in COST_PROJECTION_FACTORS.
    """
    factors = config.COST_PROJECTION_FACTORS.get(technology)
    if factors is None:
        return 1.0

    milestone_years = sorted(factors.keys())

    if year <= milestone_years[0]:
        return factors[milestone_years[0]]
    if year >= milestone_years[-1]:
        return factors[milestone_years[-1]]

    for i in range(len(milestone_years) - 1):
        y0, y1 = milestone_years[i], milestone_years[i + 1]
        if y0 <= year <= y1:
            t = (year - y0) / (y1 - y0)
            return factors[y0] + t * (factors[y1] - factors[y0])

    return 1.0


def get_annualized_capex(technology: str, build_year: int, discount_rate: float = None) -> float:
    """
    Return the annualised capital cost for a technology in a given build year.

    Applies the year-specific projection factor from COST_PROJECTION_FACTORS to
    the 2025 base BUILD_COSTS, then annualises and adds FOM.

    Parameters
    ----------
    technology : str
        Technology key (must be in config.BUILD_COSTS).
    build_year : int
        Year of investment.
    discount_rate : float, optional
        Defaults to config.DISCOUNT_RATE.

    Returns
    -------
    float  Annualised capital cost in USD/MW/year.
    """
    if discount_rate is None:
        discount_rate = config.DISCOUNT_RATE

    base_cost = config.BUILD_COSTS.get(technology, 0)
    projection_factor = _interpolate_projection_factor(technology, build_year)
    projected_cost = base_cost * projection_factor

    lifetime = config.TECHNICAL_PARAMS.get(technology, {}).get("lifetime", 25)
    fom = config.FIXED_OM_COSTS.get(technology, 0)

    return get_annualized_cost(projected_cost, lifetime, discount_rate) + fom


# ============================================================================
# Time-series builders
# ============================================================================

def build_demand_profile(
    base_csv_path: str,
    start_year: int,
    end_year: int,
    growth_rate: float,
) -> pd.Series:
    """
    Load the base-year demand CSV and extend to the full model horizon.

    Applies compound annual growth. February 29 is excluded.

    Returns
    -------
    pd.Series with DatetimeIndex.
    """
    raw = pd.read_csv(base_csv_path)
    base_load = raw["Demand"].values  # 8760 values

    years = list(range(start_year, end_year + 1))
    return build_demand_growth_profile(
        base_load_series=pd.Series(base_load),
        years=years,
        annual_growth_rate=growth_rate,
    )


def build_marginal_cost_series(
    technology: str,
    snapshots: pd.Index,
    base_marginal_cost: float,
    diesel_price_factor: float = 1.0,
    diesel_price_ramp_year: Optional[int] = None,
) -> pd.Series:
    """
    Build a time-indexed marginal cost series for a generator.

    For diesel, applies a linear price ramp from 1.0 × base_mc in the start
    year to diesel_price_factor × base_mc in diesel_price_ramp_year, then holds flat.

    Parameters
    ----------
    technology : str
    snapshots : pd.Index
        Network snapshots (single or MultiIndex).
    base_marginal_cost : float
    diesel_price_factor : float
        Final diesel price multiplier.
    diesel_price_ramp_year : int, optional
        Year by which the full price factor is reached (linear ramp from start year).

    Returns
    -------
    pd.Series indexed by snapshots.
    """
    if isinstance(snapshots, pd.MultiIndex):
        years = snapshots.get_level_values("timestep").year
    else:
        years = snapshots.year

    mc_values = np.full(len(snapshots), base_marginal_cost, dtype=float)

    if technology == "diesel" and diesel_price_factor != 1.0 and diesel_price_ramp_year is not None:
        start_year = int(years.min())
        for i, year in enumerate(years):
            if year <= start_year:
                factor = 1.0
            elif year >= diesel_price_ramp_year:
                factor = diesel_price_factor
            else:
                t = (year - start_year) / (diesel_price_ramp_year - start_year)
                factor = 1.0 + t * (diesel_price_factor - 1.0)
            mc_values[i] = base_marginal_cost * factor

    return pd.Series(mc_values, index=snapshots)


# ============================================================================
# Main network builder
# ============================================================================

def build_multiperiod_network(
    scenario_name: str = "base",
    start_year: int = None,
    end_year: int = None,
    solar_csv: str = r"data\solar_pv_output_re_ninja.csv",
    wind_csv: str = r"data\wind_output_re_ninja.csv",
    demand_csv: str = r"data\timor_leste_hourly_load_2025.csv",
) -> pypsa.Network:
    """
    Assemble a multi-period investment planning network for Timor-Leste.

    Sequence:
    1. Load scenario config.
    2. Create MultiIndex snapshots (Feb 29 excluded).
    3. Build the base Timor-Leste transmission network.
    4. Set investment_period_weightings and snapshot_weightings.
    5. Update existing generator lifetimes for multi-period compatibility.
    6. Build multi-year VRE traces (tiled Renewables Ninja data).
    7. Build multi-year demand profile (compound growth).
    8. Build multi-year diesel marginal cost series.
    9. Add new expandable generators (solar, wind, battery) with build years.
    10. Apply scenario config (filter carriers, apply price factors).
    11. Add load profiles to all buses.

    Parameters
    ----------
    scenario_name : str
        Key in config.SCENARIOS.
    start_year, end_year : int, optional
        Override config.MODEL_START_YEAR / MODEL_END_YEAR.
    solar_csv, wind_csv, demand_csv : str
        Paths to Renewables Ninja and demand CSV files.

    Returns
    -------
    pypsa.Network ready for network.optimize(multi_invest=True).
    """
    if start_year is None:
        start_year = config.MODEL_START_YEAR
    if end_year is None:
        end_year = config.MODEL_END_YEAR

    scenario = config.SCENARIOS[scenario_name]
    investment_periods = list(range(start_year, end_year + 1))

    print(f"\n{'='*70}")
    print(f"Building multi-period network: scenario='{scenario_name}'")
    print(f"Horizon: {start_year}–{end_year} ({len(investment_periods)} investment periods)")
    print(f"{'='*70}")

    # ------------------------------------------------------------------
    # 1. Create MultiIndex snapshots
    # ------------------------------------------------------------------
    snapshots = create_multiindex_snapshots(
        start_year=start_year,
        end_year=end_year,
        freq=config.FREQ,
        investment_periods=investment_periods,
    )
    print(f"\nSnapshots: {len(snapshots):,} total ({len(snapshots) // len(investment_periods):,} per year)")

    # ------------------------------------------------------------------
    # 2. Build base Timor-Leste network
    # ------------------------------------------------------------------
    network = build_timor_leste_network(snapshots=snapshots, add_generators=True)

    # ------------------------------------------------------------------
    # 3. Investment period weightings and snapshot weightings
    # ------------------------------------------------------------------
    inv_weightings = calculate_investment_period_weightings(
        end_year=end_year + 1,
        investment_period_years=investment_periods,
        discount_rate=config.DISCOUNT_RATE,
    )
    network.investment_period_weightings = inv_weightings
    calc_snapshot_weightings(network)

    # ------------------------------------------------------------------
    # 4. Fix existing generator lifetimes for multi-period mode
    # ------------------------------------------------------------------
    # Betano (built 2015, 20yr lifetime) → decommissions 2035
    # Hera   (built 2011, 20yr lifetime) → decommissions 2031
    for gen in network.generators.index:
        if network.generators.at[gen, "capital_cost"] == 0:  # existing plant
            build_yr = int(network.generators.at[gen, "build_year"])
            technology = network.generators.at[gen, "carrier"]
            lifetime = config.TECHNICAL_PARAMS.get(technology, {}).get("lifetime", 20)
            network.generators.at[gen, "lifetime"] = lifetime

    # Build diesel marginal cost time series for existing plants
    diesel_mc_series = build_marginal_cost_series(
        technology="diesel",
        snapshots=snapshots,
        base_marginal_cost=config.MARGINAL_COSTS["diesel"],
        diesel_price_factor=scenario.get("diesel_price_factor", 1.0),
        diesel_price_ramp_year=scenario.get("diesel_price_ramp_year"),
    )
    for gen in network.generators.index:
        if network.generators.at[gen, "carrier"] == "diesel":
            network.generators_t.marginal_cost[gen] = diesel_mc_series

    # ------------------------------------------------------------------
    # 5. Load Renewables Ninja CSV files
    # ------------------------------------------------------------------
    solar_raw = pd.read_csv(solar_csv)["Output"].values  # 8760 floats
    wind_raw = pd.read_csv(wind_csv)["Output"].values

    base_ts = pd.date_range(start=f"{start_year}-01-01", periods=8760, freq="1h")
    solar_base = pd.DataFrame({"Output": solar_raw}, index=base_ts)
    wind_base = pd.DataFrame({"Output": wind_raw}, index=base_ts)

    # Extend across full horizon
    solar_extended = extended_vre_trace(
        start_date=pd.Timestamp(f"{start_year}-01-01"),
        end_date=pd.Timestamp(f"{end_year}-12-31 23:00"),
        freq=config.FREQ,
        trace_df=solar_base,
    )
    wind_extended = extended_vre_trace(
        start_date=pd.Timestamp(f"{start_year}-01-01"),
        end_date=pd.Timestamp(f"{end_year}-12-31 23:00"),
        freq=config.FREQ,
        trace_df=wind_base,
    )

    # Remove Feb 29 from extended traces
    for df in [solar_extended, wind_extended]:
        mask = ~((df.index.month == 2) & (df.index.day == 29))
        df.drop(df.index[~mask], inplace=True)

    # Re-index to network MultiIndex snapshots
    timestep_index = snapshots.get_level_values("timestep")
    solar_cf = pd.Series(solar_extended["Output"].values, index=snapshots)
    wind_cf = pd.Series(wind_extended["Output"].values, index=snapshots)

    # ------------------------------------------------------------------
    # 6. Determine build years for new expandable generators
    # ------------------------------------------------------------------
    # Filter build years by lifetime: avoid adding a second cohort before the
    # first cohort is fully depreciated.
    def _filter_build_years(all_years: List[int], lifetime: int) -> List[int]:
        if not all_years:
            return all_years
        filtered = [all_years[0]]
        last = all_years[0]
        for yr in all_years[1:]:
            if yr >= last + lifetime:
                filtered.append(yr)
                last = yr
        return filtered

    solar_lifetime = config.TECHNICAL_PARAMS["solar"]["lifetime"]
    wind_lifetime = config.TECHNICAL_PARAMS["wind_onshore"]["lifetime"]
    battery_lifetime = config.TECHNICAL_PARAMS["battery"]["lifetime"]

    solar_build_years = _filter_build_years(investment_periods, solar_lifetime)
    wind_build_years = _filter_build_years(investment_periods, wind_lifetime)
    battery_build_years = _filter_build_years(investment_periods, battery_lifetime)

    allowed = scenario.get("allowed_generators", ["solar", "wind_onshore", "battery", "diesel"])

    # ------------------------------------------------------------------
    # 7. Add new solar PV generators (extendable, one per valid build year)
    # ------------------------------------------------------------------
    if "solar" in allowed:
        for build_yr in solar_build_years:
            capex = get_annualized_capex("solar", build_yr)
            add_solar_pv(
                network=network,
                name=f"Solar_Dili_{build_yr}",
                bus="Dili",
                capital_cost=capex,
                marginal_cost=config.MARGINAL_COSTS["solar"],
                p_max_pu=solar_cf,
                lifetime=solar_lifetime,
                build_year=build_yr,
                p_nom_extendable=True,
            )

    # ------------------------------------------------------------------
    # 8. Add new wind farm generators (extendable)
    # ------------------------------------------------------------------
    if "wind_onshore" in allowed:
        for build_yr in wind_build_years:
            capex = get_annualized_capex("wind_onshore", build_yr)
            add_wind_farm(
                network=network,
                name=f"Wind_Lospalos_{build_yr}",
                bus="Lospalos",
                capital_cost=capex,
                marginal_cost=config.MARGINAL_COSTS["wind_onshore"],
                p_max_pu=wind_cf,
                wind_type="onshore",
                lifetime=wind_lifetime,
                build_year=build_yr,
                p_nom_extendable=True,
            )

    # ------------------------------------------------------------------
    # 9. Add new battery storage (extendable)
    # ------------------------------------------------------------------
    if "battery" in allowed:
        battery_capex_mw = get_annualized_capex("battery", start_year)
        for build_yr in battery_build_years:
            battery_capex_mw = get_annualized_capex("battery", build_yr)
            add_battery_storage(
                network=network,
                name=f"Battery_Dili_{build_yr}",
                bus="Dili",
                capital_cost=battery_capex_mw,
                marginal_cost=config.MARGINAL_COSTS["battery"],
                efficiency_charge=config.TECHNICAL_PARAMS["battery"]["efficiency_charge"],
                efficiency_discharge=config.TECHNICAL_PARAMS["battery"]["efficiency_discharge"],
                max_hours=config.TECHNICAL_PARAMS["battery"]["max_hours"],
                standing_loss=config.TECHNICAL_PARAMS["battery"]["standing_loss"],
                lifetime=battery_lifetime,
                build_year=build_yr,
                p_nom_extendable=True,
            )

    # ------------------------------------------------------------------
    # 10. Apply scenario config (filter carriers, price overrides)
    # ------------------------------------------------------------------
    apply_scenario_config(network, scenario)

    # ------------------------------------------------------------------
    # 11. Build multi-year load profiles and attach to buses
    # ------------------------------------------------------------------
    demand_profile = build_demand_profile(
        base_csv_path=demand_csv,
        start_year=start_year,
        end_year=end_year,
        growth_rate=scenario.get("demand_growth_rate", 0.03),
    )

    # Load distribution matches timor_leste_config.add_loads_to_network
    load_distribution = {
        "Dili": 0.29, "Baucau": 0.108, "Maliana": 0.086, "Liquica": 0.172,
        "Manatuto": 0.045, "Lospalos": 0.059, "Viqueque": 0.067,
        "Cassa": 0.061, "Suai": 0.062, "Betano": 0.052,
    }

    # Re-index demand profile to network's MultiIndex snapshots
    demand_indexed = pd.Series(demand_profile.values, index=snapshots)

    for bus, share in load_distribution.items():
        if bus in network.buses.index:
            network.add(
                "Load",
                f"Load_{bus}",
                bus=bus,
                p_set=demand_indexed * share,
            )

    print(f"\nNetwork assembly complete.")
    print(f"  Generators:     {len(network.generators)}")
    print(f"  Storage units:  {len(network.storage_units)}")
    print(f"  Loads:          {len(network.loads)}")
    print(f"  Buses:          {len(network.buses)}")
    print(f"  Lines:          {len(network.lines)}")

    return network
