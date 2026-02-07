"""
A2A Client Example - Shows how to communicate with the agent servers.

This demonstrates how external systems (Power BI, chatbots, other agents)
can call your specialist agents via the A2A protocol.

Usage:
    python a2a_servers/a2a_client_example.py
"""

import sys
import os
import requests
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_servers.agent_cards import AGENT_CARDS


def discover_agent(base_url: str) -> dict:
    """Discover an agent's capabilities via its agent card."""
    resp = requests.get(f"{base_url}/.well-known/agent.json")
    resp.raise_for_status()
    return resp.json()


def send_message(base_url: str, message: str) -> str:
    """Send a message to an agent and get the response."""
    resp = requests.post(
        f"{base_url}/a2a",
        json={
            "message": {
                "role": "user",
                "parts": [{"text": message}],
            }
        },
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()

    # Extract response text
    if "message" in data and "parts" in data["message"]:
        return data["message"]["parts"][0].get("text", "")
    return str(data)


def main():
    """Example: Discover and query each agent."""
    print("=" * 60)
    print("A2A CLIENT EXAMPLE")
    print("=" * 60)

    # Example queries for each agent
    example_queries = {
        "market_intel": "What is the overall market sentiment for NASDAQ and NSE today?",
        "ml_analyst": "Which ML model has the best 7-day accuracy?",
        "tech_signal": "What are the strongest active buy signals?",
        "strategy_trade": "Show me the top TIER 1 trade opportunities today.",
        "forex": "What is the current USD/INR rate and trend?",
        "risk": "Are there any high-risk warnings or conflicting signals?",
    }

    for agent_name, query in example_queries.items():
        card = AGENT_CARDS[agent_name]
        base_url = card["url"]

        print(f"\n--- {card['name']} ({base_url}) ---")

        # Step 1: Discover
        try:
            agent_info = discover_agent(base_url)
            print(f"  Discovered: {agent_info['name']}")
            print(f"  Skills: {[s['name'] for s in agent_info.get('skills', [])]}")
        except requests.ConnectionError:
            print(f"  OFFLINE - Agent not running on {base_url}")
            continue
        except Exception as e:
            print(f"  Discovery error: {e}")
            continue

        # Step 2: Send message
        try:
            print(f"  Query: {query}")
            response = send_message(base_url, query)
            # Print first 200 chars of response
            preview = response[:200] + "..." if len(response) > 200 else response
            print(f"  Response: {preview}")
        except Exception as e:
            print(f"  Query error: {e}")


if __name__ == "__main__":
    main()
