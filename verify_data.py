import json
import hashlib
from web3 import Web3

# 1. Connect to Sepolia (No private keys needed for reading!)
ALCHEMY_RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/ZcF-CSMYdZpcyfLbrHDr8"
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

# 2. Contract Details (Provide these to your team)
CONTRACT_ADDRESS = "0x93e45367685468620d9f91454D7Cb21D1BBf9D4f"

# Make sure to use the triple quotes ''' ''' around the ABI!
CONTRACT_ABI = '''[{
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

# Initialize the contract
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

def verify_commodity_data(date, market_data_dict):
    """
    Checks if the local AI data matches the immutable blockchain record.
    Returns True if authentic, False if tampered.
    """
    print(f"\n--- Verifying Market Data for {date} ---")
    
    # Step A: Hash the data the AI team is about to use
    # Sorting keys ensures the JSON string is built the exact same way every time
    data_string = json.dumps(market_data_dict, sort_keys=True)
    current_hash = hashlib.sha256(data_string.encode()).hexdigest()
    print(f"Computed Hash from local data: {current_hash}")

    # Step B: Fetch the trusted, immutable hash from the Smart Contract
    # Notice we use .call() instead of building a transaction. This makes it instant and free!
    try:
        blockchain_hash = contract.functions.getHash(date).call()
        print(f"Trusted Hash from Blockchain:  {blockchain_hash}")
    except Exception as e:
        print(f"❌ Error reading from blockchain: {e}")
        return False

    # Step C: The Cryptographic Verification
    if blockchain_hash == "":
        print("⚠️ WARNING: No data found on the blockchain for this date.")
        return False
    elif current_hash == blockchain_hash:
        print("✅ SUCCESS: Data is completely authentic. Safe for AI processing.")
        return True
    else:
        print("🚨 ALERT: TAMPERING DETECTED! Local data does not match the Web3 record.")
        return False

# --- Example of how the AI/Data Team will use this ---
if __name__ == '__main__':
    
    # Imagine this is the data the Data team just pulled from their database
    # to feed into the AI forecasting model.
    ai_dataset = {
        "commodity": "Onion",
        "predicted_price_in_7_days": 48.50,
        "location": "Lasalgaon Mandi",
        "weather_factor": "Heavy Rain Warning"
    }
    
    # They run the verifier right before feeding it to the AI
    is_valid = verify_commodity_data("2026-02-13", ai_dataset)
    
    if is_valid:
        print("\n>> Proceeding to run Machine Learning model...")
        # ai_model.predict(ai_dataset)
    else:
        print("\n>> System Halted: Refusing to process corrupted buffer stock data.")