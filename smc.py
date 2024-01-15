import requests
import ssl
from bs4 import BeautifulSoup
from time import perf_counter, sleep
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os
import threading

requests.urllib3.disable_warnings()

load_dotenv()

url_login = 'https://10.244.170.85:8099/smc/login'
url_set_ds5_switch = 'https://10.244.170.85:8099/smc/app'
url_get_all_resi_gw = 'https://10.244.170.85:8099/smc/app?outer=700&inner=708&cid=&PageNumber=1&PageSize=1000&operation=Pop_GetGatewayList&title=Residential Gateway List'
url_get_specific_gw = 'https://10.244.170.85:8099/smc/app?operation=Pop_GetGateway&outer=700&inner=708&cid=&title=Residential Gateway Detail&GwName={}'

username = os.environ.get('SMC_USER')
password = os.environ.get('SMC_PASS')

login_body = {
   'hiqrequest': 'false',
   'imageField.x': '15',
   'imageField.y': '9',
   'j_domain': '',
   'j_password': username,
   'j_username': password,
   'locale': 'en_US',
   'securityOperation': 'UserLogin',
   'style': 'Blue',
}

ds5_body = {
   'cid':'', 
   'hiq_ip': '10.248.164.21:HCVLNYAHDS5::true:8767:false',
   'hiqrequest': 'false',
   'imageField.x': '44',
   'imageField.y': '18',
   'inner': '0',
   'inner_r': '0',
   'locale': 'en_US',
   'mainObjectType': 'null',
   'operation': 'hiqConnect',
   'outer': '100',
   'outer_r': '4',
   'RefreshCachedSwitchData': 'No',
   'style': 'Blue',
}

class HTTPAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        kwargs["ssl_context"] = ssl_context
        return super().init_poolmanager(*args, **kwargs)

class SMC:
    def __init__(self, session):
        self.session = session
        self.cookies = None
        self.result = []
        self.found = False
        self.CURSOR_UP = '\033[1A'
        self.CLEAR = '\x1b[2K'
        self.CLEAR_LINE = self.CURSOR_UP + self.CLEAR


    def login(self, url, body):
        login = self.session.post(url, data=body, verify=False)
        self.cookies = login.cookies

    def set_ds5_switch(self, url, body):
        self.session.post(url, data=body, verify=False, cookies=self.cookies)

    def get_gw_names_list(self, url):
        get_all_rei_gw_res = self.session.get(url, verify=False, cookies=self.cookies)

        page = BeautifulSoup(get_all_rei_gw_res.content, 'html.parser')
        tr = page.find_all('table')[0].find_all('tr')[3].find('td').find('table').find_all('tr')

        gw_names = [row.find('td').get_text() for row in tr[1:]]
        print(gw_names)
        return gw_names

    def send_request(self, args):
        if len(self.result) > 0:
            return
        gw_name, mac = args
        specific_gw_response = self.session.get(url=url_get_specific_gw.format(gw_name), verify=False, cookies=self.cookies)   
        specific_gw_response_page = BeautifulSoup(specific_gw_response.content, 'html.parser')
        all_tds = specific_gw_response_page.find_all('td')
        try:
            fqdn_name = str(all_tds[7].string)
        except IndexError:
            return
        if mac in fqdn_name:
            id_to_delete = str(all_tds[5].string)
            dns = []
            if len(all_tds) == 171:
                dns.append(str(all_tds[170].string))
            if len(all_tds) == 173:
                dns.append(str(all_tds[170].string))
                dns.append(str(all_tds[172].string))
            self.result.append((id_to_delete, fqdn_name, dns))

    def main(self, mac, gw_names):
        self.found = False
        self.result.clear()
        threading.Thread(target=self.timer).start()
        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(self.send_request, ((name, mac) for name in gw_names))
        
        self.found = True
        return self.result
    
    def make_table(self, result):
        # Calculate total width
        total_width = 0
        margin = 10
        headers = ["GW Name", "FQDN", "DNs", "Time"]
        header_str = ''
        data_str = ''
        for row in result:
            for data, header in zip(row, headers):
                if isinstance(data, list):
                    data = ', '.join(data)
                total_width += len(data) + margin
                header_str += f'|{header:^{len(data) + (margin-1)}}'
                data_str += f'|{data:^{len(data) + (margin-1)}}'
            
        print("-" * (total_width + 1))
        print(header_str + '|')
        print("-" * (total_width + 1))
        print(data_str + '|')
        print("-" * (total_width + 1))
        
    def timer(self):
        t = 0
        global m, s
        while not self.found:
            m, s = divmod(t, 60)
            print(f'{int(m):0>2}:{int(s):0>2}')
            sleep(1)
            t += 1
            print(self.CLEAR_LINE, end="")
            
if __name__ == "__main__":
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter())
        smc_obj = SMC(session)
        print("Logging into SMC...")
        smc_obj.login(url_login, login_body)

        print("Setting DS5 Switch...")
        smc_obj.set_ds5_switch(url_set_ds5_switch, ds5_body)
        
        print("Getting all Gateways...")
        gw_names = smc_obj.get_gw_names_list(url_get_all_resi_gw)

        dummy_mac = input("Enter mac: ").lower()
        os.system("")
        
        result = smc_obj.main(dummy_mac, gw_names)
        result = list(map(list, result))
        for row in result:
            row.append(f'{int(m):0>2}:{int(s):0>2}')
        smc_obj.make_table(result)
        input("Enter to exit")
