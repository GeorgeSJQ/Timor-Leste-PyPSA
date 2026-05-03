# Timor-Leste PyPSA Energy System Model

A PyPSA capacity expansion model for Timor-Leste's electricity system.

The current project builds a national transmission network, adds existing diesel
generation, and optimises new renewable generation and battery storage over a
single year or a multi-year investment horizon.

## Overview

This model studies cost-optimal electricity system expansion for Timor-Leste. It
uses hourly demand, solar, and wind profiles to optimise dispatch and investment
decisions for solar PV, onshore wind, battery storage, and the existing diesel
fleet.

The main workflow is now driven by `run.py`. The older single-year prototype has
been moved to `legacy/optimization_example.py`, while the active codebase has
separate modules for model assembly, scenarios, results export, and Plotly
visualisation.

## Current Capabilities

- Multi-period capacity expansion from 2025 to 2045 by default.
- Fast single-year 2025 optimisation mode for validation and development.
- Scenario runs for base, high diesel price, solar-only, high demand growth, and
  wind/solar/battery cases.
- National 150 kV transmission backbone with substations, power plant buses, and
  approximate line lengths.
- Existing diesel plants at Betano and Hera, with build years and lifetimes for
  multi-period retirement handling.
- Expandable solar PV, onshore wind, and battery storage investment.
- Hourly demand growth across the model horizon with configurable annual growth.
- Tiled hourly renewable traces from Renewables Ninja for solar PV and wind.
- Year-specific technology cost projection factors for multi-period investment.
- CSV and JSON result exports, including overview KPIs, raw PyPSA statistics,
  nodal price summaries, transmission flows, and run metadata.
- Interactive Plotly HTML outputs for dispatch, curtailment, monthly generation,
  generator heatmaps, storage state of charge, nodal prices, and transmission
  utilisation.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- A linear optimisation solver supported by PyPSA. The project defaults to HiGHS.
- Recommended: a virtual environment.

### Installation

Clone the repository and install the Python dependencies:

```bash
git clone https://github.com/GeorgeSJQ/Timor-Leste-PyPSA.git
cd Timor-Leste-PyPSA
pip install pypsa pandas numpy matplotlib plotly highspy netcdf4
```

There is currently no committed `requirements.txt`, so the command above lists
the packages used directly by the project and the default solver/export workflow.

## Running the Model

Run the default multi-period base scenario:

```bash
python run.py
```

Run a specific scenario:

```bash
python run.py --scenario high_diesel
```

Run every scenario defined in `config.SCENARIOS`:

```bash
python run.py --scenario all
```

Run a shorter or longer horizon:

```bash
python run.py --start-year 2025 --end-year 2035
```

Run the fast single-year 2025 validation model:

```bash
python run.py --single-year
```

Use a different solver:

```bash
python run.py --solver highs
```

Skip saving the optimised NetCDF network:

```bash
python run.py --no-save-network
```

## What `run.py` Does

For multi-period scenarios, the model:

1. Loads the selected scenario from `config.SCENARIOS`.
2. Creates hourly PyPSA snapshots for each investment period.
3. Builds the Timor-Leste transmission network and existing diesel plants.
4. Sets investment period and snapshot weightings.
5. Builds multi-year demand, solar, wind, and diesel marginal cost time series.
6. Adds extendable solar, wind, and battery assets with technology lifetimes.
7. Applies scenario constraints such as allowed generators and diesel price
   multipliers.
8. Solves the PyPSA optimisation with `network.optimize(..., multi_invest=True)`.
9. Saves the optimised network, statistics, metadata, and plots under `results/`.

## Project Structure

