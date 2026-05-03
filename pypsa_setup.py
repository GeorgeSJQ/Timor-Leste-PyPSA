"""
PyPSA Generator Wrapper Functions
This module provides standardized wrapper functions for adding various generator types to PyPSA networks.
"""

import pypsa
import pandas as pd


def add_solar_pv(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0.0,
    efficiency=1.0,
    p_max_pu=1.0,
    lifetime=25,
    build_year=None,
    **kwargs
):
    """
    Add a solar PV generator to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the solar PV plant
    bus : str
        Bus name where the generator is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float, optional
        Marginal cost in currency/MWh (default: 0.0)
    efficiency : float, optional
        Efficiency of conversion (default: 1.0)
    p_max_pu : float or pd.Series, optional
        Maximum output per unit of p_nom (capacity factor profile)
    lifetime : int, optional
        Lifetime in years (default: 25)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Generator",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier="solar",
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        p_max_pu=p_max_pu,
        p_min_pu=0.0,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )


def add_wind_farm(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0.0,
    efficiency=1.0,
    p_max_pu=1.0,
    wind_type="onshore",
    lifetime=25,
    build_year=None,
    **kwargs
):
    """
    Add a wind farm to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the wind farm
    bus : str
        Bus name where the generator is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float, optional
        Marginal cost in currency/MWh (default: 0.0)
    efficiency : float, optional
        Efficiency of conversion (default: 1.0)
    p_max_pu : float or pd.Series, optional
        Maximum output per unit of p_nom (capacity factor profile)
    wind_type : str, optional
        Type of wind farm: "onshore" or "offshore" (default: "onshore")
    lifetime : int, optional
        Lifetime in years (default: 25)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    carrier = f"wind_{wind_type}"
    
    network.add(
        "Generator",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier=carrier,
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        p_max_pu=p_max_pu,
        p_min_pu=0.0,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )


def add_battery_storage(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0.0,
    efficiency_charge=0.95,
    efficiency_discharge=0.95,
    max_hours=4.0,
    standing_loss=0.0,
    cyclic_state_of_charge=True,
    lifetime=15,
    build_year=None,
    **kwargs
):
    """
    Add a Battery Energy Storage System (BESS) to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the battery storage
    bus : str
        Bus name where the storage is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float, optional
        Marginal cost in currency/MWh (default: 0.0)
    efficiency_charge : float, optional
        Charging efficiency (default: 0.95)
    efficiency_discharge : float, optional
        Discharging efficiency (default: 0.95)
    max_hours : float, optional
        Maximum hours of storage at nominal power (default: 4.0)
    standing_loss : float, optional
        Hourly standing loss as fraction of energy capacity (default: 0.0)
    cyclic_state_of_charge : bool, optional
        Whether state of charge is cyclic (default: True)
    lifetime : int, optional
        Lifetime in years (default: 15)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    # Energy capacity in MWh
    energy_capacity = p_nom * max_hours
    
    network.add(
        "StorageUnit",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier="battery",
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency_store=efficiency_charge,
        efficiency_dispatch=efficiency_discharge,
        max_hours=max_hours,
        standing_loss=standing_loss,
        cyclic_state_of_charge=cyclic_state_of_charge,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )
    network.storage_units_t.inflow[name] = pd.Series(0.0, index=network.snapshots)


def add_ocgt(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0,
    efficiency=0.39,
    ramp_limit_up=None,
    ramp_limit_down=None,
    min_up_time=0,
    min_down_time=0,
    start_up_cost=0.0,
    shut_down_cost=0.0,
    p_min_pu=0.0,
    lifetime=40,
    build_year=None,
    **kwargs
):
    """
    Add an Open Cycle Gas Turbine (OCGT) to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the OCGT
    bus : str
        Bus name where the generator is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float
        Marginal cost in currency/MWh (includes fuel and O&M)
    efficiency : float, optional
        Electrical efficiency (default: 0.39, i.e., 39%)
    ramp_limit_up : float, optional
        Ramp up limit per unit of p_nom per hour
    ramp_limit_down : float, optional
        Ramp down limit per unit of p_nom per hour
    min_up_time : int, optional
        Minimum up time in hours (default: 0)
    min_down_time : int, optional
        Minimum down time in hours (default: 0)
    start_up_cost : float, optional
        Start-up cost in currency (default: 0.0)
    shut_down_cost : float, optional
        Shut-down cost in currency (default: 0.0)
    p_min_pu : float, optional
        Minimum stable generation level per unit (default: 0.0)
    lifetime : int, optional
        Lifetime in years (default: 40)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Generator",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier="OCGT",
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        ramp_limit_up=ramp_limit_up,
        ramp_limit_down=ramp_limit_down,
        min_up_time=min_up_time,
        min_down_time=min_down_time,
        start_up_cost=start_up_cost,
        shut_down_cost=shut_down_cost,
        p_min_pu=p_min_pu,
        p_max_pu=1.0,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )


