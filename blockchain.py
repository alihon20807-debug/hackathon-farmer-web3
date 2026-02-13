import sys
sys.path.append('C:/Users/aashr/OneDrive/Desktop/Year One portions/Hackathons/Yantra_2026') # (Path setup for imports)

from Blockchain.Backend.core.block import Block
from Blockchain.Backend.core.blockheader import BlockHeader
from Blockchain.Backend.util.util import hash256
from Blockchain.Backend.core.database.database import BlockchainDB
import time
import json

class Blockchain:
    def __init__(self):
        self.chain = []
        self.GenesisBlock()

    def GenesisBlock(self):
        BlockHeight = 0
        prevBlockHash = '0' * 64 # 64 zeros because there is no previous block
        self.addBlock(BlockHeight, prevBlockHash)

    def addBlock(self, BlockHeight, prevBlockHash):
        timestamp = int(time.time())
        transaction = f"Codies Alert sent {BlockHeight} Bitcoins to Joe"
        merkleRoot = hash256(transaction.encode()).hex()
        bits = 'ffff001f' # Hardcoded difficulty target
        
        blockheader = BlockHeader(1, prevBlockHash, merkleRoot, timestamp, bits)
        blockheader.mine()
        
        self.chain.append(Block(BlockHeight, 1, blockheader.__dict__, 1, transaction).__dict__)
        print(json.dumps(self.chain, indent=4))

    def main(self):
        while True:
            lastBlock = self.chain[-1]
            BlockHeight = lastBlock['BlockHeight'] + 1
            prevBlockHash = lastBlock['BlockHeader']['blockHash']
            self.addBlock(BlockHeight, prevBlockHash)

if __name__ == '__main__':
    blockchain = Blockchain()
    blockchain.main()