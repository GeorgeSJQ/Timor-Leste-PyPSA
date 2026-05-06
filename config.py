"""
Simulation Configuration File
All user-configurable parameters for the Timor-Leste PyPSA capacity expansion model.
All costs are in USD.
"""

from pypsa.common import annuity

# ============================================================================
# MODEL HORIZON
# ============================================================================

MODEL_START_YEAR = 2025
MODEL_END_YEAR = 2046   # exclusive right boundary — last investment period is MODEL_END_YEAR - 1
INVESTMENT_PERIODS = list(range(2025, 2046))   # 2025 through 2045 inclusive
FREQ = "1h"

# ============================================================================
# SIMULATION PARAMETERS (single-year / legacy)
# ============================================================================

SIMULATION_START_YEAR = 2025
SIMULATION_END_YEAR = 2025

HOURS_PER_YEAR = 8760
RESOLUTION = 1

SNAPSHOTS_START = "2025-01-01 00:00"
SNAPSHOTS_END = "2025-12-31 23:00"

# ============================================================================
# OPTIMISATION SETTINGS
# ============================================================================

SOLVER_NAME = "highs"
SOLVER_OPTIONS = {
    "threads": 4,
    "method": 2,
    "crossover": 0,
}

# ============================================================================
# ROLLING-HORIZON OPTIMISATION
# ============================================================================
# When enabled, run.py does a two-stage solve:
#   Stage 1 — full-horizon investment solve (single LP) to pick optimal
#             capacities (p_nom_opt) for every extendable asset.
#   Stage 2 — capacities frozen (p_nom_extendable=False, p_nom = p_nom_opt),
#             then PyPSA's optimize_with_rolling_horizon() solves operations
#             window-by-window, carrying SOC / store energy between windows.
#
# This is the only way to get meaningful rolling-horizon results in an
# investment-planning model: a naive call to optimize_with_rolling_horizon()
# with p_nom_extendable=True would let each window pick its own capacity,
# which destroys the investment decision.
#
# `horizon` and `overlap` are in *number of snapshots*, not hours. With
# FREQ="1h" they are equivalent.

ROLLING_HORIZON = {
    "enabled": False,
    "horizon": 168,    # 1 week per dispatch window (168 hourly snapshots)
    "overlap": 24,     # 24 h overlap between windows for SOC continuity
}

# ============================================================================
# ECONOMIC PARAMETERS
# ============================================================================

DISCOUNT_RATE = 0.08  # 8% discount rate
CO2_PRICE = 0.0  # USD/tCO2

# ============================================================================
# CARRIER DEFINITIONS
# ============================================================================

