# SECurityTr8Ker
This script is designed to monitor and report on cybersecurity disclosures in financial filings of companies. Here's a breakdown of its functionality:

1. **Monitoring an RSS Feed**: The script continuously monitors an RSS feed from the U.S. Securities and Exchange Commission (SEC). The specific feed it monitors is the "US Generally Accepted Accounting Principles (US GAAP)" feed, which contains various financial filings.

2. **Fetching Filings**: The `fetch_filings_from_rss` function retrieves the content of the RSS feed. It filters filings of type '8-K' and '6-K'. These are forms used by publicly traded companies in the United States to notify investors of significant events that may affect the company's share price.

   - **8-K Filings**: These are known as "Current Reports" and are used to report major events like bankruptcy, acquisition, resignation of directors, and other significant corporate changes.
   - **6-K Filings**: These are used by foreign private issuers to furnish information that, among other things, was made public in the country of their domicile, filed with and made public by a foreign stock exchange on which their securities are traded, or distributed to security holders.

3. **Checking for Cybersecurity Disclosures**: For each relevant filing, the script then checks for cybersecurity disclosures using the `check_cybersecurity_disclosure` function. It does this by accessing a JSON data file from the SEC's data repository using the company's CIK (Central Index Key) number.

   - The function searches for the indicator "1.05" within the 'items' field of the JSON data. This indicator signifies a cybersecurity incident disclosure.

4. **Displaying Cybersecurity Disclosures**: If a cybersecurity disclosure is found, the script prints a message to the terminal with a special red color formatting, making it stand out. This alert indicates the company name and its CIK number, notifying that a cybersecurity disclosure has been found in their filing.

5. **Timing and Repeats**: The script operates in a continuous loop, checking the RSS feed every 10 minutes. After each cycle of checks, it outputs a message indicating it is waiting for 10 minutes before the next check.

6. **Error Handling**: The script contains basic error handling which simply passes any exceptions that might occur during the fetching and parsing of data. This could be for handling HTTP errors, parsing errors, or connectivity issues.

In summary, the script serves as an automated tool to monitor and report on cybersecurity disclosures in company filings as reported to the SEC, focusing specifically on 8-K and 6-K filings.

### Idea presented by Will Hawkins & Board-Cybersecurity.com
- https://twitter.com/hawkinsw/status/1748508044802052540
- https://github.com/hawkinsw/Item105/tree/main
- https://www.board-cybersecurity.com/incidents/tracker/

### Resources
- https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent
- https://www.sec.gov/Archives/edgar/usgaap.rss.xml
- https://data.sec.gov/submissions/CIK{cik_number}.json
