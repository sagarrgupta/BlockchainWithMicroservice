# requester.py

import sys
import requests
from flask import Flask, jsonify, abort
import node as node
from node import BlockchainNode
import time
from node import get_host_port

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
        host_port = get_host_port(provider_addr)
        resp = requests.get(f"http://{host_port}/city/{city_id}", timeout=5)
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
        "recipient": provider_addr,
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
    # Sync step: adopt the longest chain from master peers first, then regular peers
    longest_chain = node.bc.chain
    sync_sources = list(node.bc.master_peers) if hasattr(node.bc, 'master_peers') and node.bc.master_peers else node.bc.get_node_addresses()
    for peer in sync_sources:
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
    # Broadcast the newly mined block: first to master peers, then to other peers
    peer_results = []
    all_peers = node.bc.get_node_addresses()
    master_peers = list(node.bc.master_peers) if hasattr(node.bc, 'master_peers') else []
    other_peers = [p for p in all_peers if p not in master_peers]
    # Send to master peers first
    for peer in master_peers:
        try:
            host_port = get_host_port(peer)
            resp = requests.post(f"http://{host_port}/receive_block", json={'block': new_block}, timeout=2)
            peer_results.append((peer, resp.status_code))
        except Exception as e:
            peer_results.append((peer, f"error: {e}"))
    # Then send to other peers
    for peer in other_peers:
        try:
            host_port = get_host_port(peer)
            resp = requests.post(f"http://{host_port}/receive_block", json={'block': new_block}, timeout=2)
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
    1) Optimized sync: For each peer, fetch only the last block hash and length. Only fetch full chain if hashes differ and peer's chain is longer.
    2) Mine a block with (contract_id="update_resource", payload includes city_id, risk_level, origin, destination).
    3) Broadcast that block.
    """
    startTime = time.time() * 1000
    node.bc.startTime.append(startTime)
    # (1) Optimized Sync step: only fetch last hash and length first
    longest_chain = node.bc.chain
    my_last_block = node.bc.last_block
    my_last_hash = node.bc.hash(my_last_block)
    my_length = len(node.bc.chain)
    candidate_peer = None
    candidate_peer_length = my_length
    candidate_peer_hash = my_last_hash
    # Try master peers first
    master_peers = list(node.bc.master_peers) if hasattr(node.bc, 'master_peers') and node.bc.master_peers else []
    # all_peers = node.bc.get_node_addresses()
    checked_peers = set()
    def try_peers(peers):
        nonlocal candidate_peer, candidate_peer_length, candidate_peer_hash, checked_peers
        import concurrent.futures
        def fetch_summary(peer):
            checked_peers.add(peer)
            try:
                r = requests.get(f"http://{peer}/chain/summary", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    peer_length = data.get('length')
                    peer_last_hash = data.get('last_hash')
                    return (peer, peer_length, peer_last_hash)
            except Exception:
                return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(peers)) as executor:
            results = list(executor.map(fetch_summary, peers))
        for result in results:
            if result:
                peer, peer_length, peer_last_hash = result
                if peer_last_hash != my_last_hash and peer_length > my_length:
                    if peer_length > candidate_peer_length:
                        candidate_peer = peer
                        candidate_peer_length = peer_length
                        candidate_peer_hash = peer_last_hash
    # 1. Try master peers
    try_peers(master_peers)
    # 2. If no candidate found, try other peers
    # if not candidate_peer:
    #     other_peers = [p for p in all_peers if p not in checked_peers]
    #     try_peers(other_peers)
    # Only fetch full chain if needed
    if candidate_peer:
        try:
            r = requests.get(f"http://{candidate_peer}/chain", timeout=5)
            if r.status_code == 200:
                data = r.json()
                peer_chain = data.get('chain')
                if peer_chain and len(peer_chain) == candidate_peer_length and node.bc.hash(peer_chain[-1]) == candidate_peer_hash and node.bc.valid_chain(peer_chain):
                    longest_chain = peer_chain
        except Exception:
            pass
    node.bc.chain = longest_chain.copy()
    node.bc.chainSyncedTime.append(time.time() * 1000)

    # (2) Mine a new block with the update request
    last_block = node.bc.last_block
    last_proof = last_block['proof']
    proof = node.bc.proof_of_work(last_proof)
    node.bc.blockMinedTime.append(time.time() * 1000)
    # Create transaction for the update request
    node.bc.new_transaction(
        sender=f"requester_{my_node.MY_ADDRESS}",
        recipient="provider",
        contract_id="update_resource_allocation",
        contract_payload={
            "city_id": city_id,
            "risk_level": risk_level,
            "authority": "provider"
        }
    )

    # Mine the block
    previous_hash = node.bc.hash(last_block)
    block = node.bc.new_block(proof, previous_hash, mined_by=f"requester_{my_node.MY_ADDRESS}")

    # (3) Broadcast the new block to all peers
    peers = node.bc.get_node_addresses()
    master_peers = list(node.bc.master_peers) if hasattr(node.bc, 'master_peers') and node.bc.master_peers else []
    provider_peers = []
    other_peers = []
    for p in peers:
        if p in master_peers:
            continue  # handled separately
        elif node.bc.peers_roles.get(p) == 'provider':
            provider_peers.append(p)
        else:
            other_peers.append(p)

    # 1. Try to broadcast to master peers first, but as soon as one succeeds, proceed to providers/others
    failed_masters = []
    for master in master_peers:
        try:
            host_port = get_host_port(master)
            resp = requests.post(f"http://{host_port}/receive_block", json={'block': block}, timeout=3)
            if resp.status_code == 200:
                break  # proceed to providers/others immediately
            else:
                failed_masters.append(master)
        except Exception:
            failed_masters.append(master)

    # 2. Broadcast to provider peers
    for peer in provider_peers:
        try:
            host_port = get_host_port(peer)
            requests.post(f"http://{host_port}/receive_block", json={'block': block}, timeout=3)
        except Exception:
            continue

    # 3. Broadcast to other peers
    for peer in other_peers:
        try:
            host_port = get_host_port(peer)
            requests.post(f"http://{host_port}/receive_block", json={'block': block}, timeout=3)
        except Exception:
            continue

    # 4. Try remaining master peers (those not contacted successfully)
    for master in failed_masters:
        try:
            host_port = get_host_port(master)
            requests.post(f"http://{host_port}/receive_block", json={'block': block}, timeout=3)
        except Exception:
            continue

    node.bc.blockPropagationTime.append(time.time() * 1000)
    timeItTook = ((time.time() * 1000) - node.bc.startTime[-1])
    return jsonify({
        "message": f"Resource update request broadcasted via blockchain. Time taken: {round(timeItTook, 2)} ms"
    }), 200

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