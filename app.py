import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from io import BytesIO
from datetime import timedelta, datetime
import pytz
import json
import requests
import math

# --- Page Configuration ---
st.set_page_config(
    page_title="Brenmiller Simulator v4.0",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Optional Dependency Handling ---
try:
    from streamlit_lottie import st_lottie
    LOTTIE_AVAILABLE = True
except ImportError:
    LOTTIE_AVAILABLE = False
    st.warning("streamlit_lottie not found. Animations will be disabled. pip install streamlit-lottie")

try:
    from streamlit_extras.colored_header import colored_header
    from streamlit_extras.metric_cards import style_metric_cards
    EXTRAS_AVAILABLE = True
except ImportError:
    EXTRAS_AVAILABLE = False
    st.warning("streamlit_extras not found. Some UI enhancements will be disabled. pip install streamlit-extras")

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* Main styling */
    .stApp {
        background-color: #FFFFFF; /* Light background for the app */
    }

    /* Scenario selector styling */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"][role="button"] {
        background-color: #f8f9fa; /* Light grey for scenario cards */
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        border: 2px solid transparent;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"][role="button"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"][role="button"].selected-scenario {
        border: 2px solid #007bff; /* Blue border for selected scenario */
        box-shadow: 0 4px 12px rgba(0,123,255,0.2);
    }

    /* Metric card styling (if streamlit-extras is not used) */
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #007bff; /* Default blue, can be overridden */
        margin-bottom: 1rem;
    }

    /* Tooltip styling */
    .tooltip {
        position: relative;
        display: inline-block;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 220px;
        background-color: #333;
        color: #fff;
        text-align: left;
        border-radius: 6px;
        padding: 8px;
        position: absolute;
        z-index: 1000;
        bottom: 110%; /* Position above the element */
        left: 50%;
        margin-left: -110px; /* Center the tooltip */
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.85rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }

    /* Tailwind-like utility classes */
    .p-4 {padding: 1rem !important;}
    .mb-6 {margin-bottom: 1.5rem !important;}
    .mt-4 {margin-top: 1rem !important;}
    .text-center {text-align: center;}
</style>
""", unsafe_allow_html=True)

# --- Lottie Animation Functions ---
def load_lottie_url(url: str):
    """Load Lottie animation from URL"""
    if not LOTTIE_AVAILABLE:
        return None
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status() # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching Lottie animation from {url}: {e}")
        return None
    except json.JSONDecodeError:
        st.error(f"Error decoding Lottie JSON from {url}")
        return None

# Lottie URLs for scenario animations (simple battery icons)
# For dynamic fill, more complex Lottie files or JS would be needed.
# These are placeholders for distinct scenario representations.
LOTTIE_BATTERY_BLUE = "https://gist.githubusercontent.com/mattjfrancis/fd5565871a89962622e010066edc6d08/raw/06ab8da96b907ec06cc060c0e6f3a4ef6fa4db71/battery.json" # Generic blue battery
LOTTIE_BATTERY_GREEN = "https://assets1.lottiefiles.com/packages/lf20_yM5N5p.json" # Generic green battery
LOTTIE_BATTERY_RED = "https://assets1.lottiefiles.com/packages/lf20_7j2qZH.json"   # Generic red battery

# --- Country code mappings ---
# Map country codes to full names
country_code_to_name = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DK": "Denmark",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
    "NO": "Norway",
    "CH": "Switzerland",
    "UK": "United Kingdom"
}

# Reverse mapping from full names to country codes
name_to_country_code = {v: k for k, v in country_code_to_name.items()}

# Map country codes to Excel column names
country_code_to_excel_col = {
    "AT": "Austria Price (EUR/MWhe)",
    "BE": "Belgium Price (EUR/MWhe)",
    "CZ": "Czechia Price (EUR/MWhe)",
    "DE": "Germany Price (EUR/MWhe)",
    "DK": "Denmark Price (EUR/MWhe)",
    "ES": "Spain Price (EUR/MWhe)",
    "FI": "Finland Price (EUR/MWhe)",
    "FR": "France Price (EUR/MWhe)",
    "HU": "Hungary Price (EUR/MWhe)",
    "IT": "Italy Price (EUR/MWhe)",
    "NL": "Netherlands Price (EUR/MWhe)",
    "NO": "Norway Price (EUR/MWhe)",
    "PL": "Poland Price (EUR/MWhe)",
    "PT": "Portugal Price (EUR/MWhe)",
    "SE": "Sweden Price (EUR/MWhe)",
    "CH": "Switzerland Price (EUR/MWhe)",
    "RO": "Romania Price (EUR/MWhe)"
    # Add more mappings as needed
}

# --- Placeholder for API Integration (if needed) ---
# class EnergyAPIs:
#     # ... (existing API integration code)
#     pass

# --- Scenario Definitions ---
SCENARIOS = {
    "REF": {
        "label": "Reference",
        "full_label": "Reference (Business-as-usual)",
        "price_multiplier": 1.0,
        "volatility": 0.0,
        "volatility_floor": 0.0,
        "activated_multiplier": 1.0,
        "co2_drop": 0.0,  # %/yr
        "description": "Standard market conditions with current volatility and price trends.",
        "color": "#007bff", # Blue
        "lottie_url": LOTTIE_BATTERY_BLUE
    },
    "NZ2050": {
        "label": "Net-Zero",
        "full_label": "Net-Zero 2050 Pathway",
        "price_multiplier": 1.15,
        "volatility": 0.05, # Small increase in volatility
        "volatility_floor": 10.0,
        "activated_multiplier": 1.15,
        "co2_drop": 0.02,  # -2%/yr, more aggressive
        "description": "Transition to net-zero emissions, 15% higher prices, increased activations, and steady CO2 reduction.",
        "color": "#28a745", # Green
        "lottie_url": LOTTIE_BATTERY_BLUE
    },
    "HOT": {
        "label": "Extreme",
        "full_label": "Extreme-climate (High Volatility)",
        "price_multiplier": 1.25,
        "volatility": 0.20,  # 20% volatility
        "volatility_floor": 30.0,  # €/MWh
        "activated_multiplier": 1.25,
        "co2_drop": 0.005, # Slower CO2 reduction due to challenges
        "description": "High volatility scenario with 25% higher prices/activations and significant market fluctuations.",
        "color": "#dc3545", # Red
        "lottie_url": LOTTIE_BATTERY_BLUE
    },
}

# --- Main App Layout ---
st.title("🔥 Brenmiller Thermal Storage Simulator v4.0")

# --- Scenario Selector UI ---
if 'scenario' not in st.session_state:
    st.session_state.scenario = "REF" # Default scenario

if EXTRAS_AVAILABLE:
    colored_header(
        label="Select Future Scenario",
        description="Hover for details, click to select.",
        color_name="blue-70"
    )
else:
    st.subheader("Select Future Scenario")
    st.caption("Hover for details, click to select.")

scenario_cols = st.columns(len(SCENARIOS))
for i, (key, props) in enumerate(SCENARIOS.items()):
    with scenario_cols[i]:
        container = st.container()
        # Add a unique key for the button if needed, but Streamlit handles it well in columns
        # The clickability comes from the button inside the container
        
        tooltip_html = f""
        tooltip_html += f"<b>{props['full_label']}</b><br>"
        tooltip_html += f"Price Multiplier: {props['price_multiplier']:.2f}x<br>"
        tooltip_html += f"Volatility: {props['volatility']*100:.0f}%<br>"
        tooltip_html += f"CO₂ Drop: {props['co2_drop']*100:.1f}%/yr"
        
        container.markdown(f"""
        <div class="tooltip text-center" style="width:100%;">
            <h5 style="color:{props['color']}; margin-bottom:0.5rem;">{props['label']}</h5>
            <span class="tooltiptext">{tooltip_html}</span>
        </div>
        """, unsafe_allow_html=True)

        if LOTTIE_AVAILABLE:
            lottie_animation = load_lottie_url(props['lottie_url'])
            if lottie_animation:
                with container:
                    st_lottie(lottie_animation, height=100, key=f"lottie_{key}")
            else:
                container.markdown(f"<div style='height:100px; display:flex; align-items:center; justify-content:center; background-color:{props['color']}20; border-radius:8px;'><p style='color:{props['color']};'>Animation N/A</p></div>", unsafe_allow_html=True)
        else:
            container.markdown(f"<div style='height:100px; display:flex; align-items:center; justify-content:center; background-color:{props['color']}20; border-radius:8px;'><h4 style='color:{props['color']};'>{props['label']}</h4></div>", unsafe_allow_html=True)
        
        if container.button(f"Select {props['label']}", key=f"btn_{key}", use_container_width=True):
            st.session_state.scenario = key
            # No rerun here, will rerun when parameters change or simulation is triggered

# Display currently selected scenario details
current_scenario_props = SCENARIOS[st.session_state.scenario]
st.markdown(f"""
<div class="p-4 mb-6" style="background-color: {current_scenario_props['color']}1A; border-left: 5px solid {current_scenario_props['color']}; border-radius: 5px;">
    <h4 style="color: {current_scenario_props['color']}; margin-bottom: 0.25rem;">Selected Scenario: {current_scenario_props['full_label']}</h4>
    <p style="margin-bottom: 0;">{current_scenario_props['description']}</p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar for Simulation Parameters ---
