"""
Script test các Chart API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJudG5oYWNrZXIxQGdtYWlsLmNvbSIsInVzZXJfaWQiOjEsImV4cCI6MTc2NTUxNTgzMn0.paDQOwOeP7qWsubxIArlOs0Cw8MG4f02iV-x4FrPRqo"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

print("=" * 80)
print("📊 TESTING CHART APIs")
print("=" * 80)

# 1. Temperature & Humidity Line Chart
print("\n1️⃣ Temperature & Humidity Line Chart")
print("-" * 80)
response = requests.get(
    f"{BASE_URL}/health/charts/temperature-humidity",
    params={"interval": "1 hour", "days": 1},
    headers=headers
)
print(f"Status: {response.status_code}")
print(f"Response:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 2. Cry Frequency Bar Chart
print("\n2️⃣ Cry Frequency Bar Chart")
print("-" * 80)
response = requests.get(
    f"{BASE_URL}/health/charts/cry-frequency",
    params={"interval": "1 day", "days": 7},
    headers=headers
)
print(f"Status: {response.status_code}")
print(f"Response:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 3. Health Distribution Pie Chart
print("\n3️⃣ Health Distribution Pie Chart")
print("-" * 80)
response = requests.get(
    f"{BASE_URL}/health/charts/health-distribution",
    params={"days": 7},
    headers=headers
)
print(f"Status: {response.status_code}")
print(f"Response:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 4. Hourly Heatmap
print("\n4️⃣ Hourly Heatmap")
print("-" * 80)
response = requests.get(
    f"{BASE_URL}/health/charts/hourly-heatmap",
    params={"days": 7},
    headers=headers
)
print(f"Status: {response.status_code}")
print(f"Response:")
data = response.json()
print(f"Hours: {data.get('hours', [])[:5]}... (showing first 5)")
print(f"Days: {data.get('days', [])}")
print(f"Data matrix: {len(data.get('data', []))} days x {len(data.get('data', [[]])[0]) if data.get('data') else 0} hours")
print("Sample data (first 3 days, first 12 hours):")
for i, day_data in enumerate(data.get('data', [])[:3]):
    print(f"  {data.get('days', [])[i]}: {day_data[:12]}")

print("\n" + "=" * 80)
print("✅ Testing Complete!")
print("=" * 80)
