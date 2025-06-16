# intermediary.py

import sys
import requests
from flask import Flask, jsonify, abort
import node as node
from node import BlockchainNode
import time

app = Flask(__name__)

if len(sys.argv) < 2:
    print("Usage: python intermediary.py <desired_port> [next_hop_address]")
    sys.exit(1)

requested_port = int(sys.argv[1])
next_hop = sys.argv[2] if len(sys.argv) >= 3 else "127.0.0.1:5003"  # default to provider

# Launch this as a blockchain node
my_node = BlockchainNode(app, desired_port=requested_port, role="intermediary")

@app.route('/request/<int:user_id>', methods=['GET'])
def forward_request(user_id):
    """
    1. Sync chain
    2. Mine a block with dummy transaction
    3. Broadcast the block
    4. Forward the GET to next hop (intermediary or provider)
    5. Return the final result
    """
    print(f"[GET /request/{user_id}] Handled by intermediary: {my_node.MY_ADDRESS}")

    # # (1) Sync chain
    # longest_chain = node.bc.chain
    # for peer in node.bc.get_node_addresses():
    #     try:
    #         r = requests.get(f"http://{peer}/chain", timeout=3)
    #         if r.status_code == 200:
    #             data = r.json()
    #             if data['length'] > len(longest_chain) and node.bc.valid_chain(data['chain']):
    #                 longest_chain = data['chain']
    #     except:
    #         continue
    # node.bc.chain = longest_chain.copy()

    # # (2) Create a dummy transaction and mine a block
    # node.bc.new_transaction(
    #     sender=f"intermediary_{my_node.MY_ADDRESS}",
    #     recipient="all"
    # )
    # last_proof = node.bc.last_block['proof']
    # proof = node.bc.proof_of_work(last_proof)
    # block = node.bc.new_block(proof, mined_by=f"intermediary_{my_node.MY_ADDRESS}")

    # # (3) Broadcast to peers
    # for peer in node.bc.get_node_addresses():
    #     try:
    #         requests.get(f"http://{peer}/sync", timeout=2)
    #         requests.post(f"http://{peer}/receive_block", json={"block": block}, timeout=2)
    #     except:
    #         continue

    # (4) Forward to next hop's /request or /city endpoint
    try:
        # If final hop is provider, use /city/<id>, else /request/<id>
        if next_hop.endswith(":5003"):
            print(f"→ Forwarding to provider: {next_hop}")
            response = requests.get(f"http://{next_hop}/city/{user_id}", timeout=3)
        else:
            print(f"→ Forwarding to next intermediary: {next_hop}")
            response = requests.get(f"http://{next_hop}/request/{user_id}", timeout=3)

        if response.status_code == 404:
            return jsonify({"error": "User not found"}), 404
        return jsonify(response.json()), 200

    except requests.exceptions.RequestException:
        return abort(503, description=f"Cannot reach next hop at {next_hop}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_node.PORT, threaded=True)