# user.py

import sys
import requests
from flask import Flask, jsonify, request, abort
import node
from node import BlockchainNode
from node import get_host_port

app = Flask(__name__)

if len(sys.argv) != 2:
    print("Usage: python user.py <desired_port>")
    sys.exit(1)

desired_port = int(sys.argv[1])

# ─── 1) Launch a P2P/Blockchain Node with role="user_contract" ────────────────
contract_node = BlockchainNode(app, desired_port=desired_port, role="user_contract")


@app.route('/add_user', methods=['POST'])
def add_user():
    """
    1) Expect JSON { "id": <int>, "name": <str>, "initial_balance": <number> }.
    2) Sync with peers.
    3) Create a transaction {contract_id:"add_user", contract_payload:{id,name,initial_balance}}.
    4) PoW → new_block → broadcast.
    5) Return { "user":id, "balance":<new_balance>, "block":<block> }.
    """
    data = request.get_json()
    if not data or "id" not in data or "name" not in data:
        return abort(400, description="'id' and 'name' are required")

    user_id = data["id"]
    name    = data["name"]
    bal     = data.get("initial_balance", 0)

    # (1) Sync step: adopt the longest chain so far
    longest_chain = node.bc.chain
    for peer in node.bc.get_node_addresses():
        try:
            host_port = get_host_port(peer)
            r = requests.get(f"http://{host_port}/chain", timeout=3)
            if r.status_code == 200:
                d = r.json()
                length = d.get('length')
                chain  = d.get('chain')
                if length and chain and length > len(longest_chain) and node.bc.valid_chain(chain):
                    longest_chain = chain
        except:
            continue
    node.bc.chain = longest_chain.copy()

    # (2) Create the "add_user" transaction
    node.bc.new_transaction(
        sender=f"user_service_{contract_node.MY_ADDRESS}",
        recipient="all",
        contract_id="add_user",
        contract_payload={
            "id": user_id,
            "name": name,
            "initial_balance": bal
        }
    )

    # (3) PoW + forge a new block
    last_proof = node.bc.last_block['proof']
    proof = node.bc.proof_of_work(last_proof)
    new_block = node.bc.new_block(proof, mined_by=f"user_service_{contract_node.MY_ADDRESS}")

    # (4) Broadcast to all peers
    for peer in node.bc.get_node_addresses():
        try:
            host_port = get_host_port(peer)
            requests.post(f"http://{host_port}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass

    # (5) Return updated state for this user
    user_entry = node.bc.users.get(user_id, {})
    updated_balance = user_entry.get("balance", 0)
    return jsonify({
        "user": user_id,
        "balance": updated_balance,
        "block": new_block
    }), 200


@app.route('/transfer', methods=['POST'])
def transfer():
    """
    1) Expect JSON { "from_id": <int>, "to_id": <int>, "amount": <number> }.
    2) Sync with peers.
    3) Create transaction {contract_id:"transfer", payload:{from_id,to_id,amount}}.
    4) PoW → new_block → broadcast.
    5) Return {
         "from_id": <int>,
         "to_id": <int>,
         "amount": <number>,
         "balances": { "<from_id>": <new_balance>, "<to_id>": <new_balance> },
         "block": <block>
       }
    """
    data = request.get_json()
    if not data or "from_id" not in data or "to_id" not in data or "amount" not in data:
        return abort(400, description="'from_id', 'to_id', and 'amount' are required")

    src = data["from_id"]
    dst = data["to_id"]
    amt = data["amount"]

    # (1) Sync step
    longest_chain = node.bc.chain
    for peer in node.bc.get_node_addresses():
        try:
            host_port = get_host_port(peer)
            r = requests.get(f"http://{host_port}/chain", timeout=3)
            if r.status_code == 200:
                d = r.json()
                length = d.get('length')
                chain  = d.get('chain')
                if length and chain and length > len(longest_chain) and node.bc.valid_chain(chain):
                    longest_chain = chain
        except:
            continue
    node.bc.chain = longest_chain.copy()

    # (2) Create "transfer" transaction
    node.bc.new_transaction(
        sender=f"user_service_{contract_node.MY_ADDRESS}",
        recipient="all",
        contract_id="transfer",
        contract_payload={
            "from_id": src,
            "to_id": dst,
            "amount": amt
        }
    )

    # (3) PoW + forge new block
    last_proof = node.bc.last_block['proof']
    proof = node.bc.proof_of_work(last_proof)
    new_block = node.bc.new_block(proof, mined_by=f"user_service_{contract_node.MY_ADDRESS}")

    # (4) Broadcast to peers
    for peer in node.bc.get_node_addresses():
        try:
            host_port = get_host_port(peer)
            requests.post(f"http://{host_port}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass

    # (5) Return updated balances
    from_balance = node.bc.users.get(src, {}).get("balance", 0)
    to_balance   = node.bc.users.get(dst, {}).get("balance", 0)
    return jsonify({
        "from_id": src,
        "to_id": dst,
        "amount": amt,
        "balances": {
            str(src): from_balance,
            str(dst): to_balance
        },
        "block": new_block
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=contract_node.PORT, threaded=True)