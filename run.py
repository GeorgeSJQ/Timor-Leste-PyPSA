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


def _freeze_capacities(network) -> None:
    """
    Copy ``p_nom_opt`` / ``s_nom_opt`` / ``e_nom_opt`` onto the static
    capacity attribute and turn off extendability on every component, so a
    follow-up dispatch solve treats capacities as fixed.

    Used between the two stages of a rolling-horizon investment-then-dispatch
    workflow.
    """
    if not network.generators.empty and "p_nom_opt" in network.generators.columns:
        network.generators["p_nom"] = network.generators["p_nom_opt"]
        network.generators["p_nom_extendable"] = False
    if not network.storage_units.empty and "p_nom_opt" in network.storage_units.columns:
        network.storage_units["p_nom"] = network.storage_units["p_nom_opt"]
        network.storage_units["p_nom_extendable"] = False
    if not network.stores.empty and "e_nom_opt" in network.stores.columns:
        network.stores["e_nom"] = network.stores["e_nom_opt"]
        network.stores["e_nom_extendable"] = False
    if not network.lines.empty and "s_nom_opt" in network.lines.columns:
        network.lines["s_nom"] = network.lines["s_nom_opt"]
        network.lines["s_nom_extendable"] = False
    if not network.links.empty and "p_nom_opt" in network.links.columns:
        network.links["p_nom"] = network.links["p_nom_opt"]
        network.links["p_nom_extendable"] = False


def _run_two_stage_rolling_horizon(network, solver_name: str, rolling_cfg: dict):
    """
    Two-stage rolling-horizon solve: full-horizon investment, then operations.

    Stage 1: full-horizon LP with ``multi_investment_periods=True`` to pick
    optimal capacities for every extendable component.
    Stage 2: capacities frozen via ``_freeze_capacities()``, then PyPSA's
    ``optimize.optimize_with_rolling_horizon()`` solves dispatch window-by-
    window, carrying state-of-charge / store energy across windows.

    Returns
    -------
    (status_str, condition) : tuple[str, str]
        Stage 1 solver status and condition strings, used by the calling
        scenario harness to format the run summary.
    """
    horizon = int(rolling_cfg.get("horizon", 168))
    overlap = int(rolling_cfg.get("overlap", 24))
    if overlap >= horizon:
        raise ValueError(
            f"ROLLING_HORIZON overlap ({overlap}) must be less than horizon "
            f"({horizon})."
        )

    print("\n" + "=" * 70)
    print("ROLLING-HORIZON MODE — two-stage solve")
    print(f"  horizon={horizon} snapshots, overlap={overlap} snapshots")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Stage 1 — full-horizon investment solve
    # ------------------------------------------------------------------
    print("\n[Stage 1/2] Full-horizon investment solve...")
    t1 = time.time()
    status = network.optimize(
        solver_name=solver_name,
        multi_investment_periods=True,
        log_to_console=False,
        include_objective_constant=False,
    )
    print(f"[Stage 1/2] complete in {time.time() - t1:.1f}s")

    status_str = status[0] if isinstance(status, tuple) else str(status)
    condition = status[1] if isinstance(status, tuple) and len(status) > 1 else ""

    if status_str != "ok":
        print(
            f"[Stage 1/2] FAILED (status={status_str}). Skipping stage 2 — "
            f"capacities not yet trustworthy."
        )
        return status_str, condition

    # ------------------------------------------------------------------
    # Freeze capacities — stage 2 must not re-decide them
    # ------------------------------------------------------------------
    _freeze_capacities(network)

    # ------------------------------------------------------------------
    # Stage 2 — rolling-horizon dispatch
    # ------------------------------------------------------------------
    n_snapshots = len(network.snapshots)
    n_windows = (n_snapshots + horizon - overlap - 1) // (horizon - overlap)
    print(
        f"\n[Stage 2/2] Rolling-horizon dispatch — {n_snapshots:,} snapshots "
        f"in ~{n_windows} windows..."
    )
    t2 = time.time()
    network.optimize.optimize_with_rolling_horizon(
        snapshots=network.snapshots,
        horizon=horizon,
        overlap=overlap,
        solver_name=solver_name,
        log_to_console=False,
    )
    print(f"[Stage 2/2] complete in {time.time() - t2:.1f}s")

    return status_str, condition


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
        output_dir=output_dir,
    )

    # Run optimisation
    rolling_cfg = getattr(config, "ROLLING_HORIZON", {"enabled": False})
    if rolling_cfg.get("enabled", False):
        status_str, condition = _run_two_stage_rolling_horizon(
            network=network,
            solver_name=solver_name,
            rolling_cfg=rolling_cfg,
        )
    else:
        print("\nSolving multi-period investment optimisation...")
        print("(This may take several minutes for a 20-year horizon)\n")

        status = network.optimize(
            solver_name=solver_name,
            multi_investment_periods=True,
            log_to_console=False,
            include_objective_constant=False,
        )

        status_str = status[0] if isinstance(status, tuple) else str(status)
        condition = status[1] if isinstance(status, tuple) and len(status) > 1 else ""

    elapsed = time.time() - t0
    print(f"\nOptimisation status: {status_str} ({condition})")
    print(f"Elapsed time: {elapsed:.1f}s")

    if status_str != "ok":
        print(f"WARNING: Optimisation did not converge cleanly (status={status_str}). Results may be invalid.")

    # Print summary
    if rolling_cfg.get("enabled", False):
        # `network.objective` after rolling-horizon = last window only.
        # The meaningful figures come from n.statistics() via calculate_system_lcoe.
        print(f"\nObjective value (last rolling-horizon window): USD {network.objective:,.0f}")
        print("    note: stage-2 rolling horizon overwrites n.objective per window.")
        print("    Use the System LCOE / statistics.csv for total system cost.")
    else:
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
    output_dir = os.path.join(config.OUTPUT_DIR, "single_year_2025")
    os.makedirs(output_dir, exist_ok=True)
    add_loads_to_network(network, output_dir=output_dir, scenario_name="single_year_2025")

    print("Solving...")
    status = network.optimize(solver_name=solver_name, log_to_console=False)
    status_str = status[0] if isinstance(status, tuple) else str(status)
    print(f"Status: {status_str}")
    print(f"Objective: USD {network.objective:,.0f}")

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
        help=(
            f"Exclusive right boundary of the model horizon (default: {config.MODEL_END_YEAR}). "
            f"The last investment period is end-year minus 1. "
            f"Example: --end-year 2031 covers 2025–2030."
        ),
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
    print(f"Horizon: {args.start_year}–{args.end_year - 1}, Solver: {args.solver}")

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
