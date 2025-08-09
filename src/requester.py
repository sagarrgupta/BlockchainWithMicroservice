# requester.py

import sys
import requests
from flask import Flask, jsonify
import node as node
from node import BlockchainNode
import time
from node import get_host_port

app = Flask(__name__)

if len(sys.argv) != 2:
    print("Usage: python requester.py <desired_port>")
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
    1) Call the provider service at /city/<city_id> to get actual data and blockTransactionData.
    2) Add our own blockTransactionData FIRST, then append others from the response chain.
    3) Return the data to the user.
    4) Sync, mine a single block with all collected blockTransactionData, and broadcast it.
    """
    start_time = time.time()
    block_transactions = []
    provider_data = None
    try:
        # (1) Directly hit provider service
        provider_addr = "provider_service:5004"
        host_port = get_host_port(provider_addr)
        resp = requests.get(f"http://{host_port}/city/{city_id}", timeout=5)
        if resp.status_code == 404:
            return jsonify({"error": "city not found"}), 404
        if resp.status_code != 200:
            return jsonify({"error": "Provider error"}), 503
        data = resp.json()
        provider_data = data.get("city_data") or data
        # (3) Collect blockTransactionData from provider
        block_tx = data.get("blockTransactionData")
        block_tx_list = data.get("blockTransactionDataList")
    except Exception as e:
        return jsonify({"error": "Failed to fetch provider data", "details": str(e)}), 503

    # (4) Add our own blockTransactionData FIRST
    my_block_tx = {
        "sender": f"requester_{my_node.MY_ADDRESS}",
        "recipient": provider_addr,
        "requestInfo": f"/request/{city_id}"
    }
    block_transactions.append(my_block_tx)
    # (5) Append other blockTransactionData from provider
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

    # (7) After responding, sync, mine, and broadcast the block via centralized helper
    import threading
    threading.Thread(
        target=node.mine_and_broadcast_transactions,
        args=(block_transactions, f"requester_{my_node.MY_ADDRESS}"),
        daemon=True
    ).start()
    return jsonify(response_json), 200

@app.route('/update_resource/<int:city_id>/<string:risk_level>', methods=['POST'])
def update_resource_allocation(city_id, risk_level):
    """
    1) Sync: prefer masters, then others
    2) Mine a block with contract_id="update_resource_allocation"
    3) Broadcast that block.
    """
    # Measure total time locally for response
    req_start = time.time()
    # (1) Sync: prefer masters, then others
    try:
        node.sync_chain_prefer_masters()
    except Exception:
        pass
    # (2) Mine and broadcast via centralized helper
    node.mine_contract_and_broadcast(
        contract_id="update_resource_allocation",
        contract_payload={
            "city_id": city_id,
            "risk_level": risk_level,
            "authority": "provider"
        },
        sender_identifier=f"requester_{my_node.MY_ADDRESS}",
        recipient_role='provider'
    )
    timeItTook = (time.time() - req_start) * 1000
    return jsonify({
        "message": f"Resource update request broadcasted via blockchain. Time taken: {round(timeItTook, 2)} ms"
    }), 200

@app.route('/direct_update_resource/<int:city_id>/<string:risk_level>', methods=['POST'])
def direct_update_resource_allocation(city_id, risk_level):
    start_time = time.time()

    # (4) Directly hit the provider service
    try:
        provider_addr = "provider_service:5004"
        host_port = get_host_port(provider_addr)
    except Exception as e:
        return jsonify({"error": "Failed to resolve provider service", "details": str(e)}), 503

    # (5) Call provider service to update the resource allocation
    try:
        response = requests.post(f"http://{host_port}/direct_update_resource/{city_id}/{risk_level}", timeout=3)
        if response.status_code == 200:
            timeItTook = (time.time() - start_time) * 1000  # convert to milliseconds
            return jsonify({
                "message": f"Resource allocation updated successfully and time it took was {round(timeItTook, 2)} ms"
            }), 200
        else:
            return jsonify({"error": "Failed to update resource allocation"}), 500
    except Exception:
        return jsonify({"error": "Provider service unavailable"}), 503

# ─── 3) Start the Flask Server ───────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_node.PORT, threaded=True)