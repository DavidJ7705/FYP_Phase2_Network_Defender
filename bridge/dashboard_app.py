"""
Real-time dashboard for GNN-PPO Network Defense
Shows network topology, attack progression, and blue agent actions
"""
import json
import os
from flask import Flask, render_template, jsonify
from datetime import datetime

app = Flask(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

def get_current_state():
    """Read the latest state from run_agent.py"""
    if not os.path.exists(STATE_FILE):
        return {
            "step": 0,
            "red_phase": 0,
            "red_phase_name": "Idle",
            "nodes": [],
            "compromised": [],
            "last_action": {"type": "Monitor", "target": "-"},
            "blue_stats": {},
            "red_log": [],
            "timestamp": datetime.now().isoformat()
        }

    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading state: {e}")
        return {"error": str(e)}

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/state')
def api_state():
    """API endpoint for current network state"""
    return jsonify(get_current_state())

if __name__ == '__main__':
    print("Starting dashboard on http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)
