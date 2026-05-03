"""
Timor-Leste PyPSA Capacity Expansion Model — Main Entry Point

Usage:
    python run.py                          # Run base scenario
    python run.py --scenario high_diesel   # Run a specific scenario
    python run.py --scenario all           # Run all defined scenarios
    python run.py --single-year            # Single-year 2025 optimisation (fast)
    python run.py --start-year 2025 --end-year 2035   # Custom horizon

See config.SCENARIOS for available scenario names.
"""

import argparse
import os
import sys
import time

import pandas as pd

import config
from model_builder import build_multiperiod_network
from src.results import export_statistics, generate_multiperiod_overview, calculate_system_lcoe
from src.plots import save_all_plots


def _run_single_scenario(
    scenario_name: str,
    start_year: int,
    end_year: int,
    solver_name: str,
    save_network: bool = True,
) -> None:
    """Build, optimise, and save results for one scenario."""
    output_dir = os.path.join(config.OUTPUT_DIR, scenario_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'#'*70}")
    print(f"  SCENARIO: {scenario_name}")
    scenario_desc = config.SCENARIOS.get(scenario_name, {}).get("description", "")
    if scenario_desc:
        print(f"  {scenario_desc}")
    print(f"{'#'*70}")

    t0 = time.time()

    # Build network
    network = build_multiperiod_network(
        scenario_name=scenario_name,
        start_year=start_year,
        end_year=end_year,
    )

    # Run optimisation
    print("\nSolving multi-period investment optimisation...")
    print("(This may take several minutes for a 20-year horizon)\n")

    status = network.optimize(
        solver_name=solver_name,
        multi_invest=True,
        log_to_console=False,
    )

    elapsed = time.time() - t0
    status_str = status[0] if isinstance(status, tuple) else str(status)
    condition = status[1] if isinstance(status, tuple) and len(status) > 1 else ""

    print(f"\nOptimisation status: {status_str} ({condition})")
    print(f"Elapsed time: {elapsed:.1f}s")

    if status_str != "ok":
        print(f"WARNING: Optimisation did not converge cleanly (status={status_str}). Results may be invalid.")

    # Print summary
    print(f"\nObjective value: USD {network.objective:,.0f}")
    lcoe = calculate_system_lcoe(network)
    if lcoe is not None and not pd.isna(lcoe):
        print(f"System LCOE:     USD {lcoe:.1f}/MWh")

    # Print capacity summary
    if not network.generators.empty and "p_nom_opt" in network.generators.columns:
        print("\n--- OPTIMISED GENERATION CAPACITY ---")
        cap = network.generators.groupby("carrier")["p_nom_opt"].sum()
        for carrier, mw in cap[cap > 0.1].items():
            print(f"  {carrier:<25} {mw:>8.1f} MW")

    if not network.storage_units.empty and "p_nom_opt" in network.storage_units.columns:
        print("\n--- OPTIMISED STORAGE CAPACITY ---")
        scap = network.storage_units.groupby("carrier")["p_nom_opt"].sum()
        for carrier, mw in scap[scap > 0.1].items():
            energy_mwh = mw * network.storage_units[network.storage_units.carrier == carrier]["max_hours"].mean()
            print(f"  {carrier:<25} {mw:>8.1f} MW  ({energy_mwh:.1f} MWh)")

    # Save network
    if save_network:
        nc_path = os.path.join(output_dir, "optimized_network.nc")
        network.export_to_netcdf(nc_path)
        print(f"\nNetwork saved to: {nc_path}")

    # Export statistics and plots
    export_statistics(network, output_dir, scenario_name=scenario_name)
    save_all_plots(network, output_dir, scenario_name=scenario_name)

    print(f"\nScenario '{scenario_name}' complete. Results in: {output_dir}\n")


