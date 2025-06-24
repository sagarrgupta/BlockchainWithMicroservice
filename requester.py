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

# ─── 2) Requester's Custom Endpoint: /request/<city_id> ──────────────────────────
@app.route('/request/<int:city_id>', methods=['GET'])
def request_city(city_id):
    """
    New flow:
    1) Call the provider/intermediary service at /city/<city_id> to get actual data and blockTransactionData.
    2) Add our own blockTransactionData FIRST, then append others from the response chain.
    3) Return the data to the user.
    4) Sync, mine a single block with all collected blockTransactionData, and broadcast it.
    """
    start_time = time.time()
    block_transactions = []
    provider_data = None
    provider_addr = None
    try:
        # (1) Fetch all peers and select the provider
        resp = requests.get(f"http://127.0.0.1:{my_node.PORT}/nodes", timeout=5)
        peers = resp.json().get("peers", [])
        providers = [p for p in peers if p.get("role") == "provider"]
        if not providers:
            return jsonify({"error": "No providers available"}), 503
        provider_addr = providers[0]["address"]
        # (2) Call provider directly (or via intermediary if needed)
        intermediary_addr = "127.0.0.1:5004"
        resp = requests.get(f"http://{intermediary_addr}/request/{city_id}", timeout=5)
        if resp.status_code == 404:
            return jsonify({"error": "city not found"}), 404
        if resp.status_code != 200:
            return jsonify({"error": "Provider error"}), 503
        data = resp.json()
        provider_data = data.get("city_data") or data
        # (3) Collect blockTransactionData from provider/intermediary
        block_tx = data.get("blockTransactionData")
        block_tx_list = data.get("blockTransactionDataList")
    except Exception as e:
        return jsonify({"error": "Failed to fetch provider data", "details": str(e)}), 503

    # (4) Add our own blockTransactionData FIRST
    my_block_tx = {
        "sender": f"requester_{my_node.MY_ADDRESS}",
        "recipient": intermediary_addr,
        "requestInfo": f"/request/{city_id}"
    }
    block_transactions.append(my_block_tx)
    # (5) Append other blockTransactionData from provider/intermediary
    if block_tx_list:
        block_transactions.extend(block_tx_list)
    elif block_tx:
        block_transactions.append(block_tx)

    # (6) Return the data to the user first
    timeItTook = (time.time() - start_time) * 1000  # ms
    response_json = {
        "city_data": provider_data,
        "message": f"Data fetched and time it took was {round(timeItTook, 2)} ms"
    }

    # (7) After responding, sync, mine, and broadcast the block
    import threading
    threading.Thread(target=mine_and_broadcast_block, args=(block_transactions,), daemon=True).start()
    return jsonify(response_json), 200

def mine_and_broadcast_block(blockTransactions):
    # start time for block propagation
    node.bc.startTime.append(time.time())
    # Sync step: adopt the longest chain from peers
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
    node.bc.chainSyncedTime.append(time.time())
    # Mine a single block with all collected blockTransactionData as transactions
    node.bc.current_transactions = blockTransactions
    last_proof = node.bc.last_block['proof']
    proof = node.bc.proof_of_work(last_proof)
    new_block = node.bc.new_block(proof, mined_by=f"requester_{my_node.MY_ADDRESS}")
    # Log mining start time
    node.bc.blockMinedTime.append(time.time())
    mining_start = time.time()
    # Broadcast the newly mined block to all peers and wait for responses
    peer_results = []
    peers = node.bc.get_node_addresses()
    # Move provider to the end of the list
    provider_peer = None
    for peer in peers:
        if "provider" in peer:
            provider_peer = peer
            break
    if provider_peer:
        peers = [p for p in peers if p != provider_peer] + [provider_peer]
    for peer in peers:
        try:
            resp = requests.post(f"http://{peer}/receive_block", json={'block': new_block}, timeout=2)
            peer_results.append((peer, resp.status_code))
        except Exception as e:
            peer_results.append((peer, f"error: {e}"))
    mining_end = time.time()
    propagation_time_ms = (mining_end - mining_start) * 1000
    print(f"[BLOCK PROPAGATION] Block index {new_block['index']} propagated to all peers in {propagation_time_ms:.2f} ms.")
    for peer, result in peer_results:
        print(f"  Peer {peer} result: {result}")

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
        intermediary_addr = "127.0.0.1:5004"
        response = requests.post(
            f"http://{intermediary_addr}/update_resource/{city_id}/{risk_level}",
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