"""
RAG Knowledge Base
Converts your India ecosystem coefficient database into searchable documents.
Also includes real Indian land-use case studies as few-shot examples.
Run once at startup — re-indexes automatically if data changes.
"""
from app.services.vector_store import VectorStore
from app.data.coefficients import (
    ECOSYSTEMS, REGIONAL_MULTIPLIERS, CARBON_PRICES,
    LAND_USE_ALTERNATIVES
)

# ── Index paths ───────────────────────────────────────────────────────────────
VECTOR_DB_PATH = "data/rag_index.json"

# Singleton store loaded once
_store: VectorStore = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore(persist_path=VECTOR_DB_PATH)
        if _store.count() == 0:
            print("[RAG] Building RAG index from scratch...")
            build_index(_store)
            print(f"[RAG] RAG index built: {_store.count()} documents indexed")
    return _store


# ── Document builders ─────────────────────────────────────────────────────────

def _ecosystem_docs() -> list:
    """Convert each ecosystem's services into rich searchable text chunks."""
    docs = []

    for eco_key, eco in ECOSYSTEMS.items():
        # ── 1. Overview document ──────────────────────────────────────────────
        total_mid = sum(s.get("mid", 0) for s in eco["services"].values())
        total_min = sum(s.get("min", 0) for s in eco["services"].values())
        total_max = sum(s.get("max", 0) for s in eco["services"].values())

        overview_text = f"""
Ecosystem: {eco['name']}
Type: {eco_key}
Found in: {eco['regions']}
Carbon sequestration rate: {eco['carbon_rate_tonnes_ha_yr']} tonnes CO2 per hectare per year
Climate resilience score: {eco['climate_resilience_score']} out of 100
Biodiversity index: {eco['biodiversity_index']} out of 100
Total annual ecosystem services value: Rs.{total_min:,.0f} to Rs.{total_max:,.0f} per hectare per year
Midpoint annual value: Rs.{total_mid:,.0f} per hectare per year
At 8 percent discount rate over 10 years, NPV factor is 6.71x annual value.
10-year NPV per hectare midpoint: Rs.{total_mid * 6.71:,.0f}
Sources: TEEB India Sukhdev 2008, FSI ISFR 2023, TERI, MoEFCC NATCOM
""".strip()

        docs.append({
            "id": f"eco_overview_{eco_key}",
            "text": overview_text,
            "metadata": {
                "type": "ecosystem_overview",
                "ecosystem": eco_key,
                "ecosystem_name": eco["name"],
                "total_mid_per_ha": total_mid,
                "carbon_rate": eco["carbon_rate_tonnes_ha_yr"],
                "climate_score": eco["climate_resilience_score"],
                "bio_index": eco["biodiversity_index"],
            }
        })

        # ── 2. Per-service documents ──────────────────────────────────────────
        for svc_key, svc in eco["services"].items():
            svc_name = svc_key.replace("_", " ")
            svc_text = f"""
Ecosystem service: {svc_name} in {eco['name']}
Ecosystem type: {eco_key}
Region examples: {eco['regions']}
Minimum value: Rs.{svc.get('min', 0):,.0f} per hectare per year
Midpoint value: Rs.{svc.get('mid', 0):,.0f} per hectare per year
Maximum value: Rs.{svc.get('max', 0):,.0f} per hectare per year
Valuation method: {svc.get('method', 'not specified')}
Data source: {svc.get('source', 'not specified')}
This service contributes to {eco['name']} total ecosystem value.
Carbon sequestration rate for this ecosystem: {eco['carbon_rate_tonnes_ha_yr']} tCO2 per hectare per year.
""".strip()

            docs.append({
                "id": f"svc_{eco_key}_{svc_key}",
                "text": svc_text,
                "metadata": {
                    "type": "ecosystem_service",
                    "ecosystem": eco_key,
                    "ecosystem_name": eco["name"],
                    "service": svc_key,
                    "service_name": svc_name,
                    "value_min": svc.get("min", 0),
                    "value_mid": svc.get("mid", 0),
                    "value_max": svc.get("max", 0),
                    "method": svc.get("method", ""),
                    "source": svc.get("source", ""),
                }
            })

    return docs