st.sidebar.header("⚙️ Simulation Parameters")
with st.sidebar:
    with st.spinner("Loading parameters..."):
        cap_kwh = st.number_input("Battery Capacity (kWh)", min_value=100, max_value=100000, value=5000, step=100, help="Total energy storage capacity of the bGen unit.")
        capex_kwh = st.number_input("CAPEX (€/kWh)", min_value=50, max_value=1000, value=350, step=10, help="Capital expenditure per kWh of storage.")
        opex_pct = st.number_input("Annual OPEX (% of CAPEX)", min_value=0.0, max_value=10.0, value=2.0, step=0.1, help="Annual operational expenditure as a percentage of total CAPEX.")
        life_yrs = st.number_input("Project Life (years)", min_value=5, max_value=30, value=20, step=1, help="Expected operational lifetime of the project.")
        disc_pct = st.number_input("Discount Rate (%)", min_value=0.0, max_value=20.0, value=7.5, step=0.1, help="Rate used for discounting future cash flows.")
        haas_eur_mwh = st.number_input("HaaS Fee (€/MWh)", min_value=0, max_value=200, value=60, step=5, help="Heat-as-a-Service fee charged per MWh of energy delivered.")

# --- Placeholder for Data Loading and Simulation Logic ---
# This will be filled in with the existing logic, adapted for the new structure
@st.cache_data(ttl=3600) # Cache for 1 hour
def load_country_data(selected_countries):
    """Load actual data from Excel files for the selected countries."""
    all_data = {}
    
    try:
        # Load down-regulation prices and activation data
        down_prices_df, activated_df = load_downreg_excel("data/down_prices.xlsx")
        
        # Load day-ahead prices
        day_ahead_prices = load_day_ahead_prices("data/price_data.xlsx")
        
        # Process data for each selected country
        for country in selected_countries:
            country_code = name_to_country_code.get(country, country)
            
            # Check if we have data for this country
            if country_code not in down_prices_df.columns and country_code not in day_ahead_prices.columns:
                st.warning(f"No data available for {country} ({country_code}). Using synthetic data.")
                # Generate synthetic data as fallback
                base_dates = pd.date_range(start='2022-01-01', periods=8760, freq='H')
                data = pd.DataFrame(index=base_dates)
                data['price'] = np.random.uniform(30, 150, size=len(base_dates)) + (np.sin(np.linspace(0, 10*np.pi, len(base_dates))) * 20)
                data['activated'] = np.random.choice([0, 100, 200], size=len(base_dates), p=[0.95, 0.03, 0.02])
                all_data[country] = data
                continue
            
            # Create DataFrame for this country
            data = pd.DataFrame()
            
            # Add price data if available
            if country_code in day_ahead_prices.columns:
                data['price'] = day_ahead_prices[country_code]
            elif country_code in down_prices_df.columns:
                data['price'] = down_prices_df[country_code]
            else:
                # Fallback to synthetic price data
                data['price'] = np.random.uniform(30, 150, size=len(down_prices_df))
            
            # Add activation data if available
            if country_code in activated_df.columns:
                data['activated'] = activated_df[country_code]
            else:
                # Fallback to synthetic activation data (mostly zeros with occasional activations)
                data['activated'] = np.zeros(len(data))
                # Add some random activations (3% of the time)
                random_indices = np.random.choice(len(data), size=int(len(data) * 0.03), replace=False)
                data.loc[data.index[random_indices], 'activated'] = np.random.choice([100, 200], size=len(random_indices))
            
            # Apply scenario transformations based on the selected scenario
            # (This will be handled by the simulation function)
            
            all_data[country] = data
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        # Provide synthetic data as fallback
        base_dates = pd.date_range(start='2022-01-01', periods=8760, freq='H')
        for country in selected_countries:
            data = pd.DataFrame(index=base_dates)
            data['price'] = np.random.uniform(30, 150, size=len(base_dates)) + (np.sin(np.linspace(0, 10*np.pi, len(base_dates))) * 20)
            data['activated'] = np.random.choice([0, 100, 200], size=len(base_dates), p=[0.95, 0.03, 0.02])
            all_data[country] = data
    
    return all_data

