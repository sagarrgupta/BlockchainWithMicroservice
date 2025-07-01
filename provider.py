# provider.py

import sys
import requests
import sqlite3
from flask import Flask, jsonify, abort
import node
from node import BlockchainNode
import os
import time

app = Flask(__name__)

if len(sys.argv) != 2:
    print("Usage: python provider.py <desired_port>")
    sys.exit(1)

desired_port = int(sys.argv[1])

# ─── 1) Launch the P2P/Blockchain "Provider" Node ─────────────────────────────
provider_node = BlockchainNode(app, desired_port=desired_port, role="provider")

# ─── 2) Database helper function ─────────────────────────────────────────────
def get_city_resources(city_id):
    """
    Fetch disaster management resource data from local SQLite database
    """
    try:
        conn = sqlite3.connect('/data/disaster_resources.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT city_id, city_name, resource_type, resources_allocated, 
                   allocation_date, disaster_risk_level
            FROM disaster_resources 
            WHERE city_id = ?
        ''', (city_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "city_id": row[0],
                "city_name": row[1],
                "resource_type": row[2],
                "resources_allocated": row[3],
                "allocation_date": row[4],
                "disaster_risk_level": row[5]
            }
        else:
            return None
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

@app.route('/city/<int:city_id>', methods=['GET'])
def get_city(city_id):
    """
    New flow:
    1) Look up disaster resource data from local database.
    2) Return JSON with city disaster management info and blockTransactionData.
    """
    print(f"[GET /city/{city_id}] Handled by container: {os.uname()[1]}")

    # ─── (1) Look up the city disaster resources from local database ───────────
    city_data = get_city_resources(city_id)
    if city_data is None:
        return jsonify({"error": f"City ID {city_id} not found in disaster management database"}), 404

    # ─── (2) Prepare blockTransactionData ─────────────────────────────────────
    blockTransactionData = {
        "sender": f"provider_{provider_node.MY_ADDRESS}",
        "recipient": "BackToSender",
        "requestInfo": f"/city/{city_id}"
    }

    return jsonify({
        "city_data": city_data,
        "blockTransactionData": blockTransactionData
    }), 200

@app.route('/update_resource/<int:city_id>/<string:risk_level>', methods=['POST'])
def update_resource(city_id, risk_level):

    # Log the container handling the request
    print(f"[GET /update_resource/{city_id, risk_level}] Handled by container: {os.uname()[1]}")

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

    # ─── (2) Mine a dummy "log request" block ───────────────────────────────────
    # We create a minimal transaction whose only purpose is to record that
    # this provider served a /city/<city_id> call. We do NOT include a contract_id,
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

    """
    Update resource allocation based on risk level:
    - Low: 100
    - Medium: 200
    - High: 300
    - Very High: 400
    """
    # Map risk levels to resource amounts
    resource_map = {
        "low": 100,
        "medium": 200,
        "high": 300,
        "veryHigh": 400
    }
    
    if risk_level not in resource_map:
        return jsonify({"error": "Invalid risk level"}), 400
        
    try:
        conn = sqlite3.connect('/data/disaster_resources.db')
        cursor = conn.cursor()
        
        # Update the resources_allocated and disaster_risk_level
        cursor.execute('''
            UPDATE disaster_resources 
            SET resources_allocated = ?, disaster_risk_level = ?
            WHERE city_id = ?
        ''', (resource_map[risk_level], risk_level, city_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "City not found"}), 404
            
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Resource allocation updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/direct_update_resource/<int:city_id>/<string:risk_level>', methods=['POST'])
def direct_update_resource(city_id, risk_level):

    # Log the container handling the request
    print(f"[GET /update_resource/{city_id, risk_level}] Handled by container: {os.uname()[1]}")

    """
    Update resource allocation based on risk level:
    - Low: 100
    - Medium: 200
    - High: 300
    - Very High: 400
    """
    # Map risk levels to resource amounts
    resource_map = {
        "low": 100,
        "medium": 200,
        "high": 300,
        "veryHigh": 400
    }
    
    if risk_level not in resource_map:
        return jsonify({"error": "Invalid risk level"}), 400
        
    try:
        conn = sqlite3.connect('/data/disaster_resources.db')
        cursor = conn.cursor()
        
        # Update the resources_allocated and disaster_risk_level
        cursor.execute('''
            UPDATE disaster_resources 
            SET resources_allocated = ?, disaster_risk_level = ?
            WHERE city_id = ?
        ''', (resource_map[risk_level], risk_level, city_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "City not found"}), 404
            
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Resource allocation updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=provider_node.PORT, threaded=True)