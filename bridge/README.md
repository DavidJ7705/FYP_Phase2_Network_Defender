# Bridge: Trained Agent → Containerlab Network

This directory bridges the trained GNN-PPO agent with the real Containerlab network topology.

## Architecture

```
┌─────────────────────┐
│ Trained GNN-PPO     │  (from trained-agent/)
│ Agent (325-dim in)  │
└──────────┬──────────┘
           │
      agent_adapter.py (pads 200→325, maps actions)
           │
┌──────────┴──────────┐
│  graph_builder.py   │  (network state → PyG graph)
└──────────┬──────────┘
           │
┌──────────┴──────────┐
│ network_monitor.py  │  (Docker SDK → state dict)
└──────────┬──────────┘
           │
┌──────────┴──────────┐
│ Containerlab        │  (5 containers)
│ Network Topology    │
└─────────────────────┘
           ↑
┌──────────┴──────────┐
│ action_executor.py  │  (actions → Docker commands)
└─────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `network_monitor.py` | Collects network state (IPs, processes, ports) from all containers |
| `graph_builder.py` | Converts network state to PyTorch Geometric graph (200-dim features) |
| `action_executor.py` | Executes agent actions (Monitor, Analyse, Restore) on containers |
| `agent_adapter.py` | Loads trained agent, pads features to 325-dim, maps action indices |
| `test_integration.py` | Full end-to-end defense loop (10 steps) |
| `test_*.py` | Individual component tests |

## Setup

**On the VM (OrbStack Ubuntu):**

```bash
# 1. Activate virtual environment (already created)
source venv-linux/bin/activate

# 2. Install any missing dependencies
pip install docker torch torch-geometric

# 3. Make sure Containerlab topology is running
cd ../containerlab-networks/
sudo containerlab deploy -t fyp-topology.yaml

# 4. Verify 5 containers running:
sudo docker ps | grep clab-fyp-defense-network
```

## Testing

### Test Individual Components

```bash
# Test network monitor
python test_monitor.py
# → Should print 5 containers with IPs, processes, and ports
# → Saves example_state.json

# Test graph builder
python test_graph_builder.py
# → Should build graph with ~10-15 nodes (5 systems + connections)

# Test action executor
sudo python test_executor.py
# → Should execute Monitor, Analyse, Restore on containers
```

### Test Full Integration

```bash
sudo python test_integration.py
```

**Expected output:**
1. Loads trained agent from `../trained-agent/weights/gnn_ppo-0.pt`
2. Runs 10 defense steps:
   - 📊 Monitor network state
   - 🔄 Build observation graph
   - 🤔 Agent decides action
   - ⚡ Execute action on container
3. Prints summary showing which components passed/failed

## Critical Unknowns

### Feature Dimension Mismatch

- **Graph builder outputs**: 200-dim features per node
- **Trained agent expects**: 325-dim features (311 base + 9 subnet + 5 message)
- **Solution**: `agent_adapter.py` pads 200→325 with zeros

**Risk**: If the trained agent semantically depends on specific feature positions beyond the first 200, it may produce garbage actions. We won't know until we test.

### Action Space Mapping

- **Agent outputs**: indices 0-80 (64 node actions + 16 edge actions + 1 sleep)
- **Bridge supports**: Monitor, Analyse, Restore
- **Mapping**: See `ACTION_TYPE_MAP` in `agent_adapter.py`

Some CybORG actions (Remove, DeployDecoy, BlockTraffic) don't have direct Containerlab equivalents, so they map to Monitor.

## Troubleshooting

### Agent fails to load

```
ModuleNotFoundError: No module named 'torch_geometric'
```
→ `pip install torch-geometric`

### Docker permission denied

```
docker.errors.DockerException: Error while fetching server API version
```
→ Run with `sudo python test_integration.py`

### Graph builder crashes

```
ValueError: need at least one array to concatenate
```
→ Make sure Containerlab is running:
```bash
cd ../containerlab-networks/
sudo containerlab deploy -t fyp-topology.yaml
```

### Agent produces random-looking actions

This is expected if feature encoding doesn't match training. The agent will technically run but won't defend intelligently. To fix:
1. Study `trained-agent/wrapper/ChallengeWrapper.py` to see exact feature encoding
2. Update `graph_builder.py` to match that encoding in the first 200 dims
3. Test again

## Next Steps

After integration test passes:
1. **Add attack simulation** (run malware in attacker container)
2. **Compare performance**: Agent vs. random baseline
3. **Document findings**: Does the agent generalize from CybORG to real networks?