# Helper functions for data loading
def load_downreg_excel(path):
    """Return (prices_df, activated_df) with UTC DatetimeIndex."""
    try:
        # Read the Excel file with first row as header
        raw = pd.read_excel(path, header=0)
        
        # Extract date and time columns (assuming they're the first two columns)
        date_col, time_col = raw.columns[:2]
        
        # Build timestamp
        ts = pd.to_datetime(
            raw[date_col].astype(str) + " " + raw[time_col].astype(str),
            errors="coerce",
        )
        raw.drop(columns=[date_col, time_col], inplace=True)

        # Filter out rows with invalid timestamps
        raw = raw.loc[ts.notna()].copy()
        ts = ts.loc[ts.notna()]
        
        # Handle timezone
        ts = ts.dt.tz_localize(
            "Europe/Paris",
            ambiguous='NaT',
            nonexistent='shift_forward'
        ).dt.tz_convert("UTC")
        
        # Set index
        raw.index = ts
        
        # Convert columns to strings and get unique column names
        raw.columns = raw.columns.astype(str)
        unique_cols = raw.columns.unique()
        
        # Split into prices and activated dataframes
        # Prices columns end with "Down Prices"
        price_cols = [str(c) for c in unique_cols if str(c).endswith("Down Prices")]
        # Activated columns end with "Down" but not "Down Prices"
        act_cols = [str(c) for c in unique_cols if str(c).endswith("Down") and not str(c).endswith("Down Prices")]
        
        if not price_cols:
            st.warning("No price columns found in down_prices.xlsx – please check the Excel header names.")
            return pd.DataFrame(), pd.DataFrame()

        # Create price and activated dataframes
        prices = raw[price_cols].astype(float).copy()
        activated = raw[act_cols].astype(float).copy() if act_cols else pd.DataFrame(index=prices.index)
        
        # Clean column names to extract just the country code
        def _clean(name):
            # Extract country code from column name (e.g., "AT Down Prices" → "AT")
            return str(name).split()[0] if str(name) else ""
        
        # Clean the column names
        prices.columns = [_clean(c) for c in prices.columns]
        activated.columns = [_clean(c) for c in activated.columns]
        
        return prices, activated
    
    except Exception as e:
        st.error(f"Error loading down-regulation data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

def load_day_ahead_prices(path):
    """Load day-ahead prices from Excel file."""
    try:
        if not os.path.exists(path):
            st.warning(f"Price data file not found: {path}")
            return pd.DataFrame()
            
        df = pd.read_excel(path, header=0, index_col=0, parse_dates=True)
        
        # Strip column names and index
        df.columns = df.columns.str.strip()
        if isinstance(df.index, pd.Index):
            df.index = df.index.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        # Drop duplicate index entries
        if df.index.duplicated().any():
            df = df[~df.index.duplicated(keep='first')]
        
        # Map column names to country codes
        country_data = {}
        for country_code, excel_col in country_code_to_excel_col.items():
            if excel_col in df.columns:
                country_data[country_code] = df[excel_col]
        
        # Create a new DataFrame with country codes as columns
        result = pd.DataFrame(country_data)
        
        # Ensure index is datetime and sorted
        if not isinstance(result.index, pd.DatetimeIndex):
            result.index = pd.to_datetime(result.index)
        result.sort_index(inplace=True)
        
        return result
    
    except Exception as e:
        st.error(f"Error loading day-ahead prices: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_price_projections():
    """Load or generate price projections for different scenarios."""
    try:
        # Check if we have a projections file
        if os.path.exists("data/price_projections.xlsx"):
            df = pd.read_excel("data/price_projections.xlsx", index_col=0, parse_dates=True)
            return df
    except Exception as e:
        st.warning(f"Error loading price projections: {str(e)}. Using generated projections.")
    
    # Generate projections if file doesn't exist or had an error
    years = pd.date_range(start='2023-01-01', end='2050-12-31', freq='A')
    df = pd.DataFrame(index=years)
    
    # Base prices from current average
    base_price = 60  # Default base price if we can't calculate from data
    
    try:
        # Try to get actual average price from day-ahead data
        day_ahead_prices = load_day_ahead_prices("data/price_data.xlsx")
        if not day_ahead_prices.empty:
            base_price = day_ahead_prices.mean().mean()  # Average across all countries
    except:
        pass  # Use default if there's an error
    
    # Create projections for each scenario with different growth rates
    df['REF_Price'] = base_price * (1 + 0.01 * (df.index.year - 2023))  # 1% annual growth
    df['NZ2050_Price'] = base_price * 1.15 * (1 + 0.015 * (df.index.year - 2023))  # 1.5% annual growth, 15% higher baseline
    df['HOT_Price'] = base_price * 1.25 * (1 + 0.02 * (df.index.year - 2023))  # 2% annual growth, 25% higher baseline
    
    return df

# --- Simulation Function (Simplified Placeholder) ---
@st.cache_data(ttl=3600)
def simulate(capacity_kwh, _scenario_params, _country_data):
    # This function will perform the core simulation and NPV calculations.
    # For now, returning dummy NPV results with component breakdown.
    npv_results_detailed = {}
    for country_name in _country_data.keys():
        npv_results_detailed[country_name] = {}
        for model_name in ["Standalone", "HaaS", "Grid Balancing"]:
            # Dummy component calculations
            base_revenue = np.random.uniform(5e6, 15e6)
            base_energy_cost = np.random.uniform(2e6, 7e6)
            base_op_cost = np.random.uniform(0.5e6, 2e6)

            # Apply scenario multipliers (simplified)
            revenue = base_revenue * _scenario_params['price_multiplier']
            energy_cost = base_energy_cost * _scenario_params['price_multiplier'] # Assuming energy cost scales with price
            op_cost = base_op_cost # Assuming op_cost is less scenario-dependent for this dummy version
            
            # Adjust for model type (very simplified)
            if model_name == "HaaS":
                revenue *= 1.1
                op_cost *= 1.2
            elif model_name == "Grid Balancing":
                revenue *= (1.2 + _scenario_params['volatility'])
                energy_cost *= (1.1 + _scenario_params['volatility'] / 2)
                op_cost *= 1.1

            npv = revenue - energy_cost - op_cost

            npv_results_detailed[country_name][model_name] = {
                "NPV": npv,
                "TotalRevenue": revenue,
                "TotalEnergyCost": energy_cost,
                "TotalOpCost": op_cost,
                # "OtherMetrics": {} # Placeholder for future
            }
    return npv_results_detailed

# --- Visualization Functions (Placeholders - to be implemented next) ---
def create_npv_comparison_chart(summary_df, scenario_props):
    st.write("NPV Comparison Chart Placeholder")
    # fig = ... (Plotly code)
    # return fig
    return go.Figure()

def create_price_projection_chart(projection_df, current_scenario_props):
    fig = go.Figure()
    
    # Add traces for each scenario's price projection
    if 'REF_Price' in projection_df.columns:
        fig.add_trace(go.Scatter(x=projection_df.index, y=projection_df['REF_Price'], 
                                 mode='lines+markers', name='Reference Scenario', 
                                 line=dict(color=SCENARIOS['REF']['color'])))
    if 'NZ2050_Price' in projection_df.columns:
        fig.add_trace(go.Scatter(x=projection_df.index, y=projection_df['NZ2050_Price'], 
                                 mode='lines+markers', name='Net-Zero 2050 Scenario', 
                                 line=dict(color=SCENARIOS['NZ2050']['color'])))
    if 'HOT_Price' in projection_df.columns:
        fig.add_trace(go.Scatter(x=projection_df.index, y=projection_df['HOT_Price'], 
                                 mode='lines+markers', name='Extreme Scenario', 
                                 line=dict(color=SCENARIOS['HOT']['color'])))

    fig.update_layout(
        title_text=f"Future Price Projections (€/MWh) - Current: {current_scenario_props['label']}",
        xaxis_title="Year",
        yaxis_title="Price (€/MWh)",
        legend_title="Scenarios",
        hovermode="x unified"
    )
    return fig

def create_strategy_map_chart(npv_results, scenario_props):
    """Create a map of Europe showing the optimal business model for each country."""
    # European country coordinates (approximate centers)
    country_coords = {
        "AT": [47.5162, 14.5501],  # Austria
        "BE": [50.8503, 4.3517],   # Belgium
        "BG": [42.7339, 25.4858],  # Bulgaria
        "HR": [45.1000, 15.2000],  # Croatia
        "CY": [35.1264, 33.4299],  # Cyprus
        "CZ": [49.8175, 15.4730],  # Czech Republic
        "DK": [56.2639, 9.5018],   # Denmark
        "EE": [58.5953, 25.0136],  # Estonia
        "FI": [61.9241, 25.7482],  # Finland
        "FR": [46.6034, 1.8883],   # France
        "DE": [51.1657, 10.4515],  # Germany
        "GR": [39.0742, 21.8243],  # Greece
        "HU": [47.1625, 19.5033],  # Hungary
        "IE": [53.1424, -7.6921],  # Ireland
        "IT": [41.8719, 12.5674],  # Italy
        "LV": [56.8796, 24.6032],  # Latvia
        "LT": [55.1694, 23.8813],  # Lithuania
        "LU": [49.8153, 6.1296],   # Luxembourg
        "MT": [35.9375, 14.3754],  # Malta
        "NL": [52.1326, 5.2913],   # Netherlands
        "PL": [51.9194, 19.1451],  # Poland
        "PT": [39.3999, -8.2245],  # Portugal
        "RO": [45.9432, 24.9668],  # Romania
        "SK": [48.6690, 19.6990],  # Slovakia
        "SI": [46.1512, 14.9955],  # Slovenia
        "ES": [40.4637, -3.7492],  # Spain
        "SE": [60.1282, 18.6435],  # Sweden
        "NO": [60.4720, 8.4689],   # Norway
        "CH": [46.8182, 8.2275],   # Switzerland
        "UK": [55.3781, -3.4360]   # United Kingdom
    }
    
    # Map full country names to codes (for lookup)
    country_name_to_code = {
        "Austria": "AT",
        "Belgium": "BE",
        "Bulgaria": "BG",
        "Croatia": "HR",
        "Cyprus": "CY",
        "Czech Republic": "CZ",
        "Denmark": "DK",
        "Estonia": "EE",
        "Finland": "FI",
        "France": "FR",
        "Germany": "DE",
        "Greece": "GR",
        "Hungary": "HU",
        "Ireland": "IE",
        "Italy": "IT",
        "Latvia": "LV",
        "Lithuania": "LT",
        "Luxembourg": "LU",
        "Malta": "MT",
        "Netherlands": "NL",
        "Poland": "PL",
        "Portugal": "PT",
        "Romania": "RO",
        "Slovakia": "SK",
        "Slovenia": "SI",
        "Spain": "ES",
        "Sweden": "SE",
        "Norway": "NO",
        "Switzerland": "CH",
        "United Kingdom": "UK"
    }
    
    # Determine the best business model for each country based on NPV
    best_model_data = []
    for country, models in npv_results.items():
        if not models:  # Skip if no models data
            continue
            
        # Find the model with highest NPV
        best_model = max(models.items(), key=lambda x: x[1]['NPV'] if isinstance(x[1], dict) else x[1])
        model_name = best_model[0]
        npv_value = best_model[1]['NPV'] if isinstance(best_model[1], dict) else best_model[1]
        
        # Get all model NPVs for hover info
        all_model_npvs = {}
        for model, data in models.items():
            model_npv = data['NPV'] if isinstance(data, dict) else data
            all_model_npvs[model] = f"€{model_npv/1e6:.2f}M"
        
        # Format for hover text
        hover_text = f"<b>{country}</b><br>"
        hover_text += f"Best Model: <b>{model_name}</b><br>"
        hover_text += f"NPV: €{npv_value/1e6:.2f}M<br><br>"
        hover_text += "<u>All Models:</u><br>"
        for model, npv_str in all_model_npvs.items():
            hover_text += f"{model}: {npv_str}<br>"
        
        # Map business models to colors
        model_colors = {
            "Standalone": "#4E79A7",  # Blue
            "HaaS": "#59A14F",       # Green
            "Grid Balancing": "#F28E2B"  # Orange
        }
        
        # Get country code and coordinates
        country_code = country_name_to_code.get(country, country)  # Try to get code, fallback to name
        coords = country_coords.get(country_code, None)
        
        if coords:  # Only add if we have coordinates
            best_model_data.append({
                "Country": country,
                "Best Model": model_name,
                "NPV": npv_value,
                "Color": model_colors.get(model_name, "#CCCCCC"),  # Default gray if model not found
                "Lat": coords[0],
                "Lon": coords[1],
                "HoverText": hover_text,
                "MarkerSize": np.log10(npv_value) * 5  # Size based on NPV (logarithmic scale)
            })
    
    # Create DataFrame
    best_model_df = pd.DataFrame(best_model_data)
    
    if best_model_df.empty:
        # Return empty figure if no data
        fig = go.Figure()
        fig.update_layout(title="No data available for map visualization")
        return fig
    
    # Create map
    fig = go.Figure()
    
    # Add country markers by model type
    for model in ["Standalone", "HaaS", "Grid Balancing"]:
        model_data = best_model_df[best_model_df["Best Model"] == model]
        if not model_data.empty:
            fig.add_trace(go.Scattergeo(
                lon=model_data["Lon"],
                lat=model_data["Lat"],
                text=model_data["HoverText"],
                hoverinfo="text",
                mode="markers",
                name=model,
                marker=dict(
                    size=model_data["MarkerSize"],
                    color=model_data["Color"],
                    line=dict(width=1, color="white"),
                    sizemode="diameter",
                    sizemin=10
                ),
            ))
    
    # Add country labels
    fig.add_trace(go.Scattergeo(
        lon=best_model_df["Lon"],
        lat=best_model_df["Lat"],
        text=best_model_df["Country"],
        mode="text",
        textfont=dict(color="black", size=9),
        showlegend=False
    ))
    
    # Update layout
    fig.update_layout(
        title=f"Optimal Business Model by Country - {scenario_props['full_label']} Scenario",
        geo=dict(
            scope="europe",
            showland=True,
            landcolor="rgb(240, 240, 240)",
            countrycolor="rgb(180, 180, 180)",
            coastlinecolor="rgb(180, 180, 180)",
            projection_type="natural earth",
            showcoastlines=True,
            showcountries=True,
            showframe=False,
            resolution=50,
            lonaxis=dict(range=[-15, 35]),
            lataxis=dict(range=[35, 70])
        ),
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    return fig

def create_battery_animation_chart(country_name, country_data, capacity_kwh, scenario_props):
    """Create an interactive animation showing thermal storage charging/discharging and grid balancing."""
    if country_data is None or country_data.empty:
        # Create a default empty figure or return None
        fig = go.Figure()
        fig.update_layout(title=f"No data for {country_name} - {scenario_props['label']}", title_x=0.5)
        return fig
    
    # Create a battery state of charge simulation
    # Initialize battery at 50% charge
    battery_capacity = capacity_kwh
    initial_charge = battery_capacity * 0.5
    
    # Create arrays to store battery state
    timestamps = country_data.index.tolist()
    battery_soc = [initial_charge]  # State of Charge in kWh
    battery_pct = [50]  # State of Charge in percentage
    charging = [0]  # Charging status (1=charging, -1=discharging, 0=idle)
    
    # Simulation parameters
    charge_rate = battery_capacity * 0.2  # Can charge at 20% of capacity per hour
    discharge_rate = battery_capacity * 0.3  # Can discharge at 30% of capacity per hour
    
    # Price thresholds for charge/discharge decisions - dynamic based on percentiles
    low_price_threshold = country_data['price'].quantile(0.3)
    high_price_threshold = country_data['price'].quantile(0.7)
    
    # Apply scenario volatility to thresholds
    threshold_spread = high_price_threshold - low_price_threshold
    volatility_factor = 1 + scenario_props.get('volatility', 0)
    low_price_threshold -= threshold_spread * 0.1 * volatility_factor
    high_price_threshold += threshold_spread * 0.1 * volatility_factor
    
    # Simulate battery operation
    current_charge = initial_charge
    
    # Add more detailed simulation data for animation
    energy_flow = [0]  # Energy flow rate (positive=charging, negative=discharging)
    grid_power = [0]  # Power from/to grid
    temperature = [50]  # Simulated temperature of thermal storage (°C)
    efficiency = [95]  # System efficiency (%)
    
    # Temperature range for thermal storage
    min_temp = 30
    max_temp = 95
    
    for i in range(1, len(country_data)):
        price = country_data['price'].iloc[i]
        is_activated = country_data['activated'].iloc[i] > 0
        
        # Determine charging action
        action = 0  # Default: idle
        flow = 0
        grid = 0
        
        # Grid activation takes precedence - discharge if activated
        if is_activated and current_charge > battery_capacity * 0.1:
            action = -1  # Discharge
            discharge_amount = min(discharge_rate, current_charge - battery_capacity * 0.1)
            current_charge -= discharge_amount
            flow = -discharge_amount
            grid = discharge_amount * 0.9  # Some losses in conversion
        # If price is low and battery not full, charge
        elif price < low_price_threshold and current_charge < battery_capacity * 0.95:
            action = 1  # Charge
            charge_amount = min(charge_rate, battery_capacity * 0.95 - current_charge)
            current_charge += charge_amount
            flow = charge_amount
            grid = -charge_amount / 0.95  # Some losses in conversion
        # If price is high and battery has charge, discharge
        elif price > high_price_threshold and current_charge > battery_capacity * 0.2:
            action = -1  # Discharge
            discharge_amount = min(discharge_rate, current_charge - battery_capacity * 0.2)
            current_charge -= discharge_amount
            flow = -discharge_amount
            grid = discharge_amount * 0.9  # Some losses in conversion
        
        # Calculate simulated temperature based on charge level
        # Higher charge = higher temperature in thermal storage
        current_temp = min_temp + ((current_charge / battery_capacity) * (max_temp - min_temp))
        
        # Calculate efficiency - higher at mid-range temperatures
        current_efficiency = 85 + 10 * (1 - abs((current_temp - ((max_temp + min_temp) / 2)) / ((max_temp - min_temp) / 2)))
        
        # Add to arrays
        battery_soc.append(current_charge)
        battery_pct.append((current_charge / battery_capacity) * 100)
        charging.append(action)
        energy_flow.append(flow)
        grid_power.append(grid)
        temperature.append(current_temp)
        efficiency.append(current_efficiency)
    
    # Create dataframe for plotting
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': country_data['price'].values,
        'activated': country_data['activated'].values,
        'battery_soc': battery_soc,
        'battery_pct': battery_pct,
        'charging': charging,
        'energy_flow': energy_flow,
        'grid_power': grid_power,
        'temperature': temperature,
        'efficiency': efficiency
    })
    
    # Add a time index column for animation frames
    df['time_idx'] = range(len(df))
    
    # Create a subset of data points for animation frames (every 24 hours)
    # This makes the animation more manageable
    frame_indices = list(range(0, len(df), 24))
    if frame_indices[-1] != len(df) - 1:
        frame_indices.append(len(df) - 1)  # Add the last point
    
    # Create figure with subplots
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            f"Thermal Storage Operation - {country_name} ({scenario_props['label']} Scenario)",
            "Energy Flow & Temperature",
            "Energy Price & Grid Activation Events"
        ),
        row_heights=[0.4, 0.3, 0.3]
    )
    
    # Create color scale for temperature visualization
    colorscale = [
        [0, 'blue'],
        [0.5, 'yellow'],
        [1, 'red']
    ]
    
    # Add battery state of charge with color based on temperature
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['battery_pct'],
            name="Charge Level (%)",
            line=dict(width=4, color='#3366CC'),
            hovertemplate="<b>Time</b>: %{x}<br><b>Charge</b>: %{y:.1f}%<br><extra></extra>"
        ),
        row=1, col=1
    )
    
    # Add a filled area under the battery charge line
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['battery_pct'],
            name="Charge Area",
            fill='tozeroy',
            mode='none',
            fillcolor='rgba(51, 102, 204, 0.2)',
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )
    
    # Add temperature visualization
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['temperature'],
            name="Temperature (°C)",
            line=dict(color='#FF9900', width=2),
            hovertemplate="<b>Time</b>: %{x}<br><b>Temp</b>: %{y:.1f}°C<br><extra></extra>"
        ),
        row=2, col=1
    )
    
    # Add efficiency visualization
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['efficiency'],
            name="Efficiency (%)",
            line=dict(color='#109618', width=2, dash='dot'),
            hovertemplate="<b>Time</b>: %{x}<br><b>Efficiency</b>: %{y:.1f}%<br><extra></extra>"
        ),
        row=2, col=1
    )
    
    # Add energy flow visualization (positive=charging, negative=discharging)
    energy_flow_colors = ['#00CC96' if flow >= 0 else '#EF553B' for flow in df['energy_flow']]
    
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['energy_flow'],
            name="Energy Flow (kWh)",
            marker_color=energy_flow_colors,
            hovertemplate="<b>Time</b>: %{x}<br><b>Energy Flow</b>: %{y:.1f} kWh<br><extra></extra>"
        ),
        row=2, col=1
    )
    
    # Add energy price
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['price'],
            name="Energy Price (€/MWh)",
            line=dict(color='#AB63FA', width=2),
            hovertemplate="<b>Time</b>: %{x}<br><b>Price</b>: %{y:.2f} €/MWh<br><extra></extra>"
        ),
        row=3, col=1
    )
    
    # Add grid activation events
    activation_df = df[df['activated'] > 0]
    fig.add_trace(
        go.Scatter(
            x=activation_df['timestamp'],
            y=activation_df['price'],
            mode='markers',
            marker=dict(
                symbol='star',
                size=12,
                color='#FFA15A',
                line=dict(width=1, color='#FFA15A')
            ),
            name="Grid Activation",
            hovertemplate="<b>Grid Activation</b><br>Time: %{x}<br>Price: %{y:.2f} €/MWh<br><extra></extra>"
        ),
        row=3, col=1
    )
    
    # Add price thresholds
    fig.add_shape(
        type="line",
        x0=df['timestamp'].iloc[0],
        y0=low_price_threshold,
        x1=df['timestamp'].iloc[-1],
        y1=low_price_threshold,
        line=dict(color="#00CC96", width=1, dash="dash"),
        row=3, col=1
    )
    
    fig.add_shape(
        type="line",
        x0=df['timestamp'].iloc[0],
        y0=high_price_threshold,
        x1=df['timestamp'].iloc[-1],
        y1=high_price_threshold,
        line=dict(color="#EF553B", width=1, dash="dash"),
        row=3, col=1
    )
    
    # Create animation frames
    frames = []
    for idx in frame_indices:
        # Get data up to this point for the animation
        frame_df = df[df['time_idx'] <= idx]
        
        # Create a frame with all traces
        frame = go.Frame(
            data=[
                # Battery charge trace
                go.Scatter(
                    x=frame_df['timestamp'],
                    y=frame_df['battery_pct'],
                    line=dict(width=4, color='#3366CC')
                ),
                # Battery fill area
                go.Scatter(
                    x=frame_df['timestamp'],
                    y=frame_df['battery_pct'],
                    fill='tozeroy',
                    mode='none',
                    fillcolor='rgba(51, 102, 204, 0.2)'
                ),
                # Temperature trace
                go.Scatter(
                    x=frame_df['timestamp'],
                    y=frame_df['temperature'],
                    line=dict(color='#FF9900', width=2)
                ),
                # Efficiency trace
                go.Scatter(
                    x=frame_df['timestamp'],
                    y=frame_df['efficiency'],
                    line=dict(color='#109618', width=2, dash='dot')
                ),
                # Energy flow bars
                go.Bar(
                    x=frame_df['timestamp'],
                    y=frame_df['energy_flow'],
                    marker_color=[energy_flow_colors[i] for i in frame_df['time_idx']]
                ),
                # Energy price trace
                go.Scatter(
                    x=frame_df['timestamp'],
                    y=frame_df['price'],
                    line=dict(color='#AB63FA', width=2)
                ),
                # Grid activation events
                go.Scatter(
                    x=activation_df[activation_df['time_idx'] <= idx]['timestamp'],
                    y=activation_df[activation_df['time_idx'] <= idx]['price'],
                    mode='markers',
                    marker=dict(
                        symbol='star',
                        size=12,
                        color='#FFA15A',
                        line=dict(width=1, color='#FFA15A')
                    )
                )
            ],
            name=str(idx)
        )
        frames.append(frame)
    
    # Add frames to the figure
    fig.frames = frames
    
    # Add slider and play button for animation
    sliders = [
        dict(
            active=0,
            yanchor="top",
            xanchor="left",
            currentvalue=dict(
                font=dict(size=12),
                prefix="Date: ",
                visible=True,
                xanchor="right"
            ),
            transition=dict(duration=300, easing="cubic-in-out"),
            pad=dict(b=10, t=50),
            len=0.9,
            x=0.1,
            y=0,
            steps=[dict(
                method="animate",
                args=[
                    [str(idx)],
                    dict(
                        frame=dict(duration=300, redraw=True),
                        mode="immediate",
                        transition=dict(duration=300)
                    )
                ],
                label=df['timestamp'][idx].strftime("%b %d")
            ) for idx in frame_indices]
        )
    ]
    
    # Update layout
    fig.update_layout(
        height=800,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=80, b=80),
        hovermode="x unified",
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[
                            None,
                            dict(
                                frame=dict(duration=300, redraw=True),
                                fromcurrent=True,
                                mode="immediate",
                                transition=dict(duration=300)
                            )
                        ],
                        label="▶ Play",
                        method="animate"
                    ),
                    dict(
                        args=[
                            [None],
                            dict(
                                frame=dict(duration=0, redraw=True),
                                mode="immediate",
                                transition=dict(duration=0)
                            )
                        ],
                        label="⏸ Pause",
                        method="animate"
                    )
                ],
                pad=dict(r=10, t=10),
                showactive=False,
                x=0.1,
                xanchor="right",
                y=0,
                yanchor="top"
            )
        ],
        sliders=sliders,
        xaxis3=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(step="all")
                ])
            )
        )
    )
    
    # Update y-axes
    fig.update_yaxes(title_text="Charge Level (%)", range=[0, 105], row=1, col=1)
    fig.update_yaxes(title_text="Energy Flow / Temperature", row=2, col=1)
    fig.update_yaxes(title_text="Price (€/MWh)", row=3, col=1)
    
    # Add annotations for price thresholds
    fig.add_annotation(
        x=df['timestamp'].iloc[10],
        y=low_price_threshold,
        text="Charge Threshold",
        showarrow=True,
        arrowhead=1,
        ax=50,
        ay=-30,
        row=3, col=1
    )
    
    fig.add_annotation(
        x=df['timestamp'].iloc[10],
        y=high_price_threshold,
        text="Discharge Threshold",
        showarrow=True,
        arrowhead=1,
        ax=50,
        ay=30,
        row=3, col=1
    )
    
    # Add current status indicators as annotations
    latest_charge = df['battery_pct'].iloc[-1]
    latest_temp = df['temperature'].iloc[-1]
    latest_efficiency = df['efficiency'].iloc[-1]
    
    # Add a battery icon and status display
    battery_icon = "🔋" if latest_charge > 50 else "🪫"
    temp_icon = "🔥" if latest_temp > 70 else "🌡️"
    
    fig.add_annotation(
        x=0.02,
        y=0.98,
        xref="paper",
        yref="paper",
        text=f"<b>{battery_icon} Current Status:</b><br>Charge: {latest_charge:.1f}%<br>{temp_icon} Temp: {latest_temp:.1f}°C<br>Efficiency: {latest_efficiency:.1f}%",
        showarrow=False,
        font=dict(size=14),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="#3366CC",
        borderwidth=2,
        borderpad=4,
        opacity=0.8
    )
    
    return fig

