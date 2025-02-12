import os
import logging
import sys
import asyncio
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

from solana_utils import extract_wallet_addresses, get_token_transactions, get_transaction_details, parse_transaction_details
from filters import filter_wallets, export_to_excel

TOKEN_INPUT, FILTER_INPUT, PROCESSING = range(3)
# Dictionary to store user data
user_data = {
}
filter_data = [
    "Raydium/PumpFum",
    "Min_WR",
    "Max_WR",
    "Min_ROI",
    "Max_ROI",
    "Min_Trades",
    "Max_Trades",
    "AVG_Min_Buy",
    "AVG_Max_Buy",
    "Rocket_Min_2x",
    "Rocket_Min_5x",
    "Rocket_Min_10x",
    "Rocket_Min_50x",
    "Rocket_Min_100x",
    "Min_SOL_Balance",
    "Max_SOL_Balance",
    "Max_Trades_1min",
    "Min_Rockets",
    "Date_Period",
    # "EDN"
]
# Token list to analyze
IS_ANALYSIS = False
IS_FILTER = False
FILENAME = ""

MAX_TRADE = 0
MIN_TRADE = 0
# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> int:
    """Handles the /start command and presents the menu."""
    reply_keyboard = [["Enter Addresses", "Upload .txt"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

    await update.message.reply_text("Welcome! Please choose how to provide token addresses:", reply_markup=markup)
    return TOKEN_INPUT

async def receive_tokens(update: Update, context: CallbackContext) -> int:
    """Handles manual token address input, ensuring it's valid."""
    user_id = update.message.chat_id
    text = update.message.text.strip()

    # Check if the user mistakenly sent the menu button text
    if text.lower() in ["enter addresses", "upload .txt"]:
        await update.message.reply_text("Please enter a valid list of token addresses, one per line.")
        return TOKEN_INPUT  # Stay in the same state

    tokens = text.split("\n")  # Split tokens by new lines
    tokens = [t.strip() for t in tokens if t.strip()]  # Remove empty lines

    if not tokens:  # If no valid tokens found
        await update.message.reply_text("Invalid input. Please enter token addresses.")
        return TOKEN_INPUT

    user_data[user_id] = {"tokens": tokens, "filters": {}}

    await update.message.reply_text(f"Now, please specify the filters.\n{filter_data[0]}:")
    return FILTER_INPUT

async def receive_txt_file(update: Update, context: CallbackContext) -> int:
    """Handles .txt file upload containing token addresses."""
    user_id = update.message.chat_id
    file = await update.message.document.get_file()
    file_path = f"{user_id}_tokens.txt"
    await file.download_to_drive(file_path)

    with open(file_path, "r") as f:
        tokens = [line.strip() for line in f.readlines() if line.strip()]

    user_data[user_id] = {"tokens": tokens, "filters": {}}
    os.remove(file_path)  # Clean up

    await update.message.reply_text(f"Now, please specify the filters.\n{filter_data[0]}:")
    print(user_data)

    return FILTER_INPUT

async def receive_filters(update: Update, context: CallbackContext) -> int:
    """Handles filter input from the user."""
    user_id = update.message.chat_id
    text = update.message.text
    filter_key = filter_data[len(user_data[user_id]['filters'])]
    user_data[user_id]["filters"][filter_key] = text
    if len(user_data[user_id]["filters"]) < 19 : 
        await update.message.reply_text(f"{filter_data[len(user_data[user_id]['filters'])]}:") 
        return FILTER_INPUT
    else:  
        print(user_data[user_id]['filters'])
        return PROCESSING    

async def process_data(update: Update, context: CallbackContext) -> int:
    """Simulates processing token data and exports results as Excel files."""
    await update.message.reply_text("Start Analysis ... ")
    user_id = update.message.chat_id
    tokens = user_data[user_id]["tokens"]
    if not user_data[user_id]["filters"]["Date_Period"]: user_data[user_id]["filters"]["Date_Period"] = 1
    for token in tokens:  
        filename = f"{token}.xlsx"
        transactions = await token_analysis(token, user_data[user_id]["filters"]["Date_Period"])
        print("=============================")
        print(transactions)
        if transactions:
            filtered_transactions = filter_wallets(transactions, user_data[user_id]["filters"])
            export_to_excel(filtered_transactions, filename)
            print("----------------------------------------")
            print(filtered_transactions)
            # Send file to user
            with open(filename, "rb") as f:
                await context.bot.send_document(chat_id=user_id, document=f, filename=filename)

            os.remove(filename)  # Clean up after sending

    await update.message.reply_text("Processing complete! All Excel files have been sent.")
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels the conversation."""
    await update.message.reply_text("Analysis Finalized!")
    return ConversationHandler.END

# Analyze the tokens
async def token_analysis(mint_address, filter_period):      
    global MAX_TRADE
    global MIN_TRADE
    global FILENAME
   
    transactions = []
    batch_size = 1 # Number of transactions to fetch in each batch 
    now_local = datetime.now()
    FILENAME = int(now_local.timestamp())
    
    # Token Mint Address List
    signatures = get_token_transactions(mint_address, int(filter_period))
    
    for i in tqdm(range(0, len(signatures), batch_size), desc="Fetching Transactions"):
        batch = signatures[i:i + batch_size]
        tasks = [get_transaction_details(sig) for sig in batch]
        if tasks[0]:     
            new_transaction = parse_transaction_details(tasks[0])  
            for transaction in transactions:
                if transaction["wallet_address"] == new_transaction["wallet_address"]:
                    transaction["amount"] += new_transaction["amount"]
                    transaction["ROI"] += new_transaction["ROI"]
                    transaction["Win_Rate"] += new_transaction["Win_Rate"]
                    transaction["Trades"] += new_transaction["Trades"]
                    transaction["Avg_Buy(SOL)"] += new_transaction["Avg_Buy(SOL)"]
                    if not transaction["SOL_Balance"]: transaction["SOL_Balance"] = new_transaction["SOL_Balance"]
                    transaction["2x_Rockets"] += new_transaction["2x_Rockets"]
                    transaction["5x_Rockets"] += new_transaction["5x_Rockets"]
                    transaction["10x_Rockets"] += new_transaction["10x_Rockets"]
                    break
            else:
                transactions.append(new_transaction)
        await asyncio.sleep(20) # Sleep for 0.5 seconds to avoid rate limiting        
    if transactions:
        return transactions
    return None
   
# Main function to run the bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TOKEN_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tokens),
                MessageHandler(filters.Document.MimeType("text/plain"), receive_txt_file)  # FIXED LINE
            ],
            FILTER_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filters)],
            PROCESSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_data)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv_handler)
    
    application.run_polling()

if __name__ == "__main__":
    main()