def _regional_docs() -> list:
    """Regional multiplier context documents."""
    docs = []
    region_context = {
        "western_ghats":       "Biodiversity hotspot, high rainfall, Western Ghats mountains, Karnataka Kerala Tamil Nadu Maharashtra, endemic species",
        "northeast_india":     "Assam Meghalaya Manipur Mizoram high biodiversity tropical forests, Brahmaputra river basin",
        "sundarbans":          "Mangrove delta West Bengal Bangladesh, tiger reserve, cyclone protection, largest mangrove forest world",
        "indo_gangetic_plain": "Uttar Pradesh Bihar Punjab Haryana agricultural heartland, Ganga Yamuna rivers, high population density",
        "deccan_plateau":      "Maharashtra Telangana Andhra Pradesh Karnataka dry deciduous forest, black cotton soil, seasonal rivers",
        "rajasthan_arid":      "Desert dryland Thar desert arid semi-arid low rainfall sparse vegetation",
        "himalayan_region":    "Uttarakhand Himachal Pradesh Sikkim alpine glaciers water tower, high altitude meadows bugyals",
        "coastal_regions":     "Odisha Andhra Pradesh Kerala Tamil Nadu coast beach estuary backwaters coral reef",
        "urban_metro":         "Delhi Mumbai Bengaluru Chennai Hyderabad Pune urban city parks green belt",
    }

    for region_key, mult in REGIONAL_MULTIPLIERS.items():
        pct = int((mult - 1) * 100)
        direction = "higher" if mult > 1 else "lower"
        context = region_context.get(region_key, "")
        text = f"""
Regional multiplier for {region_key.replace('_', ' ')}: {mult}
Ecosystem service values in this region are {abs(pct)} percent {direction} than national baseline.
Context: {context}
Apply this multiplier to all per-hectare ecosystem service values when calculating for this region.
Example: If baseline flood control value is Rs.165,000 per hectare per year,
in {region_key.replace('_', ' ')} the adjusted value is Rs.{165000 * mult:,.0f} per hectare per year.
""".strip()

        docs.append({
            "id": f"region_{region_key}",
            "text": text,
            "metadata": {
                "type": "regional_multiplier",
                "region": region_key,
                "multiplier": mult,
                "context": context,
            }
        })

    return docs


def _land_use_docs() -> list:
    """Land use alternative comparison documents."""
    docs = []
    for key, alt in LAND_USE_ALTERNATIVES.items():
        retain_pct = alt["eco_services_retained"] * 100
        loss_pct   = (1 - alt["eco_services_retained"]) * 100
        text = f"""
Land use scenario: {alt['name']}
Description: {alt['description']}
Direct revenue: Rs.{alt['revenue_ha_yr']:,.0f} per hectare per year
Ecosystem services retained after conversion: {retain_pct:.0f} percent
Ecosystem services lost after conversion: {loss_pct:.0f} percent
At 8 percent discount over 10 years, direct revenue NPV per hectare: Rs.{alt['revenue_ha_yr'] * 6.71:,.0f}
This scenario destroys {loss_pct:.0f} percent of existing ecosystem value.
For policy analysis compare combined NPV (ecosystem retained + direct revenue) against full conservation NPV.
""".strip()

        docs.append({
            "id": f"landuse_{key}",
            "text": text,
            "metadata": {
                "type": "land_use_alternative",
                "scenario": key,
                "scenario_name": alt["name"],
                "revenue_ha_yr": alt["revenue_ha_yr"],
                "eco_retained_pct": retain_pct,
            }
        })

    return docs


def _carbon_docs() -> list:
    """Carbon pricing documents."""
    docs = []
    for method, price in CARBON_PRICES.items():
        text = f"""
Carbon pricing method: {method.replace('_', ' ')}
Price: Rs.{price:,.0f} per tonne CO2
Use case: {'Policy and government analysis, recommended for EIA' if method == 'social_cost' else 'Project finance and carbon credit markets' if method == 'voluntary_market' else 'BEE Carbon Credits India domestic market'}
To calculate carbon value: multiply land area in hectares by ecosystem carbon rate (tonnes CO2 per hectare per year) by this price.
India carbon market established under Energy Conservation Amendment Act 2022.
India NDC target: reduce emissions intensity by 45 percent by 2030 from 2005 levels.
""".strip()

        docs.append({
            "id": f"carbon_{method}",
            "text": text,
            "metadata": {
                "type": "carbon_pricing",
                "method": method,
                "price_inr": price,
            }
        })

    return docs


