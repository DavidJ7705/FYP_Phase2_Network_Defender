from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from red_agent import RedAgent
from intrusion_detector import IntrusionDetector

MAX_STEPS = 100

monitor = ContainerlabMonitor()
builder = ObservationGraphBuilder()
adapter = AgentAdapter()
executor = ActionExecutor()
detector = IntrusionDetector()

state = monitor.get_network_state()
servers, users, routers = builder.classify_node_type(state)
containers = servers + users 

red_agent = RedAgent(containers, decoys=executor._decoys)


def run(total_steps = MAX_STEPS):
    print(f"Network Defender - Starting @{total_steps} steps per episode\n")

    for step in range(total_steps):
        print(f"Step {step+1}")

        #Red agent attacks
        red_action, red_host, red_success = red_agent.step()
        print(f"[RED] {red_action} on {red_host} - status: {red_success}")

        #Intrusion detector scans containers
        compromises = detector.scan()

        #Blue agent observes
        state = monitor.get_network_state()
        graph = builder.build_graph(state, compromises)
