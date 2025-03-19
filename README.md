<div align='center'>
  <img src="https://github.com/pancak3lullz/SECurityTr8Ker/blob/main/traclabs.png" style="width: 400px; height: 150px">
  <img src="https://github.com/pancak3lullz/SECurityTr8Ker/blob/main/SECurityTr8Ker.png" style="width: 175px; height: 150px">
</div>

# SECurityTr8Ker: SEC RSS Feed Monitor

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
- **Twitter Profile Status**: 
  - Automatically updates Twitter profile bio after each batch
  - Shows SEC OPEN/CLOSED status
  - Displays number of filings in last batch
  - Includes timestamp of last check
- **Rich Information**: 
  - Company name and CIK number
  - Stock ticker symbol (with Google Finance link)
  - Direct link to SEC filing
  - Filing date and context
  - Matching keywords found
- **Persistent Storage**: Maintains a record of all processed disclosures in JSON format
- **Flexible Operation Modes**:
  - Business Hours Mode (default): Only runs during SEC business hours (M-F, 9:00 AM - 5:30 PM ET)
  - 24/7 Mode: Runs continuously regardless of business hours
- **Configurable Check Intervals**: Adjustable time between SEC feed checks
- **Caching System**: Efficient caching of API responses to respect rate limits
- **Debug Logging**: Optional detailed logging for troubleshooting
- **Out-of-Band Messaging**: Send custom messages through notification channels without disrupting main operation

## System Requirements

- Python 3.9 or higher (required for asyncio.to_thread)
- Docker (for containerized deployment)
- Internet access to SEC.gov and notification services
- Valid API credentials for notification services

## How It Works

1. **RSS Feed Monitoring**:
   - Fetches the SEC's RSS feed for 8-K filings
   - Processes each filing to extract relevant information
   - Respects SEC's rate limiting guidelines
   - Caches responses for efficiency

2. **Disclosure Detection**:
   - Checks for "Item 1.05" material cybersecurity incident disclosures
   - Searches for cybersecurity-related keywords (e.g., "unauthorized access", "cyber-attack")
   - Extracts relevant context around matches
   - Prevents duplicate processing

3. **Notification Distribution**:
   - Sends alerts through configured notification channels
   - Includes direct links to SEC filings and company information
   - Prevents duplicate notifications
   - Supports multiple notification channels simultaneously

4. **Data Management**:
   - Stores processed disclosures in `disclosures.json`
   - Maintains detailed logs for troubleshooting
   - Prevents duplicate processing of filings
   - Caches API responses for efficiency

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
   Create a `.env` file in the project root with the following configuration:

   **Required Configuration**:
   ```
   # REQUIRED: Set your email address for SEC API access
   USER_AGENT=SECurityTr8Ker/1.0 (your-email@example.com)
   ```

   **SEC Rate Limiting Configuration** (optional):
   ```
   # SEC Rate Limiting Configuration (defaults shown)
   SEC_REQUEST_INTERVAL=1.0      # Time in seconds between requests (higher = fewer requests per second)
   SEC_MAX_CONCURRENT_REQUESTS=5 # Maximum number of concurrent requests
   SEC_MAX_RETRIES=3             # Maximum retries for failed requests (with exponential backoff)
   ```

   **Optional Notification Channels**:
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
   TWITTER_BEARER_TOKEN=your_bearer_token
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
   ```

4. **Run the Program**:
   ```bash
   python main.py [options]
   ```

   **Command Line Options**:
   - `--interval SECONDS`: Set check interval (default: 600 seconds)
   - `--storage-file PATH`: Specify storage file path (default: disclosures.json)
   - `--cache-dir PATH`: Set cache directory (default: ./cache)
   - `--24-7`: Run continuously 24/7 (disables business hours mode)
   - `--business-hours`: Run only during SEC business hours (default)
   - `--debug`: Enable debug logging

   **Examples**:
   ```bash
   # Run with default settings (business hours mode)
   python main.py

   # Run 24/7 with 5-minute check interval
   python main.py --24-7 --interval 300

   # Run with debug logging
   python main.py --debug
   ```

## SEC Rate Limiting Troubleshooting

If you experience HTTP 429 (Too Many Requests) errors from the SEC API, try adjusting the rate limiting parameters in your `.env` file:

- Increase `SEC_REQUEST_INTERVAL` to increase the time between requests
- Decrease `SEC_MAX_CONCURRENT_REQUESTS` to reduce the number of parallel requests
- Increase `SEC_MAX_RETRIES` if you want more automatic retry attempts

These settings help comply with the SEC's fair access policies while ensuring the application can still function effectively.

## Sending Out-of-Band Messages

You can send custom messages through the configured notification channels without disrupting the main application:

### Using the Host Shell Script

The easiest way to send messages from the host machine to the container:

```bash
# Make the script executable
chmod +x sectracker-send.sh

