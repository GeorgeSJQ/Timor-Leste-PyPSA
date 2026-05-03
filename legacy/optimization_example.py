"""
Test Optimization Script for Timor Leste Grid
Runs a 1-year optimization with randomly generated renewable profiles at 1-hour resolution
"""

import pypsa
from pypsa.common import annuity

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from timor_leste_config import build_timor_leste_network, add_loads_to_network
from pypsa_setup import add_solar_pv, add_wind_farm, add_battery_storage, add_generic_battery, battery_constraint
from model_builder import prepare_vre_trace_for_snapshots
from config import SNAPSHOTS_START, SNAPSHOTS_END, DISCOUNT_RATE , CAPITAL_COSTS, MARGINAL_COSTS, TECHNICAL_PARAMS, SOLVER_NAME

# # Set random seed for reproducibility
# np.random.seed(42)

def setup_network_for_optimization():
    """
    Set up the Timor Leste network with generators and loads for optimization.
    
    Returns:
    --------
    network : pypsa.Network
        Configured network ready for optimization
    """
    # Create snapshots for 1 year at 3-hour resolution
    snapshots = pd.date_range(
        SNAPSHOTS_START,
        SNAPSHOTS_END,
        freq="1h"
    )
    
    print(f"Creating network with {len(snapshots)} snapshots (1-hour resolution)")
    
    # Build base network
    network = build_timor_leste_network(snapshots=snapshots, add_generators=True)
    
    # ========================================================================
    # Import renewable profiles (from renewables.ninja data)
    # ========================================================================
    
    print("\nImporting renewable energy profiles...")
    
    solar_cf = prepare_vre_trace_for_snapshots(
        csv_path=r"data\solar_pv_output_re_ninja.csv",
        snapshots=snapshots,
        freq="1h",
        target_timezone="Asia/Dili",
    )
    wind_cf = prepare_vre_trace_for_snapshots(
        csv_path=r"data\wind_output_re_ninja.csv",
        snapshots=snapshots,
        freq="1h",
        target_timezone="Asia/Dili",
    )
    
    print(f"  Solar CF: mean={solar_cf.mean():.3f}, max={solar_cf.max():.3f}")
    print(f"  Wind CF:  mean={wind_cf.mean():.3f}, max={wind_cf.max():.3f}")
    
    # ========================================================================
    # Add new generators and storage here
    # ========================================================================
    
    print("\nAdding new generators and storage...")
    
    # Solar PV at Dili
    add_solar_pv(
        network=network,
        name="Solar_Dili",
        bus="Dili",
        #p_nom=50,  # 50 MW
        capital_cost=CAPITAL_COSTS["solar"],
        marginal_cost=MARGINAL_COSTS["solar"],
        p_max_pu=solar_cf,
        p_nom_extendable=True,
    )
    
    # Wind farm at Lospalos
    add_wind_farm(
        network=network,
        name="Wind_Lospalos",
        bus="Lospalos",
        #p_nom=40,  # 40 MW
        capital_cost=CAPITAL_COSTS["wind_onshore"],
        marginal_cost=MARGINAL_COSTS["wind_onshore"],
        p_max_pu=wind_cf,
        wind_type="onshore",
        p_nom_extendable=True,
    )
    
    # Battery storage at Dili
    add_battery_storage(
        network=network,
        name="Battery_Dili",
        bus="Dili",
        #p_nom=20,  # 20 MW
        capital_cost=CAPITAL_COSTS["battery"],
        marginal_cost=MARGINAL_COSTS["battery"],
        max_hours=TECHNICAL_PARAMS["battery"]["max_hours"],
        p_nom_extendable=True,
    )

    # add_generic_battery(
    #     network=network,
    #     connecting_bus="Dili",
    #     latitude=-8.56,
    #     longitude=125.61,
    #     one_way_efficiency=0.95,
    #     capital_cost=CAPITAL_COSTS["battery"],
    # )

    
    print(f"  Added {len(network.generators) - 2} renewable generators")  # -2 for existing diesel
    print(f"  Added {len(network.storage_units) + len(network.stores)} battery storage units")
    
    # ========================================================================
    # Add load profiles
    # ========================================================================
    
    add_loads_to_network(network)
    
    return network


def run_optimization(network):
    """
    Run the PyPSA optimization.
    
    Parameters:
    -----------
    network : pypsa.Network
        The network to optimize
    
    Returns:
    --------
    None
    """
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION")
    print("="*70)
    
    # Run linear optimal power flow
    print("\nSolving optimal power flow...")
    print("This may take several minutes...")
    
    status = network.optimize(
        solver_name=SOLVER_NAME, 
        log_to_console=False, 
        #extra_functionality=battery_constraint
        )
    
    print(f"\nOptimization status: {status}")
    print(f"Objective value: ${network.objective:,.2f}")
    
    return status


