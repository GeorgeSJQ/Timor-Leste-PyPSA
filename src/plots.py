"""
Plotly visualisation functions for the Timor-Leste PyPSA model.
All functions return plotly Figure objects and optionally save HTML files.
"""

import calendar
import os
import numpy as np
import pandas as pd
import pypsa
import matplotlib.colors as mcolors
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, List

import config


# ============================================================================
# Internal helper
# ============================================================================

CAPACITY_TOL = 1e-6


def _built_generator_mask(n: pypsa.Network) -> pd.Series:
    """Return a boolean mask for generators with built or existing capacity."""
    if n.generators.empty:
        return pd.Series(dtype=bool)

    if "p_nom_opt" in n.generators.columns:
        capacity = n.generators["p_nom_opt"].fillna(n.generators["p_nom"])
    else:
        capacity = n.generators["p_nom"]

    return capacity.abs() > CAPACITY_TOL


def _built_generator_carriers(n: pypsa.Network) -> list:
    """Return carriers with non-zero built or existing generator capacity."""
    mask = _built_generator_mask(n)
    if mask.empty:
        return []
    return n.generators.loc[mask, "carrier"].dropna().unique().tolist()


def _filter_snapshots(n: pypsa.Network, start_date=None, end_date=None):
    """Return filtered snapshot index and boolean mask."""
    if isinstance(n.snapshots, pd.MultiIndex):
        ts = n.snapshots.get_level_values("timestep")
        start_mask = ts >= pd.Timestamp(start_date) if start_date else pd.Series(True, index=range(len(n.snapshots)))
        end_mask = ts <= pd.Timestamp(end_date) if end_date else pd.Series(True, index=range(len(n.snapshots)))
        # Convert to numpy booleans
        start_arr = (ts >= pd.Timestamp(start_date)).values if start_date else np.ones(len(ts), dtype=bool)
        end_arr = (ts <= pd.Timestamp(end_date)).values if end_date else np.ones(len(ts), dtype=bool)
        mask = start_arr & end_arr
        return n.snapshots[mask], mask
    else:
        snaps = n.snapshots
        if start_date:
            snaps = snaps[snaps >= pd.Timestamp(start_date)]
        if end_date:
            snaps = snaps[snaps <= pd.Timestamp(end_date)]
        mask = n.snapshots.isin(snaps)
        return snaps, np.asarray(mask, dtype=bool)