def add_ccgt(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0,
    efficiency=0.58,
    ramp_limit_up=None,
    ramp_limit_down=None,
    min_up_time=4,
    min_down_time=4,
    start_up_cost=0.0,
    shut_down_cost=0.0,
    p_min_pu=0.4,
    lifetime=40,
    build_year=None,
    **kwargs
):
    """
    Add a Combined Cycle Gas Turbine (CCGT) to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the CCGT
    bus : str
        Bus name where the generator is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float
        Marginal cost in currency/MWh (includes fuel and O&M)
    efficiency : float, optional
        Electrical efficiency (default: 0.58, i.e., 58%)
    ramp_limit_up : float, optional
        Ramp up limit per unit of p_nom per hour
    ramp_limit_down : float, optional
        Ramp down limit per unit of p_nom per hour
    min_up_time : int, optional
        Minimum up time in hours (default: 4)
    min_down_time : int, optional
        Minimum down time in hours (default: 4)
    start_up_cost : float, optional
        Start-up cost in currency (default: 0.0)
    shut_down_cost : float, optional
        Shut-down cost in currency (default: 0.0)
    p_min_pu : float, optional
        Minimum stable generation level per unit (default: 0.4)
    lifetime : int, optional
        Lifetime in years (default: 40)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Generator",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier="CCGT",
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        ramp_limit_up=ramp_limit_up,
        ramp_limit_down=ramp_limit_down,
        min_up_time=min_up_time,
        min_down_time=min_down_time,
        start_up_cost=start_up_cost,
        shut_down_cost=shut_down_cost,
        p_min_pu=p_min_pu,
        p_max_pu=1.0,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )


def add_reciprocating_engine(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0,
    efficiency=0.42,
    ramp_limit_up=1.0,
    ramp_limit_down=1.0,
    min_up_time=0,
    min_down_time=0,
    start_up_cost=0.0,
    shut_down_cost=0.0,
    p_min_pu=0.3,
    lifetime=20,
    build_year=None,
    **kwargs
):
    """
    Add a reciprocating engine generator to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the reciprocating engine
    bus : str
        Bus name where the generator is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float
        Marginal cost in currency/MWh (includes fuel and O&M)
    efficiency : float, optional
        Electrical efficiency (default: 0.42, i.e., 42%)
    ramp_limit_up : float, optional
        Ramp up limit per unit of p_nom per hour (default: 1.0)
    ramp_limit_down : float, optional
        Ramp down limit per unit of p_nom per hour (default: 1.0)
    min_up_time : int, optional
        Minimum up time in hours (default: 0)
    min_down_time : int, optional
        Minimum down time in hours (default: 0)
    start_up_cost : float, optional
        Start-up cost in currency (default: 0.0)
    shut_down_cost : float, optional
        Shut-down cost in currency (default: 0.0)
    p_min_pu : float, optional
        Minimum stable generation level per unit (default: 0.3)
    lifetime : int, optional
        Lifetime in years (default: 20)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Generator",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier="reciprocating_engine",
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        ramp_limit_up=ramp_limit_up,
        ramp_limit_down=ramp_limit_down,
        min_up_time=min_up_time,
        min_down_time=min_down_time,
        start_up_cost=start_up_cost,
        shut_down_cost=shut_down_cost,
        p_min_pu=p_min_pu,
        p_max_pu=1.0,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )


