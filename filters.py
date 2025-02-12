import pandas as pd

# Example filter conditions
filter_data = [
    "Min_WR" ,
    "Max_WR" ,
    "Min_ROI" ,
    "Max_ROI" ,
    "Min_Trades" ,
    "Max_Trades" ,
    "AVG_Min_Buy" ,
    "AVG_Max_Buy" ,
    "Rocket_Min_2x" ,
    "Rocket_Min_5x" ,
    "Rocket_Min_10x" ,
    "Rocket_Min_50x" ,
    "Rocket_Min_100x" ,
    "Min_SOL_Balance" ,
    "Max_SOL_Balance" ,
    "Max_Trades" ,
    "Min_Rockets" ,
]

def export_to_excel(wallets, filename="wallets.xlsx"):
    df = pd.DataFrame(wallets)
    df.to_excel(filename, index=False)
    print(f"Saved results to {filename}")

def filter_wallets(wallets_data, filter_data):
    # Apply filters    
    filtered_wallets = wallets_data[
        # (int(wallets_data["Win_Rate"]) >= filter_data["Min_WR"]) & (int(wallets_data["Win_Rate"]) <= filter_data["Max_WR"]) &
        # (wallets_data["ROI"] >= filter_data["Min_ROI"]) & (wallets_data["ROI"] <= filter_data["Max_ROI"]) &
        (wallets_data["Trades"] >= filter_data["Min_Trades"]) & (wallets_data["Trades"] <= filter_data["Max_Trades"]) &
        (wallets_data["AVG_Buy(SOL)"] >= filter_data["AVG_Min_Buy"]) & (wallets_data["AVG_Buy(SOL)"] <= filter_data["AVG_Max_Buy"]) &
        (wallets_data["SOL_Balance"] >= filter_data["Min_SOL_Balance"]) & (wallets_data["SOL_Balance"] <= filter_data["Max_SOL_Balance"]) 
    ]
    return filtered_wallets
