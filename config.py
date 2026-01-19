"""
Simulation Configuration File
This file contains all user-configurable parameters for PyPSA simulations.
Modify these settings to customize simulation scenarios.
"""

from pypsa.common import annuity

# ============================================================================
# SIMULATION PARAMETERS
# ============================================================================

# Time period for simulation
SIMULATION_START_YEAR = 2025
SIMULATION_END_YEAR = 2025

# Temporal resolution
HOURS_PER_YEAR = 8760  # 8760 for hourly, 8784 for leap years
RESOLUTION = 1  # Weighting of each simulation timestepos

# Snapshot settings
SNAPSHOTS_START = "2025-01-01 00:00"
SNAPSHOTS_END = "2025-12-31 23:00"

# Optimization settings
SOLVER_NAME = "highs"  # Options: "gurobi", "cplex", "glpk", "cbc", "highs"
SOLVER_OPTIONS = {
    "threads": 4,
    "method": 2,  # barrier
    "crossover": 0,
    "BarConvTol": 1.e-5,
    "FeasibilityTol": 1.e-6,
    "AggFill": 0,
    "PreDual": 0,
}

# Economic parameters
DISCOUNT_RATE = 0.08  # 8% discount rate
CO2_PRICE = 0.0  # USD/tCO2 - carbon price


# ============================================================================
# CARRIER DEFINITIONS
# ============================================================================