def add_coal_generator(
    network,
    name,
    bus,
    p_nom=0,
    capital_cost=0,
    marginal_cost=0,
    efficiency=0.37,
    ramp_limit_up=0.05,
    ramp_limit_down=0.05,
    min_up_time=8,
    min_down_time=8,
    start_up_cost=0.0,
    shut_down_cost=0.0,
    p_min_pu=0.4,
    lifetime=40,
    build_year=None,
    **kwargs
):
    """
    Add a coal generator to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the coal generator
    bus : str
        Bus name where the generator is connected
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float
        Capital cost in currency/MW
    marginal_cost : float
        Marginal cost in currency/MWh (includes fuel and O&M)
    efficiency : float, optional
        Electrical efficiency (default: 0.37, i.e., 37%)
    ramp_limit_up : float, optional
        Ramp up limit per unit of p_nom per hour (default: 0.05)
    ramp_limit_down : float, optional
        Ramp down limit per unit of p_nom per hour (default: 0.05)
    min_up_time : int, optional
        Minimum up time in hours (default: 8)
    min_down_time : int, optional
        Minimum down time in hours (default: 8)
    start_up_cost : float, optional
        Start-up cost in currency (default: 0.0)
    shut_down_cost : float, optional
        Shut-down cost in currency (default: 0.0)
    p_min_pu : float, optional
        Minimum stable generation level per unit (default: 0.4)
    lifetime : int, optional
        Lifetime in years (default: 40)
    build_year : int, optional
        Year of construction
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Generator",
        name,
        bus=bus,
        p_nom=p_nom,
        carrier="coal",
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        ramp_limit_up=ramp_limit_up,
        ramp_limit_down=ramp_limit_down,
        min_up_time=min_up_time,
        min_down_time=min_down_time,
        start_up_cost=start_up_cost,
        shut_down_cost=shut_down_cost,
        p_min_pu=p_min_pu,
        p_max_pu=1.0,
        lifetime=lifetime,
        build_year=build_year,
        **kwargs
    )


# Network Component Functions

def add_bus(
    network,
    name,
    v_nom,
    x=0.0,
    y=0.0,
    carrier="AC",
    country=None,
    sub_network=None,
    **kwargs
):
    """
    Add a bus to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the bus
    v_nom : float
        Nominal voltage in kV
    x : float, optional
        Longitude/x-coordinate (default: 0.0)
    y : float, optional
        Latitude/y-coordinate (default: 0.0)
    carrier : str, optional
        Energy carrier (e.g., 'AC', 'DC')
    country : str, optional
        Country code or name
    sub_network : str, optional
        Sub-network identifier for clustering
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Bus",
        name,
        v_nom=v_nom,
        x=x,
        y=y,
        carrier=carrier,
        country=country,
        sub_network=sub_network,
        **kwargs
    )


def add_load(
    network,
    name,
    bus,
    p_set,
    q_set=0.0,
    **kwargs
):
    """
    Add a load to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the load
    bus : str
        Bus name where the load is connected
    p_set : float or pd.Series
        Active power demand in MW (time series or constant value)
    q_set : float or pd.Series, optional
        Reactive power demand in MVAr (default: 0.0)
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Load",
        name,
        bus=bus,
        p_set=p_set,
        q_set=q_set,
        **kwargs
    )


def add_line(
    network,
    name,
    bus0,
    bus1,
    length,
    r,
    x,
    s_nom=0,
    capital_cost=0.0,
    num_parallel=1,
    terrain_factor=1.0,
    s_max_pu=1.0,
    build_year=None,
    lifetime=50,
    **kwargs
):
    """
    Add a transmission line to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the line
    bus0 : str
        Name of the first bus (from)
    bus1 : str
        Name of the second bus (to)
    length : float
        Length of the line in km
    r : float
        Resistance per unit length in Ohm/km
    x : float
        Reactance per unit length in Ohm/km
    s_nom : float
        Nominal apparent power capacity in MVA
    capital_cost : float, optional
        Capital cost in currency/MVA (default: 0.0)
    num_parallel : int, optional
        Number of parallel lines (default: 1)
    terrain_factor : float, optional
        Terrain correction factor for length (default: 1.0)
    s_max_pu : float, optional
        Maximum apparent power per unit (default: 1.0)
    build_year : int, optional
        Year of construction
    lifetime : int, optional
        Lifetime in years (default: 50)
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Line",
        name,
        bus0=bus0,
        bus1=bus1,
        length=length,
        r=r,
        x=x,
        s_nom=s_nom,
        capital_cost=capital_cost,
        num_parallel=num_parallel,
        terrain_factor=terrain_factor,
        s_max_pu=s_max_pu,
        build_year=build_year,
        lifetime=lifetime,
        **kwargs
    )


