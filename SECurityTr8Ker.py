import requests
import time
import xmltodict

def fetch_filings_from_rss(url):
    filings = []
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            feed = xmltodict.parse(response.content)
            for item in feed['rss']['channel']['item']:
                form_type = item.get('edgar:xbrlFiling', {}).get('edgar:formType')
                cik_number = item.get('edgar:xbrlFiling', {}).get('edgar:cikNumber')
                if form_type and cik_number and form_type == '8-K':
                    filings.append((cik_number, item.get('title', '').split(' (')[0]))
    except Exception as e:
        pass  # Optionally log the error
    return filings

def check_cybersecurity_disclosure(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "filings" in data and "recent" in data["filings"] and "items" in data["filings"]["recent"]:
                for item in data["filings"]["recent"]["items"]:
                    if "1.05" in item.split(','):
                        print(f"\033[91mCybersecurity disclosure (1.05) found for {company_name} (CIK: {cik_number})\033[0m")
                        return
    except Exception as e:
        pass  # Optionally log the error

def main():
    print("Script started. Monitoring SEC RSS feed for cybersecurity disclosures...")
    rss_url = "https://www.sec.gov/Archives/edgar/usgaap.rss.xml"
    while True:
        filings = fetch_filings_from_rss(rss_url)
        for cik_number, company_name in filings:
            check_cybersecurity_disclosure(cik_number, company_name)
        print("Waiting for 10 minutes before the next check...")
        time.sleep(600)

if __name__ == "__main__":
    main()