def _case_study_docs() -> list:
    """
    Real Indian land-use case studies.
    These serve as few-shot examples for the narrative generator.
    Sources: TERI, MoEFCC, academic literature.
    """
    return [
        {
            "id": "case_chilika_wetland",
            "text": """
Case study: Chilika Lake Wetland Conservation vs Aquaculture, Odisha
Ecosystem: Inland wetland, 1,100 sq km, largest coastal lagoon in Asia
Region: Coastal Odisha, Indo-Gangetic Plain adjacent
Decision: Community vs commercial prawn aquaculture conversion
Ecosystem services annual value: Rs.892 crore total for full lake area
Per hectare value: Rs.81,000 midpoint annual value
Key services: fisheries Rs.450 crore supporting 200,000 fisher families, bird tourism Rs.120 crore, water filtration, flood buffer for Puri and Bhubaneswar
Aquaculture conversion offer: Rs.25,000 per hectare lease revenue
Outcome: Conservation chosen after TERI valuation showed ecosystem value exceeded aquaculture 3.2x over 10 years
Policy reference: Wetland Conservation and Management Rules 2017, Ramsar Convention
Lesson: Fishing community livelihood value of Rs.450 crore invisible to lease revenue calculation.
Biodiversity: 160 fish species, 45 migratory bird species including flamingos.
Carbon: 4.5 tonnes CO2 per hectare per year sequestered.
Source: TERI 2018, Odisha Forest Department.
""".strip(),
            "metadata": {
                "type": "case_study",
                "ecosystem": "wetlands_inland",
                "region": "coastal_regions",
                "decision": "conservation_won",
                "location": "Chilika Lake, Odisha",
            }
        },
        {
            "id": "case_western_ghats_mining",
            "text": """
Case study: Western Ghats Forest vs Iron Ore Mining, Goa Karnataka
Ecosystem: Tropical moist forest, biodiversity hotspot
Region: Western Ghats
Decision: Forest conservation vs open-cast iron ore mining lease
Forest ecosystem value: Rs.8.7 lakh per hectare per year (ATREE 2019 estimate)
Key services: Water regulation for Goa rivers Rs.3.2 lakh per ha, biodiversity Rs.2.5 lakh per ha, carbon Rs.1.1 lakh per ha, tourism Rs.0.8 lakh per ha
Mining lease offer: Rs.4.5 lakh per hectare per year royalty
10-year NPV forest: Rs.58 lakh per hectare at 8 percent discount
10-year NPV mining: Rs.30 lakh per hectare
Net ecosystem loss if mined: Rs.28 lakh per hectare over 10 years
Policy reference: Forest Rights Act 2006, Supreme Court order on mining moratorium Goa 2012
Lesson: Mining revenue appears large but ecosystem NPV is 1.93x higher over 10 years.
Rehabilitation cost after mining: Rs.12 lakh per hectare additional burden on state.
Carbon sequestration lost: 6.25 tonnes CO2 per hectare per year.
Source: ATREE 2019, Ministry of Environment Forest and Climate Change.
""".strip(),
            "metadata": {
                "type": "case_study",
                "ecosystem": "tropical_moist_forest",
                "region": "western_ghats",
                "decision": "conservation_recommended",
                "location": "Western Ghats, Goa-Karnataka border",
            }
        },
        {
            "id": "case_sundarbans_development",
            "text": """
Case study: Sundarbans Mangrove vs Industrial Port Expansion, West Bengal
Ecosystem: Mangrove forest, UNESCO World Heritage
Region: Sundarbans delta, coastal Bengal
Decision: Port expansion clearing 800 hectares mangrove vs conservation
Mangrove ecosystem value: Rs.9 lakh per hectare per year
Key services: Cyclone protection Rs.3.25 lakh per ha (Amphan 2020 caused Rs.1 lakh crore damage, mangroves reduced impact by 40 percent), blue carbon Rs.1.35 lakh per ha, fisheries Rs.1.65 lakh per ha nursery value, biodiversity Rs.1.85 lakh per ha
Port revenue projected: Rs.2.5 lakh per hectare per year
800 hectare impact: Annual ecosystem loss Rs.720 crore vs port revenue Rs.200 crore
10-year ecosystem NPV lost: Rs.4,830 crore for 800 ha
10-year port revenue NPV: Rs.1,342 crore for 800 ha
Net loss to community: Rs.3,488 crore over 10 years if converted
Climate risk: Loss of mangrove buffer increases cyclone damage to 3 million coastal residents
Policy reference: Coastal Regulation Zone rules, Mangrove protection order Supreme Court 2002
India NDC: Blue carbon mangroves critical to India 2070 net zero commitment
Source: WII 2021, Sundarbans Biosphere Reserve Authority.
""".strip(),
            "metadata": {
                "type": "case_study",
                "ecosystem": "mangroves",
                "region": "sundarbans",
                "decision": "conservation_strongly_recommended",
                "location": "Sundarbans, West Bengal",
            }
        },
        {
            "id": "case_himalayan_hydropower",
            "text": """
Case study: Himalayan Alpine Meadow vs Hydropower Dam, Uttarakhand
Ecosystem: Himalayan alpine meadows and forests
Region: Himalayan region, Uttarakhand
Decision: Large hydropower project submerging 1,200 hectares alpine ecosystem
Alpine ecosystem value: Rs.4.5 lakh per hectare per year
Key services: Water supply to downstream Ganga basin Rs.1.3 lakh per ha, biodiversity Rs.1.1 lakh per ha, climate regulation glacier preservation Rs.0.85 lakh per ha, medicinal plants Rs.0.25 lakh per ha, tourism Rs.0.58 lakh per ha
Hydropower revenue: Rs.1.8 lakh per hectare per year (electricity sale)
1,200 hectare impact: Annual ecosystem loss Rs.540 crore vs hydro revenue Rs.216 crore
Additional hidden costs: Resettlement Rs.400 crore, seismic risk Himalayan zone, siltation reducing dam life to 30 years
Kedarnath flood 2013 linked to upstream ecosystem destruction, Rs.4,000 crore damage
Policy reference: Environment Impact Assessment notification, National Green Tribunal orders
Lesson: Himalayan ecosystems provide water security to 500 million people downstream. Destruction costs exceed benefits when full accounting is done.
Carbon: 3.5 tonnes CO2 per hectare per year sequestration lost.
Source: IIFM Verma 2000, TERI Himalayan study, National Green Tribunal.
""".strip(),
            "metadata": {
                "type": "case_study",
                "ecosystem": "himalayan_alpine",
                "region": "himalayan_region",
                "decision": "conservation_recommended",
                "location": "Uttarakhand Himalayan region",
            }
        },
        {
            "id": "case_urban_green_bengaluru",
            "text": """
Case study: Urban Green Space vs Real Estate Development, Bengaluru
Ecosystem: Urban lakes and green belts
Region: Urban metro, Bengaluru
Decision: 45-hectare urban lake and green belt vs IT park development
Urban green space value: Rs.2.3 lakh per hectare per year
Key services: Flood control preventing waterlogging Rs.0.65 lakh per ha (Bengaluru floods 2022 caused Rs.400 crore damage), air purification Rs.0.58 lakh per ha, urban heat island reduction Rs.0.45 lakh per ha, recreation Rs.0.35 lakh per ha, biodiversity Rs.0.28 lakh per ha
IT park revenue: Rs.8 lakh per hectare per year
45 hectare impact: Annual ecosystem Rs.10.4 crore vs IT revenue Rs.36 crore
10-year ecosystem NPV: Rs.69.7 crore
10-year IT park NPV: Rs.241.6 crore
Hidden costs NOT counted: Stormwater infrastructure replacement Rs.50 crore, increased AC energy Rs.20 crore, health costs from pollution Rs.30 crore, flood damage risk Rs.15 crore per event
When hidden costs included: IT park economic advantage reduces to Rs.26 crore over 10 years
Policy: Karnataka Tree Preservation Act, BBMP Lake Development Authority
Lesson: Urban ecosystem services are systematically undervalued; true cost accounting closes the gap dramatically.
Source: CPR India 2021, BBMP Environmental Reports.
""".strip(),
            "metadata": {
                "type": "case_study",
                "ecosystem": "urban_green_spaces",
                "region": "urban_metro",
                "decision": "mixed_partial_conservation",
                "location": "Bengaluru, Karnataka",
            }
        },
    ]


