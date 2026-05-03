"""
Results analysis functions for the Timor-Leste PyPSA model.
Handles metric calculation, nodal price extraction, and CSV/JSON export.
"""

import json
import os
import numpy as np
import pandas as pd
import pypsa
from typing import Optional

import config


def nominal_total_system_costs(n: pypsa.Network) -> float:
    """Return total nominal system cost (CAPEX + OPEX) from n.statistics()."""
    stats = n.statistics().groupby(level=1).sum()
    if "Capital Expenditure" in stats.columns and "Operational Expenditure" in stats.columns:
        return stats[["Capital Expenditure", "Operational Expenditure"]].sum(axis=1).sum()
    return np.nan


def calculate_system_lcoe(n: pypsa.Network) -> float:
    """
    Calculate system-wide LCOE (USD/MWh) from n.statistics().

    Returns nan if statistics are unavailable.
    """
    try:
        stats = n.statistics()
        by_component = stats.groupby(level=0).sum()
        by_carrier = stats.groupby(level=1).sum()

        if "Load" in by_component.index:
            total_load = abs(by_component.loc["Load", "Energy Balance"])
        else:
            total_load = sum(
                abs(n.loads_t.p_set[load].sum()) for load in n.loads.index
            )

        if all(c in by_carrier.columns for c in ["Capital Expenditure", "Operational Expenditure"]):
            total_costs = (by_carrier["Capital Expenditure"] + by_carrier["Operational Expenditure"]).sum()
        else:
            return np.nan

        total_load_sum = total_load.sum() if hasattr(total_load, "sum") else total_load
        return total_costs / total_load_sum if total_load_sum > 0 else np.nan

    except Exception as e:
        print(f"Warning: system LCOE calculation failed: {e}")
        return np.nan


def calculate_lifetime_emissions(n: pypsa.Network) -> float:
    """Return total lifetime CO2 emissions in Mt."""
    emissions = (
        n.generators_t.p
        / n.generators.efficiency
        * n.generators.carrier.map(n.carriers.co2_emissions)
    )
    return n.snapshot_weightings.generators @ emissions.sum(axis=1) / 1e6


def average_lifetime_srmc(n: pypsa.Network) -> float:
    """Return average marginal price across all buses (USD/MWh)."""
    if n.buses_t.marginal_price.empty:
        return np.nan
    return float(n.buses_t.marginal_price.mean().mean())


def extract_nodal_prices(n: pypsa.Network) -> pd.DataFrame:
    """
    Extract marginal prices at each bus plus a system-average column.

    For multi-period networks the period index is preserved.

    Returns
    -------
    pd.DataFrame
        Columns: one per bus + 'System Average'. Index: n.snapshots.
    """
    prices = n.buses_t.marginal_price.copy()
    if prices.empty:
        return prices

    prices["System Average"] = prices.mean(axis=1)
    return prices


def nodal_price_summary(n: pypsa.Network) -> pd.DataFrame:
    """
    Compute summary statistics (mean, median, p5, p95) per bus, per year.

    Returns
    -------
    pd.DataFrame with MultiIndex (bus, stat) or empty DataFrame.
    """
    prices = extract_nodal_prices(n)
    if prices.empty:
        return pd.DataFrame()

    if isinstance(prices.index, pd.MultiIndex):
        prices_dt = prices.copy()
        prices_dt.index = prices.index.get_level_values("timestep")
    else:
        prices_dt = prices

    prices_dt["year"] = prices_dt.index.year
    rows = []
    for bus in [c for c in prices.columns if c != "System Average"]:
        for year, grp in prices_dt.groupby("year"):
            rows.append({
                "bus": bus,
                "year": year,
                "mean": grp[bus].mean(),
                "median": grp[bus].median(),
                "p5": grp[bus].quantile(0.05),
                "p95": grp[bus].quantile(0.95),
            })
    return pd.DataFrame(rows).set_index(["bus", "year"])


def get_transmission_flows(n: pypsa.Network) -> pd.DataFrame:
    """
    Return annual average flow and max utilisation per transmission line.

    Returns
    -------
    pd.DataFrame with columns ['mean_flow_MW', 'max_flow_MW', 'utilisation_pct']
    indexed by line name.
    """
    if n.lines_t.p0.empty:
        return pd.DataFrame()

    p0 = n.lines_t.p0.copy()
    if isinstance(p0.index, pd.MultiIndex):
        p0.index = p0.index.get_level_values("timestep")

    rows = []
    for line in n.lines.index:
        if line not in p0.columns:
            continue
        abs_flow = p0[line].abs()
        s_nom = n.lines.at[line, "s_nom"]
        rows.append({
            "line": line,
            "bus0": n.lines.at[line, "bus0"],
            "bus1": n.lines.at[line, "bus1"],
            "mean_flow_MW": float(abs_flow.mean()),
            "max_flow_MW": float(abs_flow.max()),
            "utilisation_pct": float(abs_flow.max() / s_nom * 100) if s_nom > 0 else np.nan,
        })
    return pd.DataFrame(rows).set_index("line")