CARRIERS = {
    # Electricity carriers
    "AC": {
        "color": "#4169E1",  # Royal Blue
        "nice_name": "AC Electricity",
        "co2_emissions": 0.0,
    },
    "DC": {
        "color": "#1E90FF",  # Dodger Blue
        "nice_name": "DC Electricity",
        "co2_emissions": 0.0,
    },
    
    # Renewable generators
    "solar": {
        "color": "#FFD700",  # Gold
        "nice_name": "Solar PV",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "wind_onshore": {
        "color": "#4682B4",  # Steel Blue
        "nice_name": "Onshore Wind",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "wind_offshore": {
        "color": "#00CED1",  # Dark Turquoise
        "nice_name": "Offshore Wind",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "hydro": {
        "color": "#1E90FF",  # Deep Sky Blue
        "nice_name": "Hydropower",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 80,
    },
    
    # Storage
    "battery": {
        "color": "#9370DB",  # Medium Purple
        "nice_name": "Battery Storage",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 15,
    },
    "pumped_hydro": {
        "color": "#4169E1",  # Royal Blue
        "nice_name": "Pumped Hydro Storage",
        "co2_emissions": 0.0,
        "capital_cost_unit": "USD/MW",
        "lifetime": 50,
    },
    
    # Fossil fuel generators
    "OCGT": {
        "color": "#CD853F",  # Peru
        "nice_name": "Open Cycle Gas Turbine",
        "co2_emissions": 0.45,  # tCO2/MWh_th (natural gas)
        "fuel": "natural_gas",
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "CCGT": {
        "color": "#D2691E",  # Chocolate
        "nice_name": "Combined Cycle Gas Turbine",
        "co2_emissions": 0.45,  # tCO2/MWh_th (natural gas)
        "fuel": "natural_gas",
        "capital_cost_unit": "USD/MW",
        "lifetime": 25,
    },
    "reciprocating_engine": {
        "color": "#A0522D",  # Sienna
        "nice_name": "Reciprocating Engine",
        "co2_emissions": 0.45,  # tCO2/MWh_th (can use natural gas or diesel)
        "fuel": "natural_gas",
        "capital_cost_unit": "USD/MW",
        "lifetime": 20,
    },
    "coal": {
        "color": "#2F4F4F",  # Dark Slate Gray
        "nice_name": "Coal Generator",
        "co2_emissions": 0.98,  # tCO2/MWh_th
        "fuel": "coal",
        "capital_cost_unit": "USD/MW",
        "lifetime": 40,
    },
    "diesel": {
        "color": "#8B4513",  # Saddle Brown
        "nice_name": "Diesel Generator",
        "co2_emissions": 0.65,  # tCO2/MWh_th
        "fuel": "diesel",
        "capital_cost_unit": "USD/MW",
        "lifetime": 20,
    },
    "oil": {
        "color": "#696969",  # Dim Gray
        "nice_name": "Oil Generator",
        "co2_emissions": 0.65,  # tCO2/MWh_th
        "fuel": "oil",
        "capital_cost_unit": "USD/MW",
        "lifetime": 30,
    },
    
    # Fuels
    "natural_gas": {
        "color": "#FFA500",  # Orange
        "nice_name": "Natural Gas",
        "co2_emissions": 0.0,  # Emissions counted at point of use
    },
    "hydrogen": {
        "color": "#FF1493",  # Deep Pink
        "nice_name": "Hydrogen",
        "co2_emissions": 0.0,
    },
}


# ============================================================================
# TECHNOLOGY COST DATA
# ============================================================================

# Build costs (AUD/MW for generators, AUD/MVA for lines/transformers)
BUILD_COSTS = {
    "solar": 1647000,  # AUD/MW
    "wind_onshore": 3534000,  # AUD/MW
    "wind_offshore": 4710000,  # AUD/MW
    "battery": 1680310,  # AUD/MW (power capacity)
    "battery_energy": 1680310,  # AUD/MWh (energy capacity)
    "OCGT": 1287000,  # AUD/MW
    "CCGT": 2409000,  # AUD/MW
    "reciprocating_engine": 2375000,  # AUD/MW
    "coal": 2000000,  # AUD/MW
    "diesel": 2375000,  # AUD/MW
    "line": 0,  # AUD/MVA/km
    "transformer": 0,  # AUD/MVA
}

# Fixed O&M costs (AUD/MW/year)
FIXED_OM_COSTS = {
    "solar": 14660,
    "wind_onshore": 34220,
    "wind_offshore": 141450,
    "battery": 21200,
    "OCGT": 14070,
    "CCGT": 15030,
    "reciprocating_engine": 17370,
    "coal": 20000,
    "diesel": 17370,
}

# Marginal costs (AUD/MWh)
MARGINAL_COSTS = {
    "solar": 0.8,  # Small O&M cost, dispatch solar after wind
    "wind_onshore": 0.5, # Small O&M cost, dispatch wind first
    "wind_offshore": 0.7,
    "battery": 0.5,  # Small O&M cost
    "OCGT": 196.19,  # Fuel + VOM
    "CCGT": 111.66,  # Fuel + VOM
    "reciprocating_engine": 199.33,  # Fuel + VOM
    "coal": 130,  # Fuel + VOM
    "diesel": 199.33,  # Fuel + VOM
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
        "lifetime": 20,
        "efficiency_charge": 0.95,
        "efficiency_discharge": 0.95,
        "max_hours": 4.0,
        "standing_loss": 0.0001,  # 0.01% per hour
    },
    "OCGT": {
        "lifetime": 40,
        "efficiency": 0.39,
        "ramp_limit_up": 0.5,  # 50% per hour
        "ramp_limit_down": 0.5,
        "min_up_time": 1,
        "min_down_time": 1,
        "p_min_pu": 0.0,
    },
    "CCGT": {
        "lifetime": 40,
        "efficiency": 0.58,
        "ramp_limit_up": 0.2,  # 20% per hour
        "ramp_limit_down": 0.2,
        "min_up_time": 4,
        "min_down_time": 4,
        "p_min_pu": 0.4,
    },
    "reciprocating_engine": {
        "lifetime": 20,
        "efficiency": 0.42,
        "ramp_limit_up": 1.0,  # 100% per hour (fast ramping)
        "ramp_limit_down": 1.0,
        "min_up_time": 0,
        "min_down_time": 0,
        "p_min_pu": 0.3,
    },
    "coal": {
        "lifetime": 40,
        "efficiency": 0.37,
        "ramp_limit_up": 0.05,  # 5% per hour (slow ramping)
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

# Capital costs (AUD/MW for generators, AUD/MVA for lines/transformers)
# Calculated as: annuity(DISCOUNT_RATE, lifetime) * BUILD_COSTS + FIXED_OM_COSTS
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
    "line": 0,  # AUD/MVA/km
    "transformer": 0,  # AUD/MVA
}

# ============================================================================
# TRANSMISSION PARAMETERS
# ============================================================================

# Typical line parameters for different voltage levels
LINE_TYPES = {
    "132kV": {
        "r_per_km": 0.1,  # Ohm/km
        "x_per_km": 0.3,  # Ohm/km
        "s_nom": 200,  # MVA
        "v_nom": 132,  # kV
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

# Transformer parameters
TRANSFORMER_TYPES = {
    "132/20kV": {
        "s_nom": 50,  # MVA
        "v_nom_0": 132,  # kV primary
        "v_nom_1": 20,  # kV secondary
        "x": 0.1,  # pu
        "r": 0.01,  # pu
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

# Renewable energy targets (as fraction of total generation)
RENEWABLE_TARGET = {
    2025: 0.30,  # 30% renewables by 2025
    2030: 0.50,  # 50% by 2030
    2040: 0.70,  # 70% by 2040
    2050: 1.00,  # 100% by 2050
}

# Maximum capacity limits (MW) - optional constraints
MAX_CAPACITY = {
    "solar": None,  # No limit
    "wind_onshore": None,
    "wind_offshore": None,
    "battery": None,
    "OCGT": 500,  # Example: max 500 MW
    "CCGT": None,
    "coal": 0,  # No new coal (set to 0 to ban)
}

# Reserve requirements
RESERVE_MARGIN = 0.15  # 15% planning reserve margin
SPINNING_RESERVE = 0.03  # 3% of load as spinning reserve


# ============================================================================
# OUTPUT SETTINGS
# ============================================================================

OUTPUT_DIR = "results"
SAVE_NETWORK = True
SAVE_RESULTS_CSV = True
SAVE_PLOTS = True

# Plotting settings
PLOT_SETTINGS = {
    "figsize": (12, 8),
    "dpi": 300,
    "style": "seaborn-v0_8-darkgrid",
}
