import asyncio
import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from config import get_llm
from mcp_client import current_weather, forecast, list_airlines, list_airports, tavily_search
from state import TravelState

llm = get_llm()

def _llm_text(system: str, prompt: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
    )
    return response.content

def _json_from_llm(text: str) -> dict:
    print("\n========== RAW LLM RESPONSE ==========")
    print(text)
    print("======================================\n")

    start = text.index("{")
    end = text.rindex("}") + 1

    json_text = text[start:end]

    print("\n========== EXTRACTED JSON ==========")
    print(json_text)
    print("====================================\n")

    return json.loads(json_text)


# with guardrail
def supervisor_agent(state: TravelState):
    query = state["user_query"]
            
    # INPUT GUARDRAIL
    guardrail_prompt = f"""
    Determine whether the following request is a valid travel planning request.

    Return only JSON in this format:

    {{
        "allowed": true,
        "reason": ""
    }}

    User request:
    {query}
    """

    guardrail_raw = _llm_text(
        "You are an input validation guardrail. Return strict JSON only.",
        guardrail_prompt,
    )

    print("\n========== GUARDRAIL RAW RESPONSE ==========")
    print(guardrail_raw)
    print("============================================\n")

    guardrail_result = _json_from_llm(guardrail_raw)

    print("\n========== GUARDRAIL PARSED RESPONSE ==========")
    print(json.dumps(guardrail_result, indent=2))
    print("================================================\n")

    if not guardrail_result.get("allowed", False):
        reason = guardrail_result.get(
            "reason",
            "Request rejected by input guardrail."
        )

        return {
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": reason,
            "final_response": reason,
            "messages": [
                AIMessage(content=f"Guardrail blocked request: {reason}")
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }



    prompt = f"""
You are the supervisor of a real-world multi-agent travel planning system.

Decide which specialist agents are needed for this user request.

Available agents:
- flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed
- hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed
- weather_agent: use when weather, climate, season, packing, or forecast is useful
- budget_agent: use when budget, affordability, cost, or price constraints are mentioned
- itinerary_agent: almost always needed to produce the travel plan

Return only JSON with this schema:
{{
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {{
    "destination": "",
    "origin": "",
    "duration": "",
    "budget": "",
    "travel_style": "",
    "special_preferences": []
  }},
  "reasoning": ""
}}

User request:
{query}
"""

 
    raw = _llm_text(
        "You route work to specialist agents. Return strict JSON only.",
        prompt,
    )

    print("\n========== RAW LLM RESPONSE ==========")
    print(raw)
    print("======================================\n")

    parsed = _json_from_llm(raw)
   
    #parsed = json.loads(raw)
    
    print("\n========== PARSED JSON ==========")
    print(json.dumps(parsed, indent=2))
    print("=================================\n")
    
    '''
    At first glance they look the same, but they're not:

    raw → string returned by the LLM
    parsed → Python dictionary created from that string

    If you really want to demonstrate the difference, add:

    print(type(raw))
    print(type(parsed))
    Output:

    <class 'str'>
    <class 'dict'>
    Yes, you can get output from a string, but it's much harder and less reliable.
    '''
    
    selected = parsed["selected_agents"]    

    return {
        "selected_agents": selected,
        "trip_constraints": parsed["trip_constraints"],
        "supervisor_reasoning": parsed["reasoning"],
        "messages": [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def flight_agent(state: TravelState):
    query = state["user_query"]
    constraints = state["trip_constraints"]
    destination = constraints["destination"]

    print("\n========== FLIGHT AGENT INPUT ==========")
    print("Query:", query)
    print("Constraints:", constraints)
    print("========================================\n")

    airports = asyncio.run(list_airports(destination, limit=10))
    airlines = asyncio.run(list_airlines("", limit=10))

    print("\n========== AIRPORT MCP DATA ==========")
    print(airports)
    print("======================================\n")

    print("\n========== AIRLINE MCP DATA ==========")
    print(airlines)
    print("======================================\n")

    prompt = f"""
Create flight guidance for this trip.

User request:
{query}

Trip constraints:
{constraints}

Airport MCP data:
{str(airports)[:3000]}

Airline MCP data:
{str(airlines)[:3000]}

Include likely departure/arrival airports, relevant airlines,
estimated duration, fare range, peak season warning,
and booking advice.
"""

    result = _llm_text(
        "You are a flight planning specialist.",
        prompt,
    )

    print("\n========== FLIGHT AGENT OUTPUT ==========")
    print(result)
    print("=========================================\n")

    return {
        "flight_results": result,
        "messages": [AIMessage(content="Flight agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

