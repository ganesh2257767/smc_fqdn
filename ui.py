import gooeypie as gp
from smc import HTTPAdapter, SMC, url_login, login_body, url_get_all_resi_gw, url_set_ds5_switch, ds5_body
import requests
import threading
from time import perf_counter
  

def create_session_and_login():
    global smc_obj
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter())
        smc_obj = SMC(session)
        status_label.text = 'Logging into SMC...'
        app.update()
        smc_obj.login(url_login, login_body)
        
        
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
            print("Something went wrong, incorrect page was loaded so can't continue further.")


def get_results():
    if len(mac_input.text) != 12:
        app.alert("Error", "Mac should be 12 characters!", "error")
        return
    status_label.text = 'Please wait...'
    start = perf_counter()
    progress.start(25)
    result = smc_obj.main(mac_input.text)
    total = perf_counter() - start
    progress.stop()
    progress.value = 0
    status_label.text = 'Done'

    if result:
        result = result[0]
        app.alert(f"Time: {total/60} minutes", f"Media gateway to delete: {result[0]}\n\nFQDN: {result[1]}\n\nDNs: {', '.join([dn for dn in result[2]])}\n\nTime: {total/60} minutes\n", "info")
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

app.set_grid(4, 2)
app.add(mac_label, 1, 1)
app.add(mac_input, 1, 2)
app.add(search_btn, 2, 1, column_span=2, align='center')
app.add(progress, 3, 1, column_span=2, align='center')
app.add(status_label, 4, 1, column_span=2, align='center')

app.on_open(lambda: threading.Thread(target=create_session_and_login).start())

app.run()