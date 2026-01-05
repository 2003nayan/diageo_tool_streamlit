#!/usr/bin/env python3
"""
Mashing Data Analysis Tool - Streamlit Version
Migrated from Tkinter v3_batch_analysis_tool_enhanced.py

Features:
- Sensory Notes Filter (Cooked, Starchy, Husky, Clean)
- 7-Phase Detection with Individual Phase Plots
- Multi-Batch Statistical Analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch

# Page configuration
st.set_page_config(
    page_title="Mashing Data Analysis Tool",
    page_icon="🍺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== DATA LOADING ==============
@st.cache_data
def load_mashing_data():
    """Load and cache mashing data"""
    # For Streamlit Cloud: data is in the same directory or a 'data' subdirectory
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Try multiple locations for flexibility
    possible_paths = [
        os.path.join(base_path, 'data', 'combined_mashing_data_all.csv'),
        os.path.join(base_path, 'New_Data', 'combined_mashing_data_all.csv'),
        os.path.join(os.path.dirname(base_path), 'New_Data', 'combined_mashing_data_all.csv'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
    
    raise FileNotFoundError(f"Could not find mashing data in: {possible_paths}")

@st.cache_data
def load_parametric_data():
    """Load and cache parametric data"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(base_path, 'data', 'Audi_parametric_data.csv'),
        os.path.join(base_path, 'New_Data', 'Audi_parametric_data.csv'),
        os.path.join(os.path.dirname(base_path), 'New_Data', 'Audi_parametric_data.csv'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return pd.read_csv(path)
    
    raise FileNotFoundError(f"Could not find parametric data in: {possible_paths}")

@st.cache_data
def load_sensory_data():
    """Load and cache sensory data"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(base_path, 'data', 'AuDi_Sensory Output File.xlsx - TC Consensus Score-FMS.csv'),
        os.path.join(base_path, 'New_Data', 'AuDi_Sensory Output File.xlsx - TC Consensus Score-FMS.csv'),
        os.path.join(os.path.dirname(base_path), 'New_Data', 'AuDi_Sensory Output File.xlsx - TC Consensus Score-FMS.csv'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, skiprows=1)
                df.columns = ['Blinding_Code', 'Cereal_Grainy', 'Fruity_Floral', 'Fermented', 
                             'Husky', 'Starchy', 'Cooked', 'FO', 'Acidic_Solvent', 
                             'Others', 'Others_COMMENTS'] + list(df.columns[11:])
                df['Blinding_Code'] = df['Blinding_Code'].astype(str)
                return df
            except Exception as e:
                st.warning(f"Could not load sensory data: {e}")
                return pd.DataFrame()
    
    # Sensory data is optional - return empty if not found
    return pd.DataFrame()

@st.cache_data
def load_good_bad_batches():
    """Load good/bad batch lists from Excel"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(base_path, 'data', 'Diageo_ Data_Available_Report (1).xlsx'),
        os.path.join(base_path, 'New_Data', 'Diageo_ Data_Available_Report (1).xlsx'),
        os.path.join(os.path.dirname(base_path), 'New_Data', 'Diageo_ Data_Available_Report (1).xlsx'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                good_df = pd.read_excel(path, sheet_name='Good Data')
                bad_df = pd.read_excel(path, sheet_name='Bad Data')
                good_batches = list(good_df['Batch_id'].dropna().astype(int).unique())
                bad_batches = list(bad_df['Batch_id'].dropna().astype(int).unique())
                return good_batches, bad_batches
            except Exception as e:
                st.warning(f"Could not load batch classification: {e}")
                return [], []
    
    # Return empty if not found
    return [], []


# ============== HELPER FUNCTIONS ==============
def get_batch_numeric(batch_id):
    """Extract numeric batch ID from string"""
    if '_' in str(batch_id):
        parts = str(batch_id).split('_')
        try:
            return int(parts[1]) if len(parts) > 1 else None
        except:
            return None
    try:
        return int(batch_id)
    except:
        return None

def get_sensory_batches(sensory_df, note_type, intensity):
    """Get batches matching specified sensory note intensity (0-3)"""
    if sensory_df is None or sensory_df.empty:
        return []
    
    col_map = {'Cooked': 'Cooked', 'Starchy': 'Starchy', 'Husky': 'Husky', 'Grainy': 'Cereal_Grainy'}
    
    if note_type in col_map:
        col = col_map[note_type]
        if col in sensory_df.columns:
            try:
                intensity_val = int(intensity)
                filtered = sensory_df[sensory_df[col] == intensity_val]
                return [str(x) for x in filtered['Blinding_Code'].tolist()]
            except:
                return []
    return []

def generate_color_shades(base_color, n_shades):
    """Generate n shades of a base color from light to dark."""
    try:
        rgb = mcolors.to_rgb(base_color)
    except:
        rgb = (0.5, 0.5, 0.5)
    
    shades = []
    for i in range(n_shades):
        factor = 0.4 + (0.6 * i / max(n_shades - 1, 1))
        shade = tuple(c * factor for c in rgb)
        shades.append(shade)
    return shades

def detect_phases_new(batch_mashing):
    """
    Detect 7 phases using specific logic signatures.
    Phase 1: Water Pre-Fill - Water flow > 0 AND Grist flow = 0
    Phase 2: Grist Addition - Grist flow > 0 until Grist flow returns to 0
    Phase 3: Resting - All flows (water + grist) = 0 until sparge or runoff starts
    Phase 4: Sparge - Sparge water flow > 0 until flow returns to 0
    Phase 5: First Wort Collection - Runoff activation until runoff stops or 2nd sparge
    Phase 6: Second Sparge - Second water spike until water flow = 0
    Phase 7: Grain Disposal - Vessel discharge until empty
    """
    phases = {}
    
    process_start = batch_mashing['minutes'].min()
    process_end = batch_mashing['minutes'].max()
    
    batch_mashing = batch_mashing.copy()
    batch_mashing['grist_flow'] = -batch_mashing['greast_case_weight'].diff().fillna(0)
    batch_mashing['grist_flow'] = batch_mashing['grist_flow'].apply(lambda x: max(x, 0))
    
    water_flow = batch_mashing['sparging_mashing_water_flow']
    grist_flow = batch_mashing['grist_flow']
    
    # PHASE 1: Water Pre-Fill
    p1_start = process_start
    grist_starts = batch_mashing[batch_mashing['grist_flow'] > 0.5]
    if not grist_starts.empty:
        p1_end = grist_starts['minutes'].iloc[0]
    else:
        p1_end = process_start + 5
    phases[1] = {'name': 'Water Pre-Fill', 'start': p1_start, 'end': p1_end}
    
    # PHASE 2: Grist Addition
    p2_start = p1_end
    grist_data = batch_mashing[batch_mashing['minutes'] >= p2_start]
    if not grist_data.empty:
        grist_active = grist_data[grist_data['grist_flow'] > 0.5]
        if not grist_active.empty:
            last_grist_time = grist_active['minutes'].iloc[-1]
            p2_end = last_grist_time + 1
        else:
            min_grist_idx = batch_mashing['greast_case_weight'].idxmin()
            p2_end = batch_mashing.loc[min_grist_idx, 'minutes']
    else:
        p2_end = p2_start + 10
    phases[2] = {'name': 'Grist Addition', 'start': p2_start, 'end': p2_end}
    
    # PHASE 3: Resting (Saccharification)
    p3_start = p2_end
    post_grist = batch_mashing[batch_mashing['minutes'] > p3_start]
    sparge_starts = post_grist[post_grist['sparging_mashing_water_flow'] > 200]
    if not sparge_starts.empty:
        p3_end = sparge_starts['minutes'].iloc[0]
    else:
        p3_end = min(p3_start + 60, process_end)
    phases[3] = {'name': 'Resting', 'start': p3_start, 'end': p3_end}
    
    # PHASE 4: Sparge
    p4_start = p3_end
    sparge_data = batch_mashing[batch_mashing['minutes'] >= p4_start]
    high_flow_data = sparge_data[sparge_data['sparging_mashing_water_flow'] > 200]
    
    if not high_flow_data.empty:
        high_flow_data = high_flow_data.copy()
        high_flow_data['gap'] = high_flow_data['minutes'].diff()
        gaps = high_flow_data[high_flow_data['gap'] > 3]
        if not gaps.empty:
            p4_end = gaps['minutes'].iloc[0] - 1
        else:
            flow_data = sparge_data[sparge_data['minutes'] > high_flow_data['minutes'].iloc[0]]
            low_flow = flow_data[flow_data['sparging_mashing_water_flow'] < 50]
            if not low_flow.empty:
                p4_end = low_flow['minutes'].iloc[0]
            else:
                p4_end = high_flow_data['minutes'].iloc[-1] + 2
    else:
        p4_end = min(p4_start + 15, process_end)
    phases[4] = {'name': 'Sparge', 'start': p4_start, 'end': p4_end}
    
    # PHASE 5: First Wort Collection
    p5_start = p4_end
    post_sparge = batch_mashing[batch_mashing['minutes'] > p5_start]
    second_sparge = post_sparge[post_sparge['sparging_mashing_water_flow'] > 200]
    
    if not second_sparge.empty:
        p5_end = second_sparge['minutes'].iloc[0] - 1
    else:
        p5_end = min(p5_start + 30, process_end)
    phases[5] = {'name': 'First Wort', 'start': p5_start, 'end': p5_end}
    
    # PHASE 6: Second Sparge
    p6_start = p5_end
    post_p5 = batch_mashing[batch_mashing['minutes'] >= p6_start]
    high_flow_p6 = post_p5[post_p5['sparging_mashing_water_flow'] > 200]
    
    if not high_flow_p6.empty:
        last_high = high_flow_p6['minutes'].iloc[-1]
        after_sparge = batch_mashing[batch_mashing['minutes'] > last_high]
        low_flow = after_sparge[after_sparge['sparging_mashing_water_flow'] < 50]
        if not low_flow.empty:
            p6_end = low_flow['minutes'].iloc[0]
        else:
            p6_end = last_high + 5
    else:
        p6_end = min(p6_start + 20, process_end)
    phases[6] = {'name': 'Second Sparge', 'start': p6_start, 'end': p6_end}
    
    # PHASE 7: Grain Disposal
    p7_start = p6_end
    p7_end = process_end
    phases[7] = {'name': 'Grain Disposal', 'start': p7_start, 'end': p7_end}
    
    return phases

def detect_phases(batch_mashing):
    """Detect 7 phases based on flow signatures (alternative method)"""
    phases = {}
    
    process_start = batch_mashing['minutes'].min()
    process_end = batch_mashing['minutes'].max()
    
    batch_mashing = batch_mashing.copy()
    batch_mashing['grist_flow'] = -batch_mashing['greast_case_weight'].diff().fillna(0)
    batch_mashing['grist_flow'] = batch_mashing['grist_flow'].clip(lower=0)
    
    water_flow = batch_mashing['sparging_mashing_water_flow']
    grist_flow = batch_mashing['grist_flow']
    
    # Phase 1: Water Pre-Fill
    p1_start = process_start
    grist_starts = batch_mashing[grist_flow > 10]
    p1_end = grist_starts['minutes'].iloc[0] if not grist_starts.empty else process_start + 5
    phases[1] = {'name': 'Water Pre-Fill', 'start': p1_start, 'end': p1_end}
    
    # Phase 2: Grist Addition
    p2_start = p1_end
    initial_grist = batch_mashing['greast_case_weight'].iloc[0]
    min_grist_idx = batch_mashing['greast_case_weight'].idxmin()
    p2_end = batch_mashing.loc[min_grist_idx, 'minutes']
    phases[2] = {'name': 'Grist Addition', 'start': p2_start, 'end': p2_end}
    
    # Phase 3: Resting
    post_grist = batch_mashing[batch_mashing['minutes'] > p2_end]
    p3_start = p2_end
    high_flow = post_grist[post_grist['sparging_mashing_water_flow'] > 300]
    p3_end = high_flow['minutes'].iloc[0] if not high_flow.empty else p3_start + 45
    phases[3] = {'name': 'Resting', 'start': p3_start, 'end': p3_end}
    
    # Phase 4: Sparge
    p4_start = p3_end
    sparge_data = batch_mashing[batch_mashing['minutes'] >= p4_start]
    high_flow_data = sparge_data[sparge_data['sparging_mashing_water_flow'] > 300]
    
    if not high_flow_data.empty:
        high_flow_data = high_flow_data.copy()
        high_flow_data['gap'] = high_flow_data['minutes'].diff()
        gaps = high_flow_data[high_flow_data['gap'] > 5]
        if not gaps.empty:
            p4_end = gaps['minutes'].iloc[0] - 2
        else:
            p4_end = high_flow_data['minutes'].iloc[-1] + 2
    else:
        p4_end = p4_start + 20
    phases[4] = {'name': 'Sparge', 'start': p4_start, 'end': p4_end}
    
    # Phase 5: First Wort Collection
    p5_start = p4_end
    post_sparge1 = batch_mashing[batch_mashing['minutes'] > p5_start]
    second_sparge = post_sparge1[post_sparge1['sparging_mashing_water_flow'] > 300]
    
    if not second_sparge.empty:
        p5_end = second_sparge['minutes'].iloc[0] - 2
    else:
        p5_end = min(p5_start + 40, process_end)
    phases[5] = {'name': 'First Wort', 'start': p5_start, 'end': p5_end}
    
    # Phase 6: Second Sparge
    p6_start = p5_end
    post_p5 = batch_mashing[batch_mashing['minutes'] >= p6_start]
    high_flow_p6 = post_p5[post_p5['sparging_mashing_water_flow'] > 300]
    
    if not high_flow_p6.empty:
        p6_end = high_flow_p6['minutes'].iloc[-1] + 5
    else:
        p6_end = min(p6_start + 30, process_end)
    phases[6] = {'name': 'Second Sparge', 'start': p6_start, 'end': p6_end}
    
    # Phase 7: Grain Disposal
    p7_start = p6_end
    p7_end = process_end
    phases[7] = {'name': 'Grain Disposal', 'start': p7_start, 'end': p7_end}
    
    return phases

def calculate_heat_available(data):
    """Calculate heat available from water per minute"""
    cp_water = 4.18
    rho_water = 1.0
    data = data.copy()
    data['heat_available'] = 0.0
    for i in range(1, len(data)):
        T_initial = data['mashing_sparging_water_temp'].iloc[i-1]
        T_final = data['mashing_temp'].iloc[i]
        flow_prev = data['sparging_mashing_water_flow'].iloc[i-1] / 60.0
        mass_prev = rho_water * flow_prev
        delta_T = T_final - T_initial if pd.notna(T_initial) and pd.notna(T_final) else 0
        Q = mass_prev * cp_water * delta_T
        data.loc[data.index[i], 'heat_available'] = Q
    return data

# ============== PLOTTING FUNCTIONS ==============
def plot_single_batch(batch_mashing, batch_id, params_to_plot):
    """Plot single batch with 7-phase markers."""
    batch_mashing = batch_mashing.copy()
    batch_mashing = batch_mashing.sort_values('timestamp')
    
    if len(batch_mashing) == 0:
        st.warning("No data available!")
        return None
    
    process_start = batch_mashing['timestamp'].min()
    batch_mashing['minutes'] = (batch_mashing['timestamp'] - process_start).dt.total_seconds() / 60
    
    # Detect phases
    phases = detect_phases_new(batch_mashing)
    
    # Create plot
    fig, ax = plt.subplots(figsize=(18, 10))
    fig.suptitle(f"Batch {batch_id} - Complete Process Overview with 7 Phase Markers", fontsize=14, fontweight='bold')
    
    phase_colors = ['#4169E1', '#228B22', '#FF8C00', '#DC143C', '#9932CC', '#20B2AA', '#8B4513']
    phase_names = ['P1: Water Pre-Fill', 'P2: Grist Addition', 'P3: Resting', 
                  'P4: Sparge', 'P5: First Wort', 'P6: Second Sparge', 'P7: Grain Disposal']
    
    lines = []
    labels = []
    
    # First parameter on primary y-axis
    col, label, color = params_to_plot[0]
    if col in batch_mashing.columns:
        line, = ax.plot(batch_mashing['minutes'], batch_mashing[col], color=color, lw=1.5, label=label)
        lines.append(line)
        labels.append(label)
    ax.set_ylabel(label, fontsize=10, color=color)
    ax.tick_params(axis='y', labelcolor=color)
    ax.set_xlabel('Time (min)', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Additional parameters on secondary y-axes
    if len(params_to_plot) > 1:
        ax2 = ax.twinx()
        for i, (col, label, color) in enumerate(params_to_plot[1:], 1):
            if col in batch_mashing.columns:
                if i > 1:
                    ax_new = ax.twinx()
                    ax_new.spines['right'].set_position(('outward', 60 * (i - 1)))
                    line, = ax_new.plot(batch_mashing['minutes'], batch_mashing[col], color=color, lw=1.5, label=label)
                    ax_new.set_ylabel(label, fontsize=9, color=color)
                    ax_new.tick_params(axis='y', labelcolor=color)
                else:
                    line, = ax2.plot(batch_mashing['minutes'], batch_mashing[col], color=color, lw=1.5, label=label)
                    ax2.set_ylabel(label, fontsize=10, color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                lines.append(line)
                labels.append(label)
    
    # Add phase markers
    ymin, ymax = ax.get_ylim()
    for pnum in range(1, 8):
        p_start = phases[pnum]['start']
        p_end = phases[pnum]['end']
        color = phase_colors[pnum - 1]
        
        ax.axvspan(p_start, p_end, alpha=0.12, color=color)
        ax.axvline(x=p_start, color=color, linestyle='--', alpha=0.7, lw=1)
        
        p_mid = (p_start + p_end) / 2
        ax.text(p_mid, ymax * 0.97, f'P{pnum}', 
               fontsize=10, fontweight='bold', ha='center', color=color,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9))
    
    ax.axvline(x=phases[7]['end'], color=phase_colors[6], linestyle='--', alpha=0.7, lw=1)
    
    # Combined legend for parameters
    ax.legend(lines, labels, loc='upper left', fontsize=9)
    
    # Add phase legend at bottom
    legend_patches = [Patch(facecolor=phase_colors[i], alpha=0.3, label=phase_names[i]) for i in range(7)]
    fig.legend(handles=legend_patches, loc='lower center', ncol=7, fontsize=8, 
              title='Phase Legend', title_fontsize=8, bbox_to_anchor=(0.5, 0.01))
    
    plt.subplots_adjust(top=0.92, bottom=0.14, left=0.06, right=0.85)
    
    return fig

def plot_multi_batch(mashing_df, batch_list, params_to_plot):
    """Plot multiple batches overlaid for comparison."""
    fig, ax = plt.subplots(figsize=(18, 10))
    
    batch_count = len(batch_list)
    fig.suptitle(f"Multi-Batch Comparison ({batch_count} batches)", fontsize=14, fontweight='bold')
    
    lines = []
    labels = []
    axes_list = [ax]
    
    ax.set_xlabel('Time (min)', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Track valid batches and their data
    batch_data_list = []
    for batch_id in batch_list:
        batch_mashing = mashing_df[mashing_df['batch_no'] == batch_id].copy()
        batch_mashing = batch_mashing.sort_values('timestamp')
        if len(batch_mashing) > 0:
            process_start = batch_mashing['timestamp'].min()
            batch_mashing['minutes'] = (batch_mashing['timestamp'] - process_start).dt.total_seconds() / 60
            batch_data_list.append((batch_id, batch_mashing))
    
    if not batch_data_list:
        st.warning("No data available for selected batches!")
        return None
    
    # Generate color shades for each parameter
    param_shades = {}
    for col, label, base_color in params_to_plot:
        param_shades[col] = generate_color_shades(base_color, len(batch_data_list))
    
    # Plot each parameter
    for param_idx, (col, label, base_color) in enumerate(params_to_plot):
        if param_idx == 0:
            current_ax = ax
            ax.set_ylabel(label, fontsize=10, color=base_color)
            ax.tick_params(axis='y', labelcolor=base_color)
        elif param_idx == 1:
            current_ax = ax.twinx()
            current_ax.set_ylabel(label, fontsize=10, color=base_color)
            current_ax.tick_params(axis='y', labelcolor=base_color)
            axes_list.append(current_ax)
        else:
            current_ax = ax.twinx()
            current_ax.spines['right'].set_position(('outward', 60 * (param_idx - 1)))
            current_ax.set_ylabel(label, fontsize=9, color=base_color)
            current_ax.tick_params(axis='y', labelcolor=base_color)
            axes_list.append(current_ax)
        
        # Plot each batch with different shade
        shades = param_shades[col]
        for batch_idx, (batch_id, batch_mashing) in enumerate(batch_data_list):
            if col in batch_mashing.columns:
                shade_color = shades[batch_idx]
                short_name = str(batch_id).split('_')[-1] if '_' in str(batch_id) else str(batch_id)
                line_label = f"{label[:10]}... ({short_name})" if len(label) > 10 else f"{label} ({short_name})"
                
                line, = current_ax.plot(
                    batch_mashing['minutes'], 
                    batch_mashing[col], 
                    color=shade_color, 
                    lw=1.2, 
                    alpha=0.85,
                    label=line_label
                )
                lines.append(line)
                labels.append(line_label)
    
    # Create legend
    fig.legend(lines, labels, 
              loc='center right', 
              bbox_to_anchor=(0.99, 0.5),
              fontsize=8,
              ncol=1,
              title='Parameter (Batch)',
              title_fontsize=9,
              framealpha=0.9)
    
    plt.subplots_adjust(top=0.92, bottom=0.08, left=0.06, right=0.80)
    
    return fig

# ============== INITIALIZE SESSION STATE ==============
def init_session_state():
    """Initialize session state variables"""
    if 'selected_batches' not in st.session_state:
        st.session_state.selected_batches = []
    if 'data_type' not in st.session_state:
        st.session_state.data_type = "Good Data"
    if 'filter_cooked' not in st.session_state:
        st.session_state.filter_cooked = "Any"
    if 'filter_starchy' not in st.session_state:
        st.session_state.filter_starchy = "Any"
    if 'filter_husky' not in st.session_state:
        st.session_state.filter_husky = "Any"
    if 'filter_grainy' not in st.session_state:
        st.session_state.filter_grainy = "Any"
    if 'ts_params' not in st.session_state:
        st.session_state.ts_params = ['Grist Weight', 'Water Flow', 'Mash Temp', 'Wort Temp']

# ============== MAIN APP ==============
def main():
    init_session_state()
    
    # Title
    st.title("🍺 Mashing Data Analysis Tool - Enhanced")
    st.markdown("**7-Phase Process Visualization | Sensory Notes Filtering | Multi-Batch Analysis**")
    
    # Load data
    try:
        mashing_df = load_mashing_data()
        parametric_df = load_parametric_data()
        sensory_df = load_sensory_data()
        good_batches, bad_batches = load_good_bad_batches()
        batch_list = sorted(mashing_df['batch_no'].unique())
        
        st.success(f"✅ Loaded {len(batch_list)} batches | {len(good_batches)} good | {len(bad_batches)} bad")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    # Store in session state for other pages
    st.session_state.mashing_df = mashing_df
    st.session_state.parametric_df = parametric_df
    st.session_state.sensory_df = sensory_df
    st.session_state.good_batches = good_batches
    st.session_state.bad_batches = bad_batches
    st.session_state.batch_list = batch_list
    
    # ========== SIDEBAR FILTERS ==========
    st.sidebar.header("🔧 Filters")
    
    # Data Type Filter
    data_type = st.sidebar.radio(
        "Data Availability:",
        ["Good Data", "Bad/Partial Data"],
        index=0 if st.session_state.data_type == "Good Data" else 1
    )
    st.session_state.data_type = data_type
    
    # Sensory Notes Filters
    st.sidebar.subheader("Sensory Notes (0-3)")
    intensity_options = ["Any", "0", "1", "2", "3"]
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        filter_cooked = st.selectbox("Cooked:", intensity_options, 
                                     index=intensity_options.index(st.session_state.filter_cooked))
        filter_husky = st.selectbox("Husky:", intensity_options,
                                    index=intensity_options.index(st.session_state.filter_husky))
    with col2:
        filter_starchy = st.selectbox("Starchy:", intensity_options,
                                      index=intensity_options.index(st.session_state.filter_starchy))
        filter_grainy = st.selectbox("Grainy:", intensity_options,
                                     index=intensity_options.index(st.session_state.filter_grainy))
    
    st.session_state.filter_cooked = filter_cooked
    st.session_state.filter_starchy = filter_starchy
    st.session_state.filter_husky = filter_husky
    st.session_state.filter_grainy = filter_grainy
    
    # Time Series Parameters
    st.sidebar.subheader("Time Series Parameters")
    param_options = ['Grist Weight', 'Water Flow', 'Mash Temp', 'Wort Temp', 'Water Temp', 'Water Totalizer']
    ts_params = st.sidebar.multiselect(
        "Select parameters to plot:",
        param_options,
        default=st.session_state.ts_params
    )
    st.session_state.ts_params = ts_params
    
    # ========== APPLY FILTERS ==========
    if data_type == "Good Data":
        base_ids = set(good_batches)
    else:
        base_ids = set(bad_batches)
    
    # Apply sensory filters
    sensory_filters = []
    filter_applied = False
    
    if filter_cooked != "Any":
        sensory_filters.extend(get_sensory_batches(sensory_df, 'Cooked', filter_cooked))
        filter_applied = True
    if filter_starchy != "Any":
        sensory_filters.extend(get_sensory_batches(sensory_df, 'Starchy', filter_starchy))
        filter_applied = True
    if filter_husky != "Any":
        sensory_filters.extend(get_sensory_batches(sensory_df, 'Husky', filter_husky))
        filter_applied = True
    if filter_grainy != "Any":
        sensory_filters.extend(get_sensory_batches(sensory_df, 'Grainy', filter_grainy))
        filter_applied = True
    
    if filter_applied and sensory_filters:
        sensory_ids = set()
        for code in sensory_filters:
            try:
                if '-' in str(code):
                    num = int(str(code).split('-')[0])
                else:
                    num = int(code)
                sensory_ids.add(num)
            except:
                pass
        base_ids = base_ids.intersection(sensory_ids)
    elif filter_applied and not sensory_filters:
        base_ids = set()
    
    # Get available batches
    available_batches = []
    for batch in batch_list:
        batch_num = get_batch_numeric(batch)
        if batch_num in base_ids:
            available_batches.append(batch)
    
    available_batches = sorted(available_batches)
    st.session_state.filtered_batch_ids = base_ids
    st.session_state.available_batches = available_batches
    
    # ========== BATCH SELECTION ==========
    st.subheader("📊 Batch Selection")
    st.info(f"**{len(available_batches)}** batches available after applying filters")
    
    selected_batches = st.multiselect(
        "Select batch(es) to analyze:",
        available_batches,
        default=st.session_state.selected_batches if all(b in available_batches for b in st.session_state.selected_batches) else []
    )
    st.session_state.selected_batches = selected_batches
    
    # ========== VISUALIZATION ==========
    st.subheader("📈 7-Phase Process Overview")
    
    if not selected_batches:
        st.warning("👆 Select batch(es) above to visualize the 7-phase process")
    elif not ts_params:
        st.warning("⚠️ Please select at least one Time Series Parameter in the sidebar")
    else:
        # Build params_to_plot
        param_map = {
            'Grist Weight': ('greast_case_weight', 'Grist Weight (kg)', 'brown'),
            'Water Flow': ('sparging_mashing_water_flow', 'Water Flow (L/hr)', 'blue'),
            'Mash Temp': ('mashing_temp', 'Mash Temp (°C)', 'red'),
            'Wort Temp': ('wort_receiver_temp', 'Wort Temp (°C)', 'green'),
            'Water Temp': ('water_temperature', 'Water Temp (°C)', 'cyan'),
            'Water Totalizer': ('water_totalizer', 'Water Totalizer (L)', 'purple')
        }
        
        params_to_plot = [param_map[p] for p in ts_params if p in param_map]
        
        if len(selected_batches) == 1:
            # Single batch with phase markers
            batch_id = selected_batches[0]
            batch_mashing = mashing_df[mashing_df['batch_no'] == batch_id]
            
            with st.spinner(f"Analyzing {batch_id}..."):
                fig = plot_single_batch(batch_mashing, batch_id, params_to_plot)
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)
        else:
            # Multi-batch comparison
            with st.spinner(f"Comparing {len(selected_batches)} batches..."):
                fig = plot_multi_batch(mashing_df, selected_batches, params_to_plot)
                if fig:
                    st.pyplot(fig)
                    plt.close(fig)
    
    # ========== NAVIGATION HINT ==========
    st.divider()
    st.markdown("""
    ### 📑 Additional Analysis Pages
    Use the **sidebar navigation** to access:
    - **Phase Analysis**: Detailed plots for each of the 6 processing phases
    - **Statistics**: Batch info, static data, and multi-batch statistical comparison
    """)

if __name__ == "__main__":
    main()
