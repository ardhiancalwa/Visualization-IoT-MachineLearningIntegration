import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
from collections import deque
import random

# =====================================================
# KONFIGURASI
# =====================================================
CSV_FILE = "iot_realtime_predictions.csv"
MAX_DATA_POINTS = 100
UPDATE_INTERVAL = 2  # seconds

# =====================================================
# STREAMLIT PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="IoT Realtime Dashboard (CSV Mode)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# INITIALIZE SESSION STATE
# =====================================================
if 'data_buffer' not in st.session_state:
    st.session_state.data_buffer = deque(maxlen=MAX_DATA_POINTS)
if 'csv_data' not in st.session_state:
    try:
        st.session_state.csv_data = pd.read_csv(CSV_FILE)
        st.session_state.csv_index = 0
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        st.stop()
if 'total_messages' not in st.session_state:
    st.session_state.total_messages = 0
if 'alert_count' not in st.session_state:
    st.session_state.alert_count = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'paused' not in st.session_state:
    st.session_state.paused = False

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def get_next_data():
    """Get next row from CSV in circular manner"""
    if st.session_state.csv_index >= len(st.session_state.csv_data):
        st.session_state.csv_index = 0
    
    row = st.session_state.csv_data.iloc[st.session_state.csv_index]
    st.session_state.csv_index += 1
    
    # Create data with current timestamp
    data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': float(row['temperature']),
        'humidity': float(row['humidity']),
        'prediction': str(row['prediction'])
    }
    
    return data

def get_dataframe():
    """Convert buffer to DataFrame"""
    if len(st.session_state.data_buffer) > 0:
        return pd.DataFrame(list(st.session_state.data_buffer))
    return pd.DataFrame()

def create_gauge(value, title, range_max, color):
    """Create gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title, 'font': {'size': 20}},
        delta={'reference': range_max * 0.5},
        gauge={
            'axis': {'range': [None, range_max]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, range_max * 0.33], 'color': "lightgray"},
                {'range': [range_max * 0.33, range_max * 0.66], 'color': "gray"},
                {'range': [range_max * 0.66, range_max], 'color': "darkgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': range_max * 0.9
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def create_timeseries_chart(df):
    """Create timeseries chart"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Temperature (°C)', 'Humidity (%)'),
        vertical_spacing=0.15
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['temperature'],
            mode='lines+markers',
            name='Temperature',
            line=dict(color='#FF6B6B', width=2),
            marker=dict(size=4)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['humidity'],
            mode='lines+markers',
            name='Humidity',
            line=dict(color='#4ECDC4', width=2),
            marker=dict(size=4)
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    
    fig.update_layout(
        height=500,
        showlegend=False,
        margin=dict(l=50, r=20, t=50, b=50),
        hovermode='x unified'
    )
    
    return fig

def create_prediction_pie(df):
    """Create pie chart"""
    if 'prediction' in df.columns:
        prediction_counts = df['prediction'].value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=prediction_counts.index,
            values=prediction_counts.values,
            hole=0.4,
            marker=dict(colors=['#51CF66', '#FF6B6B', '#FFA94D'])
        )])
        
        fig.update_layout(
            title="Prediction Distribution",
            height=300,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig
    return None

# =====================================================
# MAIN DASHBOARD
# =====================================================
def main():
    # Header
    st.title("🌡️ IoT Realtime Dashboard (CSV Simulation)")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.success("🟢 CSV Mode Active")
        st.info(f"**Source:** {CSV_FILE}")
        st.info(f"**Total Records:** {len(st.session_state.csv_data)}")
        
        st.markdown("---")
        
        # Statistics
        st.header("📊 Statistics")
        st.metric("Total Messages", st.session_state.total_messages)
        st.metric("Alert Count", st.session_state.alert_count)
        st.metric("Current Index", f"{st.session_state.csv_index}/{len(st.session_state.csv_data)}")
        
        if st.session_state.last_update:
            st.text("Last Update:")
            st.text(st.session_state.last_update.strftime("%H:%M:%S"))
        
        st.markdown("---")
        
        # Controls
        st.header("🎮 Controls")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏸️ Pause" if not st.session_state.paused else "▶️ Resume", use_container_width=True):
                st.session_state.paused = not st.session_state.paused
        
        with col2:
            if st.button("🔄 Clear", use_container_width=True):
                st.session_state.data_buffer.clear()
                st.session_state.total_messages = 0
                st.session_state.alert_count = 0
                st.session_state.csv_index = 0
                st.rerun()
        
        auto_refresh = st.checkbox("🔁 Auto Refresh", value=True)
        refresh_speed = st.slider("Refresh Speed (seconds)", 1, 10, UPDATE_INTERVAL)
        
        st.markdown("---")
        st.info("💡 This version simulates realtime data from CSV without MQTT")
    
    # Add new data if not paused
    if not st.session_state.paused:
        data = get_next_data()
        st.session_state.data_buffer.append(data)
        st.session_state.total_messages += 1
        st.session_state.last_update = datetime.now()
        
        # Check for alerts
        if data['temperature'] > 30 or data['humidity'] > 70:
            st.session_state.alert_count += 1
    
    # Get current data
    df = get_dataframe()
    
    if df.empty:
        st.warning("⏳ Initializing data...")
    else:
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Latest values
        latest = df.iloc[-1]
        
        # Row 1: Gauges
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.plotly_chart(
                create_gauge(latest['temperature'], "Temperature", 50, "#FF6B6B"),
                use_container_width=True
            )
        
        with col2:
            st.plotly_chart(
                create_gauge(latest['humidity'], "Humidity", 100, "#4ECDC4"),
                use_container_width=True
            )
        
        with col3:
            st.markdown("### 📋 Current Status")
            status_color = "🟢" if latest['prediction'] == 'Normal' else "🔴"
            st.markdown(f"## {status_color} {latest['prediction']}")
            st.metric("Temperature", f"{latest['temperature']:.1f}°C")
            st.metric("Humidity", f"{latest['humidity']:.1f}%")
        
        # Row 2: Time series
        st.markdown("---")
        st.markdown("### 📈 Historical Data")
        st.plotly_chart(create_timeseries_chart(df), use_container_width=True)
        
        # Row 3: Stats and Pie
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Statistical Summary")
            stats_df = df[['temperature', 'humidity']].describe().round(2)
            st.dataframe(stats_df, use_container_width=True)
        
        with col2:
            pie_fig = create_prediction_pie(df)
            if pie_fig:
                st.plotly_chart(pie_fig, use_container_width=True)
        
        # Row 4: Recent data
        st.markdown("---")
        st.markdown("### 📋 Recent Readings (Last 10)")
        recent_df = df.tail(10).sort_values('timestamp', ascending=False)
        recent_df['timestamp'] = recent_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
        
        # Alerts
        if st.session_state.alert_count > 0:
            st.markdown("---")
            st.warning(f"⚠️ **Alert:** {st.session_state.alert_count} anomalies detected!")
            
            anomalies = df[(df['temperature'] > 30) | (df['humidity'] > 70)]
            if not anomalies.empty:
                st.dataframe(anomalies.tail(5), use_container_width=True, hide_index=True)
    
    # Auto refresh
    if auto_refresh and not st.session_state.paused:
        time.sleep(refresh_speed)
        st.rerun()

if __name__ == "__main__":
    main()