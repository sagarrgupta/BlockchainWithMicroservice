# node.py
import sys, threading, requests, hashlib, json
from time import time, sleep
from urllib.parse import urlparse
from flask  import Flask, request, jsonify, Blueprint, abort
import os
import socket

# ─── Bootstrap Settings ─────────────────────────────────────────────
BOOTSTRAP_PORT = int(os.environ.get("BOOTSTRAP_PORT", "5002"))
BOOTSTRAP_HOST = os.getenv("BOOTSTRAP_HOST", "127.0.0.1")
BOOTSTRAP_ADDRESS = f"{BOOTSTRAP_HOST}:{BOOTSTRAP_PORT}"

# ─── Blockchain Class ──────────────────────────────────────────────
class Blockchain:
    def __init__(self):
        self.master_peers = set()      # set of all known master peer addresses (excluding ourselves)
        self.chain = []
        self.current_transactions = []
        self.nodes = set()             # peer addresses (host:port)
        self.peers_roles = {}          # peer_address → role string
        self.local_node = None         # this node's own address (host:port)
        self.bootstrap_node = None     # will store BOOTSTRAP_HOST
        self.mining_in_progress = False
        self.users = {}
        # ─── Block Propagation State ─────────────────────────────────────────────
        self.startTime = []
        self.chainSyncedTime = []
        self.blockMinedTime = []
        self.blockPropagationTime = []
        self.dataReceivedAtProviderTime = []
        self.endTime = []
        # Creating the genesis block
        self.new_block(previous_hash='1', proof=100, mined_by="Genesis", transactions=[], timestamp=time())

    # ─── NODE REGISTRATION / ROLES ───────────────────────────────────────────────
    def register_node(self, address, is_local=False):
        """
        Register a new node by its address. If is_local=True, that is this node.
        Otherwise, add to the peer set (excluding our own address).
        """
        parsed = urlparse(address if address.startswith('http') else f"http://{address}")
        node_address = parsed.netloc

        if is_local:
            self.local_node = node_address
            print(f"Registered local node as: {self.local_node}")
        else:
            if node_address != self.local_node and node_address not in self.nodes:
                self.nodes.add(node_address)
                print(f"Added remote node: {node_address}")

    def set_peer_role(self, address, role):
        """Record a peer's role (e.g. 'provider', 'requester', 'user_contract', 'master')."""
        self.peers_roles[address] = role
        # Maintain master_peers set
        if role == "master" and address != self.local_node:
            self.master_peers.add(address)
        elif address in self.master_peers:
            self.master_peers.discard(address)

    def get_node_addresses(self):
        """Return a list of all peer addresses (excluding ourselves)."""
        return [n for n in self.nodes if n != self.local_node]

    # ─── CONSENSUS / VALIDATION ─────────────────────────────────────────────────
    def valid_chain(self, chain):
        """
        Check that a given chain is valid:
        - Each block's previous_hash matches the SHA-256 of the prior block.
        - Each proof matches valid_proof(prev_proof, proof).
        """
        if not chain:
            return False

        last_block = chain[0]
        idx = 1
        while idx < len(chain):
            block = chain[idx]
            # Check previous_hash:
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Check proof of work:
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            idx += 1

        return True

    def resolve_conflicts(self):
        """
        Consensus: query all peers'/chain. If a longer valid chain is found,
        replace our own. Return True if replaced, False otherwise.
        """
        new_chain = None
        max_length = len(self.chain)

        # Query bootstrap first if present
        nodes_to_query = list(self.nodes)
        if self.bootstrap_node in nodes_to_query:
            nodes_to_query.remove(self.bootstrap_node)
            nodes_to_query.insert(0, self.bootstrap_node)

        for node_addr in nodes_to_query:
            if node_addr == self.local_node:
                continue
            try:
                host_port = get_host_port(node_addr)
                r = requests.get(f"http://{host_port}/chain", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    length = data.get('length')
                    chain = data.get('chain')
                    if length and chain and length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except requests.exceptions.RequestException:
                continue

        if new_chain:
            self.chain = new_chain
            print(f"Chain replaced with longer chain of length {len(new_chain)}")
            return True

        return False

    # ─── BLOCK & TRANSACTION MANAGEMENT ────────────────────────────────────────
    def new_block(self, proof, previous_hash=None, mined_by="Unknown", transactions=None, timestamp=None):
        """
        Create a new block in the blockchain:
        - proof: the proof-of-work found
        - previous_hash: hash of previous block (optional)
        - mined_by: identifier of miner
        - transactions: list of blockTransactionData dicts
        - timestamp: time of block mined
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': timestamp if timestamp is not None else time(),
            'transactions': transactions if transactions is not None else self.current_transactions.copy(),
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'mined_by': mined_by
        }
        self.current_transactions = []
        self.chain.append(block)
        self.apply_contracts(block)
        return block

    def new_transaction(self, sender, recipient, contract_id=None, contract_payload=None, requested_user_id=None):
        """
        Add a new transaction to the list of pending transactions. If
        contract_id is provided, then apply_contracts will pick it up later.
        :param sender: <str> e.g. "user_service_127.0.0.1:5002"
        :param recipient: <str> (not used for data contracts, but we fill 'all')
        :param contract_id: <str> one of "add_user", "transfer", etc.
        :param contract_payload: <dict> arbitrary contract data
        :return: <int> index of the block that will hold this tx (i.e. last_block.index + 1)
        """
        tx = {
            'sender': sender,
            'recipient': recipient
        }
        if contract_id:
            tx['contract_id'] = contract_id
            tx['contract_payload'] = contract_payload or {}
        
        if requested_user_id:
            tx['requested_user_id'] = requested_user_id

        self.current_transactions.append(tx)
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    # ─── PROOF‐OF‐WORK ──────────────────────────────────────────────────────────
    def proof_of_work(self, last_proof):
        """
        Simple PoW: find a number 'proof' such that SHA256(str(last_proof)+str(proof))
        starts with four leading zeros.
        """
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Check if SHA256(str(last_proof) + str(proof)) has four leading zeros.
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:1] == "0"

    # ─── HASHING ────────────────────────────────────────────────────────────────
    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a block (dictionary). We must sort keys
        to make sure that identical blocks always produce the same hash.
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    # ─── UTILITY: Return chain as JSON (for /chain endpoint) ─────────────────
    def to_dict(self):
        return {
            'chain': self.chain,
            'length': len(self.chain)
        }

    # ─── «SMART CONTRACT» HANDLER ────────────────────────────────────────────────
    def apply_contracts(self, block):
        """
        For each transaction in the newly‐appended block, check if it has a
        'contract_id'. If so, dispatch to the corresponding on‐chain logic:
          - "update_resource_allocation"
        """
        for tx in block['transactions']:
            cid = tx.get('contract_id', "")
            payload = tx.get('contract_payload', {})

            if cid == "update_resource_allocation":
                # Only provider nodes should update the DB
                if self.peers_roles.get(self.local_node, None) == payload.get("authority"):
                    self.dataReceivedAtProviderTime.append(time())
                    city_id = payload.get("city_id")
                    risk_level = payload.get("risk_level")
                    # Map risk levels to resource amounts
                    resource_map = {
                        "low": 100,
                        "medium": 200,
                        "high": 300,
                        "veryHigh": 400,
                        "Very High": 400
                    }
                    if not city_id or not risk_level:
                        print(f"[update_resource] Missing city_id or risk_level in payload: {payload}")
                        continue
                    try:
                        import sqlite3, os
                        db_path = "/data/disaster_resources.db"
                        if not os.path.exists(db_path):
                            print(f"[update_resource] DB not found at {db_path}")
                            continue
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        # Update only the risk level and resources_allocated
                        rl_key = risk_level.lower() if risk_level.lower() in resource_map else risk_level
                        resources_allocated = resource_map.get(rl_key, None)
                        if resources_allocated is None:
                            print(f"[update_resource] Invalid risk_level: {risk_level}")
                            conn.close()
                            continue
                        cursor.execute('''
                            UPDATE disaster_resources 
                            SET resources_allocated = ?, disaster_risk_level = ?
                            WHERE city_id = ?
                        ''', (resources_allocated, risk_level, city_id))
                        if cursor.rowcount == 0:
                            print(f"[update_resource] City not found: {city_id}")
                        else:
                            print(f"[update_resource] Updated city_id {city_id} to risk_level {risk_level}")
                        conn.commit()
                        conn.close()
                        self.endTime.append(time())
                    except Exception as e:
                        print(f"[update_resource] DB error: {e}")
                else:
                    print(f"[update_resource] Not a provider node, skipping DB update.")
            # else: unrecognized or no contract_id → do nothing


# ─── Blueprint for Core Blockchain Endpoints ─────────────────────────────────────
blockchain_bp = Blueprint('blockchain_bp', __name__)
bc = None  # Will be set once we instantiate Blockchain() in BlockchainNode

@blockchain_bp.route('/nodes', methods=['GET'])
def list_nodes():
    """
    Return a list of peers this node currently knows about,
    each entry: { "address": "<host:port>", "role": "<role>" }.
    """
    peers_info = []
    for addr in bc.get_node_addresses():
        role = bc.peers_roles.get(addr, "unknown")
        peers_info.append({"address": addr, "role": role})
    return jsonify({'peers': peers_info}), 200


@blockchain_bp.route('/nodes/register', methods=['POST'])
@blockchain_bp.route('/nodes/register', methods=['POST'])
def register_nodes():
    """
    Expect JSON: { "nodes": ["http://host:port", ...], "role": "<string>", "is_local": <bool> }.
    Add each node to bc.nodes, record its role if provided, then return ALL known peers
    (including ourselves) as { "address": "<host:port>", "role": "<role>" }.
    """
    values = request.get_json()
    if not values or 'nodes' not in values:
        return "Error: supply a JSON with 'nodes'", 400

    role = values.get('role', None)
    is_local = values.get('is_local', False)
    nodes = values.get('nodes')

    # 1) Register each incoming node and record its role
    for node_url in nodes:
        parsed = urlparse(node_url)
        node_addr = parsed.netloc
        if is_local or node_addr != bc.local_node:
            bc.register_node(node_addr, is_local=is_local)
            if role:
                bc.set_peer_role(node_addr, role)
                
    # 2) Build response list of ALL known peers (ourselves + others)
    peer_list = []
    if bc.local_node:
        peer_list.append({
            "address": bc.local_node,
            "role": bc.peers_roles.get(bc.local_node, "unknown")
        })
    for addr in bc.get_node_addresses():
        peer_list.append({
            "address": addr,
            "role": bc.peers_roles.get(addr, "unknown")
        })

    return jsonify({"message": "Nodes registered", "peers": peer_list}), 201


@blockchain_bp.route('/receive_block', methods=['POST'])
def receive_block():
    import time
    """
    Accepts a block with 'timestamp' and 'transactions' fields (plus others).
    Validates and appends if valid.
    """
    data = request.get_json()
    block = data.get('block')
    if not block:
        return "Invalid data", 400

    required_fields = ['index','timestamp','transactions','proof','previous_hash','mined_by']
    if not all(k in block for k in required_fields):
        return "Missing block fields", 400

    last = bc.last_block
    if block['index'] == last['index'] + 1:
        # Validate previous_hash and proof
        if block['previous_hash'] == bc.hash(last) and bc.valid_proof(last['proof'], block['proof']):
            bc.chain.append(block)
            bc.apply_contracts(block)
            # If the current node is provider role, then add endTime logic
            if bc.peers_roles.get(bc.local_node) == "provider":
                bc.endTime.append(time.time())

            # --- Master node: gossip only to other master nodes ---
            if bc.peers_roles.get(bc.local_node) == "master":
                for peer in bc.master_peers:
                    try:
                        requests.post(f"http://{peer}/receive_block", json={'block': block}, timeout=2)
                    except:
                        pass
            else:
                # Non-master: propagate to all peers as before
                for peer in bc.get_node_addresses():
                    try:
                        requests.post(f"http://{peer}/receive_block", json={'block': block}, timeout=2)
                    except:
                        pass
            return jsonify({"message": "Block accepted"}), 201
        else:
            return jsonify({"error": "Invalid block"}), 400
    elif block['index'] > last['index'] + 1:
        return jsonify({"error": "Block index too high, please sync"}), 409
    else:
        return jsonify({"message": "Block already exists or is old"}), 200


@blockchain_bp.route('/chain', methods=['GET'])
def full_chain():
    """
    Return our local chain as JSON:
    { "chain": [{"timestamp":..., "transactions": [...]}, ...], "length": <int> }
    """
    return jsonify(bc.to_dict()), 200

# --- New: Lightweight chain summary endpoint ---
@blockchain_bp.route('/chain/summary', methods=['GET'])
def chain_summary():
    """
    Return only the last block hash and chain length for efficient sync.
    { "last_hash": <str>, "length": <int> }
    """
    if not bc.chain:
        return jsonify({"last_hash": None, "length": 0}), 200
    last_block = bc.chain[-1]
    last_hash = bc.hash(last_block)
    return jsonify({"last_hash": last_hash, "length": len(bc.chain)}), 200
    # chain_summary = [{
    #     "timestamp": block["timestamp"],
    #     "transactions": block["transactions"]
    # } for block in bc.chain]
    # return jsonify({"chain": chain_summary, "length": len(bc.chain)}), 200


@blockchain_bp.route('/sync', methods=['GET'])
def sync_chain():
    """
    Query all peers'/chain endpoints.
    If any peer has a longer valid chain, adopt it and return 200.
    Otherwise return 200 saying "up to date."
    """
    replaced = False
    longest_chain = bc.chain

    for peer in bc.get_node_addresses():
        try:
            host_port = get_host_port(peer)
            r = requests.get(f"http://{host_port}/chain", timeout=3)
            if r.status_code == 200:
                data = r.json()
                length = data.get('length')
                chain = data.get('chain')
                if length and chain and length > len(longest_chain) and bc.valid_chain(chain):
                    longest_chain = chain
                    replaced = True
        except requests.exceptions.RequestException:
            continue

    if replaced:
        bc.chain = longest_chain.copy()
        return jsonify({"message": "Chain replaced", "new_length": len(longest_chain)}), 200

    return jsonify({"message": "Our chain is up to date", "length": len(longest_chain)}), 200


@blockchain_bp.route('/mine', methods=['GET'])
def mine():
    """
    1) Sync with all peers (pull their /chain).  
    2) Proof-of-Work on our tip.  
    3) new_block(proof) → apply_contracts(block) → broadcast.  
    4) Return the newly mined block.
    """
    # Step 1: Sync with master peers first, then regular peers if needed
    longest_chain = bc.chain
    sync_sources = list(bc.master_peers) if bc.master_peers else bc.get_node_addresses()
    for peer in sync_sources:
        try:
            host_port = get_host_port(peer)
            r = requests.get(f"http://{host_port}/chain", timeout=3)
            if r.status_code == 200:
                data = r.json()
                length = data.get('length')
                chain  = data.get('chain')
                if length and chain and length > len(longest_chain) and bc.valid_chain(chain):
                    longest_chain = chain
        except:
            continue
    bc.chain = longest_chain.copy()

    # Step 2: Proof-of-Work
    last_proof = bc.last_block['proof']
    proof = bc.proof_of_work(last_proof)

    # Step 3: Forge new block
    # Use the local node address for mined_by (PORT may not be defined here)
    mined_by = f"node_{bc.local_node}" if bc.local_node else "node_unknown"
    new_block = bc.new_block(proof, mined_by=mined_by)

    # Step 4: Broadcast: first to master peers, then to other peers
    master_peers = list(bc.master_peers)
    other_peers = [p for p in bc.get_node_addresses() if p not in master_peers]
    for peer in master_peers:
        try:
            host_port = get_host_port(peer)
            requests.post(f"http://{host_port}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass
    for peer in other_peers:
        try:
            host_port = get_host_port(peer)
            requests.post(f"http://{host_port}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass

    return jsonify({
        "message": "New block forged",
        "block": new_block,
        "chain_length": len(bc.chain)
    }), 200


@blockchain_bp.route('/block_propagation_metrics', methods=['GET'])
def block_propagation_metrics_endpoint():
    def avg(arr):
        return sum(arr) / len(arr) if arr else 0

    metrics = {
        "startTime_avg": avg(bc.startTime),
        "chainSyncedTime_avg": avg(bc.chainSyncedTime),
        "blockMinedTime_avg": avg(bc.blockMinedTime),
        "blockPropagationTime_avg": avg(bc.blockPropagationTime),
        "dataReceivedAtProviderTime_avg": (avg(bc.dataReceivedAtProviderTime)) * 1000,
        "endTime_avg": (avg(bc.endTime)) * 1000
    }

    # Reset the arrays after retrieving the values
    bc.startTime.clear()
    bc.chainSyncedTime.clear()
    bc.blockMinedTime.clear()
    bc.blockPropagationTime.clear()
    bc.dataReceivedAtProviderTime.clear()
    bc.endTime.clear()

    return jsonify(metrics), 200

# ─── BlockchainNode Wrapper ─────────────────────────────────────────────────────
class BlockchainNode:
    """
    Wraps a Flask app into a P2P/Blockchain node.
    Decides if we're bootstrap (first on 5002) or a normal node.
    Registers with bootstrap if needed. Registers core P2P endpoints.
    """

    def __init__(self, app: Flask, desired_port: int, role: str):
        global bc

        # Step 1: Check if someone is listening on port 5002
        requested_port = desired_port
        # Use MY_SERVICE_NAME env var if set, else fallback to BOOTSTRAP_HOST, else default
        local_hostname = os.environ.get("MY_SERVICE_NAME")
        if not local_hostname:
            local_hostname = os.environ.get("BOOTSTRAP_HOST", "localhost")
            # Fallback for legacy envs
            if "ROLE" in os.environ:
                role = os.environ["ROLE"].lower()
                if role == "master":
                    local_hostname = "master_service"
                elif role == "requester":
                    local_hostname = "requester_service"
                elif role == "provider":
                    local_hostname = "provider_service"
        # Add container hostname/ID for uniqueness
        container_id = socket.gethostname()
        requested_address = f"{local_hostname}:{requested_port}:{container_id}"

        import time
        max_retries = 30
        node_exists_at_5002 = False
        # Only wait for master if our role is NOT master
        if role != "master":
            for attempt in range(max_retries):
                try:
                    r = requests.get(f"http://{BOOTSTRAP_ADDRESS}/chain", timeout=2)
                    if r.status_code == 200:
                        node_exists_at_5002 = True
                        break
                except requests.exceptions.RequestException:
                    pass
                print(f"[BOOTSTRAP WAIT] Waiting for master at {BOOTSTRAP_ADDRESS}... ({attempt+1}/{max_retries})", flush=True)
                time.sleep(2)

        PORT = requested_port
        MY_ADDRESS = requested_address
        IS_BOOTSTRAP = False
        longest_chain = None
        # New logic: If this is a master node, try to find any existing master chains
        if role == "master":
            # Try to discover all master nodes via DNS (service discovery)
            # socket and os are already imported at the top
            # Try to resolve all A records for the master service name
            master_service_name = os.environ.get("MY_SERVICE_NAME", "master_service")
            try:
                # This will return all IPs for the service (all replicas)
                master_ips = socket.gethostbyname_ex(master_service_name)[2]
            except Exception:
                master_ips = []
            found_chain = False
            max_length = 0
            for ip in master_ips:
                if ip == socket.gethostbyname(socket.gethostname()):
                    continue  # skip self
                try:
                    url = f"http://{ip}:{requested_port}/chain"
                    r = requests.get(url, timeout=2)
                    if r.status_code == 200:
                        data = r.json()
                        chain = data.get('chain')
                        if chain and len(chain) > max_length:
                            longest_chain = chain
                            max_length = len(chain)
                            found_chain = True
                except Exception:
                    continue
            if found_chain:
                print(f"[MASTER BOOTSTRAP] Found existing master chain of length {max_length}. Joining it.")
            else:
                print(f"[MASTER BOOTSTRAP] No existing master chain found. Bootstrapping new chain.")
                IS_BOOTSTRAP = True
        else:
            if node_exists_at_5002:
                print(f"Detected existing node on 5002. Binding to port {PORT} and registering.")
            else:
                IS_BOOTSTRAP = True
                print(f"No node on 5002. Becoming the first node on {MY_ADDRESS}")

        # Step 2: Instantiate our Blockchain, register ourselves, set role
        bc = Blockchain()
        bc.register_node(MY_ADDRESS, is_local=True)
        bc.set_peer_role(MY_ADDRESS, role)
        bc.bootstrap_node = BOOTSTRAP_HOST
        if longest_chain:
            bc.chain = longest_chain

        self.IS_BOOTSTRAP = IS_BOOTSTRAP
        self.MY_ADDRESS = MY_ADDRESS
        self.PORT = PORT
        self.role = role  # e.g. "provider", "requester", or "user_contract"

        # Step 3: If not bootstrap, register with bootstrap
        if not IS_BOOTSTRAP:
            self.register_with_peer(BOOTSTRAP_ADDRESS)
            try:
                r = requests.get(f"http://{BOOTSTRAP_ADDRESS}/chain", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    chain = data.get('chain')
                    bc.chain = chain
                    print(f"Synced chain from bootstrap node ({len(chain)} blocks)")
            except Exception as e:
                print(f"Could not sync chain from bootstrap: {e}")
        else:
            print("🛠️ This node IS acting as the bootstrap.")

        # Step 4: Register the core P2P endpoints and start peer gossip
        app.register_blueprint(blockchain_bp)
        print("Registered blockchain P2P endpoints on Flask app.")

        threading.Thread(target=self.peer_gossip_loop, daemon=True).start()

        # Expose app and port for others to read
        self.app = app

    def register_with_peer(self, peer_address: str):
        """
        Tell peer_address "I exist at MY_ADDRESS with role=self.role."
        Peer will add me and return its own peer list (with roles), which I merge.
        """
        try:
            payload = {
                "nodes": [f"http://{self.MY_ADDRESS}"],
                "role": self.role,
                "is_local": False
            }
            r = requests.post(f"http://{peer_address}/nodes/register", json=payload, timeout=3)
            if r.status_code == 201:
                returned_peers = r.json().get("peers", [])
                for pinfo in returned_peers:
                    addr = pinfo.get("address")
                    role = pinfo.get("role", "unknown")
                    bc.register_node(addr, is_local=False)
                    bc.set_peer_role(addr, role)
                print(f"Registered with peer at {peer_address}.  Peer returned {len(returned_peers)} peers.")
            else:
                print(f"Peer at {peer_address} responded {r.status_code} {r.text}")
        except requests.exceptions.RequestException:
            print(f"Could not register with peer at {peer_address} (timeout or connection error).")

    def peer_gossip_loop(self):
        """
        Every 30 seconds, fetch each known peer's /nodes list (which includes role info)
        and merge them into bc.nodes + bc.peers_roles. Remove unreachable peers from all sets.
        If no peers are present, attempt to re-register with the master (bootstrap) node.
        """
        self.peer_failures = getattr(self, 'peer_failures', {})
        while True:
            current_peers = bc.get_node_addresses().copy()
            # If we have no peers, try to re-register with the master/bootstrap node
            if not current_peers:
                print("[GOSSIP] No peers found, attempting to re-register with bootstrap/master node at", BOOTSTRAP_ADDRESS, flush=True)
                try:
                    self.register_with_peer(BOOTSTRAP_ADDRESS)
                    print("[GOSSIP] Re-registration attempt complete. Current peers:", bc.get_node_addresses(), flush=True)
                except Exception as e:
                    print(f"[GOSSIP] Failed to re-register with master: {e}", flush=True)
                current_peers = bc.get_node_addresses().copy()
            for peer in current_peers:
                try:
                    host_port = get_host_port(peer)
                    r = requests.get(f"http://{host_port}/nodes", timeout=3)
                    if r.status_code == 200:
                        # Reset failure count
                        self.peer_failures[peer] = 0
                        their_list = r.json().get("peers", [])
                        for pinfo in their_list:
                            addr = pinfo.get("address")
                            role = pinfo.get("role")
                            if addr and role:
                                bc.register_node(addr, is_local=False)
                                bc.set_peer_role(addr, role)
                    else:
                        self.peer_failures[peer] = self.peer_failures.get(peer, 0) + 1

                    if self.peer_failures[peer] >= 3:
                        bc.nodes.discard(peer)
                        bc.peers_roles.pop(peer, None)
                        bc.master_peers.discard(peer)
                        print(f"Removed unreachable peer after 3 failures: {peer}")
                except requests.exceptions.RequestException:
                    self.peer_failures[peer] = self.peer_failures.get(peer, 0) + 1

                    if self.peer_failures[peer] >= 3:
                        bc.nodes.discard(peer)
                        bc.peers_roles.pop(peer, None)
                        bc.master_peers.discard(peer)
                        print(f"Removed unreachable peer after 3 failures: {peer}")
                        # Enhanced: Immediately try to re-register with bootstrap/master node
                        try:
                            self.register_with_peer(BOOTSTRAP_ADDRESS)
                            print(f"[GOSSIP] Peer removal triggered re-registration with master at {BOOTSTRAP_ADDRESS}")
                        except Exception as e:
                            print(f"[GOSSIP] Re-registration with master failed: {e}")
            sleep(30)

def get_host_port(peer):
    # peer is like "provider_service:5004:0bd02b238772"
    return ':'.join(peer.split(':')[:2])  # "provider_service:5004"

# ─── If someone runs node.py directly, bail out ────────────────────────────────
if __name__ == '__main__':
    print("node.py is a library. Run your Flask microservices (user.py, provider.py, requester.py).")
    sys.exit(0)