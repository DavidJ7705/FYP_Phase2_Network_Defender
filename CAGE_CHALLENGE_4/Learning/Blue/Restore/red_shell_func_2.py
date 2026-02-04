from CybORG import CybORG
from CybORG.Simulator.Actions import AggressiveServiceDiscovery, ExploitRemoteService, PrivilegeEscalate

red_agent_name = ['red_agent_0', 'red_agent_1']
blue_agent_name = 'blue_agent_0'


target_subnet = 'restricted_zone_a_subnet'
target_host = target_subnet + '_server_host_0'

def get_shell_on_rzas0(cyborg:CybORG, shell_type:str = 'root'):
    # shell_type = user or root

    env = cyborg.environment_controller
    target_ip = env.state.hostname_ip_map[target_host]

    # Discover a service on restricted_zone_a_subnet_server_host_0
    red_action = AggressiveServiceDiscovery(session=0, agent=red_agent_name[0], ip_address=target_ip)
    results = cyborg.step(agent=red_agent_name[0], action=red_action)
    obs = results.observation
    assert 'AggressiveServiceDiscovery' in str(obs['action'])
    print(obs['action'], obs['success'])
    assert obs['success'] == True

    # Red exploits restricted_zone_a_subnet_server_host_0 to gain a user shell
    action = ExploitRemoteService(ip_address=target_ip, session=0, agent=red_agent_name[0])
    action.duration = 1
    results = cyborg.step(agent=red_agent_name[0], action=action)
    obs = results.observation
    print(obs['action'], obs['success'])
    assert 'Exploit' in str(obs['action'])
    assert obs['success'] == True

    if shell_type == 'user':
        return cyborg

    # Red privilege escalates restricted_zone_a_subnet_server_host_0 to gain a user shell
    red_action = PrivilegeEscalate(hostname=target_host, session=0, agent=red_agent_name[1])
    red_action.duration = 1
    results = cyborg.step(agent=red_agent_name[1], action=red_action)
    obs = results.observation
    print(obs['action'], obs['success'])
    assert 'PrivilegeEscalate' in str(obs['action'])
    assert obs['success'] == True

    return cyborg