def create_24h_battery_animation(country_name, country_data, capacity_kwh, scenario_props):
    """Create a detailed 24-hour animation of battery charging/discharging and grid regulation."""
    if country_data is None or country_data.empty:
        # Create a default empty figure if no data
        fig = go.Figure()
        fig.update_layout(title=f"No data for {country_name}", title_x=0.5)
        return fig
    
    # Extract a 24-hour period (use a period with some grid activations if possible)
    # Find a day with at least one grid activation if possible
    has_activation = (country_data['activated'] > 0).groupby(country_data.index.date).sum() > 0
    if has_activation.any():
        # Get the first date with activations
        activation_date = has_activation[has_activation].index[0]
        start_time = pd.Timestamp(activation_date)
    else:
        # If no activations, just use the first day
        start_time = country_data.index[0].floor('D')
    
    end_time = start_time + pd.Timedelta(days=1)
    
    # Filter data for the 24-hour period
    mask = (country_data.index >= start_time) & (country_data.index < end_time)
    day_data = country_data[mask].copy()
    
    if day_data.empty:
        fig = go.Figure()
        fig.update_layout(title=f"No data for {country_name} on {start_time.date()}", title_x=0.5)
        return fig
    
    # Create a battery state of charge simulation
    # Initialize battery at 50% charge
    battery_capacity = capacity_kwh
    initial_charge = battery_capacity * 0.5
    
    # Simulation parameters
    charge_rate = battery_capacity * 0.2  # Can charge at 20% of capacity per hour
    discharge_rate = battery_capacity * 0.3  # Can discharge at 30% of capacity per hour
    
    # Create arrays to store battery state
    timestamps = day_data.index.tolist()
    battery_soc = [initial_charge]  # State of Charge in kWh
    battery_pct = [50]  # State of Charge in percentage
    charging = [0]  # Charging status (1=charging, -1=discharging, 0=idle)
    energy_flow = [0]  # Energy flow rate (positive=charging, negative=discharging)
    grid_power = [0]  # Power from/to grid
    temperature = [50]  # Simulated temperature of thermal storage (°C)
    efficiency = [95]  # System efficiency (%)
    regulation_type = ["None"]  # Type of regulation (None, Up, Down)
    
    # Temperature range for thermal storage
    min_temp = 30
    max_temp = 95
    
    # Price thresholds for charge/discharge decisions - dynamic based on percentiles
    low_price_threshold = country_data['price'].quantile(0.3)
    high_price_threshold = country_data['price'].quantile(0.7)
    
    # Apply scenario volatility to thresholds
    threshold_spread = high_price_threshold - low_price_threshold
    volatility_factor = 1 + scenario_props.get('volatility', 0)
    low_price_threshold -= threshold_spread * 0.1 * volatility_factor
    high_price_threshold += threshold_spread * 0.1 * volatility_factor
    
    # Simulate battery operation
    current_charge = initial_charge
    
    for i in range(1, len(day_data)):
        price = day_data['price'].iloc[i]
        is_activated = day_data['activated'].iloc[i] > 0
        
        # Determine charging action
        action = 0  # Default: idle
        flow = 0
        grid = 0
        reg_type = "None"
        
        # Grid activation takes precedence - discharge if activated (up regulation)
        if is_activated and current_charge > battery_capacity * 0.1:
            action = -1  # Discharge
            discharge_amount = min(discharge_rate, current_charge - battery_capacity * 0.1)
            current_charge -= discharge_amount
            flow = -discharge_amount
            grid = discharge_amount * 0.9  # Some losses in conversion
            reg_type = "Up Regulation"
        # If price is low and battery not full, charge (can be considered down regulation)
        elif price < low_price_threshold and current_charge < battery_capacity * 0.95:
            action = 1  # Charge
            charge_amount = min(charge_rate, battery_capacity * 0.95 - current_charge)
            current_charge += charge_amount
            flow = charge_amount
            grid = -charge_amount / 0.95  # Some losses in conversion
            reg_type = "Down Regulation"
        # If price is high and battery has charge, discharge (market optimization)
        elif price > high_price_threshold and current_charge > battery_capacity * 0.2:
            action = -1  # Discharge
            discharge_amount = min(discharge_rate, current_charge - battery_capacity * 0.2)
            current_charge -= discharge_amount
            flow = -discharge_amount
            grid = discharge_amount * 0.9  # Some losses in conversion
            reg_type = "Market Discharge"
        
        # Calculate simulated temperature based on charge level
        # Higher charge = higher temperature in thermal storage
        current_temp = min_temp + ((current_charge / battery_capacity) * (max_temp - min_temp))
        
        # Calculate efficiency - higher at mid-range temperatures
        current_efficiency = 85 + 10 * (1 - abs((current_temp - ((max_temp + min_temp) / 2)) / ((max_temp - min_temp) / 2)))
        
        # Add to arrays
        battery_soc.append(current_charge)
        battery_pct.append((current_charge / battery_capacity) * 100)
        charging.append(action)
        energy_flow.append(flow)
        grid_power.append(grid)
        temperature.append(current_temp)
        efficiency.append(current_efficiency)
        regulation_type.append(reg_type)
    
    # Create dataframe for plotting
    df = pd.DataFrame({
        'timestamp': timestamps,
        'hour': [ts.hour for ts in timestamps],
        'price': day_data['price'].values,
        'activated': day_data['activated'].values,
        'battery_soc': battery_soc,
        'battery_pct': battery_pct,
        'charging': charging,
        'energy_flow': energy_flow,
        'grid_power': grid_power,
        'temperature': temperature,
        'efficiency': efficiency,
        'regulation': regulation_type
    })
    
    # Add a time index column for animation frames
    df['time_idx'] = range(len(df))
    
    # Create figure with subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            f"Thermal Storage - 24 Hour Operation ({start_time.strftime('%Y-%m-%d')})",
            "Energy Flow & Grid Regulation",
            "Temperature & Efficiency",
            "Energy Price"
        ),
        row_heights=[0.4, 0.2, 0.2, 0.2]
    )
    
    # Create color mapping for regulation types
    reg_colors = {
        "None": "#CCCCCC",
        "Up Regulation": "#EF553B",  # Red for up regulation (discharge)
        "Down Regulation": "#00CC96",  # Green for down regulation (charge)
        "Market Discharge": "#FFA15A"  # Orange for market-based discharge
    }
    
    # Create a battery visualization
    # Battery outline
    fig.add_trace(
        go.Scatter(
            x=[0, 0, 24, 24, 0],
            y=[0, 100, 100, 0, 0],
            fill=None,
            mode='lines',
            line=dict(color='black', width=2),
            showlegend=False,
            hoverinfo='skip'
        ),
        row=1, col=1
    )
    
    # Add battery fill as animation frames
    for hour in range(24):
        hour_data = df[df['hour'] == hour]
        if not hour_data.empty:
            charge_level = hour_data['battery_pct'].iloc[-1]
            fig.add_trace(
                go.Scatter(
                    x=[hour, hour, hour+1, hour+1, hour],
                    y=[0, charge_level, charge_level, 0, 0],
                    fill='toself',
                    mode='none',
                    fillcolor='rgba(51, 102, 204, 0.7)',
                    name=f"{hour}:00 - {charge_level:.1f}%",
                    hovertemplate=f"<b>Time:</b> {hour}:00<br><b>Charge:</b> {charge_level:.1f}%<extra></extra>"
                ),
                row=1, col=1
            )
    
    # Add regulation indicators
    for reg_type in ["Up Regulation", "Down Regulation", "Market Discharge"]:
        reg_df = df[df['regulation'] == reg_type]
        if not reg_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=reg_df['hour'],
                    y=reg_df['battery_pct'],
                    mode='markers',
                    marker=dict(
                        symbol='circle',
                        size=10,
                        color=reg_colors[reg_type],
                        line=dict(width=1, color='black')
                    ),
                    name=reg_type,
                    hovertemplate=f"<b>{reg_type}</b><br>Time: %{{x}}:00<br>Charge: %{{y:.1f}}%<extra></extra>"
                ),
                row=1, col=1
            )
    
    # Add energy flow visualization
    fig.add_trace(
        go.Bar(
            x=df['hour'],
            y=df['energy_flow'],
            marker_color=[reg_colors[reg] for reg in df['regulation']],
            name="Energy Flow",
            hovertemplate="<b>Hour:</b> %{x}:00<br><b>Energy Flow:</b> %{y:.1f} kWh<br><extra></extra>"
        ),
        row=2, col=1
    )
    
    # Add grid power visualization
    fig.add_trace(
        go.Scatter(
            x=df['hour'],
            y=df['grid_power'],
            mode='lines+markers',
            line=dict(color='black', width=2, dash='dot'),
            name="Grid Power",
            hovertemplate="<b>Hour:</b> %{x}:00<br><b>Grid Power:</b> %{y:.1f} kW<br><extra></extra>"
        ),
        row=2, col=1
    )
    
    # Add temperature visualization
    fig.add_trace(
        go.Scatter(
            x=df['hour'],
            y=df['temperature'],
            mode='lines',
            line=dict(color='#FF9900', width=3),
            name="Temperature (°C)",
            hovertemplate="<b>Hour:</b> %{x}:00<br><b>Temperature:</b> %{y:.1f}°C<br><extra></extra>"
        ),
        row=3, col=1
    )
    
    # Add efficiency visualization
    fig.add_trace(
        go.Scatter(
            x=df['hour'],
            y=df['efficiency'],
            mode='lines',
            line=dict(color='#109618', width=2, dash='dot'),
            name="Efficiency (%)",
            hovertemplate="<b>Hour:</b> %{x}:00<br><b>Efficiency:</b> %{y:.1f}%<br><extra></extra>"
        ),
        row=3, col=1
    )
    
    # Add energy price
    fig.add_trace(
        go.Scatter(
            x=df['hour'],
            y=df['price'],
            mode='lines',
            line=dict(color='#AB63FA', width=3),
            name="Energy Price (€/MWh)",
            hovertemplate="<b>Hour:</b> %{x}:00<br><b>Price:</b> %{y:.2f} €/MWh<br><extra></extra>"
        ),
        row=4, col=1
    )
    
    # Add price thresholds
    fig.add_shape(
        type="line",
        x0=0,
        y0=low_price_threshold,
        x1=24,
        y1=low_price_threshold,
        line=dict(color="#00CC96", width=1, dash="dash"),
        row=4, col=1
    )
    
    fig.add_shape(
        type="line",
        x0=0,
        y0=high_price_threshold,
        x1=24,
        y1=high_price_threshold,
        line=dict(color="#EF553B", width=1, dash="dash"),
        row=4, col=1
    )
    
    # Add grid activation events
    activation_df = df[df['activated'] > 0]
    if not activation_df.empty:
        fig.add_trace(
            go.Scatter(
                x=activation_df['hour'],
                y=activation_df['price'],
                mode='markers',
                marker=dict(
                    symbol='star',
                    size=15,
                    color='#FFA15A',
                    line=dict(width=1, color='black')
                ),
                name="Grid Activation",
                hovertemplate="<b>Grid Activation</b><br>Hour: %{x}:00<br>Price: %{y:.2f} €/MWh<br><extra></extra>"
            ),
            row=4, col=1
        )
    
    # Update layout
    fig.update_layout(
        height=900,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=80, b=40),
        hovermode="x unified",
    )
    
    # Update x-axes to show hours
    for i in range(1, 5):
        fig.update_xaxes(
            title_text="Hour of Day" if i == 4 else None,
            tickmode='array',
            tickvals=list(range(0, 25, 3)),
            ticktext=[f"{h}:00" for h in range(0, 25, 3)],
            range=[0, 24],
            row=i, col=1
        )
    
    # Update y-axes
    fig.update_yaxes(title_text="Battery Charge (%)", range=[0, 105], row=1, col=1)
    fig.update_yaxes(title_text="Energy Flow (kWh)", row=2, col=1)
    fig.update_yaxes(title_text="Temperature (°C) / Efficiency (%)", row=3, col=1)
    fig.update_yaxes(title_text="Price (€/MWh)", row=4, col=1)
    
    # Add annotations for price thresholds
    fig.add_annotation(
        x=1,
        y=low_price_threshold,
        text="Charge Threshold",
        showarrow=True,
        arrowhead=1,
        ax=50,
        ay=-30,
        row=4, col=1
    )
    
    fig.add_annotation(
        x=1,
        y=high_price_threshold,
        text="Discharge Threshold",
        showarrow=True,
        arrowhead=1,
        ax=50,
        ay=30,
        row=4, col=1
    )
    
    # Add title annotation with date
    fig.add_annotation(
        x=0.5,
        y=1.05,
        xref="paper",
        yref="paper",
        text=f"<b>24-Hour Thermal Storage Operation - {country_name} ({start_time.strftime('%B %d, %Y')})</b>",
        showarrow=False,
        font=dict(size=16),
        align="center"
    )
    
    # Add a legend for regulation types
    fig.add_annotation(
        x=0.01,
        y=0.99,
        xref="paper",
        yref="paper",
        text="<b>Regulation Types:</b><br>🔴 Up Regulation (Grid Support)<br>🟢 Down Regulation (Charging)<br>🟠 Market Discharge",
        showarrow=False,
        font=dict(size=12),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="black",
        borderwidth=1,
        borderpad=4,
        opacity=0.9
    )
    
    return fig


