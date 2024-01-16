import requests
import ssl
from bs4 import BeautifulSoup
from time import perf_counter, sleep
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os
import threading
import xmltodict

requests.urllib3.disable_warnings()

load_dotenv()

url_login = 'https://10.244.170.85:8099/smc/login'
url_set_ds5_switch = url_delete_gw = 'https://10.244.170.85:8099/smc/app'
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

get_delete_gw_body = {
    'cid': '',
    'GwName': '',
    'imageField.x': 43,
    'imageField.y': 9,
    'inner': 702,
    'inner_r': 703,
    'mainObjectType': 'null',
    'operation': 'GetGateway',
    'outer': 700,
    'outer_r': 701
}


delete_gw_body = {
    'cid': '',
    'inner': 704,
    'inner_r': 702,
    'isXMLHttpRequest': 'true',
    'mainObjectType': 'null',
    'operation': 'DeleteGateway',
    'outer': 701,
    'outer_r': 700
}

get_delete_dn_body = {
   'cid': '',
   'cid': '',
   'hiqrequest': 'true',
   'imageField.x': 48,
   'imageField.y': 12,
   'inner': 2,
   'inner_r': 3,
   'mainObjectType': 'null',
   'operation': 'GetSubscriberInfo',
   'outer': 1,
   'outer_r': 3,
   'outer_r_pbx_range': 333,
   'outer_r_teen_line': 33,
   'ServiceId': ''
}

delete_dn_body = {
   'cid': '',
   'CSTA_ConnectionInfo': 'MGCP',
   'CSTA_Subscribed': 'no',
   'DeleteGatewayObjects': 'DeleteCircuitsAndGateway',
   'hiqrequest': 'true',
   'inner': 4,
   'inner_r': 2,
   'isXMLHttpRequest': 'true',
   'mainObjectType': 'null',
   'operation': 'DeleteSubscriber',
   'outer': 3,
   'outer_r': 1,
   'ServiceId': ''
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
        self.gw_names = None


    def login(self, url, body):
        login = self.session.post(url, data=body, verify=False)
        self.cookies = login.cookies

    def set_ds5_switch(self, url, body):
        self.session.post(url, data=body, verify=False, cookies=self.cookies)

    def get_gw_names_list(self, url):
        get_all_rei_gw_res = self.session.get(url, verify=False, cookies=self.cookies)

        page = BeautifulSoup(get_all_rei_gw_res.content, 'html.parser')
        tr = page.find_all('table')[0].find_all('tr')[3].find('td').find('table').find_all('tr')

        self.gw_names = [row.find('td').get_text() for row in tr[1:]][-10:]
        with open('logs.txt', 'a') as f:
            f.write(', '.join(self.gw_names))
            f.write('\n'+'-'*150)

    def send_request(self, args):
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
            try:
                dns = [dn.string for dn in all_tds[170::2] if dn.string]
            except KeyError:
                dns = []
            else:
                self.result.append((id_to_delete, fqdn_name, dns))


    def get_gw_for_delete(self, url, body, gw_name):
        body['GwName'] = gw_name
        self.session.post(url=url, data=body, verify=False, cookies=self.cookies)
    
    
    def delete_gw(self, url, body):
        delete_gw_response = self.session.post(url=url, data=body, verify=False, cookies=self.cookies)
        delete_gw_response_page = BeautifulSoup(delete_gw_response.content, 'html.parser')
        a = xmltodict.parse(str(delete_gw_response_page))
        try:
            a['root']
            code, status = 0, 'Success'
        except KeyError:
            code, status = -1, 'Failure'
        return code, status
    
    
    def get_dn_for_delete(self, url, body, dn):
        body['ServiceId'] = int(dn)
        self.session.post(url=url, data=body, verify=False, cookies=self.cookies)
    
    
    def delete_dn(self, url, body, dn):
        body['ServiceId'] = int(dn)
        delete_dn_response = self.session.post(url=url, data=body, verify=False, cookies=self.cookies)
        delete_dn_response_page = BeautifulSoup(delete_dn_response.content, 'html.parser')
        a = xmltodict.parse(str(delete_dn_response_page))
        try:
            base = a['root']['soap-env:envelope']['soap-env:body']['unsp:deletesubscriberresult']['resultcodestruct']

            code = base['resultcode']
            status = base['resulttext1']
        except KeyError:
            code, status = -1, 'Failure'
        return code, status


    def main(self, mac, gw_names):
        self.found = False
        self.result.clear()
        threading.Thread(target=self.timer).start()
        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(self.send_request, ((name, mac) for name in gw_names))
        
        self.found = True
    
    
    def make_table(self, result):
        # Calculate total width
        total_width = 0
        margin = 5
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
            print(self.CLEAR_LINE, end='')
            t += 1
        
        
if __name__ == "__main__":
    confirm = ''
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter())
        smc_obj = SMC(session)
        print("Logging into SMC...")
        smc_obj.login(url_login, login_body)

        print("Setting DS5 Switch...")
        smc_obj.set_ds5_switch(url_set_ds5_switch, ds5_body)
        
        print("Getting all Gateways...")
        smc_obj.get_gw_names_list(url_get_all_resi_gw)
        answer = ''
        while answer != 'q':
            print("1. Enter MAC to check FQDN")
            print("q. Quit")
            answer = input(">> ")
            
            if answer == '1':
                dummy_mac = input("Enter mac: ").lower()
                os.system("")
                
                smc_obj.main(dummy_mac, smc_obj.gw_names)
                if smc_obj.result:
                    smc_obj.result = list(map(list, smc_obj.result))
                    for row in smc_obj.result:
                        row.append(f'{int(m):0>2}:{int(s):0>2}')
                    smc_obj.make_table(smc_obj.result)

                    print()
                    confirm = input("Do you want to delete this FQDN?[y/n]")
                    if confirm.lower() == 'y':
                        for name, _, dns, x in smc_obj.result:
                            if dns:
                                for dn in dns:
                                    smc_obj.get_dn_for_delete(url_delete_gw, get_delete_dn_body, dn)
                                    code, status = smc_obj.delete_dn(url_delete_gw, delete_dn_body, dn)       
                            else:
                                smc_obj.get_gw_for_delete(url_delete_gw, get_delete_gw_body, name)
                                code, status = smc_obj.delete_gw(url_delete_gw, delete_gw_body)
                            if status == 'Success':
                                print(f"Done: Code {code} - Status {status}\n\nDone deleting the DN(s) and Gateway FQDN.\n\nPlease retry task from Strata.")
                            else:
                                print(f"Error: Code {code} - Status {status}\n\nIssue deleting DN(s) and Gateway FQDN.\n\nPlease delete manually from SMC v14.", "error")
                    else:
                        continue
                else:
                    print("No results found for this MAC, please try manually, sorry!")
                    continue