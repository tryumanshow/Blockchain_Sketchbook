# Pull request from https://github.com/dvf/blockchain

import hashlib  # a module to encode the blocks (hashlib.sha256)
import json # json : a kind of data format
from time import time
from urllib.parse import urlparse # urlparse('url') => returns 6-elements named-tuple (scheme, netloc, path, params, query, fragment)
from uuid import uuid4 # uuid: 128-bit number that identifies unique Internet objects or data

import requests # Need requests module to connect web URL with the local cpu
from flask import Flask, jsonify, request # flask: one of the web framework in python

# A huge class 'Blockchain'
class Blockchain:
    def __init__(self):
        # All three objects below would be used later to specify blockchain elements
        self.current_transactions = [] # A list to save transactions
        self.chain = [] # A list to save chain
        self.nodes = set() # A set to save unique nodes
        # Create the genesis block (The first block of a blockchain)
        self.new_block(previous_hash='1', proof=100)

    # Get address(location) of node as input, and add some information about that node address to 'nodes' set
    def register_node(self, address):
        """
        Add a new node to the list of nodes

        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        # In case parsed netloc exists, add netloc information to nodes, otherwise, add path info.
        # In case any of url netloc or path does not exist, show the error message 'Invalid URL'.
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accepts an URL without scheme like '192.168.0.5:5000'.
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    # Inspect whether this blockchain is valid or not
    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid

        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        # Inspect all the series of blocks in a blockchain
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct

            # Reminding the structure of the blockchain, the 'Previous hash' of the block should correspond to hash of the previous block.
            # If two values are different, invalid.
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that the Proof of Work is correct
            # If PoW is incorrect, also invalid.
            # To return True, hashed value should satisfy the level of threshold made in advance. (In this case, the first 4 digits '0000')
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            # Intention to search all the blocks in a blockchain
            last_block = block
            current_index += 1

        return True

    # In case of generating the same decoded hash at the same time, will choose the chain which is longer cuz its more believable.
    # Solution to 'Fork' problem in blockchain
    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.

        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200: # server response success
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        # If there's no conflict or the longer one is not found, no need to update the chain.
        return False

    # Make a new block and append this block to the chain list
    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain

        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    # When the transaction happens, save the new transaction to current_transactions and increase block index.
    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block

        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    # Get the last_block out of the chain
    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    # Hash the block using Sha-256 method
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    # Find the nonce which can make first 4 digits of hashed value as '0000'
    def proof_of_work(self, last_block):
        """
        Simple Proof of Work Algorithm:

         - Find a number p' such that hash(pp') contains leading 4 zeroes
         - Where p is the previous proof, and p' is the new proof
         
        :param last_block: <dict> last Block
        :return: <int>
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof

    # Would return True only if the first 4 digits of hashed value are '0000'
    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validates the Proof

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :param last_hash: <str> The hash of the Previous Block
        :return: <bool> True if correct, False if not.

        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate the Node
# Making Flask module available in Python under the variable name 'app'
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain()

# app.route: If the URL satisfying the pre-specified principle comes, implement registered function.
@app.route('/mine', methods=['GET'])

def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block # Indicates the last block in the blockchain
    proof = blockchain.proof_of_work(last_block)  # Get the nonce of last block which makes the first 4 digits of hashed value '0000'

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block) # Hashing the last block's block header to use this value as next new block's 'previous hash'.
    block = blockchain.new_block(proof, previous_hash) # Block is a new object, so total length of chain increase one unit.

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200 # Encode the response as json representation and uses 200 to show transformation succeeded


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json() # get json data in Flask

    # Check that the required fields are in the POST'ed data
    # To be recognized as valid transaction, the transaction should specify three elements: sender, recipient, amount.
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    # If a transaction is valid, that transaction is appended to 'current_transactions' and index increases by one unit.
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201 # Request completed

# View the overall structure of blockchain made till present
@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

# Get whole nodes list in set 'nodes' which are related to forming the blockchain
# The results which were in the set would be transformed to list data type under the name of 'total_nodes'
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

# If 'Fork' problem happens, replace shorter chain with the longer chain, if not stay as it is.
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

# In case of codes being implemented only in the python interpreter.
if __name__ == '__main__':
    from argparse import ArgumentParser # argparse is the parser for commandline option or element-affliated command

    parser = ArgumentParser() # ArgumentParser contains all the information which is needed to parse command line to pythonic data type
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
