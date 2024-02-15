import os
import requests
import xmltodict
import logging
import colorlog
from bs4 import BeautifulSoup
import time
from datetime import datetime
import re

# Define request interval, log file path, and logs directory
REQUEST_INTERVAL = 0.3
logs_dir = 'logs'
log_file_path = os.path.join(logs_dir, 'debug.log')

# Ensure the logs directory exists
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Initialize the root logger to capture DEBUG level logs
logger = colorlog.getLogger()
logger.setLevel(logging.DEBUG)  # Capture everything at DEBUG level and above

# Setting up colored logging for terminal
terminal_handler = colorlog.StreamHandler()
terminal_handler.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }))
terminal_handler.setLevel(logging.INFO)  # Terminal to show INFO and above
logger.addHandler(terminal_handler)

# Setting up logging to file to capture DEBUG and above
file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.DEBUG)  # File to capture everything at DEBUG level
logger.addHandler(file_handler)

def get_ticker_symbol(cik_number, company_name):
    url = f"https://data.sec.gov/submissions/CIK{cik_number}.json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            data = response.json()
            ticker_symbol = data.get('tickers', [])[0] if data.get('tickers') else None
            return ticker_symbol
        else:
            logger.error(f"Error fetching ticker symbol for CIK: {cik_number}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving ticker symbol: {e}")
        return None

