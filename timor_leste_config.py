"""
Timor Leste Grid Configuration
This file defines the existing electricity grid infrastructure of Timor Leste,
including the 150kV transmission backbone, substations, and power plants.
"""

import pypsa
import pandas as pd
from pypsa_setup import (
    add_bus, add_line, add_load
)
from config import RESOLUTION, LINE_TYPES, CAPITAL_COSTS, MARGINAL_COSTS, TECHNICAL_PARAMS, CARRIERS


# ============================================================================
# SUBSTATION COORDINATES
# ============================================================================

SUBSTATIONS = {
    # Format: name: (latitude, longitude, voltage_kv)
    "Maliana": (-8.934, 125.19, 150),
    "Liquica": (-8.60, 125.31, 150),
    "Dili": (-8.56, 125.61, 150),
    "Manatuto": (-8.54, 126.00, 150),
    "Baucau": (-8.49, 126.45, 150),
    "Lospalos": (-8.49, 127.00, 150),
    "Viqueque": (-8.84, 126.37, 150),
    "Cassa": (-9.15, 125.53, 150),
    "Suai": (-9.33, 125.27, 150),
}


# ============================================================================
# EXISTING POWER PLANTS
# ============================================================================

POWER_PLANTS = {
    "Betano": {
        "coordinates": (-9.15, 125.73),
        "voltage_kv": 150,
        "capacity_mw": 136,
        "technology": "diesel",
        "commissioning_year": 2015,
    },
    "Hera": {
        "coordinates": (-8.54, 125.70),
        "voltage_kv": 150,
        "capacity_mw": 119,
        "technology": "diesel",
        "commissioning_year": 2011,
    },
}


# ============================================================================
# TRANSMISSION BACKBONE CONNECTIONS
# ============================================================================

# Define the 150kV transmission line connections
# Format: (from_bus, to_bus, approximate_length_km)
# Total length: 553 km
TRANSMISSION_LINES = [
    # Western section
    ("Suai", "Maliana", 78),
    ("Maliana", "Liquica", 51),
    ("Liquica", "Dili", 28),
    
    # Central section - Northern route
    ("Dili", "Hera", 14),
    ("Hera", "Manatuto", 41),
    ("Manatuto", "Baucau", 46),
    ("Baucau", "Lospalos", 55),
    
    # Central section - Southern route
    ("Betano", "Cassa", 28),
    ("Cassa", "Viqueque", 41),
    ("Viqueque", "Baucau", 60),
    
    # Cross connections
    ("Manatuto", "Cassa", 46),
    ("Suai", "Betano", 65),
]


# ============================================================================
# BUILD TIMOR LESTE NETWORK
# ============================================================================

