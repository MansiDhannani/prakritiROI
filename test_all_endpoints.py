import requests
import json

base_url = 'http://localhost:8000'

# Test data
test_val = {
    "ecosystem_type": "mangrove",
    "area_hectares": 100,
    "region": "west_coast"
}

print("=" * 60)
print("TESTING ALL API ENDPOINTS")
print("=" * 60)

# Test 1: Valuate
print("\n1. POST /api/v1/valuate")
try:
    r = requests.post(f'{base_url}/api/v1/valuate', json=test_val, timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   [FAIL] Error: {r.text[:300]}")
    else:
        print(f"   [OK] Working")
        data = r.json()
        print(f"      Annual Value: Rs. {data.get('annual_value_mid', 0)}")
except Exception as e:
    print(f"   [FAIL] Exception: {str(e)[:200]}")

# Test 2: Scenarios
print("\n2. POST /api/v1/scenarios/compare")
try:
    r = requests.post(f'{base_url}/api/v1/scenarios/compare', json=test_val, timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   [FAIL] Error: {r.text[:300]}")
    else:
        print(f"   [OK] Working")
except Exception as e:
    print(f"   [FAIL] Exception: {str(e)[:200]}")

# Test 3: History
print("\n3. GET /api/v1/history")
try:
    r = requests.get(f'{base_url}/api/v1/history', timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   [FAIL] Error: {r.text[:300]}")
    else:
        print(f"   [OK] Working")
except Exception as e:
    print(f"   [FAIL] Exception: {str(e)[:200]}")

# Test 4: Impact
print("\n4. POST /api/v1/impact")
impact_data = {
    'ecosystem_type': 'mangrove',
    'area_hectares': 100,
    'annual_value_mid': 500000,
    'carbon_annual_tonnes': 50,
    'biodiversity_index': 80,
    'climate_resilience_score': 75,
    'services': []
}
try:
    r = requests.post(f'{base_url}/api/v1/impact', json=impact_data, timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   [FAIL] Error: {r.text[:300]}")
    else:
        print(f"   [OK] Working")
except Exception as e:
    print(f"   [FAIL] Exception: {str(e)[:200]}")

# Test 5: Narrative
print("\n5. POST /api/v1/report/narrative")
narrative_data = {
    'ecosystem_type': 'mangrove',
    'area_hectares': 100,
    'annual_value_mid': 500000,
    'carbon_annual_tonnes': 50,
    'biodiversity_index': 80,
    'climate_resilience_score': 75,
    'services': [],
    'ecosystem_name': 'Mangrove Forest',
    'region': 'west_coast'
}
try:
    r = requests.post(f'{base_url}/api/v1/report/narrative', json=narrative_data, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   [FAIL] Error: {r.text[:300]}")
    else:
        print(f"   [OK] Working")
except Exception as e:
    print(f"   [FAIL] Exception: {str(e)[:200]}")

# Test 6: RAG stats
print("\n6. GET /api/v1/rag/stats")
try:
    r = requests.get(f'{base_url}/api/v1/rag/stats', timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   [FAIL] Error: {r.text[:300]}")
    else:
        print(f"   [OK] Working")
        data = r.json()
        print(f"      Documents: {data.get('total_documents', 0)}")
except Exception as e:
    print(f"   [FAIL] Exception: {str(e)[:200]}")

print("\n" + "=" * 60)
print("TESTING COMPLETE")
print("=" * 60)
