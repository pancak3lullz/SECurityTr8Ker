import requests
from src.config import TEAMS_WEBHOOK_URL
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

    headers = {'Content-Type': 'application/json'}
    response = requests.post(TEAMS_WEBHOOK_URL, json=card_content, headers=headers)

    if response.status_code != 200:
        logger.error(f"Failed to post to Teams: {response.text}")
        return False
    else:
        logger.info(f"Teams posted successfully: {response}")
        return True

if __name__ == "__main__":
    # Example usage
    post_to_teams(
        "Example Company",
        "0000123456",
        "EXMP",
        "https://www.sec.gov/example",
        "2025-01-01"
    )