def create_sensitivity_chart(sensitivity_df, selected_country, parameter_name):
    st.write("Sensitivity Chart Placeholder")
    # fig = ... (Plotly code)
    # return fig
    return go.Figure()

# --- Main Data Processing and Display ---
if st.sidebar.button("🚀 Run Simulation", use_container_width=True, type="primary") or not hasattr(st.session_state, 'npv_results'):
    # Simulate for selected countries (example: Germany, UK, Spain)
    # In a real app, you'd have a multi-select for countries
    selected_countries_list = ["Germany", "UK", "Spain", "Italy", "France"]
    
    with st.spinner("🌍 Loading market data..."):
        country_data_loaded = load_country_data(selected_countries_list)
        st.session_state.country_data = country_data_loaded
        
        price_projections_loaded = load_price_projections() # Load price projection data
        st.session_state.price_projections = price_projections_loaded # Store in session state

    with st.spinner(f"⚙️ Simulating for {SCENARIOS[st.session_state.scenario]['label']} scenario..."):
        current_scenario_params = SCENARIOS[st.session_state.scenario]
        npv_results_calculated = simulate(cap_kwh, current_scenario_params, country_data_loaded)
        st.session_state.npv_results = npv_results_calculated
else:
    npv_results_calculated = st.session_state.npv_results
    country_data_loaded = st.session_state.country_data
    price_projections_loaded = st.session_state.price_projections # Retrieve from session state

