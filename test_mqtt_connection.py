import paho.mqtt.client as mqtt
import time
import sys

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/sensors/data"

message_count = 0
connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        print(f"✅ SUCCESS: Connected to {MQTT_BROKER}")
        print(f"📡 Subscribing to topic: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
        connected = True
    else:
        print(f"❌ FAILED: Connection failed with code {rc}")
        connected = False

def on_message(client, userdata, msg):
    global message_count
    message_count += 1
    payload = msg.payload.decode()
    print(f"📥 Message {message_count}: {payload[:100]}...")  

def on_disconnect(client, userdata, rc):
    global connected
    print(f"⚠️ Disconnected with code: {rc}")
    connected = False

print("=" * 60)
print("🧪 MQTT Connection Test")
print("=" * 60)
print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
print(f"Topic: {MQTT_TOPIC}")
print("-" * 60)

client = mqtt.Client(client_id=f"test_client_{int(time.time())}")
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

print("Connecting to broker...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

print("\n⏳ Waiting for messages (30 seconds)...")
print("💡 Make sure mqtt_publisher.py is running!")
print("-" * 60)

for i in range(30):
    time.sleep(1)
    if connected and message_count > 0:
        print(f"\n{'=' * 60}")
        print(f"✅ SUCCESS! Received {message_count} messages in {i+1} seconds")
        print(f"{'=' * 60}")
        print("\n✅ MQTT is working properly!")
        print("👉 The problem might be in the Streamlit dashboard code.")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)
    
    if not connected:
        print(f"⚠️ Not connected yet... ({i+1}/30)")

print(f"\n{'=' * 60}")
if message_count == 0:
    print("❌ NO MESSAGES RECEIVED!")
    print("\n🔍 Possible issues:")
    print("1. mqtt_publisher.py is not running")
    print("2. Publisher using different broker/topic")
    print("3. Firewall blocking port 1883")
    print("4. Internet connection issue")
else:
    print(f"✅ Received {message_count} messages")

print(f"{'=' * 60}")
client.loop_stop()
client.disconnect()