import requests
import json

base_url = 'http://localhost:8000'

# CORRECT test data - valid ecosystem_type AND region
test_val = {
    "ecosystem_type": "mangroves",
    "area_hectares": 100,
    "region": "coastal_regions"  # Must be one of the valid regions
}

print("=" * 70)
print("TESTING API - FINAL VALIDATION")
print("=" * 70)

# Test 1: Valuate
print("\n[1]  POST /api/v1/valuate")
try:
    r = requests.post(f'{base_url}/api/v1/valuate', json=test_val, timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   [OK] SUCCESS!")
        print(f"      Annual Value: Rs.{data.get('annual_value_mid', 0):,.0f}")
        print(f"      NPV (10yr): Rs.{data.get('npv', 0):,.0f}")
        print(f"      Carbon: {data.get('carbon_annual_tonnes', 0):.1f} tonnes/year")
        print(f"      Biodiversity Index: {data.get('biodiversity_index', 0)}")
        valuation = data
    else:
        print(f"   [FAIL] Status {r.status_code}: {r.text[:200]}")
        valuation = None
except Exception as e:
    print(f"   [FAIL] Error: {str(e)}")
    valuation = None

# Test 2: Scenarios
print("\n[2]  POST /api/v1/scenarios/compare")
try:
    r = requests.post(f'{base_url}/api/v1/scenarios/compare', json=test_val, timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   [OK] SUCCESS!")
        print(f"      Scenarios: {len(data.get('scenarios', []))} options")
        for s in data.get('scenarios', [])[:3]:
            print(f"        - {s.get('scenario_name')}: NPV Rs.{s.get('combined_npv', 0):,.0f}")
    else:
        print(f"   [FAIL] Status {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)}")

# Test 3: History
print("\n[3]  GET /api/v1/history")
try:
    r = requests.get(f'{base_url}/api/v1/history', timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   [OK] SUCCESS!")
        print(f"      Total records: {len(data.get('valuations', []))}")
    else:
        print(f"   [FAIL] Status {r.status_code}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)}")

# Test 4: Narrative (if we have valuation)
print("\n[4]  POST /api/v1/report/narrative")
if valuation:
    try:
        narrative_data = {"valuation_result": valuation}
        r = requests.post(f'{base_url}/api/v1/report/narrative', json=narrative_data, timeout=15)
        if r.status_code == 200:
            data = r.json()
            narrative = data.get('narrative', '')
            print(f"   [OK] SUCCESS!")
            print(f"      Narrative: {len(narrative)} characters")
            print(f"      Preview: {narrative[:100]}...")
        else:
            print(f"   [FAIL] Status {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"   [FAIL] Error: {str(e)[:200]}")
else:
    print(f"   [SKIP] Skipped (no valuation data)")

# Test 5: Impact
print("\n[5]  POST /api/v1/impact")
if valuation:
    try:
        r = requests.post(f'{base_url}/api/v1/impact', json=valuation, timeout=5)
        if r.status_code == 200:
            data = r.json()
            cards = data.get("impacts", [])
            print(f"   [OK] SUCCESS!")
            print(f"      Impact cards: {len(cards)}")
            for card in cards[:3]:
                metric_safe = card.get('metric', '').replace('₹', 'Rs. ').encode('ascii', 'ignore').decode('ascii')
                label_safe = card.get('label', '').encode('ascii', 'ignore').decode('ascii')
                print(f"        {metric_safe} {label_safe}")
        else:
            print(f"   [FAIL] Status {r.status_code}")
    except Exception as e:
        print(f"   [FAIL] Error: {str(e)}")
else:
    print(f"   [SKIP] Skipped")

print("\n" + "=" * 70)
print("[OK] GUIDE - VALID INPUTS")
print("=" * 70)
print("""
REGIONS (9 options):
   * western_ghats
   * northeast_india
   * sundarbans
   * indo_gangetic_plain
   * deccan_plateau
   * rajasthan_arid
   * himalayan_region
   * coastal_regions [OK]
   * urban_metro

ECOSYSTEM TYPES (9 options):
   * tropical_moist_forest
   * tropical_dry_forest
   * wetlands_inland
   * mangroves [OK]
   * grasslands_savanna
   * agricultural_land
   * himalayan_alpine
   * urban_green_spaces
   * degraded_land
""")