def _run_single_year(solver_name: str) -> None:
    """
    Fast single-year (2025) optimisation for validation and development.
    Uses the existing optimization_example.py logic.
    """
    print("\nRunning single-year 2025 optimisation...")

    from timor_leste_config import build_timor_leste_network, add_loads_to_network
    from pypsa_setup import add_solar_pv, add_wind_farm, add_battery_storage
    from model_builder import prepare_vre_trace_for_snapshots

    snapshots = pd.date_range(config.SNAPSHOTS_START, config.SNAPSHOTS_END, freq="1h")
    network = build_timor_leste_network(snapshots=snapshots, add_generators=True)

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

    add_solar_pv(
        network=network, name="Solar_Dili", bus="Dili",
        capital_cost=config.CAPITAL_COSTS["solar"],
        marginal_cost=config.MARGINAL_COSTS["solar"],
        p_max_pu=solar_cf,
        p_nom_extendable=True,
    )
    add_wind_farm(
        network=network, name="Wind_Lospalos", bus="Lospalos",
        capital_cost=config.CAPITAL_COSTS["wind_onshore"],
        marginal_cost=config.MARGINAL_COSTS["wind_onshore"],
        p_max_pu=wind_cf,
        wind_type="onshore",
        p_nom_extendable=True,
    )
    add_battery_storage(
        network=network, name="Battery_Dili", bus="Dili",
        capital_cost=config.CAPITAL_COSTS["battery"],
        marginal_cost=config.MARGINAL_COSTS["battery"],
        max_hours=config.TECHNICAL_PARAMS["battery"]["max_hours"],
        p_nom_extendable=True,
    )
    add_loads_to_network(network)

    print("Solving...")
    status = network.optimize(solver_name=solver_name, log_to_console=False)
    status_str = status[0] if isinstance(status, tuple) else str(status)
    print(f"Status: {status_str}")
    print(f"Objective: USD {network.objective:,.0f}")

    output_dir = os.path.join(config.OUTPUT_DIR, "single_year_2025")
    os.makedirs(output_dir, exist_ok=True)
    network.export_to_netcdf(os.path.join(output_dir, "optimized_network.nc"))

    export_statistics(network, output_dir, scenario_name="single_year_2025")
    save_all_plots(network, output_dir, scenario_name="single_year_2025")
    print(f"Results saved to: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Timor-Leste PyPSA capacity expansion model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available scenarios: {', '.join(config.SCENARIOS.keys())}",
    )
    parser.add_argument(
        "--scenario", default="base",
        help="Scenario name, or 'all' to run every scenario (default: base)",
    )
    parser.add_argument(
        "--start-year", type=int, default=config.MODEL_START_YEAR,
        help=f"Model start year (default: {config.MODEL_START_YEAR})",
    )
    parser.add_argument(
        "--end-year", type=int, default=config.MODEL_END_YEAR,
        help=f"Model end year (default: {config.MODEL_END_YEAR})",
    )
    parser.add_argument(
        "--solver", default=config.SOLVER_NAME,
        help=f"LP solver (default: {config.SOLVER_NAME})",
    )
    parser.add_argument(
        "--single-year", action="store_true",
        help="Run a fast single-year (2025) optimisation for validation",
    )
    parser.add_argument(
        "--no-save-network", action="store_true",
        help="Skip saving the .nc network file (speeds up runs)",
    )

    args = parser.parse_args()

    if args.single_year:
        _run_single_year(solver_name=args.solver)
        return

    scenarios_to_run = list(config.SCENARIOS.keys()) if args.scenario == "all" else [args.scenario]

    for sname in scenarios_to_run:
        if sname not in config.SCENARIOS:
            print(f"ERROR: Unknown scenario '{sname}'. Available: {', '.join(config.SCENARIOS.keys())}")
            sys.exit(1)

    print(f"Running {len(scenarios_to_run)} scenario(s): {scenarios_to_run}")
    print(f"Horizon: {args.start_year}–{args.end_year}, Solver: {args.solver}")

    for sname in scenarios_to_run:
        _run_single_scenario(
            scenario_name=sname,
            start_year=args.start_year,
            end_year=args.end_year,
            solver_name=args.solver,
            save_network=not args.no_save_network,
        )

    print("\nAll scenarios complete.")


if __name__ == "__main__":
    main()