def add_link(
    network,
    name,
    bus0,
    bus1,
    p_nom=0,
    capital_cost=0.0,
    marginal_cost=0.0,
    efficiency=1.0,
    length=0.0,
    p_min_pu=-1.0,
    p_max_pu=1.0,
    carrier=None,
    build_year=None,
    lifetime=50,
    **kwargs
):
    """
    Add a link to the PyPSA network. Links are used for unidirectional or 
    bidirectional power flow between buses, including DC lines, converters,
    and other power flow constraints.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the link
    bus0 : str
        Name of the first bus (from)
    bus1 : str
        Name of the second bus (to)
    p_nom : float
        Nominal power capacity in MW
    capital_cost : float, optional
        Capital cost in currency/MW (default: 0.0)
    marginal_cost : float, optional
        Marginal cost in currency/MWh (default: 0.0)
    efficiency : float, optional
        Transmission efficiency (default: 1.0)
    length : float, optional
        Length of the link in km (default: 0.0)
    p_min_pu : float, optional
        Minimum power per unit, negative for bidirectional (default: -1.0)
    p_max_pu : float, optional
        Maximum power per unit (default: 1.0)
    carrier : str, optional
        Energy carrier (e.g., 'DC', 'H2')
    build_year : int, optional
        Year of construction
    lifetime : int, optional
        Lifetime in years (default: 50)
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Link",
        name,
        bus0=bus0,
        bus1=bus1,
        p_nom=p_nom,
        capital_cost=capital_cost,
        marginal_cost=marginal_cost,
        efficiency=efficiency,
        length=length,
        p_min_pu=p_min_pu,
        p_max_pu=p_max_pu,
        carrier=carrier,
        build_year=build_year,
        lifetime=lifetime,
        **kwargs
    )


def add_transformer(
    network,
    name,
    bus0,
    bus1,
    s_nom=0,
    capital_cost=0.0,
    x=0.1,
    r=0.0,
    tap_ratio=1.0,
    phase_shift=0.0,
    s_max_pu=1.0,
    num_parallel=1,
    build_year=None,
    lifetime=40,
    **kwargs
):
    """
    Add a transformer to the PyPSA network.
    
    Parameters:
    -----------
    network : pypsa.Network
        The PyPSA network object
    name : str
        Unique identifier for the transformer
    bus0 : str
        Name of the primary side bus (high voltage)
    bus1 : str
        Name of the secondary side bus (low voltage)
    s_nom : float
        Nominal apparent power capacity in MVA
    capital_cost : float, optional
        Capital cost in currency/MVA (default: 0.0)
    x : float, optional
        Series reactance per unit (default: 0.1)
    r : float, optional
        Series resistance per unit (default: 0.0)
    tap_ratio : float, optional
        Ratio of actual to nominal voltage (default: 1.0)
    phase_shift : float, optional
        Phase shift angle in degrees (default: 0.0)
    s_max_pu : float, optional
        Maximum apparent power per unit (default: 1.0)
    num_parallel : int, optional
        Number of parallel transformers (default: 1)
    build_year : int, optional
        Year of construction
    lifetime : int, optional
        Lifetime in years (default: 40)
    **kwargs : dict
        Additional parameters to pass to network.add()
    
    Returns:
    --------
    None
    """
    network.add(
        "Transformer",
        name,
        bus0=bus0,
        bus1=bus1,
        s_nom=s_nom,
        capital_cost=capital_cost,
        x=x,
        r=r,
        tap_ratio=tap_ratio,
        phase_shift=phase_shift,
        s_max_pu=s_max_pu,
        num_parallel=num_parallel,
        build_year=build_year,
        lifetime=lifetime,
        **kwargs
    )

def add_generic_battery(
        network,
        connecting_bus,
        longitude,
        latitude,
        one_way_efficiency=0.95,
        capital_cost=0,
        p_nom_extendable=True,
        e_nom_extendable=True,
        e_cyclic=True,
    ):
        network.add("Bus", connecting_bus, suffix=" battery", carrier="battery", x=longitude, y=latitude)

        network.add(
            "Link",
            connecting_bus,
            suffix=" battery charger",
            bus0=connecting_bus,
            bus1=connecting_bus + " battery",
            carrier="battery charger",
            p_nom_extendable=p_nom_extendable,
            efficiency=one_way_efficiency,
            capital_cost=capital_cost,
        )

        network.add(
            "Link",
            connecting_bus,
            suffix=" battery discharger",
            bus0=connecting_bus + " battery",
            bus1=connecting_bus,
            carrier="battery discharger",
            p_nom_extendable=p_nom_extendable,
            efficiency=one_way_efficiency,
        )

        network.add(
            "Store",
            connecting_bus,
            suffix=" battery storage",
            bus=connecting_bus + " battery",
            carrier="battery storage",
            capital_cost=capital_cost,
            e_nom_extendable=e_nom_extendable,
            e_cyclic=e_cyclic,
        )

def battery_constraint(n: pypsa.Network, sns: pd.Index) -> None:
    """Constraint to ensure that the nominal capacity of battery chargers and dischargers are in a fixed ratio."""
    dischargers_i = n.links[n.links.index.str.contains(" discharger")].index
    chargers_i = n.links[n.links.index.str.contains(" charger")].index

    eff = n.links.efficiency[dischargers_i].values
    lhs = n.model["Link-p_nom"].loc[chargers_i]
    rhs = n.model["Link-p_nom"].loc[dischargers_i] * eff

    n.model.add_constraints(lhs == rhs, name="Link-charger_ratio")