def _build_dispatch_df(
    n: pypsa.Network,
    filtered_snapshots,
    show_curtailment: bool = False,
    vre_carriers: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Build a tidy DataFrame for dispatch plotting.

    Columns: one per carrier (generation), one per storage carrier (charge/discharge),
    curtailment columns if requested, and 'Load'.
    Index: timestep-level DatetimeIndex.
    """
    if vre_carriers is None:
        vre_carriers = config.RENEWABLE_CARRIERS

    built_mask = _built_generator_mask(n)
    built_generators = n.generators.index[built_mask]
    gen_data = n.generators_t.p.loc[filtered_snapshots, built_generators]
    if isinstance(gen_data.index, pd.MultiIndex):
        plot_index = gen_data.index.get_level_values("timestep")
    else:
        plot_index = gen_data.index

    df = pd.DataFrame(index=plot_index)

    # Generation grouped by carrier
    p_by_carrier = gen_data.T.groupby(n.generators.loc[built_generators, "carrier"]).sum().T
    if isinstance(p_by_carrier.index, pd.MultiIndex):
        p_by_carrier.index = p_by_carrier.index.get_level_values("timestep")
    for carrier in p_by_carrier.columns:
        if p_by_carrier[carrier].abs().max() > CAPACITY_TOL:
            df[carrier] = p_by_carrier[carrier].values

    # Curtailment
    if show_curtailment:
        for carrier in vre_carriers:
            vre_gens = built_generators[n.generators.loc[built_generators, "carrier"] == carrier]
            if len(vre_gens) == 0:
                continue
            max_possible = pd.Series(0.0, index=plot_index)
            for gen in vre_gens:
                p_max_data = n.generators_t.p_max_pu.loc[filtered_snapshots, gen] if gen in n.generators_t.p_max_pu else pd.Series(1.0, index=filtered_snapshots)
                if isinstance(p_max_data.index, pd.MultiIndex):
                    p_max_data.index = p_max_data.index.get_level_values("timestep")
                gen_capacity = n.generators.at[gen, "p_nom_opt"] if "p_nom_opt" in n.generators.columns else n.generators.at[gen, "p_nom"]
                max_possible += p_max_data.values * gen_capacity
            actual = df.get(carrier, pd.Series(0.0, index=plot_index))
            curtailed = (max_possible.values - actual.values).clip(min=0)
            if curtailed.max() > CAPACITY_TOL:
                df[f"{carrier} (curtailed)"] = curtailed

    # Storage units
    if not n.storage_units.empty:
        su_data = n.storage_units_t.p.loc[filtered_snapshots].T.groupby(n.storage_units.carrier).sum().T
        if isinstance(su_data.index, pd.MultiIndex):
            su_data.index = su_data.index.get_level_values("timestep")
        for carrier in su_data.columns:
            discharge = su_data[carrier].clip(lower=0)
            charge = su_data[carrier].clip(upper=0)
            if (discharge > 0).any():
                df[carrier] = discharge.values
            if (charge < 0).any():
                df[f"{carrier} (charging)"] = charge.values

    # Stores
    if not n.stores.empty and not n.stores_t.p.empty:
        for store, carrier in n.stores.carrier.items():
            store_p = n.stores_t.p.loc[filtered_snapshots, store]
            if isinstance(store_p.index, pd.MultiIndex):
                store_p.index = store_p.index.get_level_values("timestep")
            discharge = store_p.clip(lower=0)
            charge = store_p.clip(upper=0)
            if (discharge > 0).any():
                df[carrier] = df.get(carrier, pd.Series(0.0, index=plot_index)).values + discharge.values
            if (charge < 0).any():
                name = f"{carrier} (charging)"
                df[name] = df.get(name, pd.Series(0.0, index=plot_index)).values + charge.values

    # Load
    load_data = n.loads_t.p_set.loc[filtered_snapshots].sum(axis=1)
    if isinstance(load_data.index, pd.MultiIndex):
        load_data.index = load_data.index.get_level_values("timestep")
    df["Load"] = load_data.values

    return df


# ============================================================================
# Dispatch plot
# ============================================================================

def create_dispatch_plot(
    n: pypsa.Network,
    start_date=None,
    end_date=None,
    stack: bool = True,
    show_curtailment: bool = False,
    vre_carriers: Optional[List[str]] = None,
    y_range: Optional[List[float]] = None,
) -> go.Figure:
    """
    Create a Plotly dispatch chart showing generation, storage, and load.

    Parameters
    ----------
    n : pypsa.Network
    start_date, end_date : str or pd.Timestamp, optional
    stack : bool
        Stacked area chart if True, line chart if False.
    show_curtailment : bool
        Overlay curtailed VRE potential (lighter shade) on top.
    vre_carriers : list, optional
        Carriers treated as VRE for curtailment calculation.
    y_range : list, optional
        [y_min, y_max] for the y-axis.

    Returns
    -------
    go.Figure
    """
    filtered_snaps, _ = _filter_snapshots(n, start_date, end_date)
    df = _build_dispatch_df(n, filtered_snaps, show_curtailment=show_curtailment, vre_carriers=vre_carriers)

    curtailment_cols = [c for c in df.columns if "(curtailed)" in c]
    charge_cols = [c for c in df.columns if "(charging)" in c]
    gen_cols = [c for c in df.columns if c not in {"Load"} and "(charging)" not in c and "(curtailed)" not in c]

    fig = go.Figure()

    def _carrier_color(carrier):
        base = carrier.replace(" (curtailed)", "").replace(" (charging)", "")
        if hasattr(n.carriers, "color") and base in n.carriers.index:
            return n.carriers.color.get(base, "#CCCCCC")
        return "#CCCCCC"

    def _lighter(hex_color):
        rgb = mcolors.hex2color(hex_color)
        return mcolors.rgb2hex([min(1.0, c * 1.5) for c in rgb])

    if stack:
        for col in gen_cols:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], mode="lines",
                line=dict(width=0), stackgroup="generation",
                name=col, fillcolor=_carrier_color(col),
                hovertemplate=f"{col}: %{{y:.1f}} MW<extra></extra>",
            ))
        for col in curtailment_cols:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], mode="lines",
                line=dict(width=0), stackgroup="curtailment",
                name=col, fillcolor=_lighter(_carrier_color(col)),
                hovertemplate=f"{col}: %{{y:.1f}} MW<extra></extra>",
            ))
        for col in charge_cols:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], mode="lines",
                line=dict(width=0), stackgroup="charging",
                name=col, fillcolor=_carrier_color(col),
                hovertemplate=f"{col}: %{{y:.1f}} MW<extra></extra>",
            ))
    else:
        for col in gen_cols + curtailment_cols + charge_cols:
            is_load = col == "Load"
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], mode="lines", name=col,
                line=dict(color="black" if is_load else _carrier_color(col),
                          width=2 if is_load else 1),
            ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df["Load"], name="Load",
        line=dict(color="black", width=2),
        hovertemplate="Load: %{y:.1f} MW<extra></extra>",
    ))

    layout_kwargs = dict(
        title="Generation and Storage Dispatch",
        xaxis_title="Date / Time",
        yaxis_title="Power (MW)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    if y_range:
        layout_kwargs["yaxis_range"] = y_range

    fig.update_layout(**layout_kwargs)
    return fig


# ============================================================================
# Heatmaps
# ============================================================================

def plot_generator_output_heatmap(
    n: pypsa.Network,
    carrier: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Optional[go.Figure]:
    """
    Plot average generator output as a day-of-year × hour-of-day heatmap.

    Data is averaged across all years in the date range.
    """
    built_mask = _built_generator_mask(n)
    built_generators = n.generators.index[built_mask]
    gen_data = n.generators_t.p.loc[:, built_generators].copy()
    if gen_data.empty:
        return None

    if isinstance(gen_data.index, pd.MultiIndex):
        gen_data.index = gen_data.index.get_level_values("timestep")

    start_year = int(start_date.split("-")[0]) if start_date else gen_data.index[0].year
    end_year = int(end_date.split("-")[0]) if end_date else gen_data.index[-1].year

    gen_data = gen_data[(gen_data.index.year >= start_year) & (gen_data.index.year <= end_year)]
    carrier_gen = gen_data.T.groupby(n.generators.loc[built_generators, "carrier"]).sum().T

    if carrier not in carrier_gen.columns or carrier_gen[carrier].max() == 0:
        print(f"No generation data for carrier '{carrier}'.")
        return None

    data = carrier_gen[carrier]
    data = data[~((data.index.month == 2) & (data.index.day == 29))]

    df = pd.DataFrame({
        "generation": data.values,
        "day_of_year": data.index.dayofyear,
        "hour": data.index.hour,
    }, index=data.index)

    leap_mask = df.index.to_series().dt.is_leap_year & (df.index.month > 2)
    df.loc[leap_mask, "day_of_year"] -= 1

    heatmap = df.groupby(["day_of_year", "hour"])["generation"].mean().unstack(level=0)
    heatmap = heatmap.reindex(index=pd.Index(range(24), name="hour"), columns=pd.Index(range(1, 366), name="day_of_year"), fill_value=0)

    colorscale = [
        [0.0, "#000080"], [0.2, "#0000FF"], [0.4, "#00FFFF"],
        [0.5, "#00FF00"], [0.6, "#FFFF00"], [0.8, "#FF8000"], [1.0, "#FF0000"],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=heatmap.values, x=heatmap.columns, y=heatmap.index,
        colorscale=colorscale, zmin=0, zmax=heatmap.values.max(),
        hoverongaps=False,
        hovertemplate=f"<b>{carrier}</b><br>Day: %{{x}}<br>Hour: %{{y}}<br>Output: %{{z:.1f}} MW<extra></extra>",
        colorbar=dict(title="Output (MW)"),
    ))

    year_range = str(start_year) if start_year == end_year else f"{start_year}–{end_year}"
    fig.update_layout(
        title=f"{carrier} Generator Output Heatmap ({year_range})",
        xaxis_title="Day of Year", yaxis_title="Hour of Day",
        height=500,
    )
    fig.update_xaxes(dtick=30, range=[1, 365])
    fig.update_yaxes(dtick=4, range=[0, 23])
    return fig


def plot_storage_soc(
    n: pypsa.Network,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    resample_freq: Optional[str] = None,
) -> Optional[go.Figure]:
    """
    Plot state of charge for all StorageUnits and Stores.

    Solid lines show MWh; dotted lines (legend-only by default) show % of capacity.
    """
    soc_su = n.storage_units_t.state_of_charge.copy() if not n.storage_units.empty else pd.DataFrame()
    soc_store = n.stores_t.e.copy() if not n.stores.empty else pd.DataFrame()

    for df in [soc_su, soc_store]:
        if not df.empty and isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("timestep")

    soc_su.columns = [f"{c} [SU]" for c in soc_su.columns]
    soc_store.columns = [f"{c} [Store]" for c in soc_store.columns]
    soc = pd.concat([soc_su, soc_store], axis=1)

    if soc.empty:
        return None

    if start_date:
        soc = soc.loc[soc.index >= start_date]
    if end_date:
        soc = soc.loc[soc.index <= end_date]

    soc = soc[[c for c in soc.columns if soc[c].max() > 0]]
    if soc.empty:
        return None

    if resample_freq:
        soc = soc.resample(resample_freq).mean()

    max_soc = {}
    for col in soc.columns:
        name, typ = col.rsplit(" [", 1)
        if "SU" in typ:
            max_soc[col] = n.storage_units.at[name, "p_nom_opt"] * n.storage_units.at[name, "max_hours"]
        else:
            max_soc[col] = n.stores.at[name, "e_nom_opt"] if n.stores.at[name, "e_nom_extendable"] else n.stores.at[name, "e_nom"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2"]

    for i, col in enumerate(soc.columns):
        color = colors[i % len(colors)]
        pct = soc[col] / max_soc[col] * 100 if max_soc[col] > 0 else soc[col] * 0
        fig.add_trace(go.Scatter(x=soc.index, y=soc[col], name=f"{col} (MWh)", line=dict(color=color)), secondary_y=False)
        fig.add_trace(go.Scatter(x=soc.index, y=pct, name=f"{col} (%)", line=dict(color=color, dash="dot"), visible="legendonly"), secondary_y=True)

    fig.update_layout(
        title="Battery State of Charge",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    fig.update_yaxes(title_text="State of Charge (MWh)", secondary_y=False)
    fig.update_yaxes(title_text="State of Charge (%)", secondary_y=True, range=[0, 100])
    fig.update_xaxes(title_text="Time")
    return fig


def plot_storage_soc_heatmap(
    n: pypsa.Network,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Optional[go.Figure]:
    """Plot SOC % as day-of-year × hour-of-day heatmap, averaged across years."""
    soc_su = n.storage_units_t.state_of_charge.copy() if not n.storage_units.empty else pd.DataFrame()
    soc_store = n.stores_t.e.copy() if not n.stores.empty else pd.DataFrame()

    for df in [soc_su, soc_store]:
        if not df.empty and isinstance(df.index, pd.MultiIndex):
            df.index = df.index.get_level_values("timestep")

    soc_su.columns = [f"{c} [SU]" for c in soc_su.columns]
    soc_store.columns = [f"{c} [Store]" for c in soc_store.columns]
    soc = pd.concat([soc_su, soc_store], axis=1)

    if soc.empty:
        return None

    start_year = int(start_date.split("-")[0]) if start_date else soc.index[0].year
    end_year = int(end_date.split("-")[0]) if end_date else soc.index[-1].year
    soc = soc[(soc.index.year >= start_year) & (soc.index.year <= end_year)]
    soc = soc[[c for c in soc.columns if soc[c].max() > 0]]

    if soc.empty:
        return None

    max_soc = {}
    for col in soc.columns:
        name, typ = col.rsplit(" [", 1)
        if "SU" in typ:
            max_soc[col] = n.storage_units.at[name, "p_nom_opt"] * n.storage_units.at[name, "max_hours"]
        else:
            max_soc[col] = n.stores.at[name, "e_nom_opt"] if n.stores.at[name, "e_nom_extendable"] else n.stores.at[name, "e_nom"]

    soc_pct = pd.DataFrame(index=soc.index)
    for col in soc.columns:
        soc_pct[col] = soc[col] / max_soc[col] * 100 if max_soc[col] > 0 else 0

    leap_mask = soc_pct.index.to_series().dt.is_leap_year & (soc_pct.index.month > 2)
    soc_pct["day_of_year"] = soc_pct.index.dayofyear
    soc_pct.loc[leap_mask, "day_of_year"] -= 1
    soc_pct["hour"] = soc_pct.index.hour
    soc_pct = soc_pct[~((soc_pct.index.month == 2) & (soc_pct.index.day == 29))]

    storage_cols = [c for c in soc_pct.columns if c not in ("day_of_year", "hour")]
    n_storage = len(storage_cols)
    if n_storage == 0:
        return None

    cols = min(2, n_storage)
    rows = (n_storage + cols - 1) // cols
    titles = [c.replace(" [SU]", "").replace(" [Store]", "") for c in storage_cols]

    fig = make_subplots(rows=rows, cols=cols, subplot_titles=titles, shared_xaxes=True, shared_yaxes=True, vertical_spacing=0.15)

    colorscale = [
        [0.0, "#000080"], [0.2, "#0000FF"], [0.4, "#00FFFF"],
        [0.5, "#00FF00"], [0.6, "#FFFF00"], [0.8, "#FF8000"], [1.0, "#FF0000"],
    ]

    for i, col in enumerate(storage_cols):
        r, c = (i // cols) + 1, (i % cols) + 1
        grouped = soc_pct.groupby(["day_of_year", "hour"])[col].mean().unstack(level=0)
        grouped = grouped.reindex(index=pd.Index(range(24)), columns=pd.Index(range(1, 366)), fill_value=0)
        show_cb = i == len(storage_cols) - 1
        fig.add_trace(go.Heatmap(
            z=grouped.values, x=grouped.columns, y=grouped.index,
            colorscale=colorscale, zmin=0, zmax=100,
            hovertemplate=f"<b>{titles[i]}</b><br>Day: %{{x}}<br>Hour: %{{y}}<br>SOC: %{{z:.1f}}%<extra></extra>",
            colorbar=dict(title="SOC (%)", ticksuffix="%") if show_cb else None,
            showscale=show_cb,
        ), row=r, col=c)

    year_range = str(start_year) if start_year == end_year else f"{start_year}–{end_year}"
    fig.update_layout(title=f"BESS State of Charge Heatmap ({year_range})", height=max(400, 300 * rows))
    return fig


# ============================================================================
# Monthly production
# ============================================================================

def plot_monthly_electric_production(
    n: pypsa.Network,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> go.Figure:
    """
    Plot average monthly generation by carrier across all years in the range.

    Works for both single-period and multi-period networks.
    """
    built_mask = _built_generator_mask(n)
    built_generators = n.generators.index[built_mask]
    gen_t = n.generators_t.p.loc[:, built_generators].copy()
    if isinstance(gen_t.index, pd.MultiIndex):
        gen_t.index = gen_t.index.get_level_values("timestep")

    weightings = n.snapshot_weightings["generators"].copy()
    if isinstance(weightings.index, pd.MultiIndex):
        weightings.index = weightings.index.get_level_values("timestep")

    if start_year is None:
        start_year = gen_t.index[0].year
    if end_year is None:
        end_year = gen_t.index[-1].year

    gen_t = gen_t[(gen_t.index.year >= start_year) & (gen_t.index.year <= end_year)]
    weightings = weightings[(weightings.index.year >= start_year) & (weightings.index.year <= end_year)]

    carrier_gen = gen_t.T.groupby(n.generators.loc[built_generators, "carrier"]).sum().T
    weighted = carrier_gen.mul(weightings, axis=0)

    # StorageUnit net charge
    if not n.storage_units.empty:
        su_t = n.storage_units_t.p.copy()
        if isinstance(su_t.index, pd.MultiIndex):
            su_t.index = su_t.index.get_level_values("timestep")
        su_t = su_t[(su_t.index.year >= start_year) & (su_t.index.year <= end_year)]
        su_carrier = su_t.T.groupby(n.storage_units.carrier).sum().T
        weighted = pd.concat([weighted, su_carrier.mul(weightings, axis=0)], axis=1)

    monthly = weighted.resample("ME").sum()
    monthly["month"] = monthly.index.month
    monthly_avg = monthly.groupby("month").mean()
    monthly_avg.index = monthly_avg.index.map(lambda x: calendar.month_abbr[x])

    fig = go.Figure()
    for carrier in monthly_avg.columns:
        if monthly_avg[carrier].abs().max() <= CAPACITY_TOL:
            continue
        color = n.carriers.loc[carrier, "color"] if carrier in n.carriers.index else None
        fig.add_trace(go.Bar(
            x=monthly_avg.index,
            y=monthly_avg[carrier],
            name=carrier,
            marker_color=color,
        ))

    fig.update_layout(
        title="Average Monthly Generation by Carrier",
        xaxis_title="Month",
        yaxis_title="Energy (MWh)",
        barmode="relative",
    )
    return fig


# ============================================================================
# New Timor-specific plots
# ============================================================================

def plot_nodal_prices(
    n: pypsa.Network,
    output_dir: Optional[str] = None,
) -> go.Figure:
    """
    Plot marginal electricity price at each bus over time.

    For multi-period networks uses the full timestep axis.
    """
    prices = n.buses_t.marginal_price.copy()
    if prices.empty:
        return go.Figure()

    if isinstance(prices.index, pd.MultiIndex):
        prices.index = prices.index.get_level_values("timestep")

    fig = go.Figure()
    for bus in prices.columns:
        fig.add_trace(go.Scatter(
            x=prices.index, y=prices[bus],
            mode="lines", name=bus, line=dict(width=1),
        ))

    fig.update_layout(
        title="Nodal Marginal Prices",
        xaxis_title="Time",
        yaxis_title="Marginal Price (USD/MWh)",
        hovermode="x unified",
    )

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        fig.write_html(os.path.join(output_dir, "nodal_prices.html"))

    return fig


def plot_transmission_utilisation(
    n: pypsa.Network,
    output_dir: Optional[str] = None,
) -> go.Figure:
    """
    Bar chart showing max line loading as % of thermal rating (s_nom).
    """
    if n.lines_t.p0.empty:
        return go.Figure()

    p0 = n.lines_t.p0.copy()
    if isinstance(p0.index, pd.MultiIndex):
        p0.index = p0.index.get_level_values("timestep")

    lines = []
    utilisation = []
    for line in n.lines.index:
        if line not in p0.columns:
            continue
        s_nom = n.lines.at[line, "s_nom"]
        max_flow = p0[line].abs().max()
        lines.append(f"{n.lines.at[line, 'bus0']}→{n.lines.at[line, 'bus1']}")
        utilisation.append(max_flow / s_nom * 100 if s_nom > 0 else 0)

    fig = go.Figure(go.Bar(x=lines, y=utilisation, marker_color="#4169E1"))
    fig.update_layout(
        title="Peak Line Utilisation (% of s_nom)",
        xaxis_title="Transmission Corridor",
        yaxis_title="Utilisation (%)",
        yaxis_range=[0, 110],
    )
    fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Thermal Limit")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        fig.write_html(os.path.join(output_dir, "transmission_utilisation.html"))

    return fig


def save_all_plots(
    n: pypsa.Network,
    output_dir: str,
    scenario_name: str = "base",
    dispatch_start: Optional[str] = None,
    dispatch_end: Optional[str] = None,
) -> None:
    """
    Render and save all standard plots as HTML files.

    Parameters
    ----------
    n : pypsa.Network
        Optimised network.
    output_dir : str
        Directory under which a 'plots/' sub-folder is created.
    scenario_name : str
        Used for display in print messages only.
    dispatch_start, dispatch_end : str, optional
        Date range for the dispatch plot. Defaults to the full model horizon.
    """
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    for filename in os.listdir(plots_dir):
        if filename.endswith(".html"):
            os.remove(os.path.join(plots_dir, filename))

    plots = {
        "dispatch.html": lambda: create_dispatch_plot(n, dispatch_start, dispatch_end),
        "dispatch_with_curtailment.html": lambda: create_dispatch_plot(n, dispatch_start, dispatch_end, show_curtailment=True),
        "monthly_generation.html": lambda: plot_monthly_electric_production(n),
        "nodal_prices.html": lambda: plot_nodal_prices(n),
        "transmission_utilisation.html": lambda: plot_transmission_utilisation(n),
    }

    # Per-carrier generator heatmaps
    for carrier in _built_generator_carriers(n):
        plots[f"heatmap_{carrier}.html"] = lambda c=carrier: plot_generator_output_heatmap(n, c)

    # Storage SOC plots
    if not n.storage_units.empty:
        plots["storage_soc.html"] = lambda: plot_storage_soc(n)
        plots["storage_soc_heatmap.html"] = lambda: plot_storage_soc_heatmap(n)

    for filename, plot_fn in plots.items():
        try:
            fig = plot_fn()
            if fig is not None:
                fig.write_html(os.path.join(plots_dir, filename))
                print(f"  Saved: {filename}")
        except Exception as e:
            print(f"  Warning: could not generate {filename}: {e}")

    print(f"All plots saved to: {plots_dir}")
