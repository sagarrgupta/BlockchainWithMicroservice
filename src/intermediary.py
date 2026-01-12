# intermediary.py

import sys
import requests
from flask import Flask, jsonify, abort
import node as node
from node import BlockchainNode

app = Flask(__name__)

if len(sys.argv) < 2:
    print("Usage: python intermediary.py <desired_port> [next_hop_address]")
    sys.exit(1)

requested_port = int(sys.argv[1])
next_hop = sys.argv[2] if len(sys.argv) >= 3 else "127.0.0.1:5003"  # default to provider

# Launch this as a blockchain node
my_node = BlockchainNode(app, desired_port=requested_port, role="intermediary")

@app.route('/request/<int:city_id>', methods=['GET'])
def forward_request(city_id):
    """
    New flow:
    1. Forward the GET to next hop (provider).
    2. Collect blockTransactionData from provider's response.
    3. Add intermediary's own blockTransactionData.
    4. Return both the data and the list of blockTransactionData to the requester.
    """
    print(f"[GET /request/{city_id}] Handled by intermediary: {my_node.MY_ADDRESS}")
    block_transactions = []
    provider_data = None
    try:
        # If final hop is provider, use /city/<id>
        if next_hop.endswith(":5003"):
            print(f"→ Forwarding to provider: {next_hop}")
            response = requests.get(f"http://{next_hop}/city/{city_id}", timeout=3)
        else:
            print(f"→ Forwarding to next intermediary: {next_hop}")
            response = requests.get(f"http://{next_hop}/request/{city_id}", timeout=3)
        if response.status_code == 404:
            return jsonify({"error": "city not found"}), 404
        if response.status_code != 200:
            return jsonify({"error": "Provider/intermediary error"}), 503
        data = response.json()
        provider_data = data.get("city_data") or data

        # (3) Add intermediary's own blockTransactionData FIRST
        my_block_tx = {
            "sender": f"intermediary_{my_node.MY_ADDRESS}",
            "recipient": "BackToSender",
            "requestInfo": f"/request/{city_id}"
        }
        block_transactions.append(my_block_tx)

        # (2) Collect blockTransactionData from provider/intermediary and append after
        block_tx = data.get("blockTransactionData")
        block_tx_list = data.get("blockTransactionDataList")
        if block_tx_list:
            block_transactions.extend(block_tx_list)
        elif block_tx:
            block_transactions.append(block_tx)

        # (4) Return both the data and the blockTransactionData list
        return jsonify({
        "city_data": provider_data,
        "blockTransactionDataList": block_transactions
        }), 200
        
    except requests.exceptions.RequestException:
        return abort(503, description=f"Cannot reach next hop at {next_hop}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_node.PORT, threaded=True)