def generate_multiperiod_overview(
    n: pypsa.Network,
    renewable_carriers: Optional[list] = None,
    thermal_carriers: Optional[list] = None,
) -> pd.DataFrame:
    """
    Generate comprehensive overview statistics for a (multi-period) network.

    Includes CAPEX, OPEX, TOTEX, curtailment, capacity factors, renewable share,
    and system LCOE.

    Parameters
    ----------
    n : pypsa.Network
    renewable_carriers : list, optional
        Defaults to config.RENEWABLE_CARRIERS.
    thermal_carriers : list, optional
        Defaults to config.THERMAL_CARRIERS.

    Returns
    -------
    pd.DataFrame
    """
    if renewable_carriers is None:
        renewable_carriers = config.RENEWABLE_CARRIERS
    if thermal_carriers is None:
        thermal_carriers = config.THERMAL_CARRIERS

    results = pd.Series(dtype=float)

    try:
        stats = n.statistics().groupby(level=1).sum()

        for short, full in [("CAPEX", "Capital Expenditure"), ("OPEX", "Operational Expenditure"), ("CAPACITY", "Optimal Capacity")]:
            if full in stats.columns:
                results = pd.concat([results, stats[full].rename(lambda x: f"{x} {short}")])

        if all(c in stats.columns for c in ["Capital Expenditure", "Operational Expenditure"]):
            totex = stats["Capital Expenditure"] + stats["Operational Expenditure"]
            results = pd.concat([results, totex.rename(lambda x: f"{x} TOTEX")])

        gen_carriers = set(n.generators.carrier.unique())

        if "Curtailment" in stats.columns and "Supply" in stats.columns:
            curtailment_rates = stats["Curtailment"] / (stats["Supply"] + stats["Curtailment"])
            vre_only = curtailment_rates[curtailment_rates.index.isin(set(renewable_carriers) & gen_carriers)]
            results = pd.concat([results, vre_only.rename(lambda x: f"{x} CURTAILMENT").dropna()])

        if all(c in stats.columns for c in ["Supply", "Curtailment", "Optimal Capacity"]):
            cf_avail = (stats["Supply"] + stats["Curtailment"]) / (stats["Optimal Capacity"] * 8760)
            cf_actual = stats["Supply"] / (stats["Optimal Capacity"] * 8760)
            vre_carriers_present = set(renewable_carriers) & gen_carriers
            results = pd.concat([
                results,
                cf_avail[cf_avail.index.isin(vre_carriers_present)].rename(lambda x: f"{x} CF AVAILABLE").dropna(),
                cf_actual[cf_actual.index.isin(gen_carriers)].rename(lambda x: f"{x} CF ACTUAL").dropna(),
            ])

        by_component = n.statistics().groupby(level=0).sum()
        if "Load" in by_component.index:
            annual_load = abs(by_component.loc["Load", "Energy Balance"])
            results["Total Load (MWh)"] = annual_load.sum() if hasattr(annual_load, "sum") else annual_load

            re_carriers_present = set(renewable_carriers) & set(stats.index)
            if re_carriers_present:
                re_supply = stats.loc[list(re_carriers_present), "Energy Balance"].sum()
                re_load_sum = annual_load.sum() if hasattr(annual_load, "sum") else annual_load
                results["Renewable Share"] = re_supply / re_load_sum if re_load_sum > 0 else np.nan

    except Exception as e:
        print(f"Warning: could not compute statistics: {e}")

    try:
        results["System LCOE (USD/MWh)"] = calculate_system_lcoe(n)
    except Exception:
        pass

    try:
        results["Lifetime Emissions (Mt CO2)"] = float(calculate_lifetime_emissions(n))
    except Exception:
        pass

    return results.dropna().to_frame("value").round(2)


def export_statistics(n: pypsa.Network, output_dir: str, scenario_name: str = "base") -> None:
    """
    Export results to CSV and JSON files in output_dir.

    Writes:
    - statistics.csv — raw n.statistics() output
    - overview.csv   — high-level KPIs
    - nodal_prices_summary.csv
    - transmission_flows.csv
    - run_metadata.json
    """
    os.makedirs(output_dir, exist_ok=True)

    # Raw statistics
    try:
        n.statistics().to_csv(os.path.join(output_dir, "statistics.csv"))
    except Exception as e:
        print(f"Warning: could not export statistics.csv: {e}")

    # Overview KPIs
    try:
        generate_multiperiod_overview(n).to_csv(os.path.join(output_dir, "overview.csv"))
    except Exception as e:
        print(f"Warning: could not export overview.csv: {e}")

    # Nodal price summary
    try:
        nodal_price_summary(n).to_csv(os.path.join(output_dir, "nodal_prices_summary.csv"))
    except Exception as e:
        print(f"Warning: could not export nodal_prices_summary.csv: {e}")

    # Transmission flows
    try:
        flows = get_transmission_flows(n)
        if not flows.empty:
            flows.to_csv(os.path.join(output_dir, "transmission_flows.csv"))
    except Exception as e:
        print(f"Warning: could not export transmission_flows.csv: {e}")

    # Run metadata
    metadata = {
        "scenario": scenario_name,
        "objective": float(n.objective) if hasattr(n, "objective") and n.objective is not None else None,
        "system_lcoe_usd_mwh": float(calculate_system_lcoe(n)),
        "n_buses": int(len(n.buses)),
        "n_generators": int(len(n.generators)),
        "n_storage_units": int(len(n.storage_units)),
        "n_snapshots": int(len(n.snapshots)),
    }
    with open(os.path.join(output_dir, "run_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Results exported to: {output_dir}")
