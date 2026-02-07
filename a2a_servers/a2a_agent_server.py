"""
A2A Agent Server - Exposes CrewAI specialist agents as A2A HTTP services.

Each agent runs as a standalone Flask server that accepts A2A protocol
messages and returns structured responses. This enables:
- Inter-agent communication via standard A2A protocol
- External clients (Power BI, chatbots, mobile apps) to call agents
- Agent discovery via agent cards

Usage:
    python a2a_servers/a2a_agent_server.py --agent market_intel --port 5001
    python a2a_servers/a2a_agent_server.py --agent ml_analyst --port 5002
    python a2a_servers/a2a_agent_server.py --agent tech_signal --port 5003
    python a2a_servers/a2a_agent_server.py --agent strategy_trade --port 5004
    python a2a_servers/a2a_agent_server.py --agent forex --port 5005
    python a2a_servers/a2a_agent_server.py --agent risk --port 5006
"""

import sys
import os
import argparse
from flask import Flask, request, jsonify

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_servers.agent_cards import AGENT_CARDS

# Map agent names to their creation functions
AGENT_FACTORIES = {
    "market_intel": "agents.market_intel_agent:create_market_intel_agent",
    "ml_analyst": "agents.ml_analyst_agent:create_ml_analyst_agent",
    "tech_signal": "agents.tech_signal_agent:create_tech_signal_agent",
    "strategy_trade": "agents.strategy_trade_agent:create_strategy_trade_agent",
    "forex": "agents.forex_agent:create_forex_agent",
    "risk": "agents.risk_agent:create_risk_agent",
}


def create_agent_from_name(agent_name: str):
    """Dynamically import and create an agent by name."""
    factory_path = AGENT_FACTORIES[agent_name]
    module_path, func_name = factory_path.split(":")
    module = __import__(module_path, fromlist=[func_name])
    factory_func = getattr(module, func_name)
    return factory_func()


def create_a2a_app(agent_name: str) -> Flask:
    """Create a Flask app that serves a single agent via A2A protocol."""

    app = Flask(__name__)
    card = AGENT_CARDS[agent_name]

    # Lazily create the agent on first request
    _agent_cache = {}

    def get_agent():
        if "agent" not in _agent_cache:
            _agent_cache["agent"] = create_agent_from_name(agent_name)
        return _agent_cache["agent"]

    # =====================================================================
    # A2A Protocol Endpoints
    # =====================================================================

    @app.route("/.well-known/agent.json", methods=["GET"])
    def agent_card():
        """A2A agent discovery endpoint - returns the agent card."""
        return jsonify({
            "name": card["name"],
            "description": card["description"],
            "url": card["url"],
            "version": "1.0.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
            },
            "defaultInputModes": card["input_modes"],
            "defaultOutputModes": card["output_modes"],
            "skills": [
                {"id": cap, "name": cap.replace("_", " ").title()}
                for cap in card["capabilities"]
            ],
        })

    @app.route("/a2a", methods=["POST"])
    def handle_a2a_message():
        """
        A2A message handler - accepts a message and returns the agent's response.
        Simplified A2A protocol implementation.
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "No JSON body provided"}), 400

            # Extract the user message from A2A format
            message_text = ""
            if "message" in data:
                msg = data["message"]
                if isinstance(msg, str):
                    message_text = msg
                elif isinstance(msg, dict) and "parts" in msg:
                    for part in msg["parts"]:
                        if isinstance(part, dict) and "text" in part:
                            message_text += part["text"]
                        elif isinstance(part, str):
                            message_text += part
                elif isinstance(msg, dict) and "text" in msg:
                    message_text = msg["text"]
            elif "text" in data:
                message_text = data["text"]
            elif "query" in data:
                message_text = data["query"]

            if not message_text:
                return jsonify({"error": "No message text found in request"}), 400

            # Use CrewAI agent's kickoff method to process the message
            agent = get_agent()
            result = agent.kickoff(message_text)

            # Return A2A formatted response
            response_text = result.raw if hasattr(result, "raw") else str(result)

            return jsonify({
                "message": {
                    "role": "agent",
                    "parts": [{"text": response_text}],
                },
                "metadata": {
                    "agent_name": card["name"],
                    "agent_role": agent.role,
                },
            })

        except Exception as e:
            return jsonify({
                "error": str(e),
                "agent_name": card["name"],
            }), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        """Simple health check endpoint."""
        return jsonify({
            "status": "healthy",
            "agent": card["name"],
            "capabilities": card["capabilities"],
        })

    return app


def main():
    """Launch a single A2A agent server."""
    parser = argparse.ArgumentParser(description="A2A Agent Server")
    parser.add_argument(
        "--agent",
        required=True,
        choices=list(AGENT_FACTORIES.keys()),
        help="Which agent to serve",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5001,
        help="Port to listen on (default: 5001)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )

    args = parser.parse_args()

    print(f"Starting A2A server for: {AGENT_CARDS[args.agent]['name']}")
    print(f"Listening on: http://{args.host}:{args.port}")
    print(f"Agent card: http://{args.host}:{args.port}/.well-known/agent.json")
    print(f"A2A endpoint: http://{args.host}:{args.port}/a2a")
    print(f"Health check: http://{args.host}:{args.port}/health")

    app = create_a2a_app(args.agent)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
