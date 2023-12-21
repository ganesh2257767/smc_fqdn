import gooeypie as gp
from smc import login

app = gp.GooeyPieApp('FQDN')

app.width = 500
app.height = 300
app.set_resizable(False)

mac_label = gp.Label(app, 'Mac')
mac_input = gp.Input(app)

search_btn = gp.Button(app, )
app.on_open(login)


app.run()