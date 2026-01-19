# Timor Leste PyPSA Energy System Model

A capacity expansion planning model for Timor Leste's electricity grid built with [PyPSA](https://pypsa.org/) (Python for Power System Analysis).

## Overview

This project models Timor Leste's electricity system to optimise the deployment of generation and storage technologies. The model determines the cost-optimal mix of solar PV, wind, battery storage, and conventional generation to meet electricity demand while considering capital and operational costs.

## Current Capabilities

- **Basic Capacity Expansion Optimisation**: The model can perform single-year capacity expansion planning to determine optimal technology deployment
- **Renewable Energy Integration**: Solar PV and wind generation with real capacity factor profiles from [renewables.ninja](https://www.renewables.ninja/)
- **Battery Energy Storage**: Grid-scale battery storage modeling with configurable parameters
- **Multi-bus Network**: Representation of major load centers (Dili, Baucau, Lospalos) with transmission constraints
- **Detailed Cost Modeling**: Capital and marginal costs based on technology cost projections

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Recommended: Virtual environment (venv or conda)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/GeorgeSJQ/Timor-Leste-PyPSA.git
cd Timor-Leste-PyPSA
```

2. Install required packages:
```bash
pip install pypsa pandas numpy matplotlib
```

### Running the Model

Execute the main optimisation script:

```bash
python optimization_example.py
```

This will:
1. Build the Timor Leste network with transmission lines between major load centres
2. Add renewable generators (solar, wind) and battery storage with extendable capacity
3. Load hourly demand and renewable generation profiles for 2025
4. Optimise the system to minimise total costs
5. Generate result plots and save the optimised network

Results are saved in the `results/` directory.

## Project Structure

```
.
├── config.py                           # Global configuration parameters
├── timor_leste_config.py              # Network topology and load profiles
├── pypsa_setup.py                     # Generator and storage component definitions
├── optimization_example.py            # Main optimisation script
├── technology_costs_2030.csv          # Technology cost assumptions
├── data/
│   ├── solar_pv_output_re_ninja.csv   # Solar PV capacity factors
│   ├── wind_output_re_ninja.csv       # Wind capacity factors
│   └── timor_leste_hourly_load_2025.csv  # Hourly electricity demand
└── results/
    └── optimized_network.nc           # Optimised network output (NetCDF format)
```

## Configuration

Key parameters can be adjusted in `config.py`:
- `SNAPSHOTS_START` / `SNAPSHOTS_END`: Simulation time period
- `DISCOUNT_RATE`: Financial discount rate for annualized costs
- `CAPITAL_COSTS`: Technology capital costs ($/MW or $/MWh)
- `MARGINAL_COSTS`: Variable O&M costs ($/MWh)
- `TECHNICAL_PARAMS`: Technical parameters (efficiencies, storage duration, etc.)
- `SOLVER_NAME`: Optimisation solver (default: "highs")

## Planned Features

The following enhancements are planned for future releases:

### 📊 Advanced Results Analysis
- More sophisticated visualisation and analysis charts
- Generation dispatch time series analysis
- Capacity factor and curtailment statistics
- Cost breakdown and sensitivity analysis
- Geographic visualisation of network and generation

### 🛤️ Myopic Pathway Planning
- Multi-period capacity expansion using PyPSA's `multi_investment_period` optimisation
- Year-by-year investment decisions with path dependencies
- Technology learning curves and declining costs over time
- Long-term decarbonisation pathway analysis

### 🔌 Distribution Network Modeling
- Detailed representation of Timor Leste's distribution network
- Medium and low voltage network constraints
- Distributed generation integration (rooftop solar, small-scale wind)
- Distribution system upgrade costs

## Data Sources

- **Load profiles**: Based on Timor Leste electricity demand patterns
- **Renewable profiles**: Generated from [renewables.ninja](https://www.renewables.ninja/) using Timor Leste coordinates
- **Technology costs**: Based on IEA and IRENA projections for 2030

## License

TBA

## Acknowledgments

This model is built using [PyPSA](https://pypsa.org/), an open-source power system analysis framework developed by the PyPSA team. This project is funded by UNSW via the Collaboration on Energy and Environmental Markets (CEEM).
