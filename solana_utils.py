import requests
from solana.rpc.api import Client
from solders.pubkey import Pubkey  # Use solders.pubkey for new versions
from solders.signature import Signature
import json
import time
from datetime import datetime

# Connect to Solana mainnet
solana_client = Client("https://api.mainnet-beta.solana.com")
RPC_URL = "https://api.mainnet-beta.solana.com"
TOKEN_MINT_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

GET_SIGNATURE_LIMIT = 1000 # Max limit is 1000
ONE_DAY_PERIOD = 1000 # One day is 86400

# Fetch token transaction signatures for a specific mint address
def get_token_transactions(mint_address: str, period):
    before = None
    transactions = []
    pubkey = Pubkey.from_string(mint_address)  # Convert mint address to Pubkey
    now_local = datetime.now()
    start_time = int(now_local.timestamp())
    end_time = start_time - period * ONE_DAY_PERIOD
    while True:
        result = solana_client.get_signatures_for_address(pubkey, before=before,limit=GET_SIGNATURE_LIMIT) 
        tx_list = result.value
        if tx_list[GET_SIGNATURE_LIMIT-1].block_time <= end_time: 
            break
        if not tx_list:
            break   
        transactions.extend([tx.signature for tx in tx_list])
        before = transactions[-1]
        time.sleep(10)
    return transactions

def extract_wallet_addresses(response):
    return [str(tx.wallet_address) for tx in response]  # response.value contains the list of transactions

def get_transaction_details(signature):
    data = solana_client.get_transaction(signature, max_supported_transaction_version=0)
    if not data.value: return ""
    elif data.value.transaction.meta.err: return ""
    else:
        return data
    
def parse_transaction_details(tx_details):
    try:
        # Convert GetTransactionResp object to dictionary
        tx_dict = tx_details.value  # Convert response object to dictionary
        # Extract transaction message
        transaction = tx_dict.transaction
        meta = transaction.meta
        message = transaction.transaction.message

        # Extract account keys (wallets involved)
        account_keys = message.account_keys  # List of all involved accounts

        pre_amount = meta.pre_balances[0]
        post_amount = meta.post_balances[0]

        transferred_amount = pre_amount - post_amount
        roi = round((transferred_amount / max(1, pre_amount)) * 100, 2)  # % ROI
        win_rate = round((transferred_amount / max(1, pre_amount)) * 100, 2)  # Win Rate

        trades = len(meta.log_messages)  # Count logs as trades
        avg_buy = round(pre_amount / max(1, trades), 4) if trades > 0 else 0.0
        
        # Randomized Rocket Trades
        rockets_2x = round(transferred_amount / 2) if transferred_amount >= 2 else 0
        rockets_5x = round(transferred_amount / 5) if transferred_amount >= 5 else 0
        rockets_10x = round(transferred_amount / 10) if transferred_amount >= 10 else 0
        
        sol_balance = post_amount / 1_000_000_000  # Convert lamports to SOL
        # sol_balance =1
        tx_fee = meta.fee / 1_000_000_000  # Convert fee to SOL

        token_transfer={
            "wallet_address": str(account_keys[0]),
            "amount": transferred_amount,
            "ROI": roi,
            "Win_Rate": win_rate,
            "Trades": trades,
            "Avg_Buy(SOL)": avg_buy,
            "SOL_Balance": sol_balance,
            "2x_Rockets": rockets_2x,
            "5x_Rockets": rockets_5x,
            "10x_Rockets": rockets_10x,
        }   
        return token_transfer
    except Exception as e:
        print("Error parsing transaction:", e)
        return None
