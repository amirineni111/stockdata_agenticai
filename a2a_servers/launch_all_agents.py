"""
Launch all A2A agent servers simultaneously.
Each agent runs on its own port:
  - Market Intel:    port 5001
  - ML Analyst:      port 5002
  - Tech Signal:     port 5003
  - Strategy/Trade:  port 5004
  - Forex:           port 5005
  - Risk:            port 5006

Usage:
    python a2a_servers/launch_all_agents.py
"""

import sys
import os
import subprocess
import time
import signal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENTS = [
    ("market_intel", 5001),
    ("ml_analyst", 5002),
    ("tech_signal", 5003),
    ("strategy_trade", 5004),
    ("forex", 5005),
    ("risk", 5006),
]


def main():
    """Launch all agent servers as subprocesses."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_script = os.path.join(project_root, "a2a_servers", "a2a_agent_server.py")

    processes = []

    print("=" * 60)
    print("LAUNCHING ALL A2A AGENT SERVERS")
    print("=" * 60)

    for agent_name, port in AGENTS:
        print(f"  Starting {agent_name} on port {port}...")
        proc = subprocess.Popen(
            [
                sys.executable,
                server_script,
                "--agent", agent_name,
                "--port", str(port),
            ],
            cwd=project_root,
        )
        processes.append((agent_name, port, proc))
        time.sleep(1)  # Stagger startup

    print("\n" + "=" * 60)
    print("ALL AGENTS RUNNING:")
    for agent_name, port, proc in processes:
        print(f"  {agent_name:20s} -> http://localhost:{port}/a2a  (PID: {proc.pid})")
    print("=" * 60)
    print("\nPress Ctrl+C to stop all agents.\n")

    # Wait for Ctrl+C
    try:
        while True:
            # Check if any process has died
            for agent_name, port, proc in processes:
                if proc.poll() is not None:
                    print(f"WARNING: {agent_name} (port {port}) has exited "
                          f"with code {proc.returncode}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down all agents...")
        for agent_name, port, proc in processes:
            proc.terminate()
            print(f"  Stopped {agent_name} (port {port})")

        # Wait for all to exit
        for _, _, proc in processes:
            proc.wait(timeout=10)

        print("All agents stopped.")


if __name__ == "__main__":
    main()
