import requests
from src.config import SLACK_WEBHOOK_URL
from src.logger import logger

def post_to_slack(company_name, cik_number, ticker_symbol, document_link, pubDate):
    # Add a Google search link for the ticker symbol if available
    ticker_part = (
        f" (Ticker: <https://www.google.com/search?q=%24{ticker_symbol}+ticker|${ticker_symbol}>)"
        if ticker_symbol else ""
    )
    
    message = (
        f"*Cybersecurity Incident Disclosure*\n"
        f"Published on: {pubDate}\n"
        f"Company: *{company_name}*\n"
        f"CIK: <https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={cik_number}|{cik_number}>{ticker_part}\n"
        f"<{document_link}|View SEC Filing>"
    )

    payload = {"text": message}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload, headers=headers)

    if response.status_code != 200:
        logger.error(f"Failed to post to Slack: {response.text}")
        return False
    else:
        logger.info(f"Slack posted successfully: {response}")
        return True

if __name__ == "__main__":
    # Example usage
    post_to_slack(
        "Example Company",
        "0000123456",
        "EXMP",
        "https://www.sec.gov/example",
        "2025-01-01"
    )
