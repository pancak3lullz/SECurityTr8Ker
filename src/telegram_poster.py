import requests
from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from src.logger import logger

def send_telegram_message(company_name, cik_number, ticker_symbol, document_link, pubDate):
    ticker_part = f", Ticker: [${ticker_symbol}](https://www.google.com/search?q=%24{ticker_symbol}+ticker)" if ticker_symbol else ""
    message = f"{pubDate}\nA cybersecurity incident has been disclosed by `{company_name}` CIK: [{cik_number}](https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={cik_number}){ticker_part}.\n\n[View SEC Filing]({document_link})"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        logger.error(f"Failed to post to Telegram: {response.text}")
        return False
    else:
        logger.info(f"Telegram posted successfully: {response}")
        return True

if __name__ == "__main__":
    # Example usage
    send_telegram_message(
        "Example Company",
        "0000123456",
        "EXMP",
        "https://www.sec.gov/example",
        "2025-01-01"
    )
