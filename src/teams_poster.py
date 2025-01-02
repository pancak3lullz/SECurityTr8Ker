import requests
from src.config import TEAMS_WEBHOOK_URL
from src.logger import logger

def post_to_teams(company_name, cik_number, ticker_symbol, document_link, pubDate):
    """Post a notification to Microsoft Teams.
    
    Args:
        company_name (str): Name of the company
        cik_number (str): CIK number of the company
        ticker_symbol (str): Stock ticker symbol, if available
        document_link (str): URL to the SEC filing
        pubDate (str): Publication date of the filing
    
    Returns:
        bool: True if successful, False otherwise
    """
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
                "text": f"{pubDate}\\n\\nA cybersecurity incident has been disclosed by **{company_name}** (CIK: [{cik_number}](https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={cik_number})) {ticker_part}.",
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

    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(TEAMS_WEBHOOK_URL, json=payload, headers=headers)
        
        if response.status_code in {200, 202}:  # Teams webhooks can return either 200 or 202
            return True
        else:
            error_text = response.text if response.text else f"Status code: {response.status_code}"
            logger.error(f"Failed to post to Teams: {error_text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to post to Teams: Network error - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Failed to post to Teams: Unexpected error - {str(e)}")
        return False

if __name__ == "__main__":
    # Example usage
    post_to_teams(
        "Example Company",
        "0000123456",
        "EXMP",
        "https://www.sec.gov/example",
        "2025-01-01"
    )
