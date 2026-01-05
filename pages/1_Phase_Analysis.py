#!/usr/bin/env python3
"""
Phase Analysis Page - Detailed phase-specific visualizations
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os

# Add parent directory to path to import from v3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="Phase Analysis",
    page_icon="📊",
    layout="wide"
)

# ============== HELPER FUNCTIONS ==============
def detect_phases(batch_mashing):
    """Detect 7 phases based on flow signatures"""
    phases = {}
    
    process_start = batch_mashing['minutes'].min()
    process_end = batch_mashing['minutes'].max()
    
    batch_mashing = batch_mashing.copy()
    batch_mashing['grist_flow'] = -batch_mashing['greast_case_weight'].diff().fillna(0)
    batch_mashing['grist_flow'] = batch_mashing['grist_flow'].clip(lower=0)
    
    # Phase 1: Water Pre-Fill
    p1_start = process_start
    grist_starts = batch_mashing[batch_mashing['grist_flow'] > 10]
    p1_end = grist_starts['minutes'].iloc[0] if not grist_starts.empty else process_start + 5
    phases[1] = {'name': 'Water Pre-Fill', 'start': p1_start, 'end': p1_end}
    
    # Phase 2: Grist Addition
    p2_start = p1_end
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

# ============== PHASE PLOTTING FUNCTIONS ==============
def plot_phase_1(batch_mashing, batch_id, phases):
    """Phase 1: Raw Material Addition - 5 plots (3x2 grid)"""
    p1_start = phases[1]['start']
    p2_end = phases[2]['end']
    phase_data = batch_mashing[(batch_mashing['minutes'] >= p1_start) & (batch_mashing['minutes'] <= p2_end)].copy()
    
    initial_grist = batch_mashing['greast_case_weight'].iloc[0]
    
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle(f"Phase 1: Raw Material Addition - Batch {batch_id} ({p1_start:.0f}-{p2_end:.0f} min)", 
                 fontsize=13, fontweight='bold')
    
    # Plot 1: Cumulative Raw Data
    ax = axes[0, 0]
    phase_data['grist_consumed'] = (initial_grist - phase_data['greast_case_weight']).clip(lower=0)
    ax.plot(phase_data['minutes'], phase_data['grist_consumed'], color='brown', lw=1.5, label='Grist (kg)')
    ax.plot(phase_data['minutes'], phase_data['sparging_mashing_water_totalizer']*100, 
           color='blue', lw=1.5, label='Water (L)')
    ax.set_ylabel('Cumulative (kg/L)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Cumulative Raw Data')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Addition Rate
    ax = axes[0, 1]
    phase_data['grist_rate'] = -phase_data['greast_case_weight'].diff().fillna(0)
    phase_data['grist_rate'] = phase_data['grist_rate'].apply(lambda x: abs(x))
    phase_data['water_rate'] = phase_data['sparging_mashing_water_flow'] / 60
    ax.plot(phase_data['minutes'], phase_data['grist_rate'], color='brown', lw=1.5, label='Grist (kg/min)')
    ax.plot(phase_data['minutes'], phase_data['water_rate'], color='blue', lw=1.5, label='Water (L/min)')
    ax.set_ylabel('Rate (kg/min or L/min)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Addition Rate (Absolute Values)')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Grist:Water Ratio
    ax = axes[1, 0]
    phase_data['water_added'] = phase_data['sparging_mashing_water_totalizer'] * 100
    valid_ratio = phase_data[phase_data['water_rate'] >= 5].copy()
    valid_ratio['ratio'] = np.where(valid_ratio['water_added'] > 50, 
                                    valid_ratio['grist_consumed'] / valid_ratio['water_added'], np.nan)
    ax.plot(valid_ratio['minutes'], valid_ratio['ratio'], color='green', lw=1.5)
    ax.axhline(y=0.2, color='red', linestyle='--', alpha=0.7, label='<0.2 Risk Cooked')
    ax.axhline(y=1.5, color='orange', linestyle='--', alpha=0.7, label='>1.5 Risk Starchy')
    ax.fill_between(valid_ratio['minutes'], 0.2, 1.5, alpha=0.1, color='green', label='Safe Zone')
    ax.set_ylabel('Ratio (kg/L)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Grist:Water Ratio (Water Rate >= 5 L/min only)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Heat Available Time Series
    ax = axes[1, 1]
    phase_data = calculate_heat_available(phase_data)
    heat_val = phase_data['heat_available'] * -1
    ax.fill_between(phase_data['minutes'], heat_val, alpha=0.3, color='red')
    ax.plot(phase_data['minutes'], heat_val, color='red', lw=1.5)
    ax.set_ylabel('Heat (kJ/min)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Heat Available from Water per Minute')
    ax.grid(True, alpha=0.3)
    
    # Plot 5: Heat Bubble Chart
    ax = axes[2, 0]
    phase_data['water_per_min'] = phase_data['sparging_mashing_water_flow'] / 60
    phase_data['heat_per_grist'] = np.where(phase_data['grist_consumed'] > 100,
        (phase_data['heat_available'] * -1) / phase_data['grist_consumed'], 0)
    valid = phase_data[(phase_data['water_per_min'] > 0.1) & 
                      (phase_data['grist_consumed'] > 100) & 
                      (phase_data['heat_per_grist'] > 0.01)]
    if len(valid) >= 5:
        max_grist = valid['grist_consumed'].max()
        sizes = (valid['grist_consumed'] / max_grist) * 500 + 20
        scatter = ax.scatter(valid['water_per_min'], valid['heat_per_grist'], s=sizes,
                            c=valid['mashing_temp'], cmap='coolwarm', alpha=0.6, edgecolors='black', lw=0.5)
        plt.colorbar(scatter, ax=ax, label='Mash Temp (°C)')
    ax.set_xlabel('Water (L/min)')
    ax.set_ylabel('Heat/Grist (kJ/kg)')
    ax.set_title('Bubble Chart (Size=Grist, Color=Temp)')
    ax.grid(True, alpha=0.3)
    
    axes[2, 1].axis('off')
    
    plt.tight_layout()
    return fig

def plot_phase_2(batch_mashing, batch_id, phases):
    """Phase 2: Resting - 2 plots"""
    p_start = phases[3]['start']
    p_end = phases[3]['end']
    phase_data = batch_mashing[(batch_mashing['minutes'] >= p_start) & (batch_mashing['minutes'] <= p_end)].copy()
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f"Phase 2: Resting (Saccharification) - Batch {batch_id} ({p_start:.0f}-{p_end:.0f} min)", 
                 fontsize=13, fontweight='bold')
    
    # Plot 1: RM Addition Rates
    ax = axes[0]
    ax.plot(phase_data['minutes'], phase_data['sparging_mashing_water_flow'], color='blue', lw=1.5, label='Water Flow (L/hr)')
    phase_data['grist_rate'] = -phase_data['greast_case_weight'].diff().fillna(0)
    phase_data['grist_rate'] = phase_data['grist_rate'].apply(lambda x: abs(x))
    ax.plot(phase_data['minutes'], phase_data['grist_rate']*10, color='brown', lw=1.5, label='Grist Rate x10 (kg/min)')
    ax.set_ylabel('Flow Rate')
    ax.set_xlabel('Time (min)')
    ax.set_title('RM Addition Rates (Should be ~0 during rest)')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Temperature Variation
    ax = axes[1]
    ax.plot(phase_data['minutes'], phase_data['mashing_temp'], color='red', lw=2, label='Mashing Temp')
    ax.fill_between(phase_data['minutes'], phase_data['mashing_temp'], alpha=0.2, color='red')
    ax.set_ylabel('Temperature (°C)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Temperature Variation (Heat Loss Detection)')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_phase_3(batch_mashing, batch_id, phases):
    """Phase 3: First Wort Collection - 3 plots"""
    p_start = phases[5]['start']
    p_end = phases[5]['end']
    phase_data = batch_mashing[(batch_mashing['minutes'] >= p_start) & (batch_mashing['minutes'] <= p_end)]
    
    # Fallback if phase data is empty
    if phase_data.empty or len(phase_data) < 5:
        phase_data = batch_mashing[batch_mashing['wort_receiver_temp'] > 50]
        if not phase_data.empty:
            p_start = phase_data['minutes'].min()
            p_end = phase_data['minutes'].max()
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Phase 3: First Wort Collection - Batch {batch_id}", fontsize=13, fontweight='bold')
    
    # Plot 1: Wort Temperature
    ax = axes[0]
    if not phase_data.empty:
        ax.plot(phase_data['minutes'], phase_data['wort_receiver_temp'], color='#228B22', lw=2)
    else:
        ax.plot(batch_mashing['minutes'], batch_mashing['wort_receiver_temp'], color='#228B22', lw=2)
    ax.set_ylabel('Temperature (°C)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Wort Temperature Trend')
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Duration info
    ax = axes[1]
    duration = max(p_end - p_start, 1)
    ax.bar(['Collection Duration'], [duration], color='#4169E1', width=0.5)
    ax.set_ylabel('Duration (min)')
    ax.set_title(f'Total Collection Time: {duration:.1f} min')
    ax.text(0, duration/2, f'{duration:.1f} min', ha='center', va='center', fontsize=14, fontweight='bold', color='white')
    
    # Plot 3: Mashing Temp during collection
    ax = axes[2]
    if not phase_data.empty:
        ax.plot(phase_data['minutes'], phase_data['mashing_temp'], color='red', lw=1.5)
    else:
        ax.plot(batch_mashing['minutes'], batch_mashing['mashing_temp'], color='red', lw=1.5)
    ax.set_ylabel('Mash Temp (°C)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Mash Tun Temp During Collection')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_phase_4(batch_mashing, batch_id, phases):
    """Phase 4: Sparge - 3 plots"""
    p_start = phases[4]['start']
    p_end = phases[4]['end']
    phase_data = batch_mashing[(batch_mashing['minutes'] >= p_start) & (batch_mashing['minutes'] <= p_end)]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Phase 4: Sparge - Batch {batch_id}", fontsize=13, fontweight='bold')
    
    # Plot 1: Sparge Flow Rate
    ax = axes[0]
    ax.plot(phase_data['minutes'], phase_data['sparging_mashing_water_flow'], color='blue', lw=2)
    ax.set_ylabel('Flow Rate (L/hr)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Sparge Flow Rate')
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Sparge Temperature
    ax = axes[1]
    ax.plot(phase_data['minutes'], phase_data['mashing_sparging_water_temp'], color='orange', lw=2)
    ax.axhline(y=74, color='green', linestyle='--', alpha=0.7, label='Target Low (74°C)')
    ax.axhline(y=78, color='red', linestyle='--', alpha=0.7, label='Risk High (78°C)')
    ax.fill_between(phase_data['minutes'], 74, 76, alpha=0.2, color='green')
    ax.set_ylabel('Temperature (°C)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Sparge Temp (74-76°C Target)')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Bed Temperature Response
    ax = axes[2]
    ax.plot(phase_data['minutes'], phase_data['mashing_temp'], color='red', lw=2, label='Mash Temp')
    ax.set_ylabel('Temperature (°C)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Grain Bed Temperature Response')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_phase_5(batch_mashing, batch_id, phases):
    """Phase 5: Second Sparge - 2 plots"""
    p_start = phases[6]['start']
    p_end = phases[6]['end']
    phase_data = batch_mashing[(batch_mashing['minutes'] >= p_start) & (batch_mashing['minutes'] <= p_end)]
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"Phase 5: Second Sparge - Batch {batch_id}", fontsize=13, fontweight='bold')
    
    # Plot 1: Water Input Volume
    ax = axes[0]
    ax.plot(phase_data['minutes'], phase_data['sparging_mashing_water_flow'], color='blue', lw=2)
    ax.fill_between(phase_data['minutes'], phase_data['sparging_mashing_water_flow'], alpha=0.3, color='blue')
    total_vol = phase_data['sparging_mashing_water_flow'].sum() / 60
    ax.set_ylabel('Flow Rate (L/hr)')
    ax.set_xlabel('Time (min)')
    ax.set_title(f'Water Input (Total: ~{total_vol:.0f} L)')
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Temperature Delta
    ax = axes[1]
    phase_data_copy = phase_data.copy()
    phase_data_copy['temp_delta'] = phase_data_copy['mashing_sparging_water_temp'] - phase_data_copy['mashing_temp']
    ax.plot(phase_data_copy['minutes'], phase_data_copy['temp_delta'], color='purple', lw=2)
    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
    ax.set_ylabel('Temp Delta (°C)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Temperature Delta (Water - Bed)')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_phase_6(batch_mashing, batch_id, phases):
    """Phase 6: Grain Disposal - 2 plots"""
    p_start = phases[7]['start']
    p_end = phases[7]['end']
    phase_data = batch_mashing[(batch_mashing['minutes'] >= p_start) & (batch_mashing['minutes'] <= p_end)]
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"Phase 6: Grain Disposal - Batch {batch_id}", fontsize=13, fontweight='bold')
    
    # Plot 1: Discharge Duration
    ax = axes[0]
    duration = p_end - p_start
    ax.bar(['Discharge Time'], [duration], color='#8B4513', width=0.5)
    ax.set_ylabel('Duration (min)')
    ax.set_title(f'Discharge Duration: {duration:.1f} min')
    ax.text(0, duration/2, f'{duration:.1f} min', ha='center', va='center', fontsize=14, fontweight='bold', color='white')
    
    # Plot 2: Residual Weight
    ax = axes[1]
    ax.plot(phase_data['minutes'], phase_data['greast_case_weight'], color='brown', lw=2)
    final_weight = phase_data['greast_case_weight'].iloc[-1] if not phase_data.empty else 0
    ax.axhline(y=final_weight, color='green', linestyle='--', label=f'Final: {final_weight:.0f} kg')
    ax.set_ylabel('Vessel Weight (kg)')
    ax.set_xlabel('Time (min)')
    ax.set_title('Residual Weight Confirmation')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

# ============== MAIN PAGE ==============
def main():
    st.title("📊 Phase Analysis")
    st.markdown("**Detailed visualizations for each processing phase**")
    
    # Check if data is loaded
    if 'mashing_df' not in st.session_state:
        st.warning("⚠️ Please visit the main page first to load data!")
        st.page_link("v3.py", label="Go to Main Page", icon="🏠")
        return
    
    mashing_df = st.session_state.mashing_df
    selected_batches = st.session_state.get('selected_batches', [])
    
    if not selected_batches:
        st.warning("⚠️ No batch selected. Please select a batch on the main page.")
        st.page_link("v3.py", label="Go to Main Page", icon="🏠")
        return
    
    # Use first selected batch
    batch_id = selected_batches[0]
    st.info(f"📦 Analyzing batch: **{batch_id}**")
    
    if len(selected_batches) > 1:
        st.caption(f"Note: Phase analysis uses the first selected batch. {len(selected_batches)} batches were selected.")
    
    # Get batch data
    batch_mashing = mashing_df[mashing_df['batch_no'] == batch_id].copy()
    batch_mashing = batch_mashing.sort_values('timestamp')
    
    if batch_mashing.empty:
        st.error("No data available for this batch!")
        return
    
    process_start = batch_mashing['timestamp'].min()
    batch_mashing['minutes'] = (batch_mashing['timestamp'] - process_start).dt.total_seconds() / 60
    
    # Detect phases
    phases = detect_phases(batch_mashing)
    
    # Create tabs for each phase
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔵 P1: Raw Material Addition",
        "🟢 P2: Resting",
        "🟠 P3: First Wort Collection",
        "🔴 P4: Sparge",
        "🟣 P5: Second Sparge",
        "🟤 P6: Grain Disposal"
    ])
    
    with tab1:
        st.subheader("Phase 1: Raw Material Addition")
        st.markdown("**Water Pre-Fill + Grist Addition combined view**")
        fig = plot_phase_1(batch_mashing, batch_id, phases)
        st.pyplot(fig)
        plt.close(fig)
    
    with tab2:
        st.subheader("Phase 2: Resting (Saccharification)")
        st.markdown("**Temperature stability during enzyme activity**")
        fig = plot_phase_2(batch_mashing, batch_id, phases)
        st.pyplot(fig)
        plt.close(fig)
    
    with tab3:
        st.subheader("Phase 3: First Wort Collection")
        st.markdown("**Wort temperature and collection duration**")
        fig = plot_phase_3(batch_mashing, batch_id, phases)
        st.pyplot(fig)
        plt.close(fig)
    
    with tab4:
        st.subheader("Phase 4: Sparge")
        st.markdown("**Water addition and temperature control**")
        fig = plot_phase_4(batch_mashing, batch_id, phases)
        st.pyplot(fig)
        plt.close(fig)
    
    with tab5:
        st.subheader("Phase 5: Second Sparge")
        st.markdown("**Second water injection and temperature delta**")
        fig = plot_phase_5(batch_mashing, batch_id, phases)
        st.pyplot(fig)
        plt.close(fig)
    
    with tab6:
        st.subheader("Phase 6: Grain Disposal")
        st.markdown("**Discharge duration and residual weight**")
        fig = plot_phase_6(batch_mashing, batch_id, phases)
        st.pyplot(fig)
        plt.close(fig)

if __name__ == "__main__":
    main()
