import os
from dotenv import load_dotenv
import json
import hashlib
from web3 import Web3

load_dotenv()

# 1. Connect to Sepolia via Alchemy
ALCHEMY_RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/ZcF-CSMYdZpcyfLbrHDr8"
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

print(f"Connected to Sepolia: {w3.is_connected()}")

# 2. Your Wallet & Contract Setup
# WARNING: NEVER commit your private key to GitHub!
MY_ADDRESS = "0x225E2351311e147E814E5A0F175eaf0e7d4be2e9"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

CONTRACT_ADDRESS = "0x93e45367685468620d9f91454D7Cb21D1BBf9D4f"
# Paste the ABI you copied from Remix inside the single quotes below
CONTRACT_ABI = '''[
    {
        "anonymous": false,
        "inputs": [
            {
                "indexed": false,
                "internalType": "string",
                "name": "date",
                "type": "string"
            },
            {
                "indexed": false,
                "internalType": "string",
                "name": "dataHash",
                "type": "string"
            }
        ],
        "name": "HashStored",
        "type": "event"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "date",
                "type": "string"
            },
            {
                "internalType": "string",
                "name": "dataHash",
                "type": "string"
            }
        ],
        "name": "storeHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "name": "dataHashes",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "string",
                "name": "date",
                "type": "string"
            }
        ],
        "name": "getHash",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]'''

# 3. Initialize the Contract
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

def secure_ai_forecast(date, market_data_dict):
    print(f"\n--- Securing {date} Forecast to Web3 ---")
    
    # Step A: Hash the AI/Data team's output
    # Sorting keys ensures the JSON string is identical every time
    data_string = json.dumps(market_data_dict, sort_keys=True)
    data_hash = hashlib.sha256(data_string.encode()).hexdigest()
    print(f"Generated Hash: {data_hash}")
    
    # Step B: Build the transaction to call the storeHash function
    nonce = w3.eth.get_transaction_count(MY_ADDRESS)
    
    transaction = contract.functions.storeHash(date, data_hash).build_transaction({
        'chainId': 11155111, # Sepolia Chain ID
        'gas': 2000000,
        'maxFeePerGas': w3.to_wei('50', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('2', 'gwei'),
        'nonce': nonce,
    })
    
    # Step C: Sign the transaction with your private key
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
    
    # Step D: Send it to the blockchain!
    print("Sending transaction to Sepolia...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    
    # Wait for the block to be mined
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Success! Data hash permanently secured in Block #{receipt.blockNumber}")
    print(f"View on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")

# --- Example of How the AI/Data Team Will Use This ---
if __name__ == '__main__':
    ai_prediction_output = {
        "commodity": "Onion",
        "predicted_price_in_7_days": 48.50,
        "location": "Lasalgaon Mandi",
        "weather_factor": "Heavy Rain Warning"
    }
    
    secure_ai_forecast("2026-02-13", ai_prediction_output)