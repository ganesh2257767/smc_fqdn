import gooeypie as gp
from smc import HTTPAdapter, SMC, url_login, login_body, url_get_all_resi_gw, url_set_ds5_switch, ds5_body
import requests
import threading
from time import perf_counter, sleep
  

def create_session_and_login():
    global smc_obj
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter())
        smc_obj = SMC(session)
        status_label.text = 'Logging into SMC...'
        app.update()
        try:
            smc_obj.login(url_login, login_body)
        except requests.exceptions.ConnectionError:
            if app.confirm_retrycancel("Error", "Connection error, check VPN or Internet Connection", "error"):
                create_session_and_login()
            else:
                app.exit()
        
        status_label.text = 'Setting switch to DS5...'
        app.update()
        smc_obj.set_ds5_switch(url_set_ds5_switch, ds5_body)
        
        try:
            status_label.text = 'Fetching all gateways...'
            app.update()
            smc_obj.gw_names = smc_obj.get_gw_names_list(url_get_all_resi_gw)
            status_label.text = 'Done'
            search_btn.disabled = False
        except IndexError:
            app.alert("Error", "Something went wrong, incorrect page was loaded so can't continue further.", "error")
            return
            
def timer():
    global flag, m, s
    flag = True
    t = 0
    while flag:
        m, s = divmod(t, 60)
        status_label.text = f'{m:0>2}:{s:0>2}'
        app.update()
        t += 1
        sleep(1)


def get_results():
    global flag, m, s
    if len(mac_input.text) != 12:
        app.alert("Error", "Mac should be 12 characters!", "error")
        return
    threading.Thread(target=timer, daemon=True).start()
    progress.start(25)
    search_btn.disabled = True
    result = smc_obj.main(mac_input.text)
    progress.stop()
    progress.value = 0
    search_btn.disabled = False
    flag = False
    # status_label.text = 'Done'

    if result:
        result = result[0]
        table.data = [
            [result[0], result[1], ', '.join(result[2]), f"{int(m):0>2}:{int(s):0>2}"]
        ]
        table_win.show_on_top()
        # app.alert(f"Total time: {m:0>2}:{s:0>2}", f"Media gateway to delete: {result[0]}\n\nFQDN: {result[1]}\n\nDNs: {', '.join([dn for dn in result[2]])}\n\nTime: {total/60} minutes\n", "info")
    else:
        app.alert("No records", "No records found for this MAC, please try manually, sorry!", "info")

app = gp.GooeyPieApp('FQDN')

app.set_resizable(False)

mac_label = gp.Label(app, 'Mac')
mac_input = gp.Input(app)

search_btn = gp.Button(app, 'Submit', lambda x: threading.Thread(target=get_results).start())
search_btn.disabled = True

progress = gp.Progressbar(app, 'indeterminate')
status_label = gp.Label(app, '')

table_win = gp.Window(app, 'Result')

table = gp.Table(table_win, ['GW Name', 'FQDN', 'DNs', 'Time'])
table.set_column_alignments('center', 'center', 'center', 'center')

app.set_grid(4, 2)
app.add(mac_label, 1, 1)
app.add(mac_input, 1, 2)
app.add(search_btn, 2, 1, column_span=2, align='center')
app.add(progress, 3, 1, column_span=2, align='center')
app.add(status_label, 4, 1, column_span=2, align='center')

table_win.set_grid(1, 1)
table_win.add(table, 1, 1)

app.on_open(lambda: threading.Thread(target=create_session_and_login).start())

app.run()