def _policy_framework_docs() -> list:
    """Indian policy and regulatory context documents."""
    return [
        {
            "id": "policy_wetland_rules",
            "text": """
Indian Policy: Wetland Conservation and Management Rules 2017
Authority: Ministry of Environment Forest and Climate Change MoEFCC
Key provisions: Prohibits draining, filling, construction on notified wetlands.
Requires State Wetland Authority approval for any activity.
Mandates comprehensive ecological assessment before any land use change.
Applicable to: All wetlands of ecological significance, Ramsar sites
Relevant for: wetlands_inland, mangroves ecosystem decisions
Penalty: Violation punishable under Environment Protection Act 1986
India has 42 Ramsar wetland sites as of 2023, second highest in Asia.
""".strip(),
            "metadata": {"type": "policy_framework", "policy": "wetland_rules_2017"}
        },
        {
            "id": "policy_forest_rights",
            "text": """
Indian Policy: Forest Rights Act 2006 (Scheduled Tribes and Other Traditional Forest Dwellers Act)
Authority: Ministry of Tribal Affairs
Key provisions: Recognises rights of forest-dwelling communities over forest land they have occupied.
Community forest rights include managing and protecting forest resources.
Prior informed consent of Gram Sabha required before any diversion of forest land.
Relevant for: tropical_moist_forest, tropical_dry_forest, himalayan_alpine decisions
Implication for valuation: Community livelihood value must be included in ecosystem services assessment.
CAMPA funds: Compensatory Afforestation Management and Planning Authority collects and disburses funds for forest diversion.
Net Present Value payment required for any forest diversion to government.
""".strip(),
            "metadata": {"type": "policy_framework", "policy": "forest_rights_act_2006"}
        },
        {
            "id": "policy_india_ndc",
            "text": """
Indian Policy: India Nationally Determined Contribution NDC to UNFCCC Paris Agreement
Target 1: Reduce emissions intensity of GDP by 45 percent by 2030 from 2005 levels.
Target 2: Achieve 50 percent cumulative electric power from non-fossil sources by 2030.
Target 3: Create additional carbon sink of 2.5 to 3 billion tonnes CO2 equivalent through forest and tree cover by 2030.
Long-term: India net zero emissions by 2070.
Relevance: Ecosystem conservation directly contributes to carbon sink targets.
Forest cover increase required: 33 percent of India land area under forest and tree cover.
Blue carbon: Mangroves, wetlands, coastal ecosystems recognised as high-priority carbon sinks.
Green GDP: India committed to accounting for natural capital in national accounts.
CAMPA: Rs.47,000 crore collected for compensatory afforestation.
""".strip(),
            "metadata": {"type": "policy_framework", "policy": "india_ndc_2022"}
        },
        {
            "id": "policy_green_gdp",
            "text": """
Indian Policy: Natural Capital Accounting and Green GDP Initiative
MoEFCC and Ministry of Statistics MOSPI working on ecosystem accounts.
System of Environmental-Economic Accounting SEEA being implemented.
TEEB India study by Pavan Sukhdev 2008 estimated India loses Rs.7 lakh crore annually from ecosystem degradation.
Planning Commission 12th Five Year Plan included ecosystem valuation for first time.
National Green Tribunal NGT can order ecosystem restoration and impose eco-sensitive zone restrictions.
Environment Impact Assessment EIA notification 2006 requires ecosystem services assessment for projects above threshold.
State of Environment Report published annually by MoEFCC tracks ecosystem health indicators.
Ecosystem services valuation increasingly required for project clearance.
""".strip(),
            "metadata": {"type": "policy_framework", "policy": "green_gdp_natcap"}
        },
    ]


