import os
import requests
import logging
import asyncio
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

from solana_utils import get_token_transactions, get_transaction_details
from filters import filter_wallets, export_to_excel

TOKEN_INPUT, FILTER_INPUT, PROCESSING = range(3)
# Dictionary to store user data
user_data = {
}
filter_data = [
    "Raydium/PumpFum_input_0_or_1",
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
]

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Telegram API URL
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

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

    return FILTER_INPUT

async def receive_filters(update: Update, context: CallbackContext) -> int:
    """Handles filter input from the user."""
    user_id = update.message.chat_id
    text = update.message.text        
    filter_key = filter_data[len(user_data[user_id]['filters'])]
    user_data[user_id]["filters"][filter_key] = text    
    
    if filter_key == "Min_Rockets" :      
        await update.message.reply_text(f"{filter_data[len(user_data[user_id]['filters'])]}:")      
        return PROCESSING
    
    else:
        await update.message.reply_text(f"{filter_data[len(user_data[user_id]['filters'])]}:")
        return FILTER_INPUT

async def process_data(update: Update, context: CallbackContext) -> int:    
    """Simulates processing token data and exports results as Excel files.""" 
    user_id = update.message.chat_id   
    text = update.message.text 
    user_data[user_id]["filters"]["Date_Period"] = text
    print(text)
    await update.message.reply_text("Start Analysis ... ")   
    user_id = update.message.chat_id
    tokens = user_data[user_id]["tokens"]
    transaction_source = user_data[user_id]["filters"]["Raydium/PumpFum_input_0_or_1"]
    if not user_data[user_id]["filters"]["Date_Period"]: user_data[user_id]["filters"]["Date_Period"] = 1
    for token in tokens:  
        filename = f"{user_id}.xlsx"
        transactions = await token_analysis(token, user_data[user_id]["filters"]["Date_Period"], transaction_source, user_id)
        if transactions:
            filtered_transactions = filter_wallets(transactions, user_data[user_id]["filters"])
            # export_to_excel(transactions, filename)
            export_to_excel(filtered_transactions, filename)

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
async def token_analysis(mint_address, filter_period, transaction_source, user_id):
    global FILENAME
    
    transactions = []
    batch_size = 1 # Number of transactions to fetch in each batch
    now_local = datetime.now()
    FILENAME = int(now_local.timestamp())
    # Token Mint Address List
    signatures = get_token_transactions(mint_address, int(filter_period), user_id)
    transaction_len = len(signatures)
    for i in tqdm(range(0, transaction_len), desc="Fetching Transactions"):
        batch = signatures[i:i + batch_size]
        MESSAGE=f"Fetching transaction for __{i+1}/{transaction_len}__"
        requests.post(url, data={"chat_id": user_id, "text": MESSAGE})
        transaction = [get_transaction_details(sig, transaction_source) for sig in batch][0]

        if transaction: 
            # transactions.append(transaction[0])
            position = next((index for index, item in enumerate(transactions) if item.get("wallet_address") == transaction["wallet_address"]), None)

            if position!=None:                
                transactions[position]["win_rate"] = transactions[position]["win_rate"] + transaction["win_rate"]
                transactions[position]["buy"] = transactions[position]["buy"] + transaction["buy"]
                transactions[position]["trades"] = transactions[position]["trades"] + 1
            else: 
                transaction["trades"] = 1
                transactions.append(transaction)

        await asyncio.sleep(6) # Sleep for 0.5 seconds to avoid rate limiting        
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
