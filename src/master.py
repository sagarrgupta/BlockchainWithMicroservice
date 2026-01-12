# master.py
import sys
from flask import Flask
import node as node
from node import BlockchainNode

app = Flask(__name__)

if len(sys.argv) != 2:
    print("Usage: python master.py <desired_port>")
    sys.exit(1)

requested_port = int(sys.argv[1])

# Launch the P2P/Blockchain "Node" as a master
my_node = BlockchainNode(app, desired_port=requested_port, role="master")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=my_node.PORT, threaded=True)