def inspect_document_for_cybersecurity(link):
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Define a list of search terms you're interested in
    search_terms = ["Material Cybersecurity Incidents"]
    try:
        response = requests.get(link, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            document_text = soup.get_text()  # Keep the document text as is, respecting case
            # Check if any of the search terms is in the document_text using regex for exact match
            for term in search_terms:
                # Create a regex pattern with word boundaries for the exact term
                pattern = r'\b' + re.escape(term) + r'\b'
                if re.search(pattern, document_text):
                    return True
    except Exception as e:
        logger.error(f"Failed to inspect document at {link}: {e}")
    return False

def fetch_filings_from_rss(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        time.sleep(REQUEST_INTERVAL)
        if response.status_code == 200:
            feed = xmltodict.parse(response.content)
            for item in feed['rss']['channel']['item']:
                xbrlFiling = item['edgar:xbrlFiling']
                form_type = xbrlFiling['edgar:formType']
                pubDate = item['pubDate']
                if form_type in ['8-K', '8-K/A', '6-K']:
                    company_name = xbrlFiling['edgar:companyName']
                    cik_number = xbrlFiling['edgar:cikNumber']
                    document_links = [xbrlFile['@edgar:url'] for xbrlFile in xbrlFiling['edgar:xbrlFiles']['edgar:xbrlFile'] if xbrlFile['@edgar:url'].endswith(('.htm', '.html'))]
                    
                    for document_link in document_links:
                        if inspect_document_for_cybersecurity(document_link):
                            ticker_symbol = get_ticker_symbol(cik_number, company_name)
                            logger.info(f"Cybersecurity Incident Disclosure found: {company_name} (Ticker:${ticker_symbol}) (CIK:{cik_number}) - {document_link} - Published on {pubDate}")
                            break  # Assuming we only need to log once per filing
            logger.info("Fetched and parsed RSS feed successfully.", extra={"log_color": "green"})
    except Exception as e:
        logger.critical("Error fetching filings: {}".format(e), extra={"log_color": "red"})

def print_ascii_art():
    ascii_art = r"""
MMMMMMMMMMMMMNd;,''.................................................................................................................:KMMMMMMMMMMMMMMMM
MMMMMMMMWXKKK0kl'...................................................................................................................cXMMMMMMMMMMMMMMMM
MMMMMMM0lcc:;,,....................................................................................................................;OXKOKXXNWW0kKWMMMM
MMMMMMWO;.,:::;,'..................................................................................................................'cc::cl;cko,.,kNMMM
MMMMMMMMO,.',::::;,'..............................................................................................................',::::;........'oXMM
MMMMMMMMNo,,''';::;;;,'.  ....................................................................................................',;;::::;'. .........oXM
MMMMMMMMWd..,;,'',;:;,'..'.. ............................................................................................ .',;;;::::,'... ......',:dXM
MMMMMMMMM0;  .,;,'.'',..;c:;'.. ........................................................................................'..,;;:::,''',,. ...ck00KXNWMM
MMMMMMMMMK: ....';:,'.. .;:c::;'.....................................................................................',::'.,:;,''',;,'.  ...cXMMMMMMMM
MMMMMMMMMK:...;,'..',,..',';::::;,................................................................................',;;::'......',,''''. ....,OMMMMMMMM
MMMMMMMMMXc.....','.... .,;,',;::::;.  ........................................................................ .,;;;;;'. ....''',,,'. ......dWMMMMMMM
MMMMMMMMMXc..... ..''..  .,,;,'',;:;. .. .....................................................................'..,;;,'''.....'',,'.. ........oNMMMMMMM
MMMMMMMMMK:...... .''''..';,',,,'..'...,.. .................................................................,:,.,;,'''',.....''''. ..........lXMMMMMMM
MMMMMMMMMK:...... ..,;,,...,,,'.'''....','.. .......................''''..................................',,'..''''',,,...',;::,. ..........;0MMMMMMM
MMMMMMMMMK;...... .'''''...,,,,''.......;;,'.  ................ .cooodk0K0kxo'..........................',;;.......',,'...,;;,,.. ............xWMMMMMM
MMMMMMMMMO,....... .,;;,'...',,,''''....'::;,.. ...........';;. ..',,;cONMMMW0;.......................',,:;. ......''''...''',,'  ............cXMMMMMM
MMMMMMMMWd....... ..''',,,...,,,,,''.....'::;'.. .........ckOkd:;,.cOKXWWMMMMMXc....................',';:,.  .......''...,,,'''.  ............,kMMMMMM
MMMMMMMMK:....... .';:;,''...';;;;,,,'....';:;... ...... .::,,,,,,.:XMMMMMMMMMMK;..................',';::.  ......',,'...',',,;,. .............lNMMMMM
MMMMMMMWk'...........''',,,'..';;;,,,,,'...;::'.......... ......  .oNMMMMMMMMMMWx.................',.,::,. ....''',,,..',,,,,,'. ..............,OMMMMM
MMMMMMMNo........ .;:;,,''''...,;;;,,,'....;c:'.'................ '0MMMMMMMMMMMMNo................,'.:c:;...'''''',,'..'',,,,,,. ...............lNMMMM
MMMMMMMK:.............',,;;;'..,;;;;,,'....:c:''................. .kMMMMMMMMMMMMMXc................,',::;. ...'',,,,...,,;;::;'. ...............,OMMMM
MMMMMMMO,.............'''''''..',,,,,''...,:;,'.................. '0MMMMMMMWWWMXKW0,................',,:;. ...'',,,,...'',,,''.. ................lNMMM
MMMMMMWx'......... .,:::::::;..';;;,,'....,:,.. ..................lNMMMMMMWN00WKokNd................ .',:,.....',,,,..',,,,;:;...................,kWMM
MMMMMMWd...........  ...'','''..,,,,,'....::,.. ............... .oNMMMMMMMMMKdONd;kK:...............  .,c:...',;;;,...'',,,,'. ...................cXMM
MMMMMMNl........... .',,,,,,,,'.',;,,''...::,'.................,dXMMMMMMMMMMWKkdcldx;...............  .'::...'',,,,..'''',,,,. ...................'xWM
MMMMMMK:..............',,,,''''..,;,,''..':;'. ..............,xXMMMMMWNWMMMMMWNXOxdcckl.............. .'::....'',,..';;;;;;,.. ....................:KM
MMMMMMO,............. ..',,,,,,''',;;,,'..;:;'. ...........'dXXXWMKONKd0X0NMMOxNMKc:dxc:;..............,:;......''..',,,,''.  .....................'kW
MMMMMNo',....'......  '::::;;,,'..';;;,,..':::,... ...... .lxd:oOd;;do;:c;lkkc,okd,cl'.cd,...........,;:,...',,;,..';;;:::;'  ......................lX
MMMMWk:,,,..';'..........''''......',;;;'...;::;;,'...     ... .... ......  .... .. .....    ....'',;::,...',,;;'...''',''.  ................'......'d
MMMNx;',,;..';..........':::::;;,'..,;;;,,'...,:::;;;,. ...................................  .'',;:c:,....'',;;. ..'',,;;,. .............. .''.  .'',k
MMMKo;,..,'.',. ..........',,,,''''...;;;;,'....',;;::. ................................... .,::::;'....''',,'.......'''.. ...................  ....;O
MMWNxc;'.''.;. .......... .;:::;,''....',;,,,'......... ................................... .,,'........'',;'...''.',;,.  .......................'. .;
Xdcc;';,...,'............ ....'''',,,'...'',,,,,',,..'. ...................................   ......''''''.. ..,,,,''.. .........................'.. ;
o.... ....';....,;.........  .;::;,'...'...'',;::,',;,. ...................................   .'.';,',,,.. .'...',;:,. .......... .'.  ..','.  ..'...,
o'.... .'.,'...,;;. .............'',,;,'......,,...'..                                      ....'..''.......',;''.... ..........  ......,'........  .,
Xo....... ....';;;. ........... .,,,''',;;,...'. ... ...... .... ..... ..... ..... .... ....    ........',;,'..','. ........  ... .....'............;x
0:...,;,'......;,. ..... ....... .. .;::,'..,;...:,..,;xXkc:xK0o:lOXOl:dKKxc:cxX0l:d0Ol:lOXo. ...',..';;,.';:;.  .............'.   ...........  .'';OW
Kc...';,''''.........';,.................;:;,'.,:;.';;,kM0olOWNxcdXWKdlkWNklll0WXdcxNKdcoKMk. .;'.,;'.';:;. ... ..........''............ ..........oNM
W0c;;;;;,,,'.. .'...';:,. ....,,....... ....';;;,';:;..kW0olOWNkcdKWXdlkWNxccl0WXdcxNKdcoKMk,..,;,.,;;..... ............  ............. ..'.......lXMM
MW0o;......''.. ...':;:,  ...,:,........... .....,;'..,kW0llOWNkcdKWKdlkWNxcco0WXdcxNKdcoKMk,'..';. ...  ......................,,..''.......  ...:KMMM
W0xo;.    ........'',;;. ..';;:. ...''. .......  ..  .'kWOllOWNkcdKWKdlkWNxcco0WKdcxNKdcoKMk'    .  ........................................ ...'xWMMM
WXd,..''''...........,'....;;;,..';;;.................,kWOllOWNkcoKWKolOWNxccoKWKockNKdcdKMk'.............................................  ....lXMMMM
MW0xxdl:,,,,''............';;;..,,'.. ............','.,kW0llOWNkcoKWKolOWNxccoKWKockNKdcdKMk'',........................................   .....cKMMMMM
MMMMW0d:;;;,,'.......'...'.,,.....  ............'.'''',kW0olOWNxcdKW0olOWNklcdKW0ockNKocdKMx..'..'......................  .......... .........:0MMMMMM
MMWN0l,,,,''........,;'......   ...............'..,..,,xW0ol0WNxcdXW0olOWNklcdKW0ockNKdcdKWd..'''',,'.............;kOo:.  .   .   ...........:0MMMMMMM
MMWNKkdlc;..  .''''''''...'. ..,'.......... .''...,'','lX0ol0WXxcxXW0llOWNklldKW0lckNKocdKNl.,,'....'............:OX0l,.  ....  ............:0WMMMMMMM
MMMMMMMMWNO;..',,',:;''''''..oOOkl'....... ........'.'''cxlo0WXxcxNWOllOWNklldKW0ockNKdcd0x'.','.',''.'.........ck0kd:..,:oxdc'............cKMMMMMMMMM
MMMMMMMWKd:,,;;,,,,,,;,;odoccodxkxl,...,;coo,....'.''..'.'',oOkl;ck0dccOWWklloOKx:;lxd;',;..'..,''''.'':kxdlldxONKxc'.;oold0kc...........'dXMMMMMMMMMM
MMMMMMMXxlllc;,''..',..dXkdxl''lxxOKK00KK00Od;'...........  .......''.':xxc''''......    ...'..,..''.'.':odddolxx;..':dxdx0Ol'..........;kWMMMMMMMMMMM
MMMMMMMMMWNN0c.'',;;.  ,ooxko;',:lxO0koc;'.......... .  ...........',,'..'. .............. ............  .... ..... ,xKKOxdol'.........lKWMMMMMMMMMMMM
MMMMMMMMMMMMWx;;;:,. . .ckKOoodolc,''..........................   ............      ...............................  ,x0x:. .........,dNMMMMMMMMMMMMMM
MMMMMMMMMMMMMNd;,.......,clxKNW0xc'''..........................'.........'...   ..''...............................   .'............:OWMMMMMMMMMMMMMMM
MMMMMMMMMMMMMW0old0Kkc'.. .:OXkl;....,'.....................';;,;,. .. .      ...',,;,'...............'''''......... .............'oXMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMWWMMMMMWKxc'. .,'.......,,..................';;,;:;..''...     ..''',;,,;;'..............','.......... ............cOWMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMWKxc'..........;,................,:;;::,..;;.';.    ...'''',;;,,:;'.....   ..','.......................;kNMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMWKkl,........;'.............';;;::;'.,:;.':,.   ...''',''',;;,;:;.....  .'..''........... ........;xXMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXkl;.....',............';;;:;'.';:,.':;'.  ....','',,''',;;,;;. ..  ...'.....'..,...  .....':xXWMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXOo;...............':::;'..,::'.'::''. ..'''',;,',,,,'',;;;;. ... ..........,'... ...':d0NMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWN0xc'......... .::,'..';:;...::'.,. .',,,,';;,',,,;;,',,;. .....  .......,....,lxOKNMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXOdc,..... ...',;::;'..'::'.,,..''',,;;,;;;,,,;;::'... .......  .. .;;.';lKWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWXOxl:'.  '::;,'.'.'::'.,:..',,',;,;,';;;;,',;:'  ......,:ldxOklcO0xOKNMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMNKOo;''...,;',:;',;:;..;;;;,;;;:,.,::;..... .,;lox0XNWMMMMWWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMNKOx:',,,,..;:::'.':;::,,;;::..';:'.,cox0XNWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMXd:dxc..;::,. ,:::c;.';:;..;ldldXWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWNWMW0odkd:'.,::clc:lkkodKWWWWWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM
MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMWMMWNXkxolk0XWMMMWWMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM"""

    print(ascii_art)

def monitor_sec_feed():
    print_ascii_art()
    rss_url = 'https://www.sec.gov/Archives/edgar/usgaap.rss.xml'
    while True:
        logger.info("Checking SEC RSS feed for 8-K and 6-K filings...")
        fetch_filings_from_rss(rss_url)
        logger.info("Sleeping for 10 minutes before next check...")
        time.sleep(600)  # Sleep for 10 minutes

if __name__ == "__main__":
    monitor_sec_feed()
