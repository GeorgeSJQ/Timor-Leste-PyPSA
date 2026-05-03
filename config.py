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
MODEL_END_YEAR = 2045
INVESTMENT_PERIODS = list(range(2025, 2046))
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
# MULTI-YEAR COST PROJECTION FACTORS
# ============================================================================
# Multipliers relative to 2025 base BUILD_COSTS, keyed by year.
# Intermediate years are linearly interpolated by get_annualized_capex().

COST_PROJECTION_FACTORS = {
    "solar":        {2025: 1.00, 2030: 0.85, 2035: 0.75, 2040: 0.68, 2045: 0.62},
    "wind_onshore": {2025: 1.00, 2030: 0.92, 2035: 0.87, 2040: 0.83, 2045: 0.80},
    "battery":      {2025: 1.00, 2030: 0.70, 2035: 0.55, 2040: 0.45, 2045: 0.40},
    "battery_energy":{2025: 1.00, 2030: 0.70, 2035: 0.55, 2040: 0.45, 2045: 0.40},
    "diesel":       {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
    "OCGT":         {2025: 1.00, 2030: 1.00, 2035: 1.00, 2040: 1.00, 2045: 1.00},
}

# ============================================================================
# SCENARIO DEFINITIONS
# ============================================================================

SCENARIOS = {
    "base": {
        "description": "Base case — current diesel + RE investment allowed",
        "diesel_price_factor": 1.0,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
    "high_diesel": {
        "description": "Diesel price doubles by 2035",
        "diesel_price_factor": 2.0,
        "diesel_price_ramp_year": 2035,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
    "solar_only": {
        "description": "Only solar + battery investment allowed (no new wind)",
        "diesel_price_factor": 1.0,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "battery", "diesel"],
        "cost_projection": "default",
    },
    "high_growth": {
        "description": "5% annual demand growth",
        "diesel_price_factor": 1.0,
        "demand_growth_rate": 0.05,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
    "wind_solar_battery": {
        "description": "Full RE portfolio — solar, wind, and battery",
        "diesel_price_factor": 1.0,
        "demand_growth_rate": 0.03,
        "allowed_generators": ["solar", "wind_onshore", "battery", "diesel"],
        "cost_projection": "default",
    },
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
