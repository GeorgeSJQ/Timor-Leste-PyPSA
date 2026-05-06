# Timor-Leste PyPSA Energy System Model

A multi-period capacity expansion model for Timor-Leste's electricity system, built with [PyPSA](https://pypsa.org/).

The model optimises least-cost investment in solar PV, onshore wind, and battery storage alongside the existing diesel fleet, across a national 150 kV transmission network, from 2025 to 2045.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running the Model](#running-the-model)
3. [Project Structure](#project-structure)
4. [Scenarios](#scenarios)
5. [Fuel price trajectories](#fuel-price-trajectories)
6. [Load profiles](#load-profiles)
7. [VRE traces (Renewables Ninja or atlite)](#vre-traces-renewables-ninja-or-atlite)
8. [Rolling-horizon optimisation](#rolling-horizon-optimisation)
9. [Technology Costs](#technology-costs)
10. [Cost Projections](#cost-projections)
11. [Model Horizon and Frequency](#model-horizon-and-frequency)
12. [Outputs](#outputs)
13. [Data Sources](#data-sources)
14. [Technical Notes](#technical-notes)

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
5. Multi-year time series are built for demand (compound growth) and solar/wind capacity factors (tiled from Renewables Ninja).
6. Extendable solar, wind, and battery assets are added at candidate buses, with year-specific annualised capital costs from the scenario's cost projection set.
7. Per-carrier fuel price trajectories from the scenario are attached as time-varying marginal costs; allowed-generator filtering is applied.
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
| `fuel_price_trajectories` | `dict[str, list[dict]]` or `None` | Per-carrier date-range price modifiers — see [Fuel price trajectories](#fuel-price-trajectories). |
| `demand_growth_rate` | `float` | Compound annual growth rate for electricity demand (e.g. `0.03` = 3% p.a.) |
| `allowed_generators` | `list[str]` | Carriers eligible for new investment. Existing diesel plants are always retained regardless of this list. |
| `cost_projection` | `str` | Name of the cost projection set to use from `COST_PROJECTION_SETS` — see [Cost Projections](#cost-projections). |

### Built-in scenarios

| Name | Description |
|---|---|
| `base` | Moderate demand growth (3% p.a.), stable diesel price, full RE investment allowed |
| `high_diesel` | Diesel price doubles from 2030-01-01 onwards (uses `fuel_price_trajectories`) |
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
        "fuel_price_trajectories": None,
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

### Restricting where new builds can be placed

By default, every model run adds one extendable cohort of solar at Dili, wind at Lospalos, and battery at Dili — matching the original network topology. To allow new builds at additional buses (or restrict them to a different single bus), edit `NEW_BUILD_BUSES` in `config.py`:

```python
NEW_BUILD_BUSES = {
    "solar":        ["Dili", "Baucau", "Suai"],     # 3 candidate sites
    "wind_onshore": ["Lospalos", "Viqueque"],       # 2 candidate sites
    "battery":      ["Dili", "Baucau"],             # battery placement is independent
}
```

For each `(technology, bus, valid_build_year)` triple the model adds one extendable cohort named `Solar_<bus>_<year>` / `Wind_<bus>_<year>` / `Battery_<bus>_<year>`. Each cohort uses the bus's own VRE trace (atlite per-bus capacity factor; see [VRE traces](#vre-traces-renewables-ninja-or-atlite)) or, in `renewables_ninja` mode, the default CSV unless a per-bus CSV is configured (see below).

Buses must exist in `timor_leste_config.SUBSTATIONS` or `POWER_PLANTS` (currently 9 substations + Betano + Hera = 11 buses).

#### Per-bus capacity caps

Set a maximum installed capacity per cohort per bus (MW):

```python
MAX_BUS_CAPACITY = {
    "solar":        {"Baucau": 50.0, "Suai": 30.0},   # MW per cohort
    "wind_onshore": {"Lospalos": 150.0},
    "battery":      {},
}
```

A bus absent from this dict is unbounded. The cap applies **per cohort** (per build year) — if multiple build years are valid for a tech and you want a total cap across cohorts, either restrict the build years or accept the per-cohort interpretation.

#### Per-bus Renewables Ninja CSVs

When `VRE_TRACE_SOURCE = "renewables_ninja"` and you have multiple solar/wind buses, you can supply a different CSV per bus:

```python
RENEWABLES_NINJA_CSV_PATHS = {
    "solar": {
        "Dili":   r"data\solar_pv_output_re_ninja_dili.csv",
        "Baucau": r"data\solar_pv_output_re_ninja_baucau.csv",
    },
    "wind_onshore": {
        "Lospalos": r"data\wind_output_re_ninja_lospalos.csv",
    },
}
```

Buses absent from this dict fall back to the default `data/solar_pv_output_re_ninja.csv` / `data/wind_output_re_ninja.csv`. Has no effect in `atlite` mode, which always uses the per-bus traces from the cutout.

#### Per-scenario overrides

Any scenario can override these globals by setting `new_build_buses`, `max_bus_capacity`, or `renewables_ninja_csv_paths`. The scenario-level dict completely replaces the corresponding global dict for that scenario only — it is not deep-merged.

```python
SCENARIOS["solar_north_only"] = {
    "description":          "Solar built only at Liquica, Dili, Baucau",
    "fuel_price_trajectories": None,
    "demand_growth_rate":   0.03,
    "allowed_generators":   ["solar", "battery", "diesel"],
    "cost_projection":      "default",
    "new_build_buses": {
        "solar":        ["Liquica", "Dili", "Baucau"],
        "wind_onshore": [],          # no new wind even though it's in allowed_generators
        "battery":      ["Dili"],
    },
    "max_bus_capacity": {
        "solar": {"Liquica": 80.0, "Baucau": 60.0},
    },
}
```

A technology may appear in `allowed_generators` but be absent from `new_build_buses` (or have an empty bus list); in that case no new cohorts of that tech are built. Conversely, listing a bus in `new_build_buses` but excluding the tech from `allowed_generators` builds nothing — `allowed_generators` is the gate.

---

## Fuel price trajectories

`fuel_price_trajectories` lets a scenario apply time-varying fuel prices to any generator carrier. It is the single mechanism for diesel price ramps, gas price shocks, multi-stage price step-ups, etc.

### Shape

```python
"fuel_price_trajectories": {
    "<carrier>": [
        {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "multiplier": <float>},
        ...
    ],
    ...
}
```

- The carrier key (e.g. `"diesel"`, `"OCGT"`) must exist in `MARGINAL_COSTS` in `config.py`. The base price comes from `MARGINAL_COSTS[<carrier>]`.
- Each modifier multiplies the base price across its inclusive `start`–`end` date range (whole-day precision: `end` extends through 23:59:59 of that day).
- Date ranges can be at any resolution down to a single day.
- Multiple modifiers **compound multiplicatively** — overlapping ranges stack. For example, a 2.0× modifier overlapping a 1.5× modifier produces a 3.0× price in the overlap window.
- Set the scenario key to `None` (or omit it) for a flat base price across the whole horizon.
- The resulting price series is attached to every generator with the matching carrier (existing **and** new investment cohorts).

### Examples

**One-shot doubling from 2030 onwards:**

```python
"high_diesel": {
    ...
    "fuel_price_trajectories": {
        "diesel": [
            {"start": "2030-01-01", "end": "2045-12-31", "multiplier": 2.0},
        ],
    },
}
```

**Multi-stage step-up (different multiplier each window):**

```python
"diesel": [
    {"start": "2027-01-01", "end": "2029-12-31", "multiplier": 1.3},
    {"start": "2030-01-01", "end": "2034-12-31", "multiplier": 1.7},
    {"start": "2035-01-01", "end": "2045-12-31", "multiplier": 2.5},
]
```

**Short price spike layered on a long-run trend (overlapping → compounding):**

```python
"diesel": [
    {"start": "2030-01-01", "end": "2045-12-31", "multiplier": 1.5},   # long trend
    {"start": "2032-06-01", "end": "2032-09-30", "multiplier": 2.0},   # spike
]
# In Jun–Sep 2032 the effective multiplier is 1.5 × 2.0 = 3.0.
```

**Multiple carriers in one scenario:**

```python
"fuel_price_trajectories": {
    "diesel": [{"start": "2030-01-01", "end": "2045-12-31", "multiplier": 2.0}],
    "OCGT":   [{"start": "2028-01-01", "end": "2045-12-31", "multiplier": 1.4}],
}
```

The function lives in `src/scenarios.py` as `build_fuel_price_trajectory()` and is called from `model_builder.apply_fuel_price_trajectories()` after all generators are added.

### Exported run record

Whenever a scenario produces one or more custom marginal cost series, both the values and a chart are written to the scenario's output directory:

```text
results/<scenario>/inputs/
├── fuel_price_trajectories.csv    # one column per carrier, indexed by snapshot
└── fuel_price_trajectories.png    # all carriers plotted on a single matplotlib axis
```

This export is automatic — no extra flags. Scenarios with `fuel_price_trajectories: None` produce no `inputs/` directory. The CSV preserves the network's snapshot index (period + timestep for multi-period runs) so the file is directly importable into pandas:

```python
import pandas as pd
prices = pd.read_csv("results/high_diesel/inputs/fuel_price_trajectories.csv",
                     index_col=["period", "timestep"], parse_dates=["timestep"])
```

---

## Load profiles

The model supports two ways of building per-bus hourly load. The choice is set by `LOAD_MODE` in `config.py` and is applied to every scenario in the run.

### CSV mode (default)

```python
LOAD_MODE = "csv"
```

This is the original behaviour: the model reads `data/timor_leste_hourly_load_2025.csv`, tiles the 8760-row hourly profile across every model year, applies the scenario's `demand_growth_rate` as compound annual growth, and scales the result for each bus by its population share.

### Random mode

```python
LOAD_MODE = "random"
```

Synthesises a typical-shape daily profile in code: a morning peak, an evening peak, a flat overnight baseline, plus seasonal scaling and Gaussian noise. The same daily profile is reused every day — there is no compound demand growth and `demand_growth_rate` is ignored.

All settings live in `config.LOAD_RANDOM_CONFIG`:

```python
LOAD_RANDOM_CONFIG = {
    "peak_mw": 110.0,                  # system-wide peak before per-bus scaling
    "min_mw": 35.0,                    # system-wide overnight baseline
    "seed": 42,                        # int seed for np.random.SeedSequence
    "morning_peak_window": (6, 9),     # 06:00–09:00 inclusive, sin² ramp up/down
    "evening_peak_window": (17, 21),
    "morning_peak_fraction": 0.7,      # peak height as fraction of (peak − min)
    "evening_peak_fraction": 1.0,
    "fully_random_buses": [],          # buses that bypass the typical shape
    "seasonal_factors": {
        "DJF": 1.05, "MAM": 1.00, "JJA": 0.92, "SON": 0.98,
    },
    "noise_std": 0.05,                 # gaussian noise std as fraction of peak_mw
}
```

#### How a bus's profile is built

1. **Daily template** — by default each bus uses the same 24-hour shape: flat at `min_mw` overnight, ramping up through `morning_peak_window` to `min + morning_peak_fraction × (peak − min)`, back to `min_mw` mid-morning, then ramping up through `evening_peak_window` to `min + evening_peak_fraction × (peak − min)`. Both bumps use a sin² envelope so the ramp is smooth.
2. **Tiling** — the 24-hour template is reused every day across the full snapshot horizon.
3. **Seasonal multiplier** — every timestep is multiplied by the factor for its meteorological season (DJF, MAM, JJA, SON). Edit the `seasonal_factors` dict to use different boundaries or magnitudes.
4. **Gaussian noise** — added per timestep with std `noise_std × peak_mw`.
5. **Per-bus scaling** — the resulting series is multiplied by the bus's share in `load_distribution`.
6. **Clipping** — values are clipped below at zero.

Reproducibility comes from a single `seed` integer. The function uses `np.random.SeedSequence(seed).spawn(n_buses)` so each bus has its own deterministic sub-RNG, which means adding or removing a bus does **not** change the random draws for unrelated buses.

#### Fully random buses

To stress-test against atypical load shapes at specific buses, list them in `fully_random_buses`:

```python
LOAD_RANDOM_CONFIG["fully_random_buses"] = ["Suai", "Maliana"]
```

Listed buses replace the typical-shape template with 24 random hourly values uniformly drawn from `[min_mw, peak_mw]`, then go through the same seasonal/noise/scaling pipeline as the others. The bottom subplot of the exported `load_profiles.png` (see below) makes this visible — typical-shape buses peak at hours 7–8 and 19; fully random buses appear flat with no distinct peaks.

### Exported run record

Every run — in either CSV or random mode — writes the per-bus load profiles attached to the network to the scenario output directory:

```text
results/<scenario>/inputs/
├── load_profiles.csv             # one column per bus, indexed by snapshot
├── load_profiles.png             # overview: first week + mean daily shape
└── load_profiles/
    ├── Dili.png                  # full-horizon timeseries for each bus,
    ├── Baucau.png                # with peak / mean / min stats annotated
    ├── Liquica.png
    └── ... (one PNG per bus)
```

The CSV is directly importable into pandas:

```python
import pandas as pd
loads = pd.read_csv("results/base/inputs/load_profiles.csv",
                    index_col=["period", "timestep"], parse_dates=["timestep"])
```

This export is automatic in both `LOAD_MODE` settings — there are no flags to toggle it. The per-bus PNGs are useful for spotting outliers, year-on-year demand growth (CSV mode), or stress-test patterns from `fully_random_buses` (random mode).

The function lives in `src/scenarios.py` as `build_random_load_profiles()` (random mode only) and `export_load_profiles()` (used by both modes). It is called from `model_builder.build_multiperiod_network()` (multi-period) and `timor_leste_config.add_loads_to_network()` (single-year).

---

## VRE traces (Renewables Ninja or atlite)

Solar PV and onshore-wind capacity factors can be sourced two ways. The choice is set by `VRE_TRACE_SOURCE` in `config.py` and applies to every scenario in the run.

### Renewables Ninja CSV (default)

```python
VRE_TRACE_SOURCE = "renewables_ninja"
```

Reads `data/solar_pv_output_re_ninja.csv` and `data/wind_output_re_ninja.csv`, converts UTC → `Asia/Dili`, and tiles the single-year trace across the full multi-year horizon. Solar is attached at Dili, wind at Lospalos. Drop in different CSVs to use other locations.

### atlite + ERA5 reanalysis

```python
VRE_TRACE_SOURCE = "atlite"
```

Downloads an ERA5 cutout via the Copernicus CDS API, then computes hourly capacity factors at every model bus (9 substations + 2 power-plant buses = 11 traces) using atlite's PV and wind models. The Renewables Ninja CSV path is left untouched and remains the fallback.

#### One-time setup

1. Install atlite + cdsapi (already in the project's `.venv` if you've been running the model):
   ```bash
   pip install atlite cdsapi
   ```
2. Register at <https://cds.climate.copernicus.eu/> and accept the ERA5 license.
3. Save your CDS API key to `~/.cdsapirc`:
   ```text
   url: https://cds.climate.copernicus.eu/api
   key: <your-cds-key>
   ```

#### Configuration

All settings live in `config.ATLITE_CONFIG`:

```python
ATLITE_CONFIG = {
    "cutout_dir":           r"data\cutouts",
    "cutout_name_template": "timor_leste_{year_start}_{year_end}.nc",
    "bbox":                 {"x_min": 124.0, "x_max": 127.5,
                             "y_min": -9.6, "y_max": -8.1},
    "module":               "era5",

    # Format for the temporary ERA5 files atlite downloads. "netcdf" avoids
    # the ecCodes C library dependency (non-trivial on Windows).
    # Switch to "grib" only if you have eccodes properly installed.
    "data_format":          "netcdf",

    # CDS server now rejects single large requests. monthly_requests splits
    # each year into 12 sequential requests under the cost limit.
    "monthly_requests":     True,
    "concurrent_requests":  False,
    "show_progress":        True,

    "weather_start_year":   2010,    # earliest weather year to pull
    "weather_max_years":    15,      # cap on the cutout span
    "solar_panel":          "CSi",
    "solar_orientation":    {"slope": 30.0, "azimuth": 180.0},
    "wind_turbine":         "Vestas_V112_3MW",
}
```

#### How the cutout span is decided

The model computes the weather window as `[weather_start_year, weather_start_year + min(horizon, weather_max_years) - 1]`:

| Model horizon | Weather window | Tiling |
|---|---|---|
| 2025–2030 (6 yrs) | 2010–2015 | None — exact length |
| 2025–2045 (21 yrs) | 2010–2024 (capped at 15) | Wraps from 2010 again to fill the remaining 6 years |

The CDS download runs once per unique year range; subsequent runs reuse the cached `.nc` file. Cutouts are typically 50–500 MB depending on the span.

#### What you get

- Per-bus solar and wind capacity-factor series for every model bus.
- Currently `model_builder` still attaches solar at Dili and wind at Lospalos (matching the existing topology) using each bus's own atlite trace. Per-bus generation cohorts can be added by editing the solar/wind loops in `model_builder.build_multiperiod_network()`.

#### Exported run record

```text
results/<scenario>/inputs/
├── vre_solar.csv                  # one column per bus, hourly UTC
├── vre_solar_overview.png         # all 11 buses + mean daily shape
├── vre_solar/<bus>.png            # full-horizon CF timeseries per bus
├── vre_wind.csv
├── vre_wind_overview.png
└── vre_wind/<bus>.png
```

#### Troubleshooting

- **"atlite cutout preparation failed"** — the wrapped exception in the console explains why. Common causes follow.
- **`unrecognized engine 'cfgrib'` / `Cannot find the ecCodes library`** — keep `data_format="netcdf"` in `ATLITE_CONFIG` (the default). ecCodes is a C library that is awkward to install on Windows; the netCDF path bypasses it entirely.
- **`403 Forbidden — cost limits exceeded`** — the CDS server rejected the request as too large. Confirm `monthly_requests=True` is set; if needed, reduce the `bbox` size or the `weather_max_years`.
- **Missing or invalid `~/.cdsapirc`** — register at <https://cds.climate.copernicus.eu/> and accept the ERA5 license; verify the file matches the template above.
- **First-time downloads sit in queue for minutes** — normal CDS behaviour, especially for the first request after a license acceptance. Subsequent runs reuse the cache.
- **Disk space** — clear `data/cutouts/*.nc` to force a redownload, or change `cutout_dir` to a faster volume.

The implementation lives in `src/atlite_traces.py`.

---

## Rolling-horizon optimisation

By default the model is solved as a single perfect-foresight LP across the full horizon. To run dispatch in a rolling-horizon fashion — useful for testing operational policies, modelling limited foresight, or making long horizons tractable — flip the `ROLLING_HORIZON` config:

```python
ROLLING_HORIZON = {
    "enabled":  True,
    "horizon":  168,   # 1 week per dispatch window
    "overlap":  24,    # 24 h overlap for SOC continuity
}
```

`horizon` and `overlap` are **counts of snapshots**, not hours. With `FREQ = "1h"` they are equivalent.

### How it works (two-stage)

PyPSA's `optimize.optimize_with_rolling_horizon()` is intended for operational dispatch. Calling it naively on a network with `p_nom_extendable=True` would let every window pick its own capacity — meaningless for investment planning. The model therefore runs **two stages**:

1. **Stage 1 — full-horizon investment solve.** A single multi-period LP picks optimal capacities (`p_nom_opt`) for every extendable generator, storage unit, store and (if extendable) line.
2. **Capacities are frozen** in place: `p_nom = p_nom_opt`, `p_nom_extendable = False`, etc. for every component.
3. **Stage 2 — rolling-horizon dispatch.** PyPSA's `optimize_with_rolling_horizon()` walks across the full snapshot index in fixed-size windows. Each window solves an independent LP for that subset of snapshots; PyPSA carries `state_of_charge` (storage units) and energy levels (stores) from one window to the next so reservoirs / batteries deplete realistically.

### When to use it

- You want operational decisions taken with limited foresight (e.g. a week ahead) rather than the full 21-year horizon.
- You're stress-testing dispatch sensitivity to short-window storage behaviour or imperfect VRE forecasts (replace VRE traces window-by-window).
- The full-horizon LP is too large for your solver and you want to break dispatch into smaller chunks.

If you only care about least-cost capacity expansion under perfect foresight, leave `ROLLING_HORIZON["enabled"] = False`.

### Caveats

- **`network.objective` after a rolling-horizon run reflects only the last window's cost.** PyPSA's `optimize_with_rolling_horizon()` overwrites the objective per call. The console prints a clear note. For total system cost use the System LCOE or `statistics.csv` (which read from the persisted dispatch results in `network.generators_t.p`, etc., and remain valid across windows).
- Stage 2 takes substantially longer than a single solve — expect roughly `n_windows × seconds_per_window`. A 2-year horizon with `horizon=168, overlap=24` produces ~122 windows.
- If stage 1 fails (`status != "ok"`), stage 2 is skipped — capacities aren't trustworthy yet, so dispatch on top of them would be misleading.

### Tuning windows

| Use-case | `horizon` | `overlap` | Approx. windows over 1 year |
|---|---:|---:|---:|
| Daily dispatch with overnight SOC carry | 24 | 4 | ~440 |
| Weekly dispatch (default) | 168 | 24 | ~61 |
| Monthly dispatch | 730 | 48 | ~13 |

A larger `overlap` smooths SOC transitions at window boundaries but adds redundant work; a smaller one is faster but risks abrupt transitions. Keep `overlap < horizon`.

The two-stage logic lives in `run.py::_run_two_stage_rolling_horizon()`.

---

## Technology Costs

All technology costs are in **USD** and are set in `config.py`. The current assumptions use the Australian technology-cost workbook as the engineering baseline, then apply a `1.15x` uplift to overnight build costs to reflect Timor-Leste import logistics, smaller project scale, and island delivery risk.

### Base build costs (`BUILD_COSTS`)

`BUILD_COSTS` are 2025 overnight costs. Generators are in `USD/MW`, battery energy capacity is in `USD/MWh`, lines are in `USD/MVA/km`, and transformers are in `USD/MVA`.

```python
BUILD_COSTS = {
    "solar":          1_322_500,
    "wind_onshore":   3_507_500,
    "wind_offshore":  4_951_900,
    "hydro":          6_037_500,
    "pumped_hydro":   8_050_000,
    "battery":          603_750,   # power capacity, USD/MW
    "battery_energy":   315_100,   # energy capacity, USD/MWh
    "OCGT":           2_521_950,
    "CCGT":           2_714_000,
    "diesel":         1_600_000,
    "line":               6_000,   # indicative only
    "transformer":       30_000,   # indicative only
    ...
}
```

The model **never uses these raw figures directly** for multi-period investment. Instead, `get_annualized_capex()` in `model_builder.py` applies a year-specific cost projection factor (see [Cost Projections](#cost-projections)), then annualises the result with the annuity formula and adds fixed O&M.

Line and transformer build-cost entries are retained for future transmission expansion analysis, but `CAPITAL_COSTS["line"]` and `CAPITAL_COSTS["transformer"]` are intentionally kept at `0` for now.

### Fixed O&M costs (`FIXED_OM_COSTS`)

Annual fixed operation and maintenance costs per MW of installed capacity:

```python
FIXED_OM_COSTS = {
    "solar":        12_000,
    "wind_onshore": 28_000,
    "battery":      12_800,
    "OCGT":         17_368,
    "CCGT":         15_028,
    "diesel":       29_383,
    ...
}
```

### Marginal costs (`MARGINAL_COSTS`)

Short-run marginal costs are in `USD/MWh_e`. For thermal generators, fuel prices are stored as `USD/GJ` and converted to electrical output with:

```python
fuel_cost_usd_per_mwh = fuel_price_usd_per_gj * (3.6 / efficiency)
marginal_cost = fuel_cost_usd_per_mwh + variable_om_usd_per_mwh
```

The current base thermal marginal costs are approximately:

| Carrier | Base marginal cost |
|---|---:|
| `OCGT` | 184.03 USD/MWh |
| `CCGT` | 117.26 USD/MWh |
| `reciprocating_engine` | 384.76 USD/MWh |
| `coal` | 55.96 USD/MWh |
| `diesel` | 393.23 USD/MWh |

Diesel uses a fuel-price proxy of `USD 1.65/L`, converted to `USD/GJ` using `38.6 GJ/kL`. Per-scenario time-varying price changes are configured via `fuel_price_trajectories` and multiply the base `MARGINAL_COSTS` series; see [Fuel price trajectories](#fuel-price-trajectories).

### Emissions factors (`CARRIERS`)

Carrier `co2_emissions` values are thermal fuel factors in `tCO2-e/MWh_th`, used by PyPSA primary-energy emissions accounting:

```python
NATURAL_GAS_CO2_T_PER_MWH_TH = 0.1855
DIESEL_CO2_T_PER_MWH_TH = 0.2527
FUEL_OIL_CO2_T_PER_MWH_TH = 0.2658
BLACK_COAL_CO2_T_PER_MWH_TH = 0.3249
```

These are converted from Australia National Greenhouse Accounts fuel factors in `kg CO2-e/GJ` using `kg/GJ * 3.6 / 1000`.

### Technical parameters (`TECHNICAL_PARAMS`)

Asset lifetimes, efficiencies, and operational limits:

```python
TECHNICAL_PARAMS = {
    "solar":   {"efficiency": 1.0, "lifetime": 30, "forced_outage_rate": 0.015},
    "battery": {"lifetime": 20, "efficiency_charge": 0.925,
                "efficiency_discharge": 0.925, "max_hours": 4.0, ...},
    "OCGT":    {"lifetime": 25, "efficiency": 0.343, "p_min_pu": 0.5, ...},
    "CCGT":    {"lifetime": 25, "efficiency": 0.509, "p_min_pu": 0.46, ...},
    "diesel":  {"lifetime": 25, "efficiency": 0.40, "p_min_pu": 0.2, ...},
    ...
}
```

`lifetime` determines how many years an asset built in a given investment period remains eligible to generate. When an asset's lifetime expires, PyPSA stops building on it and the model can invest in a new cohort.

Note: some technical parameters such as ramp rate can only be used when the generator has fixed capacity.

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
| `C:/Users/georg/Downloads/technical_parameters.xlsx` | Australian technology-cost and technical-parameter workbook used as the baseline for `BUILD_COSTS`, `FIXED_OM_COSTS`, variable O&M, and `TECHNICAL_PARAMS` |

Additional parameter sources used in `config.py`:

- [Australia National Greenhouse Accounts Factors 2025](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts-factors-2025) for thermal fuel emissions factors.
- [Timor-Leste 2026 temporary fuel price cap](https://timor-leste.gov.tl/?lang=en&n=1&p=48029) (`USD 1.65/L`) as the diesel fuel-price proxy.
- [Timor-Leste Solar and BESS project public information](https://www.miga.org/project/timor-leste-solar-and-bess) for local context on solar-plus-storage development.
- [AEMO Transmission Cost Database](https://www.aemo.com.au/energy-systems/major-publications/integrated-system-plan-isp/2026-integrated-system-plan-isp/2025-26-inputs-assumptions-and-scenarios/transmission-cost-database) as a reference point for indicative line and transformer costs; these are not yet active in `CAPITAL_COSTS`.

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
