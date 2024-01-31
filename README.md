# SECurityTr8Ker
This script is designed to monitor and report on cybersecurity disclosures in financial filings of companies.

#### Overview
This Python script is designed to continuously monitor and analyze filings from the U.S. Securities and Exchange Commission (SEC) for cybersecurity disclosures. Its primary function is to fetch and parse data from the SEC's RSS feed, identify specific filings related to cybersecurity, and log relevant information for further analysis.

#### Key Features
1. **Colored Logging:** Implements colored logging for easier differentiation of log levels in the terminal. Custom color schemes are set for various log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).

2. **File Logging:** In addition to terminal logging, the script also logs to a file, ensuring that a persistent record of events is maintained.

3. **RSS Feed Parsing:** Fetches and parses the SEC RSS feed to identify filings of specific types (8-K, 6-K) and logs successful parsing or critical errors.

4. **SEC Filings Analysis:** Analyzes SEC filings for mentions of "Material Cybersecurity Incidents" within a specified recent time frame.

5. **Ticker Symbol Extraction:** Retrieves and logs the ticker symbol for companies from the SEC's JSON data.

6. **Cybersecurity Disclosure Check:** Specifically checks for Item 1.05 (Cybersecurity Disclosure) in recent filings.

7. **Continuous Monitoring:** The script runs in a loop, periodically checking the RSS feed every 10 minutes.

#### Implementation Details
- **Logging Setup:** Uses `colorlog` and Python's `logging` module for terminal and file logging. Logs are stored in a local directory (`logs`), which is created if it doesn't exist.
- **External Libraries:** Utilizes `requests` for HTTP requests, `xmltodict` for parsing XML, `BeautifulSoup` from `bs4` for HTML parsing, and `re` and `datetime` for handling regular expressions and date/time operations.
- **Error Handling:** Includes try-except blocks for robust error handling during HTTP requests and data parsing.
- **Functionality Breakdown:**
  - `fetch_filings_from_rss`: Retrieves and parses the RSS feed for specific form types.
  - `fetch_directories`: Fetches directories from the SEC archive for a given CIK number.
  - `find_cybersecurity_htm_link`: Searches for a .htm link containing the phrase "Material Cybersecurity Incidents".
  - `check_cybersecurity_disclosure`: Checks for cybersecurity disclosures in a company's filings.
  - `main`: Orchestrates the script's workflow, continuously monitoring the SEC RSS feed and performing checks.

#### Usage
Designed for stakeholders in financial or cybersecurity domains, this script assists in real-time monitoring of public company disclosures related to cybersecurity, aiding in compliance, research, or investment analysis.

#### Dependencies
- Python 3.x
- Libraries: `os`, `requests`, `time`, `xmltodict`, `logging`, `colorlog`, `json`, `datetime`, `re`, `bs4`

#### Setup and Execution
1. Ensure Python 3.x is installed.
2. Install required libraries (e.g., via `pip install requests xmltodict colorlog bs4`).
3. Run the script using Python.

#### Note
This script makes real-time queries to the SEC website and is dependent on the structure of the SEC's RSS feed and website, which may change over time. Regular updates and maintenance might be required to keep the script functional.

### Idea presented by Will Hawkins & Board-Cybersecurity.com
- https://twitter.com/hawkinsw/status/1748508044802052540
- https://github.com/hawkinsw/Item105/tree/main
- https://www.board-cybersecurity.com/incidents/tracker/

### Resources
- https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent
- https://www.sec.gov/Archives/edgar/usgaap.rss.xml
- https://data.sec.gov/submissions/CIK{cik_number}.json