```text
.
|-- config.py                     # Model settings, costs, scenarios, carriers
|-- model_builder.py              # Multi-period network assembly and helpers
|-- pypsa_setup.py                # Reusable PyPSA component creation helpers
|-- run.py                        # Main CLI entry point
|-- timor_leste_config.py         # Grid topology, substations, plants, loads
|-- data/
|   |-- solar_pv_output_re_ninja.csv
|   |-- timor_leste_hourly_load_2025.csv
|   `-- wind_output_re_ninja.csv
|-- legacy/
|   |-- optimization_example.py   # Earlier single-year prototype
|   `-- playground.ipynb
|-- src/
|   |-- plots.py                  # Plotly visualisation functions
|   |-- results.py                # KPI calculations and result export
|   |-- scenarios.py              # Scenario and time-series utilities
|   `-- __init__.py
`-- results/                      # Generated outputs
```

## Configuration

Most model assumptions live in `config.py`:

- `MODEL_START_YEAR`, `MODEL_END_YEAR`, `INVESTMENT_PERIODS`, and `FREQ`
- `SOLVER_NAME` and `SOLVER_OPTIONS`
- `DISCOUNT_RATE` and `CO2_PRICE`
- `CARRIERS`, `RENEWABLE_CARRIERS`, and `THERMAL_CARRIERS`
- `BUILD_COSTS`, `FIXED_OM_COSTS`, `MARGINAL_COSTS`, and `CAPITAL_COSTS`
- `TECHNICAL_PARAMS`
- `COST_PROJECTION_FACTORS`
- `SCENARIOS`
- `LINE_TYPES` and transmission assumptions
- `OUTPUT_DIR`, `SAVE_NETWORK`, `SAVE_RESULTS_CSV`, `SAVE_PLOTS`

Grid topology and existing assets are defined in `timor_leste_config.py`.

## Scenarios

The current scenario set is defined in `config.SCENARIOS`:

- `base`: current diesel plus renewable and battery investment.
- `high_diesel`: diesel price doubles by 2035.
- `solar_only`: solar and battery investment allowed, with no new wind.
- `high_growth`: 5% annual demand growth.
- `wind_solar_battery`: full renewable portfolio with solar, wind, and battery.

Each scenario can set diesel price factors, demand growth rates, allowed
generator technologies, and cost projection behaviour.

## Outputs

Each scenario writes to `results/<scenario_name>/`.

Typical outputs include:

- `optimized_network.nc`: optimised PyPSA network in NetCDF format.
- `statistics.csv`: raw `n.statistics()` output.
- `overview.csv`: high-level system KPIs.
- `nodal_prices_summary.csv`: nodal price summary statistics by bus and year.
- `transmission_flows.csv`: average and maximum line flows.
- `run_metadata.json`: scenario metadata and headline outputs.
- `plots/*.html`: interactive Plotly charts.

The single-year validation mode writes to `results/single_year_2025/`.

## Data Sources

- Hourly demand: `data/timor_leste_hourly_load_2025.csv`
- Solar PV capacity factors: `data/solar_pv_output_re_ninja.csv`
- Wind capacity factors: `data/wind_output_re_ninja.csv`
- Renewable profiles are from Renewables Ninja.
- Technology costs and projection factors are configured in `config.py`.

## Notes

- Leap days are removed in multi-year profiles so each model year has 8760
  hourly timesteps.
- Current Renewables Ninja input traces are hourly, so the active multi-period
  model does not allow sub-hourly frequencies. Coarser frequencies are supported
  by averaging the hourly renewable traces.
- The current one-year renewable traces are tiled across multi-year horizons.
  This is valid for scenario analysis with a representative weather year, but it
  does not capture inter-annual weather variability unless additional yearly
  traces are added.
- Existing diesel plants are retained even when a scenario restricts new
  investment technologies.
- The repository currently contains generated result files. Re-running scenarios
  can overwrite files under `results/`.
- `technology_costs_2030.csv` is referenced by the older README but is not part
  of the active workflow in the current root project.

## License

TBA

## Acknowledgments

This model is built using [PyPSA](https://pypsa.org/), an open-source power
system analysis framework developed by the PyPSA team. This project is funded by
UNSW via the Collaboration on Energy and Environmental Markets (CEEM).
