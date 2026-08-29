"""
Groq + RAG powered narrative generation with official SDK
Flow:
  1. Build search query from valuation data
  2. Retrieve top-8 relevant docs from RAG index (coefficients + case studies + policy)
  3. Inject retrieved context into Groq prompt
  4. Groq (Qwen 3 32B) generates grounded, accurate policy narrative
Result: narratives cite real Indian data, case studies, and policy frameworks automatically.

Note: Uses official `groq` SDK which bypasses Cloudflare blocking issues that 
urllib raw HTTP requests encountered. Automatically sends correct headers and TLS fingerprint.
"""
import os
import json
from typing import Optional, List
from groq import Groq
from app.models.schemas import NarrativeResponse


GROQ_MODEL = "qwen/qwen3.8-27b"  # Updated to use the active Qwen 3.8 model on this Groq endpoint


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError(
            "GROQ_API_KEY not set. "
            "Get a FREE key at https://console.groq.com (no credit card needed)."
        )
    return key


def _call_groq(system_prompt: str, user_prompt: str, max_tokens: int = 1400) -> str:
    """Call Groq API using official SDK - simplified to avoid httpx proxies issue"""
    try:
        # The Groq client will read GROQ_API_KEY from environment automatically
        # This avoids passing it through kwargs which can cause proxy conflicts
        import httpx
        
        # Create a custom httpx client without proxies
        http_client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
        )
        
        client = Groq(
            api_key=os.getenv("GROQ_API_KEY"),
            http_client=http_client
        )
        
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            temperature=0.35,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        http_client.close()
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        # Fallback: try with default Groq initialization
        try:
            client = Groq()  # Will use GROQ_API_KEY from env
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=max_tokens,
                temperature=0.35,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content
        except Exception as e2:
            raise RuntimeError(f"Groq API error (fallback failed): {str(e2)}")


