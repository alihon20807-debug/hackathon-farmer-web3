import os
from dotenv import load_dotenv
from web3 import Web3
import json

# Load the hidden variables from the .env file
load_dotenv()

# 1. Connect to Sepolia 
ALCHEMY_RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/ZcF-CSMYdZpcyfLbrHDr8"
w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))

# 2. Setup your credentials securely
MY_ADDRESS = "0x225E2351311e147E814E5A0F175eaf0e7d4be2e9"
PRIVATE_KEY = os.getenv("PRIVATE_KEY") # This pulls the key safely from .env!

# 3. Setup the Farmer Payment Contract
# Get the new address from Remix under 'Deployed Contracts'
PAYMENT_CONTRACT_ADDRESS = "0x80F955f798Fc434B5550d88aBB8B4F05e5dB942f" 

# Get the ABI by clicking the copy button at the bottom of the Solidity Compiler tab in Remix
PAYMENT_CONTRACT_ABI = json.loads('''[
    
	{
		"inputs": [],
		"name": "depositFunds",
		"outputs": [],
		"stateMutability": "payable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address payable",
				"name": "_farmer",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "_amount",
				"type": "uint256"
			}
		],
		"name": "payFarmer",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"inputs": [],
		"name": "getBalance",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "owner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}

]''')

payment_contract = w3.eth.contract(address=PAYMENT_CONTRACT_ADDRESS, abi=PAYMENT_CONTRACT_ABI)

def trigger_farmer_payment(farmer_wallet, amount_in_wei):
    """
    Executes a transfer of funds to the specified farmer wallet.
    """
    print(f"\n--- Initiating Payment ---")
    print(f"Sending {amount_in_wei} wei to {farmer_wallet}...")
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(MY_ADDRESS)
    payment_txn = payment_contract.functions.payFarmer(
        Web3.to_checksum_address(farmer_wallet), 
        amount_in_wei
    ).build_transaction({
        'chainId': 11155111,
        'from': MY_ADDRESS,
        'nonce': nonce,
        'gas': 100000,
        'maxFeePerGas': w3.to_wei('50', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('2', 'gwei'),
    })

    # Sign and send
    signed_txn = w3.eth.account.sign_transaction(payment_txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    
    print(f"Transaction broadcasted! Hash: {tx_hash.hex()}")
    
    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Payment successfully confirmed in Block #{receipt.blockNumber}!")
    return True

# Quick test if you run this file directly
if __name__ == '__main__':
    # Test sending a tiny amount to a secondary wallet
    test_farmer_wallet = "0xa81E35D97D6148470788e3Ab14d57b6B84FC3515"  # 0xYourSecondaryWalletAddressHere
    trigger_farmer_payment(test_farmer_wallet, 5000000000000000)