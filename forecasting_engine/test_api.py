import urllib.request
import urllib.error
import json
import time

url = "http://127.0.0.1:8001/api/predict"
payload = {
    "diesel_tax": 0.0,
    "subsidy_percent": 0.0,
    "export_ban": False
}
headers = {'Content-Type': 'application/json'}

print("Waiting for server to start...")
time.sleep(5)

try:
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            print("API Test Passed!")
            data = json.loads(response.read())
            print(f"Final Price: {data['final_adjusted_price']}")
            print(f"Prophet Price: {data['models']['prophet']}")
            print(f"LSTM Confidence: {data['lstm_direction']['confidence_score']}")
            print("Models Check:", data['models'])
        else:
            print(f"API Test Failed with status {response.status}")
except urllib.error.HTTPError as e:
    print(f"API Test Error: {e.code} {e.reason}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"API Test Error: {e}")
