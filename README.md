<div align='center'>
  <img src="https://github.com/pancak3lullz/SECurityTr8Ker/blob/main/traclabs.png" style="width: 400px; height: 150px">
  <img src="https://github.com/pancak3lullz/SECurityTr8Ker/blob/main/SECurityTr8Ker.png" style="width: 175px; height: 150px">
</div>

# SECurityTr8Ker: SEC Cybersecurity Disclosure Monitor

SECurityTr8Ker is a Python application designed to monitor the U.S. Securities and Exchange Commission's (SEC) RSS feed for new 8-K filings that contain material cybersecurity incident disclosures. This tool is particularly useful for cybersecurity analysts, financial professionals, and researchers interested in real-time alerts of cybersecurity incidents disclosed by publicly traded companies.

## Features

- **Real-time Monitoring**: Continuously monitors the SEC's RSS feed for new 8-K filings
- **Intelligent Detection**: 
  - Searches for Item 1.05 (Material Cybersecurity Incidents) disclosures
  - Identifies cybersecurity-related keywords and context
  - Prevents duplicate notifications
- **Multi-channel Notifications**: 
  - Slack
  - Microsoft Teams
  - Telegram
  - Twitter
  - Console logging (always enabled)
- **Rich Information**: 
  - Company name and CIK number
  - Stock ticker symbol (with Google Finance link)
  - Direct link to SEC filing
  - Filing date and context
  - Matching keywords found
- **Persistent Storage**: Maintains a record of all processed disclosures in JSON format

## How It Works

1. **RSS Feed Monitoring**:
   - Fetches the SEC's RSS feed for 8-K filings
   - Processes each filing to extract relevant information
   - Respects SEC's rate limiting guidelines

2. **Disclosure Detection**:
   - Checks for "Item 1.05" material cybersecurity incident disclosures
   - Searches for cybersecurity-related keywords (e.g., "unauthorized access", "cyber-attack")
   - Extracts relevant context around matches

3. **Notification Distribution**:
   - Sends alerts through configured notification channels
   - Includes direct links to SEC filings and company information
   - Prevents duplicate notifications

4. **Data Management**:
   - Stores processed disclosures in `disclosures.json`
   - Maintains detailed logs for troubleshooting
   - Prevents duplicate processing of filings

## Setup and Configuration

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/pancak3lullz/SECurityTr8Ker.git
   cd SECurityTr8Ker
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```

4. **Required Configuration**:
   Edit `.env` and set your email address for the SEC API:
   ```
   # REQUIRED: Set your email address for SEC API access
   USER_AGENT=SECurityTr8Ker/1.0 (your-email@example.com)
   ```

5. **Optional Notification Channels**:
   Configure any of the following in `.env`:

   **Slack**:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
   ```

   **Microsoft Teams**:
   ```
   TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
   ```

   **Telegram**:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

   **Twitter**:
   ```
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
   ```

6. **Run the Program**:
   ```bash
   python main.py
   ```

## Output Examples

### Console Output
```
2025-01-01 19:27:36,581 - INFO - SECurityTr8Ker starting up...
2025-01-01 19:27:36,581 - INFO - Starting new check cycle...
2025-01-01 19:27:36,581 - INFO - Fetching SEC RSS feed for 8-K filings...
2025-01-01 19:27:36,809 - INFO - Found 200 filings to inspect
2025-01-01 19:27:36,809 - INFO - Inspecting documents for cybersecurity disclosures...
```

### Notification Format
All notification channels receive alerts in this format:
```
Cybersecurity Incident Disclosure
Published on: Tue, 31 Dec 2024 17:30:28 EST
Company: Example Corp (Ticker: $EXMP)
CIK: 0000123456
View SEC Filing: https://www.sec.gov/...
```

## File Structure

- `main.py`: Main program entry point
- `src/`
  - `config.py`: Configuration and environment variables
  - `utils.py`: Core functionality for processing filings
  - `logger.py`: Logging configuration
  - `slack_poster.py`: Slack notification module
  - `teams_poster.py`: Microsoft Teams notification module
  - `telegram_poster.py`: Telegram notification module
  - `twitter_poster.py`: Twitter notification module
- `.env`: Configuration file (create from .env.example)
- `disclosures.json`: Record of processed disclosures
- `logs/`: Directory containing log files

## Acknowledgments

- SEC EDGAR system for providing public access to filings
- Inspired by the need for real-time cybersecurity incident monitoring
- Idea presented by Will Hawkins & Board-Cybersecurity.com

## Resources

- [SEC EDGAR RSS Feed](https://www.sec.gov/Archives/edgar/usgaap.rss.xml)
- [Form 8-K Information](https://www.sec.gov/fast-answers/answersform8khtm.html)
- [Item 1.05 Material Cybersecurity Incidents](https://www.sec.gov/rules/final/2023/33-11216.pdf)