# --- Main Dashboard Content ---
# (Strategy Map has been moved to the tabs interface to avoid duplication)

# --- Display Results in Tabs ---
if EXTRAS_AVAILABLE:
    colored_header("📊 Detailed Analysis Dashboard", description="Explore detailed simulation results", color_name="green-70")
else:
    st.header("📊 Detailed Analysis Dashboard")

tab1, tab_strategy, tab2, tab3, tab4, tab5, tab_recommendations = st.tabs([
    "Interactive Thermal Storage Animation", "Strategy Map", "Detailed Analysis", "Price Projections", 
    "Sensitivity Analysis", "Grid Stability", "Recommendations"
]) 

# Strategy Map Tab Content
with tab_strategy:
    st.subheader("Optimal Business Model Strategy Map")
    st.caption("This map shows which business model yields the highest NPV for each country in the selected scenario.")
    
    strategy_map = create_strategy_map_chart(npv_results_calculated, SCENARIOS[st.session_state.scenario])
    st.plotly_chart(strategy_map, use_container_width=True, key=f"strategy_map_{st.session_state.scenario}")
    
    st.markdown("""
    **Legend:**
    - **Blue circles**: Standalone model is optimal
    - **Green circles**: Heat as a Service (HaaS) model is optimal
    - **Orange circles**: Grid Balancing model is optimal
    
    *Circle size indicates relative NPV value - larger circles represent higher NPV potential.*
    
    **Hover over any country** to see detailed information including:
    - Best business model
    - NPV value for the best model
    - NPV values for all business models
    """)
    
    # Add explanation of what this means
    st.markdown("""
    ### How to interpret this map:
    Each country is color-coded according to its optimal business model, with circle size indicating the relative NPV value.
    This visualization helps identify regional patterns and prioritize markets based on both business model fit and potential returns.
    """)