CARRIERS = {
    "AC": {
        "color": "#4169E1",
        "nice_name": "AC Electricity",
        "co2_emissions": 0.0,
    },
    "DC": {
        "color": "#1E90FF",
        "nice_name": "DC Electricity",
        "co2_emissions": 0.0,
    },
    "solar": {
        "color": "#FFD700",
        "nice_name": "Solar PV",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "wind_onshore": {
        "color": "#4682B4",
        "nice_name": "Onshore Wind",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "wind_offshore": {
        "color": "#00CED1",
        "nice_name": "Offshore Wind",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "hydro": {
        "color": "#1E90FF",
        "nice_name": "Hydropower",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 80,
    },
    "battery": {
        "color": "#9370DB",
        "nice_name": "Battery Storage",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 15,
    },
    "pumped_hydro": {
        "color": "#4169E1",
        "nice_name": "Pumped Hydro Storage",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 50,
    },
    "OCGT": {
        "color": "#CD853F",
        "nice_name": "Open Cycle Gas Turbine",
        "co2_emissions": 0.45,
        "fuel": "natural_gas",
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "CCGT": {
        "color": "#D2691E",
        "nice_name": "Combined Cycle Gas Turbine",
        "co2_emissions": 0.45,
        "fuel": "natural_gas",
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "reciprocating_engine": {
        "color": "#A0522D",
        "nice_name": "Reciprocating Engine",
        "co2_emissions": 0.45,
        "fuel": "natural_gas",
        "capital_cost_unit": "USD/MW",
        "lifetime": 20,
    },
    "coal": {
        "color": "#2F4F4F",
        "nice_name": "Coal Generator",
        "co2_emissions": 0.98,
        "fuel": "coal",
        "capital_cost_unit": "USD/MW",
        "lifetime": 40,
    },
    "diesel": {
        "color": "#8B4513",
        "nice_name": "Diesel Generator",
        "co2_emissions": 0.65,  # tCO2/MWh_th
        "fuel": "diesel",
        "capital_cost_unit": "USD/MW",
        "lifetime": 20,
    },
    "oil": {
        "color": "#696969",
        "nice_name": "Oil Generator",
        "co2_emissions": 0.65,
        "fuel": "oil",
        "capital_cost_unit": "USD/MW",
        "lifetime": 30,
    },
    "natural_gas": {
        "color": "#FFA500",
        "nice_name": "Natural Gas",
        "co2_emissions": 0.0,
    },
    "hydrogen": {
        "color": "#FF1493",
        "nice_name": "Hydrogen",
        "co2_emissions": 0.0,
    },
}

# ============================================================================
# CARRIER GROUPINGS
# ============================================================================

RENEWABLE_CARRIERS = ["solar", "wind_onshore", "wind_offshore"]
THERMAL_CARRIERS = ["diesel", "OCGT", "CCGT"]

# ============================================================================
# TECHNOLOGY COST DATA (USD)
# ============================================================================

# Build costs (USD/MW for generators, USD/MVA for lines/transformers)
# These are 2025 base costs for Timor-Leste, reflecting island import premiums.
BUILD_COSTS = {
    "solar": 1_200_000,        # USD/MW
    "wind_onshore": 2_200_000,  # USD/MW
    "wind_offshore": 3_500_000,  # USD/MW
    "battery": 500_000,         # USD/MW (power capacity)
    "battery_energy": 400_000,  # USD/MWh (energy capacity)
    "OCGT": 900_000,            # USD/MW
    "CCGT": 1_600_000,          # USD/MW
    "reciprocating_engine": 1_000_000,  # USD/MW
    "coal": 2_000_000,          # USD/MW
    "diesel": 1_000_000,        # USD/MW
    "line": 0,                  # USD/MVA/km
    "transformer": 0,           # USD/MVA
}

# Fixed O&M costs (USD/MW/year)
FIXED_OM_COSTS = {
    "solar": 12_000,
    "wind_onshore": 35_000,
    "wind_offshore": 90_000,
    "battery": 20_000,
    "OCGT": 12_000,
    "CCGT": 15_000,
    "reciprocating_engine": 18_000,
    "coal": 20_000,
    "diesel": 20_000,
}

# Marginal costs (USD/MWh)
# Diesel: ~$0.90/L fuel price × 0.27 L/kWh heat rate ≈ $243/MWh fuel + $10 VOM
MARGINAL_COSTS = {
    "solar": 0.5,
    "wind_onshore": 0.5,
    "wind_offshore": 0.7,
    "battery": 0.5,
    "OCGT": 180.0,
    "CCGT": 100.0,
    "reciprocating_engine": 200.0,
    "coal": 120.0,
    "diesel": 250.0,
}

# ============================================================================
# TECHNICAL PARAMETERS
# ============================================================================

TECHNICAL_PARAMS = {
    "solar": {
        "efficiency": 1.0,
        "lifetime": 25,
    },
    "wind_onshore": {
        "efficiency": 1.0,
        "lifetime": 25,
    },
    "wind_offshore": {
        "efficiency": 1.0,
        "lifetime": 25,
    },
    "battery": {
        "lifetime": 15,
        "efficiency_charge": 0.95,
        "efficiency_discharge": 0.95,
        "max_hours": 4.0,
        "standing_loss": 0.0001,
    },
    "OCGT": {
        "lifetime": 25,
        "efficiency": 0.39,
        "ramp_limit_up": 0.5,
        "ramp_limit_down": 0.5,
        "min_up_time": 1,
        "min_down_time": 1,
        "p_min_pu": 0.0,
    },
    "CCGT": {
        "lifetime": 25,
        "efficiency": 0.58,
        "ramp_limit_up": 0.2,
        "ramp_limit_down": 0.2,
        "min_up_time": 4,
        "min_down_time": 4,
        "p_min_pu": 0.4,
    },
    "reciprocating_engine": {
        "lifetime": 20,
        "efficiency": 0.42,
        "ramp_limit_up": 1.0,
        "ramp_limit_down": 1.0,
        "min_up_time": 0,
        "min_down_time": 0,
        "p_min_pu": 0.3,
    },
    "coal": {
        "lifetime": 40,
        "efficiency": 0.37,
        "ramp_limit_up": 0.05,
        "ramp_limit_down": 0.05,
        "min_up_time": 8,
        "min_down_time": 8,
        "p_min_pu": 0.4,
    },
    "diesel": {
        "lifetime": 20,
        "efficiency": 0.40,
        "ramp_limit_up": 1.0,
        "ramp_limit_down": 1.0,
        "min_up_time": 0,
        "min_down_time": 0,
        "p_min_pu": 0.2,
    },
}

# Capital costs (USD/MW) — annualised build cost + FOM. Used for single-year optimisation.
CAPITAL_COSTS = {
    "solar": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["solar"]["lifetime"]) * BUILD_COSTS["solar"] + FIXED_OM_COSTS["solar"],
    "wind_onshore": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["wind_onshore"]["lifetime"]) * BUILD_COSTS["wind_onshore"] + FIXED_OM_COSTS["wind_onshore"],
    "wind_offshore": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["wind_offshore"]["lifetime"]) * BUILD_COSTS["wind_offshore"] + FIXED_OM_COSTS["wind_offshore"],
    "battery": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["battery"]["lifetime"]) * BUILD_COSTS["battery"] + FIXED_OM_COSTS["battery"],
    "battery_energy": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["battery"]["lifetime"]) * BUILD_COSTS["battery_energy"] + FIXED_OM_COSTS["battery"],
    "OCGT": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["OCGT"]["lifetime"]) * BUILD_COSTS["OCGT"] + FIXED_OM_COSTS["OCGT"],
    "CCGT": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["CCGT"]["lifetime"]) * BUILD_COSTS["CCGT"] + FIXED_OM_COSTS["CCGT"],
    "reciprocating_engine": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["reciprocating_engine"]["lifetime"]) * BUILD_COSTS["reciprocating_engine"] + FIXED_OM_COSTS["reciprocating_engine"],
    "coal": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["coal"]["lifetime"]) * BUILD_COSTS["coal"] + FIXED_OM_COSTS["coal"],
    "diesel": annuity(DISCOUNT_RATE, TECHNICAL_PARAMS["diesel"]["lifetime"]) * BUILD_COSTS["diesel"] + FIXED_OM_COSTS["diesel"],
    "line": 0,
    "transformer": 0,
}

