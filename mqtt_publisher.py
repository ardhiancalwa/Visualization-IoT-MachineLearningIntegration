"""
MQTT Publisher - IoT Sensor Simulator
======================================
Script ini mensimulasikan sensor IoT yang mengirim data temperature dan humidity
ke MQTT broker untuk testing dashboard.

Author: IoT Engineer
"""

import paho.mqtt.client as mqtt
import time
import random
import json
from datetime import datetime

# =====================================================
# KONFIGURASI MQTT
# =====================================================
MQTT_BROKER = "broker.hivemq.com"  # Ganti dengan broker Anda
MQTT_PORT = 1883
MQTT_TOPIC_TEMP = "iot/temperature"
MQTT_TOPIC_HUMIDITY = "iot/humidity"
MQTT_TOPIC_COMBINED = "iot/sensors"
MQTT_CLIENT_ID = f"iot_sensor_{random.randint(1000, 9999)}"

# =====================================================
# KONFIGURASI SENSOR SIMULATION
# =====================================================
TEMP_MIN = 15.0
TEMP_MAX = 35.0
HUMIDITY_MIN = 30.0
HUMIDITY_MAX = 80.0
PUBLISH_INTERVAL = 2  # seconds

# =====================================================
# MQTT CALLBACKS
# =====================================================
def on_connect(client, userdata, flags, rc):
    """Callback ketika koneksi berhasil"""
    if rc == 0:
        print(f"✅ Connected to MQTT Broker: {MQTT_BROKER}")
        print(f"📡 Publishing to topics:")
        print(f"   - {MQTT_TOPIC_TEMP}")
        print(f"   - {MQTT_TOPIC_HUMIDITY}")
        print(f"   - {MQTT_TOPIC_COMBINED}")
    else:
        print(f"❌ Failed to connect, return code {rc}")

def on_publish(client, userdata, mid):
    """Callback ketika publish berhasil"""
    pass

# =====================================================
# SENSOR SIMULATION
# =====================================================
def generate_sensor_data():
    """Generate random sensor data yang realistis"""
    # Base values dengan trend
    base_temp = 25.0 + random.uniform(-5, 5)
    base_humidity = 60.0 + random.uniform(-15, 15)
    
    # Add small variations untuk smooth changes
    temperature = round(base_temp + random.uniform(-1, 1), 2)
    humidity = round(base_humidity + random.uniform(-2, 2), 2)
    
    # Ensure within bounds
    temperature = max(TEMP_MIN, min(TEMP_MAX, temperature))
    humidity = max(HUMIDITY_MIN, min(HUMIDITY_MAX, humidity))
    
    return temperature, humidity

def simulate_anomaly():
    """Simulasi anomaly dengan probabilitas rendah"""
    if random.random() < 0.1:  # 10% chance
        anomaly_type = random.choice(['high_temp', 'low_temp', 'high_humidity', 'low_humidity'])
        
        if anomaly_type == 'high_temp':
            return random.uniform(35, 40), random.uniform(60, 70)
        elif anomaly_type == 'low_temp':
            return random.uniform(5, 10), random.uniform(40, 50)
        elif anomaly_type == 'high_humidity':
            return random.uniform(28, 32), random.uniform(85, 95)
        else:  # low_humidity
            return random.uniform(22, 28), random.uniform(15, 25)
    
    return None, None

# =====================================================
# MAIN PUBLISHER
# =====================================================
def main():
    print("=" * 60)
    print("🌡️ IoT MQTT Sensor Simulator")
    print("=" * 60)
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Client ID: {MQTT_CLIENT_ID}")
    print(f"Publish Interval: {PUBLISH_INTERVAL} seconds")
    print("=" * 60)
    print()
    
    # Setup MQTT Client
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    # Connect to broker
    try:
        print("🔄 Connecting to MQTT Broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(2)  # Wait for connection
        
        print("✅ Connection established!")
        print("📊 Starting data transmission...\n")
        
        message_count = 0
        
        while True:
            message_count += 1
            
            # Check for anomaly
            anomaly_temp, anomaly_humidity = simulate_anomaly()
            
            if anomaly_temp is not None:
                temperature = anomaly_temp
                humidity = anomaly_humidity
                print(f"⚠️  ANOMALY GENERATED!")
            else:
                temperature, humidity = generate_sensor_data()
            
            # Publish to individual topics
            client.publish(MQTT_TOPIC_TEMP, str(temperature))
            client.publish(MQTT_TOPIC_HUMIDITY, str(humidity))
            
            # Publish to combined topic (JSON)
            combined_data = {
                "temperature": temperature,
                "humidity": humidity,
                "timestamp": datetime.now().isoformat(),
                "sensor_id": MQTT_CLIENT_ID
            }
            client.publish(MQTT_TOPIC_COMBINED, json.dumps(combined_data))
            
            # Log output
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{message_count:04d}] {timestamp} | Temp: {temperature:5.2f}°C | Humidity: {humidity:5.2f}%")
            
            time.sleep(PUBLISH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping sensor simulation...")
        client.loop_stop()
        client.disconnect()
        print("✅ Disconnected from broker")
        print(f"📊 Total messages sent: {message_count}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()