# Animation Tab Content
with tab1: # Interactive Thermal Storage Animation
    st.subheader("24-Hour Thermal Storage Operation")
    st.caption("Detailed visualization of battery charging/discharging cycles and grid regulation over a 24-hour period")
    
    # Create two columns for controls and info
    control_col, info_col = st.columns([3, 2])
    
    with control_col:
        # Country selector for the animation
        animation_country = st.selectbox(
            "Select Country", 
            list(country_data_loaded.keys()),
            key="animation_country_select"
        )
        
        # Capacity slider for more interactivity
        animation_capacity = st.slider(
            "Storage Capacity (kWh)",
            min_value=1000,
            max_value=10000,
            value=cap_kwh,
            step=1000,
            format="%d kWh",
            key="animation_capacity_slider"
        )
    
    with info_col:
        st.markdown("### System Performance")
        
        # Calculate some metrics based on the simulation
        country_data = country_data_loaded[animation_country]
        avg_price = country_data['price'].mean()
        price_volatility = country_data['price'].std() / avg_price * 100
        activation_count = (country_data['activated'] > 0).sum()
        activation_pct = activation_count / len(country_data) * 100
        
        # Display metrics
        metrics_cols = st.columns(2)
        with metrics_cols[0]:
            st.metric("Avg. Price", f"€{avg_price:.2f}/MWh")
            st.metric("Grid Events", f"{activation_count} times")
        with metrics_cols[1]:
            st.metric("Price Volatility", f"{price_volatility:.1f}%")
            st.metric("Activation %", f"{activation_pct:.2f}%")
        
        # Add scenario info
        st.markdown(f"**Scenario:** {SCENARIOS[st.session_state.scenario]['full_label']}")
        st.markdown(f"**Volatility Factor:** {SCENARIOS[st.session_state.scenario].get('volatility', 0) * 100:.1f}%")
    
    # Create and display the 24-hour animation
    battery_24h_animation = create_24h_battery_animation(
        animation_country,
        country_data_loaded[animation_country],
        animation_capacity,
        SCENARIOS[st.session_state.scenario]
    )
    st.plotly_chart(battery_24h_animation, use_container_width=True, key=f"battery_24h_animation_{animation_country}_{animation_capacity}")
    
    # Add explanation with improved formatting
    with st.expander("How to interpret this visualization", expanded=True):
        st.markdown("""
        ### 24-Hour Battery Operation Guide
        
        #### Top Panel: Battery Charge Level
        - **Blue outline**: Battery container visualization
        - **Blue filled sections**: Battery charge level at each hour
        - **Colored dots**: Regulation events (see legend)
        
        #### Second Panel: Energy Flow & Grid Regulation
        - **Colored bars**: Energy flow - charging (green) and discharging (red/orange)
        - **Dotted line**: Power exchange with the grid (positive = to grid, negative = from grid)
        
        #### Third Panel: Temperature & Efficiency
        - **Orange line**: Temperature of the thermal storage (°C)
        - **Green dotted line**: System efficiency (%)
        
        #### Bottom Panel: Energy Market & Grid Events
        - **Purple line**: Energy price (€/MWh)
        - **Green dashed line**: Price threshold for charging
        - **Red dashed line**: Price threshold for discharging
        - **⭐ Orange stars**: Grid activation events
        
        ### Regulation Types:
        - 🔴 **Up Regulation**: Battery discharges to support grid during high demand/frequency drops
        - 🟢 **Down Regulation**: Battery charges to absorb excess energy during low demand periods
        - 🟠 **Market Discharge**: Battery discharges to sell energy during high price periods
        """)
    
    # Add a section for key insights
    st.markdown("### Key Insights")
    
    # Find a day with grid activations if possible
    has_activation = (country_data['activated'] > 0).groupby(country_data.index.date).sum() > 0
    if has_activation.any():
        sample_date = has_activation[has_activation].index[0]
    else:
        sample_date = country_data.index[0].date()
    
    # Get price data for the sample date
    day_mask = (country_data.index.date == sample_date)
    day_prices = country_data.loc[day_mask, 'price']
    
    # Find peak and off-peak hours
    if not day_prices.empty:
        peak_hour = day_prices.idxmax().hour
        off_peak_hour = day_prices.idxmin().hour
    else:
        peak_hour = 18  # Default if no data
        off_peak_hour = 3  # Default if no data
    
    st.markdown(f"""
    Based on the 24-hour simulation for **{animation_country}** on **{sample_date}**:
    
    1. **Daily Cycle**: The thermal storage system follows a daily charge/discharge cycle, with charging primarily during off-peak hours (around {off_peak_hour}:00) and discharging during peak hours (around {peak_hour}:00).
    
    2. **Grid Regulation**: The system provides grid support through up-regulation (discharging during grid events) and down-regulation (charging during excess generation).
    
    3. **Temperature Management**: The thermal storage temperature fluctuates between 30-95°C throughout the day, affecting system efficiency.
    
    4. **Price Arbitrage**: By charging at low prices (below €{country_data['price'].quantile(0.3):.2f}/MWh) and discharging at high prices (above €{country_data['price'].quantile(0.7):.2f}/MWh), the system captures value from daily price spreads.
    
    5. **Efficiency Optimization**: The system maintains optimal efficiency by managing charge/discharge cycles to keep temperatures in the ideal range.
    """)
    
    # Add a call-to-action button to explore other tabs
    st.markdown("---")
    st.markdown("### Explore More Detailed Analysis")
    st.markdown("Use the tabs above to explore detailed analysis of different business models, price projections, and country-specific recommendations.")

    st.subheader("Detailed NPV Breakdown by Country/Model")
    countries_for_select = list(npv_results_calculated.keys())
    if countries_for_select:
        selected_country_for_detail = st.selectbox(
            "Select Country for Detailed Breakdown", 
            options=countries_for_select, 
            key=f"npv_detail_country_select_{st.session_state.scenario}"
        )
        
        if selected_country_for_detail:
            models_for_select = list(npv_results_calculated[selected_country_for_detail].keys())
            if models_for_select:
                selected_model_for_detail = st.selectbox(
                    "Select Model for Detailed Breakdown",
                    options=models_for_select,
                    key=f"npv_detail_model_select_{st.session_state.scenario}_{selected_country_for_detail}"
                )

                if selected_model_for_detail:
                    details = npv_results_calculated[selected_country_for_detail][selected_model_for_detail]
                    st.markdown(f"#### Breakdown for {selected_country_for_detail} - {selected_model_for_detail}")
                    
                    cols = st.columns(4)
                    with cols[0]:
                        st.metric("NPV", f"€{details['NPV']/1e6:.2f}M")
                    with cols[1]:
                        st.metric("Total Revenue", f"€{details['TotalRevenue']/1e6:.2f}M")
                    with cols[2]:
                        st.metric("Total Energy Cost", f"€{details['TotalEnergyCost']/1e6:.2f}M")
                    with cols[3]:
                        st.metric("Total Op Cost", f"€{details['TotalOpCost']/1e6:.2f}M")
                    if EXTRAS_AVAILABLE:
                        style_metric_cards(border_left_color=SCENARIOS[st.session_state.scenario]['color'])
            else:
                st.info(f"No models available for {selected_country_for_detail} in the current results.")
    else:
        st.info("Run simulation to see detailed breakdown options.")

with tab2: # Detailed Analysis
    st.subheader("Detailed Country Analysis")
    selected_country_detailed = st.selectbox("Select Country for Detailed View", list(country_data_loaded.keys()), key="detailed_country_select")
    
    if selected_country_detailed and EXTRAS_AVAILABLE:
        metric_cols = st.columns(3)
        models_available = list(npv_results_calculated[selected_country_detailed].keys())
        for i, model_name in enumerate(models_available):
            with metric_cols[i % 3]: # Corrected from metric_cols[i]
                st.metric(
                    label=f"{model_name} NPV", 
                    value=f"€{npv_results_calculated[selected_country_detailed][model_name]['NPV']/1e6:.1f}M",
                    # delta=f"{npv_results_calculated[selected_country_detailed][model_name]['NPV']/1e6/cap_kwh*1000:.0f} €/kWh" # Example delta
                )
                st.metric(
                    label=f"{model_name} Revenue", 
                    value=f"€{npv_results_calculated[selected_country_detailed][model_name]['TotalRevenue']/1e6:.1f}M",
                )
                st.metric(
                    label=f"{model_name} Energy Cost", 
                    value=f"€{npv_results_calculated[selected_country_detailed][model_name]['TotalEnergyCost']/1e6:.1f}M",
                )
                st.metric(
                    label=f"{model_name} Op Cost", 
                    value=f"€{npv_results_calculated[selected_country_detailed][model_name]['TotalOpCost']/1e6:.1f}M",
                )
        style_metric_cards(border_left_color=SCENARIOS[st.session_state.scenario]['color'])
    elif selected_country_detailed:
        # Fallback for metrics if streamlit-extras not available
        for model_name, npv_components in npv_results_calculated[selected_country_detailed].items():
            st.markdown(f"<div class='metric-card' style='border-left-color:{SCENARIOS[st.session_state.scenario]['color']};'><h5>{model_name} NPV</h5><h3>€{npv_components['NPV']/1e6:.1f}M</h3></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card' style='border-left-color:{SCENARIOS[st.session_state.scenario]['color']};'><h5>{model_name} Revenue</h5><h3>€{npv_components['TotalRevenue']/1e6:.1f}M</h3></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card' style='border-left-color:{SCENARIOS[st.session_state.scenario]['color']};'><h5>{model_name} Energy Cost</h5><h3>€{npv_components['TotalEnergyCost']/1e6:.1f}M</h3></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-card' style='border-left-color:{SCENARIOS[st.session_state.scenario]['color']};'><h5>{model_name} Op Cost</h5><h3>€{npv_components['TotalOpCost']/1e6:.1f}M</h3></div>", unsafe_allow_html=True)

    if selected_country_detailed:
        st.subheader("Battery Operation Simulation (Placeholder)")
        battery_op_chart = create_battery_animation_chart(
            selected_country_detailed, 
            country_data_loaded[selected_country_detailed], 
            cap_kwh, 
            SCENARIOS[st.session_state.scenario]
        )
        st.plotly_chart(battery_op_chart, use_container_width=True, key=f"battery_op_chart_{selected_country_detailed}_{st.session_state.scenario}")