# Send a message to all configured channels
./sectracker-send.sh "Your message here"

# Send to specific channels
./sectracker-send.sh --channels=slack,teams "Your message here"

# Customize message prefix
./sectracker-send.sh --prefix="[URGENT]" "Your message here"

# Specify a different container name
./sectracker-send.sh --container=my-sectracker-container "Your message here"

# Show help
./sectracker-send.sh --help
```

### With Docker Directly

```bash
# Send a message to all configured channels
docker exec -it securitytracker sectracker-message "Your message here"

# Send to specific channels (comma-separated list)
docker exec -it securitytracker sectracker-message --channels "slack,teams" "Your message here"

# Customize message prefix (default is [SECurityTr8Ker])
docker exec -it securitytracker sectracker-message --prefix "[ALERT]" "Your message here"
```

### Direct Script Usage

```bash
# Send a message to all configured channels
python send_message.py "Your message here"

# Send to specific channels (comma-separated list)
python send_message.py --channels "slack,teams" "Your message here"

# Customize message prefix 
python send_message.py --prefix "[ALERT]" "Your message here"

# Enable debug logging
python send_message.py --debug "Your message here"
```

## Project Structure

```
SECurityTr8Ker/
├── main.py                 # Main program entry point
├── send_message.py         # Out-of-band messaging tool
├── sectracker-send.sh      # Host shell script wrapper for messaging
├── requirements.txt        # Python dependencies
├── .env                   # Configuration file
├── disclosures.json       # Record of processed disclosures
├── cache/                 # API response cache
├── logs/                  # Log files
└── src/
    ├── api/              # SEC API client
    ├── analyzers/        # Disclosure analysis logic
    ├── core/             # Core application components
    ├── models/           # Data models
    ├── notifiers/        # Notification channels
    ├── parsers/          # Filing parsers
    ├── utils/            # Utility functions
    └── tests/            # Test suite
```

## Output Examples

### Console Output
```
2024-03-18 15:27:36,581 - INFO - SECurityTr8Ker starting up...
2024-03-18 15:27:36,581 - INFO - Active notification channels: slack, teams, telegram, twitter
2024-03-18 15:27:36,581 - INFO - Operating in business hours mode (M-F, 9:00 AM - 5:30 PM ET)
2024-03-18 15:27:36,581 - INFO - Starting new check cycle...
2024-03-18 15:27:36,809 - INFO - Found 200 filings to inspect
2024-03-18 15:27:36,809 - INFO - Inspecting documents for cybersecurity disclosures...
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

## Acknowledgments

- SEC EDGAR system for providing public access to filings
- Inspired by the need for real-time cybersecurity incident monitoring
- Idea presented by Will Hawkins & Board-Cybersecurity.com

## Resources

- [SEC EDGAR RSS Feed](https://www.sec.gov/Archives/edgar/usgaap.rss.xml)
- [Form 8-K Information](https://www.sec.gov/fast-answers/answersform8khtm.html)
- [Item 1.05 Material Cybersecurity Incidents](https://www.sec.gov/rules/final/2023/33-11216.pdf)
