# provider.py

import sys
import requests
from flask import Flask, jsonify, abort
import node
from node import BlockchainNode
import os

app = Flask(__name__)

if len(sys.argv) != 2:
    print("Usage: python provider.py <desired_port>")
    sys.exit(1)

desired_port = int(sys.argv[1])

# ─── 1) Launch the P2P/Blockchain “Provider” Node ─────────────────────────────
provider_node = BlockchainNode(app, desired_port=desired_port, role="provider")


@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    1) Sync → adopt the longest chain from peers.
    2) Mine a “log request” block (dummy transaction) so that every GET /user/... 
       creates a new block (without altering on‐chain user balances).
    3) Broadcast that dummy block.
    4) Look up on‐chain user (by id) in bc.users.
    5) Return JSON { "id":..., "name":..., "balance":... } or 404 if missing.
    """

    # Log the container handling the request
    print(f"[GET /user/{user_id}] Handled by container: {os.uname()[1]}")

    # ─── (1) Sync step ──────────────────────────────────────────────────────────
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

    # ─── (2) Mine a dummy “log request” block ───────────────────────────────────
    # We create a minimal transaction whose only purpose is to record that
    # this provider served a /user/<user_id> call. We do NOT include a contract_id,
    # so apply_contracts(...) will ignore it and not change any balances.
    node.bc.new_transaction(
        sender=f"provider_{provider_node.MY_ADDRESS}",
        recipient="all"
        # no contract_id or contract_payload here; this is purely for logging
    )

    # Proof‐of‐Work, forge a new block, and broadcast it
    last_proof = node.bc.last_block['proof']
    proof = node.bc.proof_of_work(last_proof)
    new_block = node.bc.new_block(proof, mined_by=f"provider_{provider_node.MY_ADDRESS}")

    # Broadcast new block to all peers
    for peer in node.bc.get_node_addresses():
        try:
            requests.post(f"http://{peer}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass

    # ─── (3) Look up the user on‐chain ─────────────────────────────────────────
    entry = node.bc.users.get(user_id, None)
    if entry is None:
        return jsonify({"error": f"User ID {user_id} not found"}), 404

    return jsonify({
        "id": user_id,
        "name": entry["name"],
        "balance": entry["balance"]
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=provider_node.PORT, threaded=True)