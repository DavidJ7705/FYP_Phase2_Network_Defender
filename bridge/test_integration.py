from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder  # Reverted to working version
from action_executor import ActionExecutor
from agent_adapter import AgentAdapter
import os
import time
import random
import logging

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
    # Initialize components
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    executor = ActionExecutor()

    logger.info("Starting integration test...")
    logger.info("=" * 60)

    # Try to load trained agent
    agent = None
    try:
        agent = AgentAdapter(WEIGHTS_PATH)
        logger.info("✅ Trained GNN-PPO agent loaded successfully!")
        logger.info(f"   Model input dimension: {agent.in_dim}\n")
    except Exception as e:
        logger.error(f"❌ Failed to load agent: {e}")
        logger.info("   Falling back to random decisions\n")

    steps_completed = 0
    monitor_ok = False
    graph_ok = False
    action_ok = False
    agent_decided = False

    # Run defense loop
    for step in range(10):
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP {step + 1}/10")
        logger.info(f"{'='*60}")

        # 1. OBSERVE: Get current network state
        logger.info("📊 Observing network state...")
        state = monitor.get_network_state()
        container_names = [c["name"] for c in state["containers"]]
        logger.info(f"   Found {len(state['containers'])} containers")
        for c in state["containers"]:
            logger.info(f"     - {c['name']}: {c['ip']}")
        monitor_ok = True

        # 2. CONVERT: Build observation graph
        logger.info("\n🔄 Converting to observation graph...")
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
        logger.info("\n🤔 Deciding action...")
        if agent:
            try:
                decision = agent.get_action(graph, container_names)
                action_type = decision["type"]
                target = decision["target"]
                logger.info(
                    f"   🎯 Agent decision: {action_type} on {target} "
                    f"(raw index: {decision['raw_index']})"
                )
                agent_decided = True
            except Exception as e:
                logger.error(f"   Agent decision failed: {e}")
                logger.info("   Falling back to random for this step")
                action_type = random.choice(["Monitor", "Analyse", "Restore"])
                target = random.choice(container_names)
                logger.info(f"   🎲 Random fallback: {action_type} on {target}")
        else:
            action_type = random.choice(["Monitor", "Analyse", "Restore"])
            target = random.choice(container_names)
            logger.info(f"   🎲 Random action: {action_type} on {target}")

        # 4. ACT: Execute action on real network
        logger.info(f"\n⚡ Executing {action_type} on {target}...")
        result = executor.execute(action_type, target)
        if result["success"]:
            logger.info(f"   ✅ {result['message']}")
            action_ok = True
        else:
            logger.error(f"   ❌ {result.get('error', 'Unknown error')}")

        steps_completed += 1

        # Wait before next step
        logger.info(f"\n⏳ Waiting 5 seconds before next step...")
        time.sleep(5)

    logger.info(f"\n{'='*60}")
    logger.info("INTEGRATION TEST COMPLETE!")
    logger.info(f"{'='*60}")

    # Summary
    logger.info("\n📊 Summary:")
    logger.info(f"   - Completed {steps_completed}/10 defense steps")
    logger.info(f"   - Network monitoring: {'✅ PASS' if monitor_ok else '❌ FAIL'}")
    logger.info(f"   - Graph conversion:   {'✅ PASS' if graph_ok else '❌ FAIL'}")
    logger.info(f"   - Action execution:   {'✅ PASS' if action_ok else '❌ FAIL'}")
    logger.info(f"   - Agent decisions:    {'✅ PASS' if agent_decided else '⚠️  FAIL (random fallback)'}")

    if agent and agent_decided:
        logger.info(
            "\n🎉 SUCCESS: Trained GNN-PPO agent defended real Containerlab network!"
        )
    elif agent:
        logger.info("\n⚠️  Partial: Agent loaded but some decisions failed")
    else:
        logger.info("\n⚠️  Partial: Components work, agent loading failed")


if __name__ == "__main__":
    test_full_loop()