
import logging
import time
import os
import sys
import random

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
    logger.info("Importing red_agent...")
    from red_agent import RedAgent

    # Single shared Docker client for all components
    logger.info("Connecting to Docker daemon...")
    shared_client = docker.from_env()
    logger.info("Docker connected. Initializing components...")
    monitor = ContainerlabMonitor(client=shared_client)
    builder = ObservationGraphBuilder()
    executor = ActionExecutor(client=shared_client)
    detector = IntrusionDetector(client=shared_client)
    red_team = RedAgent(['web-server', 'database', 'admin-ws', 'public-web'], client=shared_client)

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

    # Clean all containers before starting (remove stale IOCs from previous runs)
    logger.info("Cleaning all containers (removing stale IOCs)...")
    CLAB_PREFIX = "clab-fyp-defense-network-"
    for host in ['admin-ws', 'web-server', 'database', 'public-web']:
        try:
            c = shared_client.containers.get(f"{CLAB_PREFIX}{host}")
            c.exec_run(['/bin/sh', '-c', 'rm -f /tmp/pwned'])
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

    # Run defense loop (extended to 20 steps for a good battle)
    for step in range(20):
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP {step + 1}/20")
        logger.info(f"{'='*60}")

        # 0. ADVERSARY TURN: Red Agent attempts to attack
        # Attack with 30% probability each step
        red_team.attack(probability=0.3)

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
            logger.info("   All systems appear clean.")

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