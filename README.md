# Timor-Leste PyPSA Energy System Model

A multi-period capacity expansion model for Timor-Leste's electricity system, built with [PyPSA](https://pypsa.org/).

The model optimises least-cost investment in solar PV, onshore wind, and battery storage alongside the existing diesel fleet, across a national 150 kV transmission network, from 2025 to 2045.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running the Model](#running-the-model)
3. [Project Structure](#project-structure)
4. [Scenarios](#scenarios)
5. [Technology Costs](#technology-costs)
6. [Cost Projections](#cost-projections)
7. [Model Horizon and Frequency](#model-horizon-and-frequency)
8. [Outputs](#outputs)
9. [Data Sources](#data-sources)
10. [Technical Notes](#technical-notes)

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A linear programme solver supported by PyPSA — the project defaults to [HiGHS](https://highs.dev/) (open-source, no licence required)
- A virtual environment is recommended

### Installation

```bash
git clone https://github.com/GeorgeSJQ/Timor-Leste-PyPSA.git
cd Timor-Leste-PyPSA
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pypsa pandas numpy matplotlib plotly highspy netcdf4
```

> **Gurobi users:** install `gurobipy` and set `SOLVER_NAME = "gurobi"` in `config.py`.

---

## Running the Model

All runs go through `run.py`. The `--help` flag lists every option:

```bash
python run.py --help
```

### Common commands

| Goal | Command |
|---|---|
| Run the default base scenario (2025–2045) | `python run.py` |
| Run a specific scenario | `python run.py --scenario high_diesel` |
| Run all defined scenarios | `python run.py --scenario all` |
| Run a scenario over a custom horizon | `python run.py --scenario high_diesel --start-year 2025 --end-year 2031` |
| Fast single-year 2025 validation | `python run.py --single-year` |
| Use a different solver | `python run.py --solver gurobi` |
| Skip saving the NetCDF network file | `python run.py --no-save-network` |

**`--scenario`, `--start-year`, and `--end-year` are independent flags** and can always be combined freely. `--scenario all` respects any `--start-year`/`--end-year` values you provide.

#### Model horizon convention

`--end-year` is an **exclusive right boundary**, following Python range convention:

- `--end-year 2031` → investment periods 2025, 2026, 2027, 2028, 2029, 2030 (last full year = 2030)
- `--end-year 2046` (the default) → investment periods 2025 through 2045 (last full year = 2045)

This means `MODEL_END_YEAR = 2046` in `config.py` produces a 2025–2045 run.

### What happens during a run

1. The scenario configuration is loaded from `config.SCENARIOS`.
2. Hourly PyPSA snapshots are created for every investment period year, with leap days removed.
3. The Timor-Leste 150 kV transmission backbone is built, including the existing Betano (136 MW) and Hera (119 MW) diesel generators.
4. Investment period and snapshot weightings are applied for correct multi-year discounting.
5. Multi-year time series are built for demand (compound growth), solar and wind capacity factors (tiled from Renewables Ninja), and diesel marginal costs.
6. Extendable solar, wind, and battery assets are added at candidate buses, with year-specific annualised capital costs from the scenario's cost projection set.
7. Scenario constraints are applied — allowed generator types and diesel price ramps.
8. The PyPSA multi-investment optimisation is solved.
9. Results are exported to `results/<scenario_name>/` — CSVs, JSON metadata, and interactive Plotly HTML charts.

### Typical solve times

| Mode | Approximate time |
|---|---|
| Single-year 2025 | 30 seconds – 2 minutes |
| 5-year horizon (2025–2030) | 2 – 5 minutes |
| Full 21-year horizon (2025–2045) | 10 – 30 minutes |

Times depend on hardware. A higher-performance solver like Gurobi typically solves 3–5× faster than HiGHS for the full horizon.

---

## Project Structure

```text
.
├── config.py                   # All parameters: costs, scenarios, model horizon
├── model_builder.py            # Multi-period network assembly
├── pypsa_setup.py              # Reusable PyPSA component wrappers
├── run.py                      # Main CLI entry point
├── timor_leste_config.py       # Grid topology, substations, existing plants
├── src/
│   ├── results.py              # KPI calculations and result export
│   ├── plots.py                # Plotly visualisation functions
│   ├── scenarios.py            # VRE tiling, demand growth, scenario application
│   └── __init__.py
├── data/
│   ├── solar_pv_output_re_ninja.csv
│   ├── wind_output_re_ninja.csv
│   └── timor_leste_hourly_load_2025.csv
├── legacy/
│   └── optimization_example.py # Archived single-year prototype
└── results/                    # Generated outputs (created on first run)
```

**`config.py` is the main file you edit.** Almost every modelling assumption — costs, scenarios, horizon, solver — lives there.

---

## Scenarios

Scenarios are defined in `config.SCENARIOS` in `config.py`. Each scenario is a dictionary with the following keys:

| Key | Type | Description |
|---|---|---|
| `description` | `str` | Human-readable label printed at runtime |
| `diesel_price_factor` | `float` | Final diesel price multiplier relative to `MARGINAL_COSTS["diesel"]` |
| `diesel_price_ramp_year` | `int` | Year by which the full price factor is reached (linear ramp from start year). Omit if no ramp is needed. |
| `demand_growth_rate` | `float` | Compound annual growth rate for electricity demand (e.g. `0.03` = 3% p.a.) |
| `allowed_generators` | `list[str]` | Carriers eligible for new investment. Existing diesel plants are always retained regardless of this list. |
| `cost_projection` | `str` | Name of the cost projection set to use from `COST_PROJECTION_SETS` — see [Cost Projections](#cost-projections). |

### Built-in scenarios

| Name | Description |
|---|---|
| `base` | Moderate demand growth (3% p.a.), stable diesel price, full RE investment allowed |
| `high_diesel` | Diesel price doubles linearly from 2025 to 2035, then holds flat |
| `solar_only` | New wind investment excluded; only solar and battery allowed |
| `high_growth` | 5% annual demand growth |
| `wind_solar_battery` | Full RE portfolio — identical to `base` by design; modify as needed |

### Adding a new scenario

Open `config.py` and add a new entry to `SCENARIOS`:

```python
SCENARIOS = {
    ...
    "my_scenario": {
        "description": "High growth with fast RE cost decline",
        "diesel_price_factor": 1.0,
        "demand_growth_rate": 0.05,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "optimistic",
    },
}
```

Then run it:

```bash
python run.py --scenario my_scenario
```

### Restricting investment to specific technologies

Set `allowed_generators` to only the carriers you want to allow for **new** investment:

```python
# Solar and battery only — no new wind
"allowed_generators": ["solar", "battery", "diesel"],

# Renewables only — forces aggressive RE build-out
"allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
```

Note: `"diesel"` should remain in this list to keep the existing Betano and Hera plants operational. New extendable diesel generators are not added by the model regardless.

---

## Technology Costs

All technology costs are in **USD** and are set in `config.py`.

### Base capital costs (`BUILD_COSTS`)

These are 2025 overnight capital costs per MW of installed capacity, reflecting island import premiums applicable to Timor-Leste:

```python
BUILD_COSTS = {
    "solar":         1_200_000,   # USD/MW
    "wind_onshore":  2_200_000,   # USD/MW
    "battery":         500_000,   # USD/MW  (power capacity)
    "battery_energy":  400_000,   # USD/MWh (energy capacity)
    ...
}
```

The model **never uses these raw figures directly** for multi-period investment. Instead, `get_annualized_capex()` in `model_builder.py` applies a year-specific cost projection factor (see [Cost Projections](#cost-projections)), then annualises the result with the annuity formula and adds fixed O&M.

### Fixed O&M costs (`FIXED_OM_COSTS`)

Annual fixed operation and maintenance costs per MW of installed capacity:

```python
FIXED_OM_COSTS = {
    "solar":        12_000,   # USD/MW/year
    "wind_onshore": 35_000,   # USD/MW/year
    "battery":      20_000,   # USD/MW/year
    ...
}
```

### Marginal (variable) costs (`MARGINAL_COSTS`)

Short-run marginal costs per MWh of generated electricity. For diesel, this includes fuel at approximately USD 0.90/L:

```python
MARGINAL_COSTS = {
    "solar":        0.5,    # USD/MWh
    "wind_onshore": 0.5,    # USD/MWh
    "battery":      0.5,    # USD/MWh
    "diesel":     250.0,    # USD/MWh (fuel + VOM)
    ...
}
```

To change the diesel fuel price, edit `MARGINAL_COSTS["diesel"]` directly. A per-scenario diesel price ramp is applied on top via `diesel_price_factor` and `diesel_price_ramp_year` in the scenario definition.

### Technical parameters (`TECHNICAL_PARAMS`)

Asset lifetimes, efficiencies, and operational limits:

```python
TECHNICAL_PARAMS = {
    "solar":        {"efficiency": 1.0, "lifetime": 25},
    "wind_onshore": {"efficiency": 1.0, "lifetime": 25},
    "battery":      {"lifetime": 15, "efficiency_charge": 0.95,
                     "efficiency_discharge": 0.95, "max_hours": 4.0, ...},
    "diesel":       {"lifetime": 20, "efficiency": 0.40, ...},
    ...
}
```

`lifetime` determines how many years an asset built in a given investment period remains eligible to generate. When an asset's lifetime expires, PyPSA stops building on it and the model can invest in a new cohort.

### Discount rate

The discount rate used for annualising capital costs and weighting future investment periods:

```python
DISCOUNT_RATE = 0.08   # 8%
```

### Capital costs for single-year mode (`CAPITAL_COSTS`)

Single-year mode (`--single-year`) uses pre-computed annualised capital costs from `CAPITAL_COSTS`. These are calculated at module load time using `BUILD_COSTS` and `TECHNICAL_PARAMS["lifetime"]` for 2025, and do not reflect cost projections.

---

## Cost Projections

Technology costs — particularly for solar PV and batteries — are expected to fall significantly over a 20-year horizon. The model captures this through **cost projection sets**.

### How it works

When building extendable generators, `get_annualized_capex()` in `model_builder.py`:

1. Looks up the 2025 base `BUILD_COSTS` for the technology.
2. Multiplies by a year-specific **projection factor** from the active projection set, interpolating linearly between milestone years.
3. Annualises the result with the annuity formula.
4. Adds the annual fixed O&M cost.

For example, a solar plant built in 2035 under the `"default"` projection uses a factor of `0.75`, meaning 75% of the 2025 base cost.

### Projection sets (`COST_PROJECTION_SETS`)

Three sets are defined in `config.py`:

| Set | RE cost assumption | Basis |
|---|---|---|
| `default` | Moderate decline | Broadly aligned with IEA WEO stated policies |
| `optimistic` | Aggressive decline | Aligned with IEA WEO net-zero / IRENA targets |
| `conservative` | Slow decline | Assumes supply-chain constraints and island import premiums persist |

**Solar PV projection factors (relative to 2025 base cost):**

| Year | `default` | `optimistic` | `conservative` |
|---:|---:|---:|---:|
| 2025 | 1.00 | 1.00 | 1.00 |
| 2030 | 0.85 | 0.78 | 0.93 |
| 2035 | 0.75 | 0.65 | 0.88 |
| 2040 | 0.68 | 0.56 | 0.84 |
| 2045 | 0.62 | 0.50 | 0.81 |

**Battery storage projection factors:**

| Year | `default` | `optimistic` | `conservative` |
|---:|---:|---:|---:|
| 2025 | 1.00 | 1.00 | 1.00 |
| 2030 | 0.70 | 0.60 | 0.82 |
| 2035 | 0.55 | 0.42 | 0.70 |
| 2040 | 0.45 | 0.32 | 0.62 |
| 2045 | 0.40 | 0.25 | 0.57 |

Diesel and OCGT factors are `1.00` across all years (no projected cost decline).

### Assigning a projection set to a scenario

Set `"cost_projection"` in the scenario definition:

```python
"my_scenario": {
    ...
    "cost_projection": "optimistic",   # or "default" or "conservative"
},
```

The set name is printed at the start of each run so it is visible in the console output.

### Adding a custom projection set

Add a new entry to `COST_PROJECTION_SETS` in `config.py`:

```python
COST_PROJECTION_SETS["my_projection"] = {
    "solar":         {2025: 1.00, 2030: 0.80, 2035: 0.68, 2040: 0.60, 2045: 0.55},
    "wind_onshore":  {2025: 1.00, 2030: 0.90, 2035: 0.84, 2040: 0.79, 2045: 0.75},
    "battery":       {2025: 1.00, 2030: 0.65, 2035: 0.48, 2040: 0.38, 2045: 0.32},
    "battery_energy":{2025: 1.00, 2030: 0.65, 2035: 0.48, 2040: 0.38, 2045: 0.32},
    "diesel":        {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
    "OCGT":          {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
}
```

Only milestone years need to be specified — intermediate years are linearly interpolated. Then reference it in a scenario: `"cost_projection": "my_projection"`.

---

## Model Horizon and Frequency

The default horizon is set in `config.py`:

```python
MODEL_START_YEAR = 2025
MODEL_END_YEAR   = 2046   # exclusive — last investment period is 2045
FREQ             = "1h"   # Hourly resolution
```

`MODEL_END_YEAR` is an **exclusive right boundary**: investment periods run from `MODEL_START_YEAR` up to but not including `MODEL_END_YEAR`. The default of `2046` therefore covers 2025–2045 (21 investment periods). The `--start-year` and `--end-year` CLI flags override these values per run without editing `config.py`.

**Leap days** are removed across all multi-year profiles so that every model year has exactly 8760 hourly timesteps. This ensures snapshot weightings sum correctly.

**Coarser frequencies** (e.g. `FREQ = "2h"`) are supported: the hourly Renewables Ninja traces and the demand CSV are averaged to the coarser frequency automatically. Sub-hourly frequencies are not supported.

---

## Outputs

Each scenario writes results to `results/<scenario_name>/`:

```text
results/base/
├── optimized_network.nc        # Full PyPSA network in NetCDF format (reloadable)
├── statistics.csv              # Long-format n.statistics() output (see below)
├── overview.csv                # High-level KPIs: LCOE, RE share, emissions, TOTEX
├── nodal_prices_summary.csv    # Mean/median/p5/p95 marginal price per bus per year
├── transmission_flows.csv      # Average and peak MW flow per line, % utilisation
├── run_metadata.json           # Objective value, LCOE, solve status, component counts
└── plots/
    ├── dispatch.html                    # Stacked area dispatch chart
    ├── dispatch_with_curtailment.html   # Dispatch with curtailed VRE overlay
    ├── monthly_generation.html          # Average monthly generation by carrier
    ├── nodal_prices.html                # Marginal electricity price at each bus
    ├── transmission_utilisation.html    # Peak line loading as % of thermal rating
    ├── heatmap_solar.html               # Day-of-year × hour-of-day solar output
    ├── heatmap_wind_onshore.html        # Day-of-year × hour-of-day wind output
    ├── storage_soc.html                 # Battery state of charge over time
    └── storage_soc_heatmap.html         # Battery SOC heatmap
```

#### `statistics.csv` format

`statistics.csv` is exported in **long (tidy) format** with one observation per row, making it easy to filter, pivot, or import into Excel or a data analysis tool:

| Column | Description | Example values |
|---|---|---|
| `Network_Component` | PyPSA component type | `Generator`, `StorageUnit`, `Line` |
| `Component_Name` | Individual component identifier | `Solar_Dili_2025`, `Betano_Existing` |
| `Category` | Metric name from `n.statistics()` | `Optimal Capacity`, `Capital Expenditure`, `Supply` |
| `Investment_Period` | Investment period year (multi-period runs) or `NA` (single-year) | `2025`, `2030`, `2045` |
| `Value` | Metric value in PyPSA native units | MW, USD, MWh |

To load and pivot in Python:

```python
import pandas as pd
stats = pd.read_csv("results/base/statistics.csv")

# Total optimised capacity by carrier per period
capacity = (
    stats[stats.Category == "Optimal Capacity"]
    .groupby(["Component_Name", "Investment_Period"])["Value"]
    .sum()
    .unstack("Investment_Period")
)
```

The single-year validation mode (`--single-year`) writes to `results/single_year_2025/`.

### Reloading a saved network

```python
import pypsa
n = pypsa.Network()
n.import_from_netcdf("results/base/optimized_network.nc")
```

---

## Data Sources

| File | Contents |
|---|---|
| `data/timor_leste_hourly_load_2025.csv` | 8760-row hourly electricity demand (MW), representative year |
| `data/solar_pv_output_re_ninja.csv` | 8760-row hourly solar PV capacity factors (0–1) from Renewables Ninja |
| `data/wind_output_re_ninja.csv` | 8760-row hourly onshore wind capacity factors (0–1) from Renewables Ninja |

Renewables Ninja CSVs must have columns `Time` (UTC timestamps) and `Output` (capacity factor). The model converts timestamps from UTC to Timor-Leste local time (`Asia/Dili`, UTC+9) before tiling across the multi-year horizon.

The single 2025 renewable trace is tiled across the full 2025–2045 horizon. This is standard practice for scenario analysis with a representative weather year, but does not capture inter-annual weather variability. To use different weather years per investment period, the VRE loading code in `model_builder.py` would need to be extended.

---

## Technical Notes

### Grid topology

The model represents Timor-Leste's 150 kV national transmission backbone as defined in `timor_leste_config.py`:

- **9 substation buses:** Maliana, Liquica, Dili, Manatuto, Baucau, Lospalos, Viqueque, Cassa, Suai
- **2 power plant buses:** Betano, Hera
- **12 transmission lines** forming a coastal loop and cross connections (~553 km total)
- **Existing diesel generators:** Betano (136 MW, commissioned 2015) and Hera (119 MW, commissioned 2011)

Transmission lines are **not extendable** in the current model. The existing 150 kV backbone capacity is treated as fixed infrastructure.

### Load distribution

Hourly system demand is distributed across buses in proportion to population:

| Bus | Share |
|---|---:|
| Dili | 29.0% |
| Liquica | 17.2% |
| Baucau | 10.8% |
| Viqueque | 6.7% |
| Cassa | 6.1% |
| Suai | 6.2% |
| Lospalos | 5.9% |
| Betano | 5.2% |
| Maliana | 8.6% |
| Manatuto | 4.5% |

### Existing plant retirement

The existing diesel generators are modelled with their commissioning years and 20-year lifetimes:

- Hera retires at end of 2031 (commissioned 2011 + 20 years)
- Betano retires at end of 2035 (commissioned 2015 + 20 years)

PyPSA handles retirement automatically when `build_year` and `lifetime` are set. The model can invest in new capacity in the same periods as retirement.

### New investment cohorts

To avoid investment model artefacts from building multiple short-lifetime cohorts, new solar, wind, and battery assets are added only at non-overlapping build years. For example, with a 25-year solar lifetime and a 2025 start, the model can build solar in 2025 and 2050 — but 2050 is beyond the 2045 horizon, so only one solar cohort is available. Battery storage (15-year lifetime) can build in 2025 and 2040.

---

## Acknowledgements

This model is built using [PyPSA](https://pypsa.org/), an open-source power system analysis framework. Renewable energy capacity factor profiles are sourced from [Renewables Ninja](https://www.renewables.ninja/). This project is funded by UNSW via the Collaboration on Energy and Environmental Markets (CEEM).

## License

TBA
