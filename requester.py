# requester.py

import sys
import requests
from flask import Flask, jsonify, abort
import node as node
from node import BlockchainNode
import time

app = Flask(__name__)

if len(sys.argv) != 2:
    print("Usage: python provider.py <desired_port>")
    sys.exit(1)

requested_port = int(sys.argv[1])

# ─── 1) Launch the P2P/Blockchain "Node" ────────────────────────────────────────
# Supply the Flask app and the desired port (from sys.argv)
my_node = BlockchainNode(app, desired_port=requested_port, role="requester")

# ─── 2) Requester's Custom Endpoint: /request/<user_id> ──────────────────────────
@app.route('/request/<int:user_id>', methods=['GET'])
def request_user(user_id):
    """
    1) Sync → mine a block with (origin="requester", destination="provider", requested_user_id=user_id).
    2) Broadcast that block.
    3) Call the provider service at /user/<user_id> to get actual data.
    4) Return that data (or 404).
    """
    # (1) Sync step: adopt the longest chain from peers
    longest_chain = node.bc.chain
    for peer in node.bc.get_node_addresses():
        try:
            r = requests.get(f"http://{peer}/chain", timeout=3)
            if r.status_code == 200:
                data = r.json()
                length = data.get('length')
                chain  = data.get('chain')
                if length and chain and length > len(longest_chain) and node.bc.valid_chain(chain):
                    longest_chain = chain
        except:
            continue
    node.bc.chain = longest_chain.copy()

    # (2) Record the transaction & mine a new block
    node.bc.new_transaction(
        sender="requester",
        recipient="provider",
        requested_user_id=user_id
    )
    last_proof = node.bc.last_block['proof']
    proof = node.bc.proof_of_work(last_proof)
    new_block = node.bc.new_block(proof, mined_by=f"requester_{my_node.MY_ADDRESS}")

    # Broadcast the newly mined block to all peers
    for peer in node.bc.get_node_addresses():
        try:
            requests.post(f"http://{peer}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass

    # (3) Fetch all peers and select the provider with the lowest load
    try:
        resp = requests.get(f"http://127.0.0.1:{my_node.PORT}/nodes", timeout=5)
        peers = resp.json().get("peers", [])
        # Just look for role == "provider"
        providers = [p for p in peers if p.get("role") == "provider"]
        if not providers:
            return jsonify({"error": "No providers available"}), 503
        # Pick the first provider (or implement any other selection logic)
        provider_addr = providers[0]["address"]
    except Exception as e:
        return jsonify({"error": "Failed to fetch providers", "details": str(e)}), 503

    # (4) Fetch actual data from selected provider
    try:
        resp = requests.get(f"http://{provider_addr}/city/{user_id}", timeout=5)
    except requests.exceptions.RequestException:    
        return abort(503, description="Cannot reach provider service")

    if resp.status_code == 404:
        return jsonify({"error": "User not found"}), 404

    user_data = resp.json()
    # (5) Return the user data, plus the newly mined block and the updated chain
    return jsonify({
        "user_data": user_data,
        "logged_block": new_block,
        "chain": node.bc.chain,
        "provider": provider_addr
    }), 200

@app.route('/update_resource/<int:city_id>/<string:risk_level>', methods=['POST'])
def update_resource_allocation(city_id, risk_level):
    """
    1) Sync → mine a block with (origin="requester", destination="provider", city_id=city_id, risk_level=risk_level).
    2) Broadcast that block.
    3) Call the provider service to update the resource allocation.
    4) Return success or error.
    """
    start_time = time.time()
    # (1) Sync step: adopt the longest chain from peers
    longest_chain = node.bc.chain
    for peer in node.bc.get_node_addresses():
        try:
            r = requests.get(f"http://{peer}/chain", timeout=3)
            if r.status_code == 200:
                data = r.json()
                length = data.get('length')
                chain  = data.get('chain')
                if length and chain and length > len(longest_chain) and node.bc.valid_chain(chain):
                    longest_chain = chain
        except:
            continue
    node.bc.chain = longest_chain.copy()

    # (2) Mine a new block with the update request
    last_block = node.bc.last_block
    last_proof = last_block['proof']
    proof = node.bc.proof_of_work(last_proof)

    # Create transaction for the update request
    node.bc.new_transaction(
        sender="requester",
        recipient="provider",
        contract_id=city_id,
        contract_payload={"risk_level": risk_level}
    )

    # Mine the block
    previous_hash = node.bc.hash(last_block)
    block = node.bc.new_block(proof, previous_hash, mined_by="requester")

    # (3) Broadcast the new block to all peers
    for peer in node.bc.get_node_addresses():
        try:
            requests.post(f"http://{peer}/receive_block", json=block, timeout=3)
        except:
            continue

    # (4) Fetch all peers and select the provider with the lowest load
    try:
        resp = requests.get(f"http://127.0.0.1:{my_node.PORT}/nodes", timeout=5)
        peers = resp.json().get("peers", [])
        # Just look for role == "provider"
        providers = [p for p in peers if p.get("role") == "provider"]
        if not providers:
            return jsonify({"error": "No providers available"}), 503
        # Pick the first provider (or implement any other selection logic)
        provider_addr = providers[0]["address"]
    except Exception as e:
        return jsonify({"error": "Failed to fetch providers", "details": str(e)}), 503

    # (5) Call provider service to update the resource allocation
    try:
        response = requests.post(
            f"http://{provider_addr}/update_resource/{city_id}/{risk_level}",
            timeout=3
        )
        if response.status_code == 200:
            timeItTook = (time.time() - start_time) * 1000  # convert to milliseconds
            return jsonify({
                "message": f"Resource allocation updated successfully and time it took was {round(timeItTook, 2)} ms"
            }), 200
        else:
            return jsonify({"error": "Failed to update resource allocation"}), 500
    except:
        return jsonify({"error": "Provider service unavailable"}), 503

@app.route('/direct_update_resource/<int:city_id>/<string:risk_level>', methods=['POST'])
def direct_update_resource_allocation(city_id, risk_level):
    start_time = time.time()

    # (4) Fetch all peers and select the provider with the lowest load
    try:
        resp = requests.get(f"http://127.0.0.1:{my_node.PORT}/nodes", timeout=5)
        peers = resp.json().get("peers", [])
        # Just look for role == "provider"
        providers = [p for p in peers if p.get("role") == "provider"]
        if not providers:
            return jsonify({"error": "No providers available"}), 503
        # Pick the first provider (or implement any other selection logic)
        provider_addr = providers[0]["address"]
    except Exception as e:
        return jsonify({"error": "Failed to fetch providers", "details": str(e)}), 503

    # (5) Call provider service to update the resource allocation
    try:
        response = requests.post(
            f"http://{provider_addr}/direct_update_resource/{city_id}/{risk_level}",
            timeout=3
        )
        if response.status_code == 200:
            timeItTook = (time.time() - start_time) * 1000  # convert to milliseconds
            return jsonify({
                "message": f"Resource allocation updated successfully and time it took was {round(timeItTook, 2)} ms"
            }), 200
        else:
            return jsonify({"error": "Failed to update resource allocation"}), 500
    except:
        return jsonify({"error": "Provider service unavailable"}), 503

# ─── 3) Start the Flask Server ───────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_node.PORT, threaded=True)