def generate_narrative(
    valuation_result: dict,
    scenario_results: Optional[List[dict]] = None,
    location_name:    Optional[str] = None,
    policy_context:   Optional[str] = None,
) -> NarrativeResponse:

    # Gracefully handle missing GROQ_API_KEY
    if not os.getenv("GROQ_API_KEY"):
        annual_val = valuation_result.get("annual_value_mid", 0)
        npv        = valuation_result.get("npv", 0)
        carbon_t   = valuation_result.get("carbon_annual_tonnes", 0)
        bio_idx    = valuation_result.get("biodiversity_index", 0)
        return NarrativeResponse(
            narrative=(
                "EcoValue India Policy Brief: The AI Policy Narrative feature is currently disabled because "
                "no GROQ_API_KEY was found in the environment variables.\n\n"
                "To enable this feature, please follow these steps:\n"
                "1. Get a free API key from the Groq Console at https://console.groq.com.\n"
                "2. Create a .env file locally and add your key: GROQ_API_KEY=gsk_...\n"
                "3. Restart the backend server."
            ),
            key_findings=[
                f"Ecosystem services annual value midpoint: Rs.{annual_val/1e7:.2f} Cr/year",
                f"10-year Net Present Value (NPV): Rs.{npv/1e7:.2f} Cr",
                f"Annual carbon sequestration: {carbon_t:,.0f} tonnes CO2",
                f"Biodiversity Index: {bio_idx}/100"
            ],
            policy_recommendations=[
                "Add your GROQ_API_KEY to generate custom policy analysis and recommendations."
            ]
        )

    eco_name    = valuation_result.get("ecosystem_name", "ecosystem")
    eco_type    = valuation_result.get("ecosystem_type", "")
    area        = valuation_result.get("area_hectares", 0)
    annual_val  = valuation_result.get("annual_value_mid", 0)
    annual_min  = valuation_result.get("annual_value_min", 0)
    annual_max  = valuation_result.get("annual_value_max", 0)
    npv         = valuation_result.get("npv", 0)
    carbon_t    = valuation_result.get("carbon_annual_tonnes", 0)
    carbon_inr  = valuation_result.get("carbon_annual_value_inr", 0)
    bio_idx     = valuation_result.get("biodiversity_index", 0)
    clim_score  = valuation_result.get("climate_resilience_score", 0)
    region      = valuation_result.get("region", "")
    multiplier  = valuation_result.get("regional_multiplier", 1.0)
    proj_years  = valuation_result.get("projection_years", 10)
    discount    = valuation_result.get("discount_rate", 0.08)
    location_str = f"in {location_name}" if location_name else f"({region.replace('_',' ').title()})"

    # ── 1. RAG retrieval ─────────────────────────────────────────────────────
    rag_context = ""
    try:
        from app.services.rag_service import retrieve_context
        rag_query = f"{eco_name} {region} ecosystem services valuation land use India"
        if scenario_results:
            top_scenario = max(scenario_results, key=lambda x: x.get("combined_npv", 0))
            rag_query += f" {top_scenario.get('scenario_name', '')}"
        rag_context = retrieve_context(rag_query, ecosystem_type=eco_type, region=region, k=8)
    except Exception as e:
        rag_context = f"(RAG retrieval unavailable: {e})"

    # ── 2. Scenario summary ───────────────────────────────────────────────────
    scenario_summary = ""
    if scenario_results:
        top = sorted(scenario_results, key=lambda x: x.get("combined_npv", 0), reverse=True)
        lines = []
        for s in top:
            lines.append(
                f"  - {s['scenario_name']}: combined {proj_years}-yr NPV Rs.{s['combined_npv']/1e7:.1f} Cr "
                f"| ecosystem retained {s['ecosystem_retained_pct']:.0f}% "
                f"| ecosystem loss {s['ecosystem_loss_pct']:.0f}%"
            )
        scenario_summary = f"LAND USE SCENARIO COMPARISON ({proj_years}-year NPV at {discount*100:.0f}% discount):\n" + "\n".join(lines)

    # ── 3. Services breakdown ─────────────────────────────────────────────────
    services = valuation_result.get("services", [])
    top_services = sorted(services, key=lambda x: x.get("total_for_area", 0), reverse=True)[:5]
    svc_lines = [
        f"  - {s['service_name']}: Rs.{s['adjusted_value']:,.0f}/ha/yr "
        f"(Rs.{s['total_for_area']/1e7:.2f} Cr total) | {s['contribution_pct']:.1f}% of value"
        for s in top_services
    ]
    services_breakdown = "TOP ECOSYSTEM SERVICES BY VALUE:\n" + "\n".join(svc_lines)

    # ── 4. System prompt ──────────────────────────────────────────────────────
    system_prompt = f"""You are Dr. Priya Sharma, a senior environmental economist at TERI (The Energy and Resources Institute), \
New Delhi, with 20 years of experience advising Indian state governments on ecosystem valuation and land use policy. \
You write evidence-based policy briefs that have influenced forest conservation decisions in 12 Indian states. \
You always cite specific rupee values, reference real Indian policy frameworks, and make clear economic arguments \
that resonate with District Collectors and state planning officials who think in terms of budgets and development targets. \
You never use bullet points inside narrative paragraphs.

CRITICAL: Each ecosystem type has unique characteristics and threats. You are writing about {eco_name} ({eco_type.replace('_',' ')}). \
Make your brief SPECIFIC to this ecosystem type - reference its particular ecological role, specific users/beneficiaries, \
and region-specific threats. Do NOT write generic briefs that could apply to any ecosystem."""

    # ── 5. User prompt with RAG context injected ──────────────────────────────
    user_prompt = f"""Write a policy brief for the following land use decision.

=== RETRIEVED KNOWLEDGE BASE (use these specific facts and case studies) ===
{rag_context}
=== END KNOWLEDGE BASE ===

=== CURRENT VALUATION DATA ===
Ecosystem: {eco_name} {location_str}
Area: {area:,.0f} hectares
Annual ecosystem services value (midpoint): Rs.{annual_val/1e7:.2f} crore/year
  Range: Rs.{annual_min/1e7:.2f} Cr – Rs.{annual_max/1e7:.2f} Cr per year
{proj_years}-year NPV at {discount*100:.0f}% discount rate: Rs.{npv/1e7:.2f} crore
Regional multiplier applied: {multiplier}x ({region.replace('_',' ')})
Annual carbon sequestration: {carbon_t:,.0f} tonnes CO2 (value: Rs.{carbon_inr/1e5:.1f} lakh/yr)
Biodiversity Index: {bio_idx}/100
Climate Resilience Score: {clim_score}/100

{services_breakdown}

{scenario_summary}
{"Additional context: " + policy_context if policy_context else ""}
=== END VALUATION DATA ===

INSTRUCTIONS:
Write a 280-320 word policy brief in 3-4 flowing prose paragraphs (NO bullet points in narrative).

Paragraph 1: State the ecosystem's annual and NPV value in crore rupees. Reference the regional context and why \
this ecosystem is ecologically significant. Use specific service values from the data above.

Paragraph 2: Explain what is lost if this land is converted. Reference the scenario comparison if provided. \
Draw a parallel to a real Indian case study from the knowledge base above if one is relevant.

Paragraph 3: Frame this within Indian policy — mention at least 2 specific policies (Forest Rights Act, \
Wetland Rules 2017, India NDC, Green GDP, CAMPA, NGT) that apply. Connect to India's 2070 net-zero commitment \
and the carbon sequestration value.

Paragraph 4: Give a clear, specific recommendation with 1-2 actionable steps the planning authority should take.

After the narrative write EXACTLY this block:

###JSON###
{{
  "key_findings": [
    "finding 1 with specific Rs. figure",
    "finding 2 with specific figure",
    "finding 3 with specific figure",
    "finding 4 with specific figure"
  ],
  "policy_recommendations": [
    "specific actionable recommendation 1",
    "specific actionable recommendation 2",
    "specific actionable recommendation 3"
  ]
}}
###END###"""

    # ── 6. Call Groq ──────────────────────────────────────────────────────────
    full_text = _call_groq(system_prompt, user_prompt, max_tokens=1800)

    # ── 7. Clean up thinking tags ─────────────────────────────────────────────
    # Remove <think>...</think> tags that Groq uses for reasoning
    import re
    full_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL).strip()

    # ── 8. Parse response ─────────────────────────────────────────────────────
    narrative: str = full_text.strip()
    key_findings: List[str] = []
    policy_recommendations: List[str] = []

    if "###JSON###" in full_text and "###END###" in full_text:
        parts     = full_text.split("###JSON###")
        narrative = parts[0].strip()
        json_str  = parts[1].split("###END###")[0].strip()
        try:
            parsed                 = json.loads(json_str)
            key_findings           = parsed.get("key_findings", [])
            policy_recommendations = parsed.get("policy_recommendations", [])
        except json.JSONDecodeError:
            pass  # still return narrative

    return NarrativeResponse(
        narrative              = narrative,
        key_findings           = key_findings,
        policy_recommendations = policy_recommendations,
    )