with tab3: # Price Projections
    st.subheader("Future Price Projections")
    price_proj_chart = create_price_projection_chart(price_projections_loaded, SCENARIOS[st.session_state.scenario])
    st.plotly_chart(price_proj_chart, use_container_width=True, key=f"price_proj_chart_{st.session_state.scenario}")
    # st.info("Price projection chart to be implemented with actual data and slider.")

with tab4: # Sensitivity Analysis
    st.subheader("Sensitivity Analysis (Placeholder)")
    st.info("Sensitivity analysis charts for capacity and volatility to be implemented.")

# --- Grid Stability Tab ---
with tab5:
    st.subheader("Grid Stability Simulation")
    st.caption("How ETES activation helps stabilize the grid frequency in real scenarios.")
    
    # Country selector for grid stability
    stability_country = st.selectbox("Select Country for Grid Stability View", list(country_data_loaded.keys()), key="stability_country_select")
    country_df = country_data_loaded[stability_country]
    
    # Use the 'activated' column as ETES activation signal
    if 'activated' in country_df.columns:
        time = country_df.index
        activation = country_df['activated'].astype(float).fillna(0)
        # Simulate grid frequency (no ETES): nominal 50 Hz, with noise and drift
        np.random.seed(42)
        freq_no_etes = 50 + np.random.normal(0, 0.035, len(time))
        # Add artificial frequency dips when activation is needed
        freq_no_etes = freq_no_etes - activation * np.random.uniform(0.03, 0.08, len(time))
        # With ETES: frequency is restored to nominal during activation
        freq_with_etes = freq_no_etes.copy()
        freq_with_etes[activation > 0] = 50.0
        # Plotly figure
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=time, y=freq_no_etes, mode='lines', name='Grid Frequency (No ETES)', line=dict(color='#888', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=time, y=freq_with_etes, mode='lines', name='Grid Frequency (With ETES)', line=dict(color='#0066cc', width=2)))
        # Highlight ETES activation periods
        fig.add_trace(go.Scatter(x=time, y=[49.92 if act > 0 else None for act in activation],
                                 mode='markers', marker=dict(size=4, color='#28a745'),
                                 name='ETES Activated', showlegend=True))
        fig.update_layout(
            template='simple_white',
            yaxis_title='Grid Frequency (Hz)',
            xaxis_title='Time',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(l=30, r=30, t=40, b=30),
            height=400,
            font=dict(family='Inter, Arial', size=15, color='#222'),
        )
        fig.update_yaxes(range=[49.85, 50.15], showgrid=True, gridwidth=1, gridcolor='#eee')
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
        st.plotly_chart(fig, use_container_width=True, key=f"grid_stability_{stability_country}_{st.session_state.scenario}")
        st.caption("\nThe blue line shows grid frequency with ETES response; the grey dotted line shows what would happen without ETES. Green dots indicate when ETES is activated to restore stability.\n")
    else:
        st.info("No activation data available for this country.")

# --- Recommendations Tab ---
with tab_recommendations:
    st.subheader("Market Entry Recommendations")
    st.caption("Strategic recommendations based on simulation results across scenarios and countries.")
    
    # Create a summary of the best models across countries
    country_models = {}
    model_counts = {"Standalone": 0, "HaaS": 0, "Grid Balancing": 0}
    top_countries = {}
    
    # Analyze results to generate recommendations
    for country, models in npv_results_calculated.items():
        if not models:
            continue
            
        # Find best model and its NPV
        best_model = max(models.items(), key=lambda x: x[1]['NPV'] if isinstance(x[1], dict) else x[1])
        model_name = best_model[0]
        npv_value = best_model[1]['NPV'] if isinstance(best_model[1], dict) else best_model[1]
        
        # Store best model for each country
        country_models[country] = model_name
        model_counts[model_name] += 1
        
        # Track top countries for each model
        if model_name not in top_countries:
            top_countries[model_name] = []
        top_countries[model_name].append((country, npv_value))
    
    # Sort top countries by NPV for each model
    for model in top_countries:
        top_countries[model] = sorted(top_countries[model], key=lambda x: x[1], reverse=True)[:3]  # Top 3
    
    # Display overall recommendations
    st.markdown(f"### Overall Strategy for {SCENARIOS[st.session_state.scenario]['full_label']} Scenario")
    
    # Create a summary table of model distribution
    model_summary = pd.DataFrame({
        "Business Model": list(model_counts.keys()),
        "Number of Countries": list(model_counts.values()),
        "Percentage": [f"{count/sum(model_counts.values())*100:.1f}%" for count in model_counts.values()]
    })
    
    # Display the summary table
    st.dataframe(model_summary.set_index("Business Model"), use_container_width=True)
    
    # Determine the dominant strategy
    dominant_model = max(model_counts.items(), key=lambda x: x[1])[0] if model_counts else None
    
    if dominant_model:
        # Display the dominant strategy recommendation
        st.markdown(f"""#### Primary Recommendation
        
        Based on the simulation results for the **{SCENARIOS[st.session_state.scenario]['full_label']}** scenario, the **{dominant_model}** model emerges as the most profitable approach across {model_counts[dominant_model]} countries ({float(model_counts[dominant_model])/sum(model_counts.values())*100:.1f}% of analyzed markets).
        
        This suggests that Brenmiller Energy should **prioritize the {dominant_model} business model** as its primary market entry strategy for European expansion, while maintaining flexibility to adapt to specific country conditions.
        """)
    
    # Display top countries for each model
    st.markdown("### Top Markets by Business Model")
    st.caption("Countries with highest NPV potential for each business model")
    
    model_cols = st.columns(len(top_countries))
    for i, (model, countries) in enumerate(top_countries.items()):
        with model_cols[i % len(top_countries)]:
            st.markdown(f"**{model}**")
            for country, npv in countries:
                st.markdown(f"• {country}: €{npv/1e6:.2f}M")
    
    # Country-specific recommendations
    st.markdown("### Country-Specific Recommendations")
    st.caption("Select a country to see detailed recommendations")
    
    # Country selector for recommendations
    rec_country = st.selectbox("Select Country", list(country_models.keys()), key="rec_country_select")
    
    if rec_country and rec_country in npv_results_calculated:
        models_data = npv_results_calculated[rec_country]
        best_model = country_models.get(rec_country)
        
        # Calculate differences between models
        model_npvs = {model: (data['NPV'] if isinstance(data, dict) else data) for model, data in models_data.items()}
        sorted_models = sorted(model_npvs.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate percentage differences
        best_npv = sorted_models[0][1]
        diffs = {}
        for model, npv in sorted_models[1:]:
            diffs[model] = (best_npv - npv) / best_npv * 100
        
        # Display country recommendation
        st.markdown(f"#### {rec_country} Strategy")
        
        # Create metrics for each model
        metric_cols = st.columns(len(model_npvs))
        for i, (model, npv) in enumerate(sorted_models):
            with metric_cols[i]:
                if model == best_model:
                    st.metric(f"{model}", f"€{npv/1e6:.2f}M", "BEST")
                else:
                    st.metric(f"{model}", f"€{npv/1e6:.2f}M", f"{-diffs[model]:.1f}% vs best")
        
        # Recommendation text
        if best_model == "Standalone":
            st.markdown(f"""**Recommendation for {rec_country}:** Focus on direct sales of ETES units to industrial customers. The standalone model provides the highest NPV in this market, likely due to favorable upfront capital expenditure conditions and customer willingness to purchase technology outright.""")
        elif best_model == "HaaS":
            st.markdown(f"""**Recommendation for {rec_country}:** Implement a Heat-as-a-Service (HaaS) model, retaining ownership of the ETES units and selling thermal energy output via long-term contracts. This market shows strong potential for recurring revenue streams, possibly due to customers' preference for OPEX over CAPEX.""")
        elif best_model == "Grid Balancing":
            st.markdown(f"""**Recommendation for {rec_country}:** Partner with local grid operators or energy service companies (ESCOs) to provide grid balancing services. This market shows high volatility and grid balancing needs, creating significant value from frequency regulation and demand response capabilities.""")
        
        # Risk factors
        st.markdown("#### Risk Factors")
        
        # Calculate the gap between best and second-best model
        if len(sorted_models) > 1:
            gap = (sorted_models[0][1] - sorted_models[1][1]) / sorted_models[0][1] * 100
            if gap < 10:
                st.warning(f"The NPV difference between {sorted_models[0][0]} and {sorted_models[1][0]} is only {gap:.1f}%. Consider a hybrid approach or monitor market conditions closely as the optimal strategy could shift.")
            else:
                st.success(f"The {sorted_models[0][0]} model has a strong {gap:.1f}% NPV advantage over alternatives, suggesting a robust strategic choice for {rec_country}.")
        
        # Scenario sensitivity
        st.markdown("#### Scenario Sensitivity")
        st.info(f"This recommendation is based on the {SCENARIOS[st.session_state.scenario]['full_label']} scenario. To test robustness, change scenarios using the selector at the top of the page.")
    else:
        st.info("Select a country to view detailed recommendations.")

# --- Footer (Optional) ---
st.markdown("---_" * 10)
st.caption("Brenmiller Energy - Thermal Storage Simulator v4.0")

# To run this app: streamlit run enhanced_app.py
