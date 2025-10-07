import requests
import socket

def test_mpesa_connection():
    try:
        # Test DNS resolution
        ip = socket.gethostbyname('api.safaricom.co.ke')
        print(f"✅ DNS resolved: api.safaricom.co.ke -> {ip}")
        
        # Test HTTP connection
        response = requests.get('https://api.safaricom.co.ke/', timeout=10)
        print(f"✅ Can reach MPesa API: Status {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

# Run this test
test_mpesa_connection()