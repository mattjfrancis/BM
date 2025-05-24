# Brenmiller Thermal Storage Simulator v4.0

## Overview
This interactive Streamlit application simulates the operation of Brenmiller Energy's thermal storage technology across different European markets and scenarios. The simulator helps users understand how thermal energy storage systems respond to price signals, provide grid balancing services, and optimize energy usage.

## Features
- **24-Hour Thermal Storage Visualization**: Detailed animation showing battery charging/discharging cycles and grid regulation over a typical day
- **Strategy Map**: Geographic visualization of optimal business models across European countries
- **Detailed Analysis**: In-depth financial analysis of different business models (Standalone, HaaS, Grid Balancing)
- **Price Projections**: Forecasting of energy prices under different scenarios
- **Sensitivity Analysis**: Impact of key parameters on system performance
- **Grid Stability**: Visualization of grid frequency regulation capabilities
- **Market Recommendations**: Tailored business model recommendations by country

## How to Use
1. Select a scenario (Reference, Net-Zero, or Extreme) at the top of the page
2. Adjust simulation parameters in the sidebar
3. Explore the 24-hour thermal storage operation visualization
4. Navigate through the tabs to view detailed analysis and recommendations

## Scenarios
- **Reference**: Business-as-usual scenario with standard price levels and volatility
- **Net-Zero 2050**: Transition to net-zero emissions with higher prices and increased grid activations
- **Extreme Climate**: High volatility scenario with significant price fluctuations and market events

## Deployment
This app is deployed on Hugging Face Spaces. You can access it at: [Hugging Face Space URL]

## Local Development
To run this app locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

## About Brenmiller Energy
Brenmiller Energy (NASDAQ: BNRG) develops and manufactures thermal energy storage systems that enable industrial and commercial customers to optimize their energy usage, reduce carbon emissions, and transition to cleaner energy sources.