# ── Main builder ──────────────────────────────────────────────────────────────

def build_index(store: VectorStore):
    """Index all knowledge sources into the vector store."""
    all_docs = (
        _ecosystem_docs()       +   # 9 ecosystems × (1 overview + N services)
        _regional_docs()        +   # 9 regions
        _land_use_docs()        +   # 6 land use alternatives
        _carbon_docs()          +   # 3 carbon pricing methods
        _case_study_docs()      +   # 5 real Indian case studies
        _policy_framework_docs()    # 4 policy frameworks
    )
    store.add_batch(all_docs)
    return len(all_docs)


def retrieve_context(
    query: str,
    ecosystem_type: str = None,
    region: str = None,
    k: int = 8,
) -> str:
    """
    Retrieve top-k relevant documents for a query.
    Returns formatted context string ready to inject into prompt.
    """
    store = get_store()

    # Build enriched query
    parts = [query]
    if ecosystem_type:
        eco_name = ECOSYSTEMS.get(ecosystem_type, {}).get("name", ecosystem_type)
        parts.append(eco_name)
    if region:
        parts.append(region.replace("_", " "))

    enriched_query = " ".join(parts)
    results = store.query(enriched_query, k=k)

    if not results:
        return "No specific context available."

    sections = []
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        doc_type = meta.get("type", "data")
        label = {
            "ecosystem_overview":   "📊 Ecosystem Data",
            "ecosystem_service":    "💰 Service Valuation",
            "regional_multiplier":  "🗺 Regional Context",
            "land_use_alternative": "🏗 Land Use Scenario",
            "carbon_pricing":       "☁️ Carbon Pricing",
            "case_study":           "📋 India Case Study",
            "policy_framework":     "⚖️ Policy Framework",
        }.get(doc_type, "📄 Data")

        sections.append(f"[{i}] {label} (relevance: {r['score']:.2f})\n{r['text']}")

    return "\n\n---\n\n".join(sections)