# ============================================================================
# MULTI-YEAR COST PROJECTION SETS
# ============================================================================
# Each set is a dict of technology → {milestone_year: cost_multiplier}.
# Multipliers are relative to 2025 base BUILD_COSTS.
# Intermediate years are linearly interpolated by get_annualized_capex().
#
# To use a set, set "cost_projection" in a SCENARIOS entry to the set name,
# e.g. "cost_projection": "optimistic".
#
# Set         RE cost decline assumption
# ---------   ---------------------------------------------------
# default     Moderate decline — broadly aligned with IEA WEO stated policies
# optimistic  Aggressive decline — aligned with IEA WEO net-zero / IRENA targets
# conservative Slow decline — assumes supply-chain constraints persist

COST_PROJECTION_SETS = {
    "default": {
        "solar":         {2025: 1.00, 2030: 0.85, 2035: 0.75, 2040: 0.68, 2045: 0.62},
        "wind_onshore":  {2025: 1.00, 2030: 0.92, 2035: 0.87, 2040: 0.83, 2045: 0.80},
        "battery":       {2025: 1.00, 2030: 0.70, 2035: 0.55, 2040: 0.45, 2045: 0.40},
        "battery_energy":{2025: 1.00, 2030: 0.70, 2035: 0.55, 2040: 0.45, 2045: 0.40},
        "diesel":        {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
        "OCGT":          {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
    },
    "optimistic": {
        "solar":         {2025: 1.00, 2030: 0.78, 2035: 0.65, 2040: 0.56, 2045: 0.50},
        "wind_onshore":  {2025: 1.00, 2030: 0.88, 2035: 0.80, 2040: 0.74, 2045: 0.70},
        "battery":       {2025: 1.00, 2030: 0.60, 2035: 0.42, 2040: 0.32, 2045: 0.25},
        "battery_energy":{2025: 1.00, 2030: 0.60, 2035: 0.42, 2040: 0.32, 2045: 0.25},
        "diesel":        {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
        "OCGT":          {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
    },
    "conservative": {
        "solar":         {2025: 1.00, 2030: 0.93, 2035: 0.88, 2040: 0.84, 2045: 0.81},
        "wind_onshore":  {2025: 1.00, 2030: 0.97, 2035: 0.94, 2040: 0.92, 2045: 0.90},
        "battery":       {2025: 1.00, 2030: 0.82, 2035: 0.70, 2040: 0.62, 2045: 0.57},
        "battery_energy":{2025: 1.00, 2030: 0.82, 2035: 0.70, 2040: 0.62, 2045: 0.57},
        "diesel":        {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
        "OCGT":          {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
    },
}

# Convenience alias — used by single-year mode and any code that doesn't go through scenarios.
COST_PROJECTION_FACTORS = COST_PROJECTION_SETS["default"]

# ============================================================================
# SCENARIO DEFINITIONS
# ============================================================================

# Fuel price trajectories
# ------------------------
# Per-scenario fuel price modifiers: {carrier: [{"start": "YYYY-MM-DD",
# "end": "YYYY-MM-DD", "multiplier": float}, ...]}.
# Each modifier multiplies the carrier's MARGINAL_COSTS base price across the
# inclusive date range. Multiple modifiers compound (overlaps stack).
# Omit the key (or set to None) to keep the static base price.

SCENARIOS = {
    "base": {
        "description": "Base case — current diesel + RE investment allowed",
        "fuel_price_trajectories": None,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
    "high_diesel": {
        "description": "Diesel price doubles from 2030, holds 2x through 2045",
        "fuel_price_trajectories": {
            "diesel": [
                {"start": "2030-01-01", "end": "2045-12-31", "multiplier": 2.0},
            ],
        },
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
    "solar_only": {
        "description": "Only solar + battery investment allowed (no new wind)",
        "fuel_price_trajectories": None,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "battery", "diesel"],
        "cost_projection": "default",
    },
    "high_growth": {
        "description": "5% annual demand growth",
        "fuel_price_trajectories": None,
        "demand_growth_rate": 0.05,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
    "wind_solar_battery": {
        "description": "Full RE portfolio — solar, wind, and battery",
        "fuel_price_trajectories": None,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
}

# ============================================================================
# VRE TRACE SOURCE
# ============================================================================
# VRE_TRACE_SOURCE selects how solar/wind capacity-factor traces are built:
#   "renewables_ninja" — load pre-downloaded hourly CSVs from data/ and tile
#                        them across the model horizon (existing behaviour).
#   "atlite"           — download an ERA5 cutout via the CDS API for the
#                        Timor-Leste bbox and compute per-bus solar PV and
#                        wind capacity factors for each substation/power-plant
#                        coordinate.
#
# atlite mode requires:
#   1. `pip install atlite cdsapi` (already in this env).
#   2. A CDS API key at ~/.cdsapirc — see https://cds.climate.copernicus.eu/api-how-to.

VRE_TRACE_SOURCE = "renewables_ninja"

ATLITE_CONFIG = {
    # On-disk cache for ERA5 cutouts. Cutout filenames are derived from the
    # weather year range — re-runs reuse a cached file if present.
    "cutout_dir": r"data\cutouts",
    "cutout_name_template": "timor_leste_{year_start}_{year_end}.nc",

    # Bounding box covering Timor-Leste with a small buffer for spatial
    # interpolation at coastal substations.
    "bbox": {"x_min": 124.0, "x_max": 127.5, "y_min": -9.6, "y_max": -8.1},

    # Module that supplies weather data for the cutout.
    "module": "era5",

    # Format for the temporary ERA5 files atlite downloads. "netcdf" avoids
    # the ecCodes C library dependency (which is non-trivial on Windows).
    # Use "grib" only if you have eccodes properly installed.
    "data_format": "netcdf",

    # CDS-API tuning. Recent CDS server limits reject large single-request
    # downloads even for small bboxes. monthly_requests splits each year into
    # 12 monthly requests, which usually stays under the cost limit.
    "monthly_requests": True,
    "concurrent_requests": False,
    "show_progress": True,

    # Weather years to pull. If the model horizon exceeds `weather_max_years`,
    # the cutout is repeated from `weather_start_year` again (wrap-around).
    "weather_start_year": 2010,
    "weather_max_years": 15,

    # Tech specs — None ⇒ use atlite's defaults.
    "solar_panel": "CSi",
    "solar_orientation": {"slope": 30.0, "azimuth": 180.0},
    "wind_turbine": "Vestas_V112_3MW",
}

# ============================================================================
# LOAD PROFILE CONFIGURATION
# ============================================================================
# LOAD_MODE selects how per-bus hourly load is built:
#   "csv"    — read data/timor_leste_hourly_load_2025.csv, tile across years
#              with compound demand growth (existing behaviour).
#   "random" — synthesise a typical daily shape with morning + evening peaks,
#              add Gaussian noise, apply seasonal factors, and scale per bus
#              by load_distribution. Same daily profile is reused every day.
#              Demand growth is NOT applied in this mode.

LOAD_MODE = "csv"

# Settings used only when LOAD_MODE == "random".
# system-level peak/min are scaled per bus by the load_distribution shares
# in timor_leste_config.add_loads_to_network / build_multiperiod_network.
LOAD_RANDOM_CONFIG = {
    "peak_mw": 110.0,                  # system-wide peak (MW) before scaling per bus
    "min_mw": 35.0,                    # system-wide overnight min (MW)
    "seed": 42,                        # integer seed for np.random.SeedSequence

    # Daily shape: two cosine bumps over a min-MW baseline.
    # Window is inclusive on both ends, hours of day (0–23).
    "morning_peak_window": (6, 9),     # 06:00–09:00
    "evening_peak_window": (17, 21),   # 17:00–21:00
    "morning_peak_fraction": 0.7,      # fraction of (peak − min) reached at morning peak
    "evening_peak_fraction": 1.0,      # 1.0 = full peak in evening

    # Buses listed here use 24 fully random hourly values (uniform between
    # min_mw and peak_mw) instead of the typical-shape template, then go
    # through the same seasonal/noise/scaling pipeline as the others.
    "fully_random_buses": [],

    # Seasonal multiplier applied to every timestep based on its month.
    # Default uses meteorological seasons (DJF/MAM/JJA/SON).
    "seasonal_factors": {
        "DJF": 1.05,   # Dec–Feb (Timor-Leste wet season)
        "MAM": 1.00,   # Mar–May
        "JJA": 0.92,   # Jun–Aug (dry season, cooler)
        "SON": 0.98,   # Sep–Nov
    },

    # Gaussian noise std as a fraction of peak_mw, added per timestep.
    "noise_std": 0.05,
}

# ============================================================================
# TRANSMISSION PARAMETERS
# ============================================================================

LINE_TYPES = {
    "132kV": {
        "r_per_km": 0.1,
        "x_per_km": 0.3,
        "s_nom": 200,
        "v_nom": 132,
    },
    "150kV": {
        "r_per_km": 0.08,
        "x_per_km": 0.28,
        "s_nom": 250,
        "v_nom": 150,
    },
    "220kV": {
        "r_per_km": 0.05,
        "x_per_km": 0.25,
        "s_nom": 400,
        "v_nom": 220,
    },
    "400kV": {
        "r_per_km": 0.03,
        "x_per_km": 0.2,
        "s_nom": 1000,
        "v_nom": 400,
    },
}

TRANSFORMER_TYPES = {
    "132/20kV": {
        "s_nom": 50,
        "v_nom_0": 132,
        "v_nom_1": 20,
        "x": 0.1,
        "r": 0.01,
    },
    "220/132kV": {
        "s_nom": 200,
        "v_nom_0": 220,
        "v_nom_1": 132,
        "x": 0.12,
        "r": 0.01,
    },
}

# ============================================================================
# CONSTRAINTS AND LIMITS
# ============================================================================

RENEWABLE_TARGET = {
    2025: 0.30,
    2030: 0.50,
    2040: 0.70,
    2050: 1.00,
}

MAX_CAPACITY = {
    "solar": None,
    "wind_onshore": None,
    "wind_offshore": None,
    "battery": None,
    "OCGT": 500,
    "CCGT": None,
    "coal": 0,
}

RESERVE_MARGIN = 0.15
SPINNING_RESERVE = 0.03

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================

OUTPUT_DIR = "results"
SAVE_NETWORK = True
SAVE_RESULTS_CSV = True
SAVE_PLOTS = True

PLOT_SETTINGS = {
    "figsize": (12, 8),
    "dpi": 300,
    "style": "seaborn-v0_8-darkgrid",
}
