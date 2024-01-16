import gooeypie as gp
from smc import HTTPAdapter, SMC, url_login, login_body, url_get_all_resi_gw, url_set_ds5_switch, ds5_body, url_delete_gw, get_delete_gw_body, delete_gw_body, get_delete_dn_body, delete_dn_body
import requests
import threading
from time import sleep

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
        
        status_label.text = 'Fetching all gateways...'
        app.update()
        try:
            smc_obj.get_gw_names_list(url_get_all_resi_gw)
        except IndexError:
            app.alert("Error", "Something went wrong, incorrect page was loaded so can't continue further.", "error")
            return
        else:
            status_label.text = 'Done'
            search_btn.disabled = False


def delete_dn_or_gw(result):
    delete_btn.disabled = True
    for name, _, dns in result:
        answer = app.confirm_yesno("Delete", f"Are you sure you want to delete?\n\nName: {name}\n\nDN(s): {', '.join(dns)}", "warning")
        if answer:
            if dns:
                for dn in dns:
                    smc_obj.get_dn_for_delete(url_delete_gw, get_delete_dn_body, dn)
                    code, status = smc_obj.delete_dn(url_delete_gw, delete_dn_body, dn)
                    
            else:
                smc_obj.get_gw_for_delete(url_delete_gw, get_delete_gw_body, name)
                code, status = smc_obj.delete_gw(url_delete_gw, delete_gw_body)
            if status == 'Success':
                app.alert(f"Done: Code {code}", "Done deleting the DN(s) and Gateway FQDN.\n\nPlease retry task from Strata.", "info")
            else:
                app.alert(f"Error: Code {code}", "Issue deleting DN(s) and Gateway FQDN.\n\nPlease delete manually from SMC v14.", "error")
        else:
            delete_btn.disabled = False
                
  
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
    delete_btn.disabled = False
    global flag, m, s
    if len(mac_input.text) != 12:
        app.alert("Error", "Mac should be 12 characters!", "error")
        return
    threading.Thread(target=timer, daemon=True).start()
    progress.start(25)
    search_btn.disabled = True
    smc_obj.main(mac_input.text.lower())
    progress.stop()
    progress.value = 0
    search_btn.disabled = False
    flag = False

    data = []
    
    if smc_obj.result:
        for result in smc_obj.result:
            name, fqdn, dns = result
            data.append([name, fqdn, ', '.join(dns), f"{int(m):0>2}:{int(s):0>2}"])
        table.data = data

        table_win.show_on_top()
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
table.set_column_widths(250, 250, 200, 100)

delete_btn = gp.Button(table_win, 'Delete FQDN?', lambda x: delete_dn_or_gw(smc_obj.result))

app.set_grid(4, 3)
app.add(mac_label, 1, 1)
app.add(mac_input, 1, 2)
app.add(search_btn, 1, 3)
app.add(progress, 3, 1, column_span=3, align='center')
app.add(status_label, 4, 1, column_span=3, align='center')

table_win.set_grid(2, 1)
table_win.add(table, 1, 1)
table_win.add(delete_btn, 2, 1, align='center')

app.on_open(lambda: threading.Thread(target=create_session_and_login).start())

app.run()