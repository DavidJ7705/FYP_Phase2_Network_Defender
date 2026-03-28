from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from red_agent import RedAgent, ACTION_NAMES

monitor = ContainerlabMonitor()
builder = ObservationGraphBuilder()
state   = monitor.get_network_state()

servers, users, routers = builder.classify_node_type(state)
containers = servers + users

agent = RedAgent(containers)
print("Initial host states:")
for host, info in agent.host_states.items():
    print(f"  {host}: {info['state']}")

print("\nCalling _choose_host_and_action 10 times\n")
for i in range(10):
    host, action_idx = agent._choose_host_and_action()
    action_name = ACTION_NAMES[action_idx]
    success = agent._execute_action(host, action_idx)
    print(f"Step {i+1}: {action_name} on {host} — success={success}\n")

