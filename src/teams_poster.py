import requests
from src.config import TEAMS_WEBHOOK_URL
from src.utils import fetch_filings_from_rss, process_disclosures
from src.logger import logger

def post_to_teams(company_name, cik_number, ticker_symbol, document_link, pubDate):
    ticker_part = f"(Ticker: [${ticker_symbol}](https://www.google.com/search?q=%24{ticker_symbol}+ticker))" if ticker_symbol else ""
    
    card_content = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
            {
                "type": "TextBlock",
                "text": "Cybersecurity Incident Disclosure",
                "weight": "Bolder",
                "size": "Medium"
            },
            {
                "type": "TextBlock",
                "text": f"{pubDate}\n\nA cybersecurity incident has been disclosed by **{company_name}** (CIK: [{cik_number}](https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={cik_number})) {ticker_part}.",
                "wrap": True
            },
            {
                "type": "ActionSet",
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "View SEC Filing",
                        "url": document_link
                    }
                ]
            }
        ]
    }

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": card_content
            }
        ]
    }

    headers = {'Content-Type': 'application/json'}
    response = requests.post(TEAMS_WEBHOOK_URL, json=payload, headers=headers)
    if response.status_code not in {200, 202}:
        logger.error(f"Failed to post to Teams: {response.text}")
        return False
    else:
        logger.info(f"Teams posted successfully: {response}")
        return True

def process_teams_disclosures(filings):
    process_disclosures(filings, post_to_teams)

if __name__ == "__main__":
    filings = fetch_filings_from_rss()
    process_teams_disclosures(filings)
