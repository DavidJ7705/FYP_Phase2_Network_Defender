# Feature Encoding Improvements

## Problem
The agent was stuck outputting action index 64 (Monitor on database) for every decision because our original 200-dim feature encoding didn't match what the agent was trained on.

## Root Cause
The trained GNN-PPO agent expects a **192-dim** feature vector with this exact structure:

```
Position | Content                          | Dims
---------|----------------------------------|------
0-3      | Node type one-hot                | 4
4-173    | SystemNode features              | 170
         | - Architecture enum             | 
         | - OS Distribution enum          |
         | - OS Type enum                  |
         | - OS Version enum               |
         | - OS Kernel Version enum        |
         | - OS Patches enum               |
         | - crown_jewel flag              | 1
         | - user flag                     | 1
         | - server flag                   | 1
         | - router flag                   | 1
174-182  | Subnet membership (one-hot)      | 9
183-184  | Tabular (compromised, scanned)   | 2
185-187  | Messages (from other agents)     | 3
188-191  | Padding                          | 4
---------|----------------------------------|------
TOTAL                                       | 192
```

Our original `graph_builder.py` produced 200-dim features with generic placeholders.

## Solution: `graph_builder_v2.py`

Created a new graph builder that produces the exact 192-dim encoding:

### Key Changes:

1. **Node Type One-Hot** (positions 0-3):
   - SystemNode: [1,0,0,0]
   - ConnectionNode: [0,1,0,0]
   - FileNode: [0,0,1,0]
   - InternetNode: [0,0,0,1]

2. **SystemNode Features** (positions 4-173):
   - Infer OS from container image name (alpine → Alpine, postgres → Postgres, etc.)
   - Set role flags based on container name:
     - `crown_jewel=1` if "database" in name
     - `user=1` if "user" or "admin" in name
     - `server=1` if "server" or "web" or "database" in name
     - `router=0` (none of our containers are routers)

3. **Subnet Membership** (positions 174-182):
   - Map containers to subnet indices:
     - admin → subnet 0
     - operational (web-server, database) → subnet 1
     - public → subnet 2
     - attacker/internet → subnet 8

4. **Tabular Features** (positions 183-184):
   - `compromised=0` (not compromised yet)
   - `scanned=0` (not scanned yet)
   - ***Note***: These would update during an attack scenario

5. **Message Features** (positions 185-187):
   - `was_scanned=0`
   - `was_compromised=0`
   - `is_received=0`
   - ***Note***: In CybORG, agents share intel. We don't have multi-agent setup.

### ConnectionNode Encoding

For open ports (e.g., port 22, 80, 443):
- Node type: [0,1,0,0]
- Process name inferred from port (22 → SSH, 80 → Apache, 443 → HTTPS, etc.)
- Process type inferred from port (80/443 → WebServer, 22 → SSH, 5432 → Database)
- Flags:
  - `is_default=1` for standard services (22, 80, 443, 5432)
  - `is_ephemeral=1` for high ports (>49152)
  - `suspicious_pid=0`, `is_decoy=0` by default

## Expected Improvement

With features matching the training distribution:
- **Before**: Agent saw mostly zeros/garbage → defaulted to safe action (index 64)
- **After**: Agent sees structured features it was trained on → should make diverse decisions

###Testing

Run the integration test again:
```bash
cd /mnt/mac/Users/davidjayakumar/Desktop/FYP_PHASE2_NETWORK_DEFENDER/bridge
sudo ./venv-linux/bin/python test_integration.py
```

Look for:
- ✅ **Different action indices** across 10 steps (not just 64 repeatedly)
- ✅ **Variety in targets** (not just "database" every time)
- ✅ **Mix of Monitor/Analyse/Restore** actions

## Remaining Limitations

Even with matching features, the agent may still struggle because:
1. **Different network topology**: Trained on CybORG's 9-subnet enterprise, deployed on our 3-zone network
2. **No attack indicators**: Features like `compromised=0` don't trigger defensive behavior
3. **No multi-agent comms**: Message features are zeros (trained agents coordinate)

To truly evaluate, we'd need to:
- Simulate attacks (next step: SCRUM-104)
- Update `compromised` and `scanned` flags when attacks are detected
- Compare agent performance vs. random baseline