def build_timor_leste_network(
    snapshots=None,
    freq=1,
    add_generators=True,
    line_type="150kV",
):
    """
    Build the PyPSA network model for Timor Leste's existing grid.
    
    Parameters:
    -----------
    snapshots : pd.DatetimeIndex, optional
        Time snapshots for the simulation. If None, creates a simple snapshot.
    freq : int, optional
        Time resolution in hours for the simulation (default: 1)
    add_generators : bool, optional
        Whether to add existing power plants (default: True)
    line_type : str, optional
        Type of transmission line to use (default: "150kV")
    
    Returns:
    --------
    network : pypsa.Network
        The configured PyPSA network object
    """
    
    # Initialize network
    if snapshots is None:
        snapshots = pd.date_range("2025-01-01", periods=1, freq=f"{freq}h")
    if isinstance(snapshots, pd.MultiIndex):
        model_start_year = int(snapshots.get_level_values("timestep").year.min())
    else:
        model_start_year = int(pd.Index(snapshots).year.min())
    
    network = pypsa.Network(snapshots=snapshots)
    network.snapshots.name = "snapshot"
    network.name = "Timor Leste Grid"
    
    print("Building Timor Leste electricity network...")
    
    # ========================================================================
    # Add carriers from config
    # ========================================================================
    
    print("\nAdding carriers...")
    for carrier_name, carrier_data in CARRIERS.items():
        network.add(
            "Carrier",
            carrier_name,
            color=carrier_data.get("color", "#000000"),
            nice_name=carrier_data.get("nice_name", carrier_name),
            co2_emissions=carrier_data.get("co2_emissions", 0.0),
        )
    print(f"  Added {len(network.carriers)} carriers")
    
    # ========================================================================
    # Add substations as buses
    # ========================================================================
    
    print("\nAdding substations...")
    for substation_name, (lat, lon, v_nom) in SUBSTATIONS.items():
        add_bus(
            network=network,
            name=substation_name,
            v_nom=v_nom,
            x=lon,  # Longitude as x-coordinate
            y=lat,  # Latitude as y-coordinate
            carrier="AC",
            country="TL",
        )
        print(f"  Added substation: {substation_name} ({v_nom}kV)")
    
    # ========================================================================
    # Add power plant buses
    # ========================================================================
    
    print("\nAdding power plant buses...")
    for plant_name, plant_data in POWER_PLANTS.items():
        lat, lon = plant_data["coordinates"]
        v_nom = plant_data["voltage_kv"]
        
        add_bus(
            network=network,
            name=plant_name,
            v_nom=v_nom,
            x=lon,
            y=lat,
            carrier="AC",
            country="TL",
        )
        print(f"  Added power plant bus: {plant_name} ({v_nom}kV)")
    
    # ========================================================================
    # Add transmission lines
    # ========================================================================
    
    print("\nAdding 150kV transmission lines...")
    
    # Get line parameters based on type
    if line_type not in LINE_TYPES:
        # Create custom 150kV line type if not in config
        line_params = {
            "r_per_km": 0.08,  # Ohm/km
            "x_per_km": 0.28,  # Ohm/km
            "s_nom": 250,  # MVA
            "v_nom": 150,  # kV
        }
    else:
        line_params = LINE_TYPES[line_type]
    
    for i, (bus0, bus1, length) in enumerate(TRANSMISSION_LINES):
        line_name = f"Line_{bus0}_{bus1}"
        
        add_line(
            network=network,
            name=line_name,
            bus0=bus0,
            bus1=bus1,
            length=length,
            r=line_params["r_per_km"] * length,
            x=line_params["x_per_km"] * length,
            s_nom=line_params["s_nom"],
            capital_cost=CAPITAL_COSTS.get("line", 1000) * length,
            terrain_factor=1.0,
            build_year=model_start_year,
            lifetime=50,
            
        )
        print(f"  Added line: {bus0} -> {bus1} ({length} km)")
    
    # ========================================================================
    # Add existing power plants
    # ========================================================================
    
    if add_generators:
        print("\nAdding existing diesel power plants...")
        
        for plant_name, plant_data in POWER_PLANTS.items():
            capacity = plant_data["capacity_mw"]
            technology = plant_data["technology"]
            
            # Get diesel parameters from config
            efficiency = TECHNICAL_PARAMS.get("diesel", {}).get("efficiency", 0.40)
            marginal_cost = MARGINAL_COSTS.get("diesel", 150)
            
            # Add diesel generator using a simple network.add call
            # (we don't have add_diesel_generator in pypsa_setup, so use the reciprocating engine function)
            network.add(
                "Generator",
                plant_name + "_Existing",
                bus=plant_name,
                p_nom=capacity,
                carrier="diesel",
                capital_cost=0,  # Existing plant, no capital cost
                marginal_cost=marginal_cost,
                efficiency=efficiency,
                # p_min_pu=0.2,
                # p_max_pu=1.0,
                # ramp_limit_up=1.0,
                # ramp_limit_down=1.0,
                build_year=plant_data["commissioning_year"],
            )
            print(f"  Added generator: {plant_name} ({capacity} MW, {technology})")
    
    # ========================================================================
    # Set snapshot weighting
    # ========================================================================
   
    network.snapshot_weightings.loc[:, :] = RESOLUTION

    # ========================================================================
    # Network summary
    # ========================================================================
    
    print("\n" + "="*70)
    print("TIMOR LESTE NETWORK SUMMARY")
    print("="*70)
    print(f"Substations (buses):        {len(network.buses)}")
    print(f"Transmission lines:         {len(network.lines)}")
    print(f"Generators:                 {len(network.generators)}")
    print(f"Total generation capacity:  {network.generators.p_nom.sum():.1f} MW")
    print("="*70)

    network.snapshots.name = "snapshot"
    
    return network


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_loads_to_network(
    network,
    load_csv_path=r"data\timor_leste_hourly_load_2025.csv",
    output_dir=None,
    scenario_name="single_year",
):
    """
    Add electrical loads to each substation based on population distribution.

    Honours ``config.LOAD_MODE``:
      - ``"csv"`` (default): tile the hourly load CSV across snapshots and
        scale each bus by its population share.
      - ``"random"``: synthesise typical-shape per-bus profiles from
        ``config.LOAD_RANDOM_CONFIG``. If ``output_dir`` is provided, the
        profiles are also exported to ``{output_dir}/inputs/``.

    Parameters
    ----------
    network : pypsa.Network
        The PyPSA network object.
    load_csv_path : str, optional
        Path to the CSV file containing the hourly load profile (CSV mode).
    output_dir : str, optional
        Scenario output directory. If given AND mode is "random", random
        profiles are exported to ``{output_dir}/inputs/``.
    scenario_name : str, optional
        Used only as the title of the exported plot.
    """
    import config
    from src.scenarios import build_random_load_profiles, export_load_profiles

    print("\nAdding load profiles...")

    # Load distribution based on population
    # Oecusse and Atauro Island are excluded from the model
    load_distribution = {
        "Dili": 0.29,
        "Baucau": 0.108,
        "Maliana": 0.086,
        "Liquica": 0.172,
        "Manatuto": 0.045,
        "Lospalos": 0.059,
        "Viqueque": 0.067,
        "Cassa": 0.061,
        "Suai": 0.062,
        "Betano": 0.052,
    }

    snapshots = network.snapshots
    load_mode = getattr(config, "LOAD_MODE", "csv")
    print(f"  Load mode: {load_mode}")

    if load_mode == "random":
        profiles = build_random_load_profiles(
            snapshots=snapshots,
            load_distribution=load_distribution,
            config_dict=config.LOAD_RANDOM_CONFIG,
        )
        if output_dir is not None:
            export_load_profiles(profiles, output_dir, scenario_name=scenario_name)

        for bus, p_set in profiles.items():
            if bus in network.buses.index:
                network.add(
                    "Load",
                    f"Load_{bus}",
                    bus=bus,
                    p_set=p_set,
                )
    else:
        # Read the default load profile (CSV mode)
        default_load = pd.read_csv(load_csv_path)

        # Set the index to match the network snapshots if lengths match
        if len(default_load) == len(snapshots):
            default_load.drop(columns=['Time'], inplace=True)
            default_load.index = snapshots.copy()
            default_load.index.name = snapshots.name
        else:
            print(f"Warning: Load data length ({len(default_load)}) does not match snapshots length ({len(snapshots)})")
            print("Please check the input data.")
            return

        csv_profiles = {}
        for bus, population_factor in load_distribution.items():
            if bus in network.buses.index:
                bus_load_profile = (default_load['Demand'] * population_factor).rename(f"Load_{bus}")
                network.add(
                    "Load",
                    f"Load_{bus}",
                    bus=bus,
                    p_set=bus_load_profile,
                )
                csv_profiles[bus] = bus_load_profile

        if output_dir is not None:
            export_load_profiles(csv_profiles, output_dir, scenario_name=scenario_name)

    print(f"  Added {len(network.loads)} loads")
    if not network.loads.empty:
        print(f"  Average load: {network.loads_t.p_set.sum(axis=1).mean():.1f} MW")


def get_network_statistics(network):
    """
    Print detailed statistics about the network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    
    Returns:
    --------
    dict : Network statistics
    """
    stats = {
        "n_buses": len(network.buses),
        "n_lines": len(network.lines),
        "n_generators": len(network.generators),
        "n_loads": len(network.loads),
        "total_line_length_km": network.lines.length.sum(),
        "total_generation_mw": network.generators.p_nom.sum(),
        "total_load_mw": network.loads_t.p_set.sum(axis=1).mean() if len(network.loads) > 0 else 0,
    }
    
    print("\nDetailed Network Statistics:")
    print("-" * 50)
    for key, value in stats.items():
        print(f"{key:.<40} {value:.2f}" if isinstance(value, float) else f"{key:.<40} {value}")
    print("-" * 50)
    
    return stats


# ============================================================================
# MAIN EXECUTION (for testing)
# ============================================================================

if __name__ == "__main__":
    # Build the network
    network = build_timor_leste_network()
    
    # Add loads
    add_loads_to_network(network)
    
    # Print statistics
    get_network_statistics(network)
    
    # Save the network
    network.export_to_netcdf("timor_leste_grid.nc")
    print("\nNetwork saved to: timor_leste_grid.nc")
