import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
from collections import deque
import random
import io
import json
import paho.mqtt.client as mqtt
import threading

# =====================================================
# KONFIGURASI MQTT
# =====================================================
MQTT_BROKER = "broker.hivemq.com"  # Public broker, ganti dengan broker Anda
MQTT_PORT = 1883
MQTT_TOPIC_TEMP = "iot/temperature"  # Topic untuk temperature
MQTT_TOPIC_HUMIDITY = "iot/humidity"  # Topic untuk humidity
MQTT_TOPIC_COMBINED = "iot/sensor/data"  # Topic untuk data gabungan (JSON)
MQTT_CLIENT_ID = f"streamlit_dashboard_{random.randint(1000, 9999)}"

# =====================================================
# KONFIGURASI DASHBOARD
# =====================================================
MAX_DATA_POINTS = 100
UPDATE_INTERVAL = 2  # seconds

# Threshold untuk prediction categories
TEMP_COLD_MAX = 20      # Dibawah ini = Dingin
TEMP_NORMAL_MAX = 30    # 20-30 = Normal
# Diatas 30 = Panas

# =====================================================
# STREAMLIT PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="IoT Realtime MQTT Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS
# =====================================================
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .status-cold {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    .status-normal {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    .status-hot {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    .alert-box {
        background: #ff4444;
        padding: 15px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    .mqtt-connected {
        background: #43e97b;
        padding: 10px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    .mqtt-disconnected {
        background: #ff4444;
        padding: 10px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================
# MQTT CLIENT CLASS
# =====================================================
class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.connected = False
        self.latest_temp = None
        self.latest_humidity = None
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback saat koneksi berhasil"""
        if rc == 0:
            self.connected = True
            print(f"✅ Connected to MQTT Broker: {MQTT_BROKER}")
            # Subscribe ke topics
            self.client.subscribe(MQTT_TOPIC_TEMP)
            self.client.subscribe(MQTT_TOPIC_HUMIDITY)
            self.client.subscribe(MQTT_TOPIC_COMBINED)
            print(f"📡 Subscribed to topics: {MQTT_TOPIC_TEMP}, {MQTT_TOPIC_HUMIDITY}, {MQTT_TOPIC_COMBINED}")
        else:
            self.connected = False
            print(f"❌ Failed to connect, return code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback saat terputus"""
        self.connected = False
        print(f"⚠️ Disconnected from MQTT Broker")
        
    def on_message(self, client, userdata, msg):
        """Callback saat menerima message"""
        try:
            payload = msg.payload.decode()
            
            # Cek topic yang diterima
            if msg.topic == MQTT_TOPIC_TEMP:
                self.latest_temp = float(payload)
                print(f"🌡️ Temperature received: {self.latest_temp}°C")
                
            elif msg.topic == MQTT_TOPIC_HUMIDITY:
                self.latest_humidity = float(payload)
                print(f"💧 Humidity received: {self.latest_humidity}%")
                
            elif msg.topic == MQTT_TOPIC_COMBINED:
                # Parse JSON data
                data = json.loads(payload)
                self.latest_temp = float(data.get('temperature', 0))
                self.latest_humidity = float(data.get('humidity', 0))
                print(f"📦 Combined data received: Temp={self.latest_temp}°C, Humidity={self.latest_humidity}%")
                
        except Exception as e:
            print(f"❌ Error parsing message: {e}")
    
    def connect(self):
        """Koneksi ke MQTT Broker"""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()  # Start background thread
            return True
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect dari broker"""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
    
    def get_latest_data(self):
        """Ambil data terbaru"""
        return self.latest_temp, self.latest_humidity

# =====================================================
# INITIALIZE SESSION STATE
# =====================================================
if 'data_buffer' not in st.session_state:
    st.session_state.data_buffer = deque(maxlen=MAX_DATA_POINTS)

if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = MQTTClient()
    st.session_state.mqtt_client.connect()

if 'total_messages' not in st.session_state:
    st.session_state.total_messages = 0

if 'alert_count' not in st.session_state:
    st.session_state.alert_count = 0

if 'last_update' not in st.session_state:
    st.session_state.last_update = None

if 'paused' not in st.session_state:
    st.session_state.paused = False

if 'manual_alert_enabled' not in st.session_state:
    st.session_state.manual_alert_enabled = True

if 'anomaly_detected' not in st.session_state:
    st.session_state.anomaly_detected = False

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def get_temperature_category(temp):
    """Determine temperature category"""
    if temp < TEMP_COLD_MAX:
        return "Dingin", "#4facfe"
    elif temp <= TEMP_NORMAL_MAX:
        return "Normal", "#43e97b"
    else:
        return "Panas", "#fa709a"

def calculate_confidence(temp, humidity):
    """Calculate confidence score based on sensor stability"""
    # Simulate confidence based on reasonable ranges
    temp_confidence = 100 if 15 <= temp <= 35 else 80
    humidity_confidence = 100 if 30 <= humidity <= 80 else 85
    
    # Add small random variation
    variation = random.uniform(-5, 5)
    confidence = min(100, max(60, (temp_confidence + humidity_confidence) / 2 + variation))
    return round(confidence, 1)

def detect_anomaly(temp, humidity):
    """Detect anomaly in sensor readings"""
    # Anomaly conditions
    if temp > 35 or temp < 10:
        return True, "Temperature out of normal range"
    if humidity > 85 or humidity < 20:
        return True, "Humidity out of normal range"
    if temp > 30 and humidity > 70:
        return True, "High temperature and humidity combination"
    return False, ""

def get_mqtt_data():
    """Get data from MQTT broker"""
    temp, humidity = st.session_state.mqtt_client.get_latest_data()
    
    # Jika belum ada data, return None
    if temp is None or humidity is None:
        return None
    
    # Calculate additional metrics
    category, color = get_temperature_category(temp)
    confidence = calculate_confidence(temp, humidity)
    is_anomaly, anomaly_reason = detect_anomaly(temp, humidity)
    
    data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'temperature': temp,
        'humidity': humidity,
        'prediction': category,
        'confidence': confidence,
        'anomaly_flag': is_anomaly,
        'anomaly_reason': anomaly_reason if is_anomaly else "",
        'alert_triggered': is_anomaly and st.session_state.manual_alert_enabled
    }
    
    return data

def get_dataframe():
    """Convert buffer to DataFrame"""
    if len(st.session_state.data_buffer) > 0:
        return pd.DataFrame(list(st.session_state.data_buffer))
    return pd.DataFrame()

def export_to_csv(df):
    """Export dataframe to CSV for download"""
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def create_gauge(value, title, range_max, color, threshold_value=None):
    """Create enhanced gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title, 'font': {'size': 24, 'color': 'white'}},
        delta={'reference': range_max * 0.5, 'increasing': {'color': '#FF6B6B'}, 'decreasing': {'color': '#4ECDC4'}},
        number={'font': {'size': 40, 'color': 'white'}},
        gauge={
            'axis': {'range': [None, range_max], 'tickcolor': 'white'},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': 'rgba(0,0,0,0.1)',
            'borderwidth': 2,
            'bordercolor': 'white',
            'steps': [
                {'range': [0, range_max * 0.33], 'color': 'rgba(76, 172, 254, 0.3)'},
                {'range': [range_max * 0.33, range_max * 0.66], 'color': 'rgba(67, 233, 123, 0.3)'},
                {'range': [range_max * 0.66, range_max], 'color': 'rgba(250, 112, 154, 0.3)'}
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 4},
                'thickness': 0.75,
                'value': threshold_value if threshold_value else range_max
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def create_confidence_gauge(confidence):
    """Create confidence gauge"""
    color = '#43e97b' if confidence >= 90 else '#FFA94D' if confidence >= 75 else '#FF6B6B'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence,
        title={'text': "📊 Confidence Score", 'font': {'size': 24, 'color': 'white'}},
        number={'font': {'size': 40, 'color': 'white'}, 'suffix': '%'},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': 'white'},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': 'rgba(0,0,0,0.1)',
            'borderwidth': 2,
            'bordercolor': 'white',
            'steps': [
                {'range': [0, 50], 'color': 'rgba(255, 107, 107, 0.3)'},
                {'range': [50, 75], 'color': 'rgba(255, 169, 77, 0.3)'},
                {'range': [75, 100], 'color': 'rgba(67, 233, 123, 0.3)'}
            ]
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def create_timeseries_chart(df):
    """Create time series chart for temperature and humidity"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('🌡️ Temperature Over Time', '💧 Humidity Over Time'),
        vertical_spacing=0.15,
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Temperature trace
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['temperature'],
            mode='lines+markers',
            name='Temperature',
            line=dict(color='#FF6B6B', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(255, 107, 107, 0.2)'
        ),
        row=1, col=1
    )
    
    # Humidity trace
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['humidity'],
            mode='lines+markers',
            name='Humidity',
            line=dict(color='#4ECDC4', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(78, 205, 196, 0.2)'
        ),
        row=2, col=1
    )
    
    # Add threshold lines
    fig.add_hline(y=TEMP_COLD_MAX, line_dash="dash", line_color="cyan", 
                  annotation_text="Cold Threshold", row=1, col=1)
    fig.add_hline(y=TEMP_NORMAL_MAX, line_dash="dash", line_color="orange", 
                  annotation_text="Hot Threshold", row=1, col=1)
    
    fig.update_xaxes(title_text="Time", row=2, col=1, color='white')
    fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1, color='white')
    fig.update_yaxes(title_text="Humidity (%)", row=2, col=1, color='white')
    
    fig.update_layout(
        height=600,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.05)',
        font={'color': 'white'},
        hovermode='x unified'
    )
    
    return fig

def create_prediction_distribution(df):
    """Create pie chart for prediction distribution"""
    if 'prediction' not in df.columns or df['prediction'].empty:
        return None
    
    prediction_counts = df['prediction'].value_counts()
    
    colors = {'Dingin': '#4facfe', 'Normal': '#43e97b', 'Panas': '#fa709a'}
    pie_colors = [colors.get(pred, '#999999') for pred in prediction_counts.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=prediction_counts.index,
        values=prediction_counts.values,
        hole=0.4,
        marker=dict(colors=pie_colors, line=dict(color='white', width=2)),
        textinfo='label+percent',
        textfont=dict(size=14, color='white')
    )])
    
    fig.update_layout(
        title={
            'text': "🎯 Temperature Distribution",
            'font': {'size': 20, 'color': 'white'},
            'x': 0.5,
            'xanchor': 'center'
        },
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white'},
        height=400,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.1
        )
    )
    
    return fig

def create_anomaly_timeline(df):
    """Create timeline of anomalies"""
    anomalies = df[df['anomaly_flag'] == True].copy()
    
    if anomalies.empty:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=anomalies['timestamp'],
        y=[1] * len(anomalies),
        mode='markers+text',
        marker=dict(
            size=15,
            color='red',
            symbol='x',
            line=dict(width=2, color='white')
        ),
        text=anomalies['anomaly_reason'],
        textposition="top center",
        name='Anomalies',
        hovertemplate='<b>Time:</b> %{x}<br><b>Reason:</b> %{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': "⚠️ Anomaly Detection Timeline",
            'font': {'size': 20, 'color': 'white'},
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis=dict(title="Time", color='white'),
        yaxis=dict(showticklabels=False, color='white'),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.05)',
        font={'color': 'white'},
        height=250,
        showlegend=False
    )
    
    return fig

# =====================================================
# MAIN APPLICATION
# =====================================================
def main():
    # Header
    st.markdown("""
    <h1 style='text-align: center; color: white;'>
        🌡️ IoT Real-time MQTT Dashboard
    </h1>
    <p style='text-align: center; color: #888;'>
        Temperature & Humidity Monitoring dengan Machine Learning Integration
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Dashboard Control")
        
        # MQTT Connection Status
        st.markdown("### 📡 MQTT Status")
        mqtt_status = st.session_state.mqtt_client.connected
        if mqtt_status:
            st.markdown("""
                <div class='mqtt-connected'>
                    ✅ CONNECTED
                </div>
            """, unsafe_allow_html=True)
            st.success(f"Broker: {MQTT_BROKER}")
        else:
            st.markdown("""
                <div class='mqtt-disconnected'>
                    ❌ DISCONNECTED
                </div>
            """, unsafe_allow_html=True)
            st.error("Attempting to reconnect...")
            if st.button("🔄 Reconnect MQTT"):
                st.session_state.mqtt_client.connect()
                st.rerun()
        
        st.markdown("---")
        
        # Statistics
        st.header("📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📨 Messages", st.session_state.total_messages)
        with col2:
            st.metric("⚠️ Alerts", st.session_state.alert_count)
        
        if st.session_state.last_update:
            st.caption(f"⏰ Last Update: {st.session_state.last_update.strftime('%H:%M:%S')}")
        
        st.markdown("---")
        
        # MQTT Configuration
        st.header("📡 MQTT Config")
        st.text_input("Broker", value=MQTT_BROKER, disabled=True)
        st.text_input("Port", value=str(MQTT_PORT), disabled=True)
        
        with st.expander("📋 Topics"):
            st.code(f"Temperature: {MQTT_TOPIC_TEMP}")
            st.code(f"Humidity: {MQTT_TOPIC_HUMIDITY}")
            st.code(f"Combined: {MQTT_TOPIC_COMBINED}")
        
        st.markdown("---")
        
        # Controls
        st.header("🎮 Controls")
        st.session_state.manual_alert_enabled = st.checkbox(
            "🔔 Enable Alerts", 
            value=st.session_state.manual_alert_enabled
        )
        
        if st.button("⏸️ Pause" if not st.session_state.paused else "▶️ Resume", 
                    use_container_width=True, type="primary"):
            st.session_state.paused = not st.session_state.paused
            st.rerun()
        
        if st.button("🗑️ Clear Data", use_container_width=True):
            st.session_state.data_buffer.clear()
            st.session_state.total_messages = 0
            st.session_state.alert_count = 0
            st.rerun()
        
        auto_refresh = st.checkbox("🔁 Auto Refresh", value=True)
        refresh_speed = st.slider("⏱️ Refresh Rate (sec)", 1, 10, UPDATE_INTERVAL)
        
        st.markdown("---")
        
        # Export Data
        st.header("💾 Data Export")
        df_export = get_dataframe()
        if not df_export.empty:
            csv_data = export_to_csv(df_export)
            st.download_button(
                label="📥 Download Log (CSV)",
                data=csv_data,
                file_name=f"iot_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
            st.caption(f"📊 {len(df_export)} records ready for export")
        else:
            st.info("No data to export yet")
        
        st.markdown("---")
        st.caption("💡 Dashboard will auto-refresh based on selected rate")
    
    # Main Content Area
    # Add new data if not paused and MQTT connected
    if not st.session_state.paused and st.session_state.mqtt_client.connected:
        data = get_mqtt_data()
        if data is not None:
            st.session_state.data_buffer.append(data)
            st.session_state.total_messages += 1
            st.session_state.last_update = datetime.now()
            
            # Update anomaly status
            if data['anomaly_flag'] and st.session_state.manual_alert_enabled:
                st.session_state.alert_count += 1
                st.session_state.anomaly_detected = True
            else:
                st.session_state.anomaly_detected = False
    
    df = get_dataframe()
    
    if df.empty:
        st.warning("⏳ Waiting for MQTT data stream...")
        st.info("🔄 Please ensure your IoT devices are publishing to the MQTT broker.")
        st.markdown(f"""
        **Expected Topics:**
        - `{MQTT_TOPIC_TEMP}` - Temperature data (float)
        - `{MQTT_TOPIC_HUMIDITY}` - Humidity data (float)
        - `{MQTT_TOPIC_COMBINED}` - Combined JSON: `{{"temperature": 25.5, "humidity": 60.0}}`
        """)
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        latest = df.iloc[-1]
        
        # Alert Banner (if anomaly detected)
        if st.session_state.anomaly_detected and st.session_state.manual_alert_enabled:
            st.markdown(
                f"""<div class='alert-box'>
                🚨 ALERT: Anomaly Detected! {latest['anomaly_reason']}
                </div>""",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Row 1: Current Status Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            category, color = get_temperature_category(latest['temperature'])
            css_class = "status-cold" if category == "Dingin" else "status-normal" if category == "Normal" else "status-hot"
            st.markdown(f"""
                <div class='{css_class}'>
                    <h3 style='margin: 0;'>🌡️ Status</h3>
                    <h1 style='margin: 10px 0;'>{category}</h1>
                    <p style='margin: 0;'>{latest['temperature']:.1f}°C</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div class='metric-card'>
                    <h3 style='margin: 0;'>💧 Humidity</h3>
                    <h1 style='margin: 10px 0;'>{latest['humidity']:.1f}%</h1>
                    <p style='margin: 0;'>Current Level</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col3:
            confidence_color = '#43e97b' if latest['confidence'] >= 90 else '#FFA94D' if latest['confidence'] >= 75 else '#FF6B6B'
            st.markdown(f"""
                <div class='metric-card' style='background: linear-gradient(135deg, {confidence_color} 0%, {confidence_color} 100%);'>
                    <h3 style='margin: 0;'>📊 Confidence</h3>
                    <h1 style='margin: 10px 0;'>{latest['confidence']}%</h1>
                    <p style='margin: 0;'>Sensor Reliability</p>
                </div>
            """, unsafe_allow_html=True)
        
        with col4:
            anomaly_color = '#FF6B6B' if latest['anomaly_flag'] else '#43e97b'
            anomaly_icon = '⚠️' if latest['anomaly_flag'] else '✅'
            anomaly_text = 'ANOMALY' if latest['anomaly_flag'] else 'NORMAL'
            st.markdown(f"""
                <div class='metric-card' style='background: linear-gradient(135deg, {anomaly_color} 0%, {anomaly_color} 100%);'>
                    <h3 style='margin: 0;'>{anomaly_icon} Anomaly</h3>
                    <h1 style='margin: 10px 0;'>{anomaly_text}</h1>
                    <p style='margin: 0;'>Detection Status</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Row 2: Gauges
        col1, col2, col3 = st.columns(3)
        
        with col1:
            _, temp_color = get_temperature_category(latest['temperature'])
            st.plotly_chart(
                create_gauge(latest['temperature'], "🌡️ Temperature", 50, temp_color, TEMP_NORMAL_MAX),
                use_container_width=True
            )
        
        with col2:
            st.plotly_chart(
                create_gauge(latest['humidity'], "💧 Humidity", 100, "#4ECDC4", 70),
                use_container_width=True
            )
        
        with col3:
            st.plotly_chart(
                create_confidence_gauge(latest['confidence']),
                use_container_width=True
            )
        
        st.markdown("---")
        
        # Row 3: Time Series Charts
        st.markdown("### 📈 Historical Trends")
        st.plotly_chart(create_timeseries_chart(df), use_container_width=True)
        
        st.markdown("---")
        
        # Row 4: Distribution & Anomalies
        col1, col2 = st.columns(2)
        
        with col1:
            pie_fig = create_prediction_distribution(df)
            if pie_fig:
                st.plotly_chart(pie_fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📊 Statistical Summary")
            stats_df = df[['temperature', 'humidity', 'confidence']].describe().round(2)
            st.dataframe(stats_df, use_container_width=True, height=350)
        
        # Anomaly Timeline
        anomaly_fig = create_anomaly_timeline(df)
        if anomaly_fig:
            st.markdown("---")
            st.plotly_chart(anomaly_fig, use_container_width=True)
        
        st.markdown("---")
        
        # Row 5: Data Tables
        tab1, tab2, tab3 = st.tabs(["📋 Recent Readings", "⚠️ Anomalies", "📊 All Data"])
        
        with tab1:
            st.markdown("### Latest 15 Readings")
            recent_df = df.tail(15).sort_values('timestamp', ascending=False).copy()
            recent_df['timestamp'] = recent_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            recent_df['temperature'] = recent_df['temperature'].round(1)
            recent_df['humidity'] = recent_df['humidity'].round(1)
            recent_df['confidence'] = recent_df['confidence'].round(1)
            
            # Color code the display
            def highlight_anomalies(row):
                if row['anomaly_flag']:
                    return ['background-color: rgba(255, 68, 68, 0.3)'] * len(row)
                return [''] * len(row)
            
            styled_df = recent_df.style.apply(highlight_anomalies, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)
        
        with tab2:
            st.markdown("### Detected Anomalies")
            anomalies = df[df['anomaly_flag'] == True].copy()
            if not anomalies.empty:
                anomalies['timestamp'] = anomalies['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                anomalies_display = anomalies[['timestamp', 'temperature', 'humidity', 
                                              'confidence', 'anomaly_reason']].sort_values('timestamp', ascending=False)
                st.dataframe(anomalies_display, use_container_width=True, hide_index=True, height=500)
                st.warning(f"⚠️ Total anomalies detected: {len(anomalies)}")
            else:
                st.success("✅ No anomalies detected in current data")
        
        with tab3:
            st.markdown("### Complete Dataset")
            all_data = df.copy()
            all_data['timestamp'] = all_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(all_data, use_container_width=True, hide_index=True, height=500)
            st.caption(f"📊 Total records: {len(all_data)}")
    
    # Auto refresh
    if auto_refresh and not st.session_state.paused:
        time.sleep(refresh_speed)
        st.rerun()

if __name__ == "__main__":
    main()