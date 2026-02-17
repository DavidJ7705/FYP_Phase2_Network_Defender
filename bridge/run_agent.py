
import logging
import time
import os
import sys
import random
import json
from datetime import datetime

print("Starting up...", flush=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

def write_state(step, max_steps, node_statuses, highlighted_nodes,
                last_blue_action, last_red_action, red_fsm, events):
    """Write current simulation state for the dashboard to read."""
    state = {
        "step": step,
        "max_steps": max_steps,
        "running": True,
        "node_statuses": node_statuses,
        "highlighted_nodes": highlighted_nodes,
        "last_blue_action": last_blue_action,
        "last_red_action": last_red_action,
        "red_fsm": red_fsm,
        "events": events[-20:],  # keep last 20
        "timestamp": datetime.now().isoformat(),
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"Could not write state.json: {e}")


def test_full_loop():
    """
    End-to-end test of the complete agent loop.
    If agent loads: trained GNN-PPO makes all decisions.
    If agent fails: random decisions validate all components work.
    """
    logger.info("Starting integration test...")
    logger.info("=" * 60)

    # Import heavy modules inside the function so startup print is immediate
    logger.info("Importing docker...")
    import docker
    logger.info("Importing network_monitor...")
    from network_monitor import ContainerlabMonitor
    logger.info("Importing graph_builder...")
    from graph_builder import ObservationGraphBuilder
    logger.info("Importing action_executor...")
    from action_executor import ActionExecutor
    logger.info("Importing intrusion_detection...")
    from intrusion_detection import IntrusionDetector
    logger.info("Importing red_agent_cage4...")
    from red_agent_cage4 import CAGE4RedAgent

    # Single shared Docker client for all components
    logger.info("Connecting to Docker daemon...")
    shared_client = docker.from_env()
    logger.info("Docker connected. Initializing components...")
    monitor = ContainerlabMonitor(client=shared_client)
    builder = ObservationGraphBuilder()
    executor = ActionExecutor(client=shared_client)
    detector = IntrusionDetector(client=shared_client)
    red_team = CAGE4RedAgent(client=shared_client)

    # Lazy-load torch + agent (heaviest part)
    agent = None
    try:
        logger.info("Loading PyTorch + GNN-PPO agent (this will take a moment)...")
        from agent_adapter import AgentAdapter
        agent = AgentAdapter(WEIGHTS_PATH)
        logger.info("Trained GNN-PPO agent loaded successfully!")
        logger.info(f"   Model input dimension: {agent.in_dim}\n")
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")
        logger.info("   Falling back to random decisions\n")

    # Clean all CAGE4 containers before starting (remove stale IOCs from previous runs)
    logger.info("Cleaning all containers (removing stale IOCs)...")
    CLAB_PREFIX = "clab-cage4-defense-network-"
    # MINIMAL TOPOLOGY: 6 servers + 10 users = 16 hosts (fits agent capacity)
    cage4_hosts = [
        'restricted-zone-a-server-0', 'restricted-zone-a-server-1', 'restricted-zone-a-user-0',
        'operational-zone-a-server-0', 'operational-zone-a-user-0',
        'restricted-zone-b-server-0', 'restricted-zone-b-user-0',
        'operational-zone-b-server-0', 'operational-zone-b-user-0',
        'contractor-network-server-0', 'contractor-network-user-0', 'contractor-network-user-1',
        'public-access-zone-user-0',
        'admin-network-user-0',
        'office-network-user-0', 'office-network-user-1',
    ]
    for host in cage4_hosts:
        try:
            c = shared_client.containers.get(f"{CLAB_PREFIX}{host}")
            c.exec_run(['/bin/sh', '-c', 'rm -f /tmp/pwned /tmp/pwned_root /tmp/exfil_*'])
            logger.info(f"   Cleaned {host}")
        except Exception as e:
            logger.warning(f"   Could not clean {host}: {e}")
    logger.info("All containers cleaned. Starting defense loop.\n")

    steps_completed = 0
    monitor_ok = False
    graph_ok = False
    action_ok = False
    agent_decided = False
    action_counts = {}

    # Dashboard state tracking
    node_statuses = {}      # {container_name: "clean"|"compromised"|"decoy"|"restored"|"analysed"}
    events = []             # rolling event log
    last_blue_action = {}
    last_red_action = {}
    MAX_STEPS = 20

    # Run defense loop (extended to 20 steps for a good battle)
    for step in range(20):
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP {step + 1}/20")
        logger.info(f"{'='*60}")

        # 0. ADVERSARY TURN: Red Agent attempts FSM transition
        # Attack every step with 100% probability (for testing visibility)
        red_result = red_team.attack(probability=1.0)
        # Show red agent's FSM state distribution
        fsm_summary = red_team.get_fsm_summary()
        logger.info(f"RED AGENT FSM: K={fsm_summary['K']}, S={fsm_summary['S']}, U={fsm_summary['U']}, R={fsm_summary['R']}")
        if red_result:
            last_red_action = {"type": red_team.host_states.get(red_result, {}).get("state", "attack"), "target": red_result}
            events.append({"step": step+1, "actor": "red", "type": "attack", "target": red_result, "time": datetime.now().strftime("%H:%M:%S")})

        # 1. OBSERVE: Get current network state
        logger.info("Observing network state...")
        state = monitor.get_network_state()
        container_names = [c["name"] for c in state["containers"]]

        # REAL DETECTION: Check for IOCs
        compromised_count = 0
        for c in state['containers']:
            # Check if this container has the flag file
            is_compromised = detector.check_compromise(c['name'])
            c['is_compromised'] = is_compromised

            if is_compromised:
                compromised_count += 1
                logger.info(f"   DETECTION ALERT: {c['name']} is COMPROMISED (IOC found)!")

        if compromised_count == 0:
            logger.info("   All systems appear clean (0/16 compromised).")
        else:
            logger.info(f"   ⚠️  {compromised_count}/16 hosts COMPROMISED!")

        # Update node_statuses from detection results
        for c in state['containers']:
            name = c['name']
            # Strip clab prefix
            for prefix in ["clab-cage4-defense-network-"]:
                if name.startswith("clab-" ) :
                    name = name.split("clab-cage4-defense-network-")[-1] if "clab-cage4-defense-network-" in name else name
            if c.get('is_compromised'):
                node_statuses[name] = "compromised"
            elif node_statuses.get(name) not in ("decoy", "restored", "analysed"):
                node_statuses[name] = "clean"

        monitor_ok = True

        # 2. CONVERT: Build observation graph
        logger.info("\nConverting to observation graph...")
        try:
            graph = builder.build_graph(state)
            logger.info(
                f"   Graph: {graph.x.shape[0]} nodes, "
                f"{graph.edge_index.shape[1]} edges, "
                f"{graph.x.shape[1]}-dim features"
            )
            graph_ok = True
        except Exception as e:
            logger.error(f"   Graph conversion failed: {e}")
            break

        # 3. DECIDE: Agent chooses action
        logger.info("\nDeciding action...")
        decision = {}
        if agent:
            try:
                decision = agent.get_action(graph, container_names)
                action_type = decision["type"]
                target = decision["target"]
                iface = decision.get("interface", "")
                label = f"{action_type} on {target}" + (f":{iface}" if iface else "")
                logger.info(f"   Agent decision: {label} (raw index: {decision['raw_index']})")
                agent_decided = True
                action_counts[action_type] = action_counts.get(action_type, 0) + 1
            except Exception as e:
                logger.error(f"   Agent decision failed: {e}")
                logger.info("   Falling back to random for this step")
                action_type = random.choice(["Monitor", "Analyse", "Restore"])
                target = random.choice(container_names)
                decision = {"type": action_type, "target": target}
                logger.info(f"   Random fallback: {action_type} on {target}")
        else:
            action_type = random.choice(["Monitor", "Analyse", "Restore"])
            target = random.choice(container_names)
            decision = {"type": action_type, "target": target}
            logger.info(f"   Random action: {action_type} on {target}")

        # 4. ACT: Execute action on real network
        interface = decision.get("interface")
        logger.info(f"\nExecuting {action_type} on {target}...")
        result = executor.execute(action_type, target, interface=interface)
        if result["success"]:
            logger.info(f"   {result['message']}")
            action_ok = True
        else:
            logger.error(f"   {result.get('error', 'Unknown error')}")

        # Update node_statuses and events from blue action
        clean_target = target.replace("clab-cage4-defense-network-", "")
        action_status_map = {
            "Restore":          "restored",
            "Remove":           "clean",
            "Analyse":          "analysed",
            "DeployDecoy":      "decoy",
            "AllowTrafficZone": None,   # router — don't override
            "BlockTrafficZone": None,
            "Monitor":          None,
        }
        new_status = action_status_map.get(action_type)
        if new_status and result["success"]:
            node_statuses[clean_target] = new_status
        highlighted_nodes = {clean_target: action_type} if new_status else {}

        last_blue_action = {"type": action_type, "target": clean_target, "interface": interface}
        events.append({"step": step+1, "actor": "blue", "type": action_type, "target": clean_target,
                        "time": datetime.now().strftime("%H:%M:%S")})

        # Write dashboard state
        write_state(
            step=step+1, max_steps=MAX_STEPS,
            node_statuses=node_statuses,
            highlighted_nodes=highlighted_nodes,
            last_blue_action=last_blue_action,
            last_red_action=last_red_action,
            red_fsm=fsm_summary,
            events=events,
        )

        steps_completed += 1

        # Wait before next step
        logger.info(f"\nWaiting 2 seconds before next step...")
        time.sleep(2)

    logger.info(f"\n{'='*60}")
    logger.info("INTEGRATION TEST COMPLETE!")
    logger.info(f"{'='*60}")

    # Summary
    logger.info("\nSummary:")
    logger.info(f"   - Completed {steps_completed}/20 defense steps")
    logger.info(f"   - Network monitoring: {'PASS' if monitor_ok else 'FAIL'}")
    logger.info(f"   - Graph conversion:   {'PASS' if graph_ok else 'FAIL'}")
    logger.info(f"   - Action execution:   {'PASS' if action_ok else 'FAIL'}")
    logger.info(f"   - Agent decisions:    {'PASS' if agent_decided else 'FAIL (random fallback)'}")
    if action_counts:
        logger.info(f"   - Action breakdown:   {action_counts}")

    if agent and agent_decided:
        logger.info(
            "\nSUCCESS: Trained GNN-PPO agent defended real Containerlab network!"
        )
    elif agent:
        logger.info("\nPartial: Agent loaded but some decisions failed")
    else:
        logger.info("\nPartial: Components work, agent loading failed")


if __name__ == "__main__":
    test_full_loop()