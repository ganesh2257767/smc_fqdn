import requests
import ssl
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os

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
        print(gw_names[150:450])
        print(len(gw_names[150:450]))
        return gw_names[150:450]

    def send_request(self, args):
        if len(self.result) > 0:
            return
        gw_name, mac = args
        print(gw_name)
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

    def main(self, mac):
        self.result.clear()
        gw_names = self.get_gw_names_list(url_get_all_resi_gw)

        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(self.send_request, ((name, mac) for name in gw_names))

        print(f'{self.result=}')
        return self.result
