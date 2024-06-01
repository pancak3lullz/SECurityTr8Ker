# SECurityTr8Ker: SEC RSS Feed Monitor

SECurityTr8Ker is a Python script designed to monitor the U.S. Securities and Exchange Commission's (SEC) RSS feed for new 8-K filings that contain material related to cybersecurity incidents. This script is tailored for cybersecurity analysts, financial professionals, and researchers interested in real-time alerts of potential cybersecurity incidents disclosed by publicly traded companies.

## Features

- **Real-time Monitoring**: Continuously monitors the SEC's RSS feed for 8-K filings, ensuring timely detection of new disclosures.
- **Cybersecurity Incident Detection**: Searches the content of each filing for mentions of terms which could be related to disclosures of cybersecurity incidents, flagging relevant documents for further review.
- **Logging**: Detailed logging of findings, including company name, CIK number, document link, and publication date, to a specified log file. Additional debug information is logged to facilitate troubleshooting and verification.

## How It Works

The script operates by performing the following steps in a continuous loop:

1. **Requesting the SEC RSS Feed**: Utilizes the `requests` library to fetch the latest RSS feed from the SEC's website, targeting filings that potentially include cybersecurity-related disclosures.
2. **Parsing RSS Feed**: Employs `xmltodict` to parse the XML format of the RSS feed, extracting relevant information about each filing.
3. **Inspecting Filings**: For each filing identified as an 8-K form, the script retrieves the document(s) linked within the filing and inspects the content for the string "Material Cybersecurity Incidents."
4. **Logging Findings**: When a filing containing the specified string is found, details such as the company name, CIK number, ticker symbol (if available), document link, and publication date are logged to the `debug.log` file. Informational messages are also printed to the terminal.
5. **Sleep Interval**: After each cycle of checking the feed, the script pauses for a specified interval (default: 10 minutes) before checking the feed again, minimizing unnecessary load on SEC servers and adhering to respectful usage practices.

## Installation and Usage

### Prerequisites

- Python 3.x
- Required Python packages: `requests`, `xmltodict`, `beautifulsoup4`, `colorlog`

You can install the necessary Python packages using `pip`:

```bash
pip install requests xmltodict beautifulsoup4 colorlog
```

### Running the Script

1. Clone the repository or download the script to your local machine.
2. Open a terminal and navigate to the directory containing the script.
3. Run the script using Python:

```bash
python SECurityTr8Ker.py
```

The script will begin monitoring the SEC RSS feed, logging any findings as described above.

### Configuration

You can adjust the request interval and logging settings by modifying the following variables in the script:

- `REQUEST_INTERVAL`: Time in seconds to wait between each check of the RSS feed.
- `logs_dir`: Directory where `debug.log` will be stored.

## Logging

The script generates two types of logs:

- **Debug Log (`debug.log`)**: Contains detailed debug information and findings. Stored in the specified `logs_dir` directory.
- **Terminal Output**: Displays informational messages about the script's operation, including findings and operational status updates.

## Acknowledgements

**Idea presented by Will Hawkins & Board-Cybersecurity.com**

- https://twitter.com/hawkinsw/status/1748508044802052540
- https://github.com/hawkinsw/Item105/tree/main
- https://www.board-cybersecurity.com/incidents/tracker/

**Resources**

- https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent
- https://www.sec.gov/Archives/edgar/usgaap.rss.xml
- https://data.sec.gov/submissions/CIK{cik_number}.json
