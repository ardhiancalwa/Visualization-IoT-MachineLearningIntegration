"""
MQTT Connection Test Script
============================
Script untuk test koneksi ke MQTT broker sebelum menjalankan dashboard
"""

import paho.mqtt.client as mqtt
import time
import sys

# Import config (gunakan default values jika config.py tidak ada)
try:
    from config import (
        MQTT_BROKER, MQTT_PORT, 
        MQTT_TOPIC_TEMP, MQTT_TOPIC_HUMIDITY, MQTT_TOPIC_COMBINED,
        MQTT_USERNAME, MQTT_PASSWORD
    )
except ImportError:
    print("⚠️  config.py not found, using default values")
    MQTT_BROKER = "broker.hivemq.com"
    MQTT_PORT = 1883
    MQTT_TOPIC_TEMP = "iot/temperature"
    MQTT_TOPIC_HUMIDITY = "iot/humidity"
    MQTT_TOPIC_COMBINED = "iot/sensors"
    MQTT_USERNAME = None
    MQTT_PASSWORD = None

# Test results
test_results = {
    'connection': False,
    'subscription': False,
    'publish': False,
    'receive': False
}

messages_received = []

def on_connect(client, userdata, flags, rc):
    """Callback saat koneksi berhasil"""
    if rc == 0:
        print("✅ Connection successful!")
        test_results['connection'] = True
        
        # Subscribe to test topics
        client.subscribe(MQTT_TOPIC_TEMP)
        client.subscribe(MQTT_TOPIC_HUMIDITY)
        client.subscribe(MQTT_TOPIC_COMBINED)
        print(f"📡 Subscribed to topics:")
        print(f"   - {MQTT_TOPIC_TEMP}")
        print(f"   - {MQTT_TOPIC_HUMIDITY}")
        print(f"   - {MQTT_TOPIC_COMBINED}")
        test_results['subscription'] = True
    else:
        print(f"❌ Connection failed with code {rc}")
        print(f"   Error codes:")
        print(f"   0: Success")
        print(f"   1: Incorrect protocol version")
        print(f"   2: Invalid client identifier")
        print(f"   3: Server unavailable")
        print(f"   4: Bad username or password")
        print(f"   5: Not authorized")

def on_message(client, userdata, msg):
    """Callback saat menerima message"""
    print(f"📨 Message received on topic: {msg.topic}")
    print(f"   Payload: {msg.payload.decode()}")
    messages_received.append((msg.topic, msg.payload.decode()))
    test_results['receive'] = True

def on_publish(client, userdata, mid):
    """Callback saat publish berhasil"""
    print("✅ Test message published successfully!")
    test_results['publish'] = True

def on_disconnect(client, userdata, rc):
    """Callback saat disconnect"""
    if rc != 0:
        print(f"⚠️  Unexpected disconnect (code: {rc})")

def run_connection_test():
    """Run comprehensive MQTT connection test"""
    print("=" * 60)
    print("🧪 MQTT CONNECTION TEST")
    print("=" * 60)
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Username: {MQTT_USERNAME if MQTT_USERNAME else 'None (anonymous)'}")
    print("=" * 60)
    print()
    
    # Create client
    client = mqtt.Client(client_id="mqtt_test_client")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    
    # Set credentials if provided
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    try:
        # Test 1: Connection
        print("Test 1: Connecting to broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(2)
        
        if not test_results['connection']:
            print("❌ Connection test failed!")
            return False
        
        print()
        
        # Test 2: Publishing
        print("Test 2: Publishing test messages...")
        client.publish(MQTT_TOPIC_TEMP, "25.5")
        client.publish(MQTT_TOPIC_HUMIDITY, "60.0")
        client.publish(MQTT_TOPIC_COMBINED, '{"temperature": 25.5, "humidity": 60.0}')
        time.sleep(2)
        
        if not test_results['publish']:
            print("⚠️  Publish test - status unknown")
        
        print()
        
        # Test 3: Receiving
        print("Test 3: Waiting for messages (5 seconds)...")
        time.sleep(5)
        
        if test_results['receive']:
            print(f"✅ Received {len(messages_received)} message(s)")
        else:
            print("⚠️  No messages received (might be normal if no publishers)")
        
        print()
        
        # Clean up
        client.loop_stop()
        client.disconnect()
        
        # Results
        print("=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        print(f"Connection:    {'✅ PASS' if test_results['connection'] else '❌ FAIL'}")
        print(f"Subscription:  {'✅ PASS' if test_results['subscription'] else '❌ FAIL'}")
        print(f"Publish:       {'✅ PASS' if test_results['publish'] else '⚠️  UNKNOWN'}")
        print(f"Receive:       {'✅ PASS' if test_results['receive'] else '⚠️  NO DATA'}")
        print("=" * 60)
        print()
        
        # Overall status
        if test_results['connection'] and test_results['subscription']:
            print("✅ MQTT connection is working!")
            print("   You can proceed to run the dashboard.")
            print()
            print("   Start dashboard with:")
            print("   streamlit run app_mqtt.py")
            return True
        else:
            print("❌ MQTT connection has issues!")
            print("   Please check:")
            print("   1. Broker address and port")
            print("   2. Network connectivity")
            print("   3. Firewall settings")
            print("   4. Authentication credentials (if required)")
            return False
            
    except ConnectionRefusedError:
        print("❌ Connection refused!")
        print("   Possible causes:")
        print("   - Broker is not running")
        print("   - Incorrect broker address or port")
        print("   - Firewall blocking the connection")
        return False
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def test_network_connectivity():
    """Test basic network connectivity"""
    print("🌐 Testing network connectivity...")
    import socket
    
    try:
        # Try to resolve hostname
        ip = socket.gethostbyname(MQTT_BROKER)
        print(f"✅ Hostname resolved: {MQTT_BROKER} -> {ip}")
        
        # Try to connect to port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((MQTT_BROKER, MQTT_PORT))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {MQTT_PORT} is reachable")
            return True
        else:
            print(f"❌ Port {MQTT_PORT} is not reachable")
            return False
            
    except socket.gaierror:
        print(f"❌ Cannot resolve hostname: {MQTT_BROKER}")
        return False
    except Exception as e:
        print(f"❌ Network test error: {e}")
        return False

if __name__ == "__main__":
    print()
    
    # First test basic network connectivity
    if not test_network_connectivity():
        print()
        print("⚠️  Network connectivity issues detected!")
        print("   Cannot proceed with MQTT test.")
        sys.exit(1)
    
    print()
    
    # Run MQTT connection test
    success = run_connection_test()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)