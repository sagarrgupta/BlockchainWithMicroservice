# node.py
import sys, threading, requests, hashlib, json
from time   import time, sleep
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
        self.chain = []
        self.current_transactions = []
        self.nodes = set()             # peer addresses (host:port)
        self.peers_roles = {}          # peer_address → role string
        self.local_node = None         # this node's own address (host:port)
        self.bootstrap_node = None     # will store BOOTSTRAP_HOST
        self.mining_in_progress = False

        # ─── ON‐CHAIN USER STORAGE ───────────────────────────────────────────────
        # Each entry: user_id:int → {"name": str, "balance": float}
        self.users = {}

        # Creating the genesis block
        self.new_block(previous_hash='1', proof=100, mined_by="Genesis")

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
        """Record a peer's role (e.g. 'provider', 'requester', 'user_contract')."""
        self.peers_roles[address] = role

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
                r = requests.get(f"http://{node_addr}/chain", timeout=5)
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
    def new_block(self, proof, previous_hash=None, mined_by="Unknown"):
        """
        Create a new block in the blockchain:
        - proof: the proof-of-work found
        - previous_hash: hash of previous block (optional)
        - mined_by: identifier of miner
        Reset current_transactions and append block to chain.
        Then call apply_contracts(block) to update on-chain state.
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions.copy(),
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
            'mined_by': mined_by
        }
        # Clear the current list of transactions
        self.current_transactions = []
        # Append the new block
        self.chain.append(block)

        # Apply contract logic on any transactions in this block
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
        return 1 # this is temporary
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
        return guess_hash[:4] == "0000"

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
          - "add_user"
          - "transfer"
        """
        for tx in block['transactions']:
            cid = tx.get('contract_id', "")
            payload = tx.get('contract_payload', {})

            if cid == "add_user":
                # payload: {"id": <int>, "name": <str>, "initial_balance": <number>}
                user_id = payload.get("id")
                name    = payload.get("name")
                bal     = payload.get("initial_balance", 0)
                if isinstance(user_id, int) and name and user_id not in self.users:
                    self.users[user_id] = {
                        "name": name,
                        "balance": bal
                    }
                    print(f"  ▶️ Contract 'add_user' succeeded: id={user_id}, name={name}, bal={bal}")
                else:
                    print(f"  ⚠️ Contract 'add_user' skipped/invalid: {payload}")

            elif cid == "transfer":
                # payload: {"from_id": <int>, "to_id": <int>, "amount": <number>}
                src = payload.get("from_id")
                dst = payload.get("to_id")
                amt = payload.get("amount", 0)
                if (
                    isinstance(src, int)
                    and isinstance(dst, int)
                    and isinstance(amt, (int, float))
                    and src in self.users
                    and dst in self.users
                    and self.users[src]["balance"] >= amt
                ):
                    self.users[src]["balance"] -= amt
                    self.users[dst]["balance"] += amt
                    print(f"  ▶️ Contract 'transfer' succeeded: {amt} from id={src} → id={dst}")
                else:
                    print(f"  ⚠️ Contract 'transfer' failed or invalid: {payload}")

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
    """
    1) Validate incoming block's previous_hash and proof.  
    2) If valid and extends our chain, append → apply_contracts(block) → broadcast to peers.  
    3) If index > expected, return 409 ("please sync").  
    4) If duplicate/old, return 200.
    """
    data = request.get_json()
    block = data.get('block')
    if not block:
        return "Invalid data", 400

    required_fields = ['index','timestamp','transactions','proof','previous_hash','mined_by']
    if not all(k in block for k in required_fields):
        return "Missing block fields", 400

    last = bc.last_block
    # Case: new block extends our chain
    if block['index'] == last['index'] + 1:
        if block['previous_hash'] == bc.hash(last) and bc.valid_proof(last['proof'], block['proof']):
            bc.chain.append(block)
            bc.apply_contracts(block)  # update on-chain state
            # Broadcast this block onward
            for peer in bc.get_node_addresses():
                try:
                    requests.post(f"http://{peer}/receive_block", json={'block': block}, timeout=2)
                except requests.exceptions.RequestException:
                    pass
            return "Block added", 201
        else:
            return "Invalid proof or previous_hash", 400

    # Case: block is ahead of us → we need to sync instead
    elif block['index'] > last['index'] + 1:
        return "Chain out of sync, please sync", 409

    # Case: block.index <= last.index → we already have it or this is old
    else:
        return "Block already exists", 200


@blockchain_bp.route('/chain', methods=['GET'])
def full_chain():
    """
    Return our local chain as JSON:
    { "chain": [<block>, …], "length": <int> }
    """
    return jsonify(bc.to_dict()), 200


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
            r = requests.get(f"http://{peer}/chain", timeout=3)
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
    # Step 1: Sync with peers
    longest_chain = bc.chain
    for peer in bc.get_node_addresses():
        try:
            r = requests.get(f"http://{peer}/chain", timeout=3)
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
    new_block = bc.new_block(proof, mined_by=f"node_{PORT}")

    # Step 4: Broadcast to all peers
    for peer in bc.get_node_addresses():
        try:
            requests.post(f"http://{peer}/receive_block", json={'block': new_block}, timeout=2)
        except:
            pass

    return jsonify({
        "message": "New block forged",
        "block": new_block,
        "chain_length": len(bc.chain)
    }), 200


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
        local_hostname = os.environ.get("HOSTNAME", socket.gethostname())
        requested_address = f"{local_hostname}:{requested_port}"

        try:
            r = requests.get(f"http://{BOOTSTRAP_ADDRESS}/chain", timeout=2)
            node_exists_at_5002 = (r.status_code == 200)
        except requests.exceptions.RequestException:
            node_exists_at_5002 = False

        PORT = requested_port
        MY_ADDRESS = f"{local_hostname}:{PORT}"
        if node_exists_at_5002:
            IS_BOOTSTRAP = False
            print(f"Detected existing node on 5002. Binding to port {PORT} and registering.")
        else:
            IS_BOOTSTRAP = True
            print(f"No node on 5002. Becoming the first node on {MY_ADDRESS}")

        # Step 2: Instantiate our Blockchain, register ourselves, set role
        bc = Blockchain()
        bc.register_node(MY_ADDRESS, is_local=True)
        bc.set_peer_role(MY_ADDRESS, role)
        bc.bootstrap_node = BOOTSTRAP_HOST

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
        and merge them into bc.nodes + bc.peers_roles. Remove unreachable peers.
        """
        while True:
            current_peers = bc.get_node_addresses().copy()
            for peer in current_peers:
                try:
                    r = requests.get(f"http://{peer}/nodes", timeout=3)
                    if r.status_code == 200:
                        their_list = r.json().get("peers", [])
                        for pinfo in their_list:
                            addr = pinfo.get("address")
                            role = pinfo.get("role")
                            if addr and role:
                                bc.register_node(addr, is_local=False)
                                bc.set_peer_role(addr, role)
                    else:
                        # Non-200 → remove peer
                        bc.nodes.discard(peer)
                        bc.peers_roles.pop(peer, None)
                        print(f"Removed unreachable peer: {peer}")
                except requests.exceptions.RequestException:
                    bc.nodes.discard(peer)
                    bc.peers_roles.pop(peer, None)
                    print(f"Removed unreachable peer: {peer}")
            sleep(30)


# ─── If someone runs node.py directly, bail out ────────────────────────────────
if __name__ == '__main__':
    print("node.py is a library. Run your Flask microservices (user.py, provider.py, requester.py).")
    sys.exit(0)