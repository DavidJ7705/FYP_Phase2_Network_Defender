from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent
from CybORG.Simulator.Actions import DiscoverRemoteSystems, AggressiveServiceDiscovery, ExploitRemoteService, PrivilegeEscalate, Sleep

red_agent_name = ['red_agent_0', 'red_agent_1']
blue_agent_name = 'blue_agent_0'


def cyborg_with_root_shell_on_cns0() -> CybORG:
    """Get red_agent_0 a root shell on 'contractor_network_subnet_server_host_0' 

    Observation gained from last PrivilegeEscalate:
        'public_access_zone_subnet_server_host_0': {'Interface': [{'ip_address': IPv4Address('10.0.176.254')}]},
        'restricted_zone_a_subnet_server_host_0': {'Interface': [{'ip_address': IPv4Address('10.0.7.254')}]},
        'restricted_zone_b_subnet_server_host_0': {'Interface': [{'ip_address': IPv4Address('10.0.100.254')}]},

    Returns
    -------
    cyborg : CybORG
        a cyborg environment with a root shell on cns0
    """
    ent_sg = EnterpriseScenarioGenerator(
            blue_agent_class=SleepAgent,
            red_agent_class=SleepAgent,
            green_agent_class=SleepAgent,
            steps=100
        )
    cyborg = CybORG(scenario_generator=ent_sg, seed=100)
    cyborg.reset()
    env = cyborg.environment_controller

    s0_hostname = 'contractor_network_subnet_server_host_0'
    s0_ip_addr = env.state.hostname_ip_map[s0_hostname]
    cn_subnet_ip = env.subnet_cidr_map[env.state.hostname_subnet_map[s0_hostname]]

    action = DiscoverRemoteSystems(subnet=cn_subnet_ip, session=0, agent=red_agent_name[0])
    results = cyborg.step(agent=red_agent_name[0], action=action)
    obs = results.observation
    print(obs['action'], obs['success'])

    action = AggressiveServiceDiscovery(session=0, agent=red_agent_name[0], ip_address=s0_ip_addr)
    results = cyborg.step(agent=red_agent_name[0], action=action)
    obs = results.observation
    print(obs['action'], obs['success'])

    action = ExploitRemoteService(ip_address=s0_ip_addr, session=0, agent=red_agent_name[0])
    action.duration = 1
    results = cyborg.step(agent=red_agent_name[0], action=Sleep())
    obs = results.observation
    print(obs['action'], obs['success'])

    action = PrivilegeEscalate(hostname=s0_hostname, session=0, agent=red_agent_name[0])
    results = cyborg.step(agent=red_agent_name[0], action=action)
    obs = results.observation
    print(obs['action'], obs['success'])

    return cyborg