def print_results(network):
    """
    Print optimization results.
    
    Parameters:
    -----------
    network : pypsa.Network
        The optimized network
    """
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS")
    print("="*70)
    
    # Generation statistics
    print("\n--- GENERATION CAPACITY ---")
    gen_stats = network.generators.groupby("carrier")["p_nom_opt"].sum()
    for carrier, capacity in gen_stats.items():
        print(f"  {carrier:.<30} {capacity:>10.2f} MW")
    
    if len(network.storage_units) > 0:
        storage_stats = network.storage_units.groupby("carrier")["p_nom_opt"].sum()
        print("\n--- STORAGE CAPACITY ---")
        for carrier, capacity in storage_stats.items():
            print(f"  {carrier:.<30} {capacity:>10.2f} MW")
    
    if len(network.stores) > 0:
        generic_storage_stats = network.stores.groupby("carrier")["e_nom_opt"].sum()
        # TODO: add inverter capacity stats
        # inverter_size = network.links
        print("\n--- GENERIC STORAGE CAPACITY ---")
        for carrier, capacity in generic_storage_stats.items():
            print(f"  {carrier:.<30} {capacity:>10.2f} MWh")
    
    # Energy generation
    print("\n--- ANNUAL ENERGY GENERATION ---")
    gen_energy = network.generators_t.p.sum() * 3  # 3-hour resolution
    gen_energy_by_carrier = gen_energy.groupby(network.generators.carrier).sum()
    total_energy = gen_energy_by_carrier.sum()
    
    for carrier, energy in gen_energy_by_carrier.items():
        share = energy / total_energy * 100
        print(f"  {carrier:.<30} {energy/1000:>10.2f} GWh ({share:>5.1f}%)")
    
    print(f"  {'TOTAL':.<30} {total_energy/1000:>10.2f} GWh")
    
    # Load statistics
    total_load = network.loads_t.p_set.sum().sum() * 3
    print(f"\n--- LOAD ---")
    print(f"  Total load served: {total_load/1000:.2f} GWh")
    
    # Renewable share
    renewable_carriers = ["solar", "wind_onshore", "wind_offshore"]
    renewable_energy = gen_energy_by_carrier[
        gen_energy_by_carrier.index.isin(renewable_carriers)
    ].sum()
    renewable_share = renewable_energy / total_energy * 100
    print(f"\n--- RENEWABLE ENERGY SHARE ---")
    print(f"  {renewable_share:.1f}%")
    
    print("="*70)


def plot_results(network, output_dir="results"):
    """
    Create plots of the optimization results.
    
    Parameters:
    -----------
    network : pypsa.Network
        The optimized network
    output_dir : str
        Directory to save plots
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nGenerating plots...")
    
    # Plot 1: Generation dispatch for first week
    fig, ax = plt.subplots(figsize=(15, 6))
    
    # Select first week
    first_week = network.snapshots[:56]  # 7 days * 8 periods/day
    
    gen_dispatch = network.generators_t.p.loc[first_week]
    gen_dispatch_by_carrier = gen_dispatch.groupby(network.generators.carrier, axis=1).sum()
    
    gen_dispatch_by_carrier.plot(kind="area", ax=ax, alpha=0.8, stacked=True)
    
    # Add load line
    load = network.loads_t.p_set.loc[first_week].sum(axis=1)
    ax.plot(load.index, load.values, 'k--', linewidth=2, label='Load')
    
    ax.set_xlabel("Time")
    ax.set_ylabel("Power (MW)")
    ax.set_title("Generation Dispatch - First Week of 2025")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/dispatch_first_week.png", dpi=300)
    print(f"  Saved: {output_dir}/dispatch_first_week.png")
    
    # Plot 2: Capacity comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    
    capacity = network.generators.groupby("carrier")[["p_nom", "p_nom_opt"]].sum()
    capacity.plot(kind="bar", ax=ax)
    
    ax.set_xlabel("Technology")
    ax.set_ylabel("Capacity (MW)")
    ax.set_title("Initial vs Optimized Capacity")
    ax.legend(["Initial", "Optimized"])
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/capacity_comparison.png", dpi=300)
    print(f"  Saved: {output_dir}/capacity_comparison.png")
    
    # Plot 3: Energy generation pie chart
    fig, ax = plt.subplots(figsize=(10, 8))
    
    gen_energy = network.generators_t.p.sum() * 3
    gen_energy_by_carrier = gen_energy.groupby(network.generators.carrier).sum()
    
    ax.pie(gen_energy_by_carrier, labels=gen_energy_by_carrier.index,
           autopct='%1.1f%%', startangle=90)
    ax.set_title("Annual Energy Generation by Technology")
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/energy_generation_pie.png", dpi=300)
    print(f"  Saved: {output_dir}/energy_generation_pie.png")
    
    print("Plotting complete!")


if __name__ == "__main__":
    # Setup network
    network = setup_network_for_optimization()
    
    # Run optimization
    status = run_optimization(network)
    
    # Check if optimization was successful (status is a tuple like ('ok', 'optimal'))
    if status[0] == "ok":
        # Print results
        print_results(network)
        
        # Plot results
        plot_results(network)
        
        # Save network
        network.export_to_netcdf("results/optimized_network.nc")
        print("\nOptimized network saved to: results/optimized_network.nc")
    else:
        print(f"\n⚠ Optimization failed with status: {status}")
