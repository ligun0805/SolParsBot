import pandas as pd

def export_to_excel(wallets, filename="wallets.xlsx"):
    df = pd.DataFrame(wallets)
    df.to_excel(filename, index=False)
    print(f"Saved results to {filename}")

def filter_wallets(wallets_data, filter_data):
    print(wallets_data)
    # Apply filters   
    min_win_rate = int(filter_data["Min_WR"])
    max_win_rate = int(filter_data["Max_WR"])
    min_trades = int(filter_data["Min_Trades"]) 
    max_trades = int(filter_data["Max_Trades"]) 
    min_avg_buy = int(filter_data["AVG_Min_Buy"])
    max_avg_buy = int(filter_data["AVG_Max_Buy"])
    min_sol_balance = int(filter_data["Min_SOL_Balance"])
    max_sol_balance = int(filter_data["Max_SOL_Balance"])

    filtered_wallets = [item for item in wallets_data if 
                        (item["win_rate"] >= min_win_rate) & (item["win_rate"] <= max_win_rate) &
                        (item["trades"] >= min_trades) & (item["trades"] <= max_trades) &
                        (((item["buy"] / item["trades"]) * 100) >= min_avg_buy) & (((item["buy"] / item["trades"]) * 100) <= max_avg_buy) &
                        (item["sol_balance"] >= min_sol_balance) & (item["sol_balance"] <= max_sol_balance)]

    return filtered_wallets
    # return extract_wallet_addresses(filtered_wallets)


def extract_wallet_addresses(response):
    return [str(tx.wallet_address) for tx in response]  # response.value contains the list of transactions

