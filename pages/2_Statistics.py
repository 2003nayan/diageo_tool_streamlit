#!/usr/bin/env python3
"""
Statistics Page - Batch information, static data, and multi-batch statistics
"""

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Statistics",
    page_icon="📈",
    layout="wide"
)

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

# ============== MAIN PAGE ==============
def main():
    st.title("📈 Statistics")
    st.markdown("**Batch information, parametric data, and multi-batch statistical analysis**")
    
    # Check if data is loaded
    if 'mashing_df' not in st.session_state:
        st.warning("⚠️ Please visit the main page first to load data!")
        st.page_link("v3.py", label="Go to Main Page", icon="🏠")
        return
    
    mashing_df = st.session_state.mashing_df
    parametric_df = st.session_state.parametric_df
    sensory_df = st.session_state.get('sensory_df', pd.DataFrame())
    selected_batches = st.session_state.get('selected_batches', [])
    
    if not selected_batches:
        st.warning("⚠️ No batch selected. Please select batch(es) on the main page.")
        st.page_link("v3.py", label="Go to Main Page", icon="🏠")
        return
    
    st.info(f"📦 Selected batches: **{', '.join(selected_batches)}**")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📋 Info Panel",
        "⚙️ Static Data",
        "📊 Multi-Batch Stats"
    ])
    
    # ========== TAB 1: INFO PANEL ==========
    with tab1:
        st.subheader("Batch Information")
        
        for batch_id in selected_batches:
            batch_mashing = mashing_df[mashing_df['batch_no'] == batch_id].copy()
            batch_mashing = batch_mashing.sort_values('timestamp')
            
            with st.expander(f"📦 Batch: {batch_id}", expanded=True):
                if not batch_mashing.empty:
                    process_start = batch_mashing['timestamp'].min()
                    process_end = batch_mashing['timestamp'].max()
                    duration = (process_end - process_start).total_seconds() / 60
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Process Start", str(process_start)[:19])
                    with col2:
                        st.metric("Process End", str(process_end)[:19])
                    with col3:
                        st.metric("Duration", f"{duration:.1f} min")
                    with col4:
                        st.metric("Data Points", len(batch_mashing))
                    
                    # Sensory notes
                    batch_num = get_batch_numeric(batch_id)
                    if sensory_df is not None and not sensory_df.empty and batch_num:
                        sensory = sensory_df[sensory_df['Blinding_Code'].astype(str).str.contains(str(batch_num))]
                        if not sensory.empty:
                            row = sensory.iloc[0]
                            notes = []
                            if row.get('Cooked', 0) == 1: notes.append('🔥 Cooked')
                            if row.get('Starchy', 0) == 1: notes.append('🌾 Starchy')
                            if row.get('Husky', 0) == 1: notes.append('🌿 Husky')
                            if row.get('Cereal_Grainy', 0) == 1: notes.append('🥣 Cereal/Grainy')
                            
                            st.markdown("**Sensory Notes:**")
                            if notes:
                                st.write(", ".join(notes))
                            else:
                                st.write("✅ Clean (no off-notes)")
                else:
                    st.warning("No data available for this batch")
    
    # ========== TAB 2: STATIC DATA ==========
    with tab2:
        st.subheader("Parametric Data")
        
        batch_id = selected_batches[0]
        st.caption(f"Showing static data for: {batch_id}")
        
        batch_num = get_batch_numeric(batch_id)
        param_row = parametric_df[parametric_df['batch_no'] == batch_num]
        
        if param_row.empty:
            st.warning("No parametric data available for this batch")
        else:
            # Display as a formatted table
            data_display = []
            for col in param_row.columns:
                if col != 'batch_no':
                    value = param_row[col].iloc[0]
                    if pd.notna(value):
                        display_name = col.replace('_', ' ').title()
                        if isinstance(value, (int, float)):
                            data_display.append({
                                'Parameter': display_name,
                                'Value': f"{value:.2f}"
                            })
                        else:
                            data_display.append({
                                'Parameter': display_name,
                                'Value': str(value)
                            })
            
            if data_display:
                df_display = pd.DataFrame(data_display)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # ========== TAB 3: MULTI-BATCH STATS ==========
    with tab3:
        st.subheader("Multi-Batch Statistical Comparison")
        
        if len(selected_batches) < 2:
            st.warning("⚠️ Please select at least 2 batches on the main page for comparison!")
        else:
            # Collect data for all batches
            all_data = []
            for batch_id in selected_batches:
                batch_mashing = mashing_df[mashing_df['batch_no'] == batch_id].copy()
                if not batch_mashing.empty:
                    all_data.append({
                        'Batch': batch_id,
                        'Mash Temp (°C)': batch_mashing['mashing_temp'].mean(),
                        'Max Mash Temp': batch_mashing['mashing_temp'].max(),
                        'Min Mash Temp': batch_mashing['mashing_temp'].min(),
                        'Water Flow (L/hr)': batch_mashing['sparging_mashing_water_flow'].mean(),
                        'Max Water Flow': batch_mashing['sparging_mashing_water_flow'].max(),
                        'Wort Temp (°C)': batch_mashing['wort_receiver_temp'].mean(),
                        'Grist Used (kg)': batch_mashing['greast_case_weight'].iloc[0] - batch_mashing['greast_case_weight'].min(),
                        'Duration (min)': (batch_mashing['timestamp'].max() - batch_mashing['timestamp'].min()).total_seconds() / 60
                    })
            
            if not all_data:
                st.warning("No data available for selected batches")
            else:
                df_stats = pd.DataFrame(all_data)
                
                # Interpretation guide
                with st.expander("📖 How to Interpret Statistics", expanded=False):
                    st.markdown("""
                    | Metric | Meaning |
                    |--------|---------|
                    | **Average (Avg)** | Mean value - represents typical/normal for your process |
                    | **Minimum (Min)** | Lowest recorded - unusually low values may indicate issues |
                    | **Maximum (Max)** | Highest recorded - unusually high values may indicate anomalies |
                    | **Std Dev (SD)** | Measures consistency - LOW (<5%): Excellent, MODERATE (5-15%): Good, HIGH (>15%): Variable |
                    """)
                
                # Summary statistics
                st.markdown("### 📊 Statistical Summary")
                
                params = ['Mash Temp (°C)', 'Water Flow (L/hr)', 'Wort Temp (°C)', 'Grist Used (kg)', 'Duration (min)']
                
                summary_data = []
                for param in params:
                    if param in df_stats.columns:
                        avg_val = df_stats[param].mean()
                        min_val = df_stats[param].min()
                        max_val = df_stats[param].max()
                        sd_val = df_stats[param].std()
                        
                        # Consistency level
                        if avg_val > 0:
                            cv = (sd_val / avg_val) * 100
                            if cv < 5:
                                consistency = "🟢 Excellent"
                            elif cv < 15:
                                consistency = "🟡 Good"
                            elif cv < 25:
                                consistency = "🟠 Moderate"
                            else:
                                consistency = "🔴 Variable"
                        else:
                            consistency = "N/A"
                        
                        summary_data.append({
                            'Parameter': param,
                            'Average': f"{avg_val:.2f}",
                            'Min': f"{min_val:.2f}",
                            'Max': f"{max_val:.2f}",
                            'Std Dev': f"{sd_val:.2f}",
                            'Consistency': consistency
                        })
                
                df_summary = pd.DataFrame(summary_data)
                st.dataframe(df_summary, use_container_width=True, hide_index=True)
                
                # Individual batch values
                st.markdown("### 📋 Individual Batch Values")
                st.caption("Review individual values to identify outliers")
                
                display_cols = ['Batch', 'Mash Temp (°C)', 'Water Flow (L/hr)', 'Grist Used (kg)', 'Duration (min)']
                df_display = df_stats[display_cols].round(2)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # Recommendations
                st.markdown("### 💡 Interpretation Tips")
                st.info("""
                - **High Standard Deviation?** → Check individual batch values above to identify which batch(es) are causing variation
                - **Large Min-Max gap?** → Investigate the extreme batches for process anomalies
                - **Unusual individual values?** → Compare to the average to spot outliers
                """)

if __name__ == "__main__":
    main()
