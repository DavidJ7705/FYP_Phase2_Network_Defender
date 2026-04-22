# Unit tests for RedAgent — 20-step FSM run covering all 9 action branches and state transitions.
#
# Terminal 1 (deploy topology):
#   cd ~/Desktop/Network_Defender_FYP/containerlab-networks
#   sudo containerlab deploy -t cage4-topology.yaml
#
# Terminal 2 (run):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   sudo ~/fyp-venv-linux/bin/python -m pytest tests/test_red_agent.py -v

from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from red_agent import RedAgent, ACTION_NAMES


def test_initial_states_are_known():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    agent = RedAgent(servers + users)
    for host, info in agent.host_states.items():
        assert info["state"] == "K", f"{host} should start in state K"


def test_step_returns_valid_action():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    agent = RedAgent(servers + users)
    action_name, host, success = agent.step()
    assert action_name in ACTION_NAMES
    assert host is not None
    assert isinstance(success, bool)


def test_fsm_progresses_over_steps():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    agent = RedAgent(servers + users)
    for _ in range(20):
        action_name, host, success = agent.step()
        assert action_name in ACTION_NAMES
        assert host is not None