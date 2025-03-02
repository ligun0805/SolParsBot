from solana.rpc.api import Client
from solders.pubkey import Pubkey  # Use solders.pubkey for new versions
from solders.signature import Signature
import time
from datetime import datetime

# Connect to Solana mainnet
solana_client = Client("https://api.mainnet-beta.solana.com")
RPC_URL = "https://api.mainnet-beta.solana.com"
TOKEN_MINT_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

GET_SIGNATURE_LIMIT = 1000 # Max limit is 1000
ONE_DAY_PERIOD = 86000 # One day is 86400

tx_source_paydium = [
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C", 
    "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",
    "5quBtoiQqxF9Jv6KYKctB59NT3gtJD2Y65kdnB1Uev3h",
    "routeUGWgWzqBWFcrCfv8tritsqukccJPu3q5GPP3xS",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
]
tx_source_pumpfun = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

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
        transactions.extend([tx.signature for tx in tx_list])
        block_time = tx_list[GET_SIGNATURE_LIMIT-1].block_time
        if block_time <= end_time: 
            break
        if not tx_list:
            break   
        dt = datetime.fromtimestamp(block_time)
        print(f"_____Fetching transactions for {start_time-block_time} seconds ago. Last block time: {block_time}: {dt}_____")
        before = transactions[-1]
        time.sleep(10)
    return transactions

def get_transaction_details(signature, tx_source):  
    data = solana_client.get_transaction(signature, max_supported_transaction_version=0)    
    return parse_transaction_details(data, tx_source)
    
def parse_transaction_details(tx_details, tx_source):
    try:
        # Convert GetTransactionResp object to dictionary
        info = tx_details.value  # Convert response object to dictionary        
        
        tx_dict = info.transaction
        transaction = tx_dict.transaction
        meta = tx_dict.meta
        message = transaction.message

        # Extract account keys (wallets involved)
        account_keys = message.account_keys  
        
        pre_token_balances = meta.pre_token_balances[0]
        post_token_balances = meta.post_token_balances[0]

        transferred_amount = int(post_token_balances.ui_token_amount.amount) - int(pre_token_balances.ui_token_amount.amount)
        if transferred_amount>0: buy=1
        else: buy=0
        if meta.err: wr=0
        else: wr=1
        token_transfer={
            "win_rate":  wr,
            "wallet_address": str(account_keys[0]),
            "buy": buy,            
            "sol_balance": meta.post_balances[0],
        }
        return token_transfer
    except Exception as e:
        print("Error parsing transaction:", e)
        return None
