from nicegui import ui, run
import requests
from contextlib import contextmanager
from smc import SMC, HTTPAdapter, url_login, url_set_ds5_switch, url_get_all_resi_gw, url_get_specific_gw, url_delete_gw, login_body, ds5_body, get_delete_gw_body, get_delete_dn_body, delete_gw_body, delete_dn_body
import time


columns = [
    {'name': 'mac', 'label': 'MAC', 'field': 'mac', 'align': 'center'},
    {'name': 'gw_name', 'label': 'Gateway Name', 'field': 'gw_name', 'required': True, 'align': 'center'},
    {'name': 'fqdn', 'label': 'FQDN', 'field': 'fqdn', 'required': True, 'align': 'center'},
    {'name': 'dn', 'label': 'DNs', 'field': 'dn', 'align': 'center'},
]
# rows = [
#     {'gw_name': '1003866', 'fqdn': 'v00152F2877BA.ny77.voip.eng.cv.net', 'dn': '5164923932, 5164923933', 'mac': '00152F2877BA'},
# ]


@contextmanager
def disable_enable_button(button: ui.button):
    button.disable()
    try:
        yield
    finally:
        button.enable()


@contextmanager
def start_loading_animation(spinner:ui.spinner):
    spinner.visible = True
    try:
        yield
    finally:
        spinner.visible = False

@contextmanager
def show_hide_label(label: ui.label):
    label.visible = True
    try:
        yield
    finally:
        label.visible = False
    

async def login_smc(button: ui.button = None, spinner: ui.spinner = None, label: ui.label = None, stepper: ui.stepper = None):
    print('login_smc called')
    global smc_obj
    data = []
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter())
        smc_obj = SMC(session)
        try:
            with disable_enable_button(button):
                with start_loading_animation(spinner):
                    with show_hide_label(label):
                        label.text = 'Logging into SMC'
                        await run.io_bound(smc_obj.login, url_login, login_body)
                        label.text = 'Setting switch to DS5'
                        await run.io_bound(smc_obj.set_ds5_switch, url_set_ds5_switch, ds5_body)
                        
                        # ui.notify('Logged in', position='center', type='positive')
        except requests.exceptions.ConnectionError as e:
            print("Exception occurred, quitting!", e)
            ui.notify(f"Network exception occurred, please make sure VPN is connected and try again.", type='negative')
            ui.notify(f"{type(e)} - {str(e)}", type='negative')
        else:
            stepper.next()

async def get_all_gateways(button: ui.button = None, spinner: ui.spinner = None, label: ui.label = None, stepper: ui.stepper = None):
    with disable_enable_button(button):
        with start_loading_animation(spinner):
            with show_hide_label(label):
                label.text = "Getting gateway names"
                await run.io_bound(smc_obj.get_gw_names_list, url_get_all_resi_gw)
                ui.notify('Done getting all Gateways', position='center', type='positive')
                stepper.next()


async def get_mac_fqdn(mac: str, button: ui.button = None, spinner: ui.spinner = None, label: ui.label = None, stepper: ui.stepper = None, table: ui.table = None):
    with disable_enable_button(button):
        with start_loading_animation(spinner):
            with show_hide_label(label):
                label.text = f"Getting FQDN details for mac: {mac}."
                await run.io_bound(smc_obj.main, mac)
                rows = []
                if smc_obj.result:
                    for result in smc_obj.result:
                        print(result)
                        rows.append({'gw_name': result[0], 'fqdn': result[1], 'dn': ', '.join(result[2]), 'mac': mac})
                print(smc_obj.result)
                print(rows)
                table.rows = rows
                stepper.next()

def reset(stepper: ui.stepper):
    stepper.previous()
    stepper.previous()


with ui.stepper().props('vertical').classes('w-full') as stepper:
    with ui.step('Login to SMC'):
        ui.button('Login', on_click=lambda e: login_smc(button=e.sender, spinner=login_spinner, label=login_label, stepper=stepper))
        login_label = ui.label('')
        login_spinner = ui.spinner('dots', size='lg', color='red')
        login_label.visible = False
        login_spinner.visible = False
    with ui.step('Get all Gateways'):
        ui.button('Get', on_click=lambda e: get_all_gateways(e.sender, get_all_gw_spinner, get_all_gw_label, stepper))
        get_all_gw_label = ui.label('Please wait, getting all Gateways...')
        get_all_gw_spinner = ui.spinner('dots', size='lg', color='red')
        get_all_gw_label.visible = False
        get_all_gw_spinner.visible = False
    with ui.step('MAC'):
        mac_input = ui.input(label='', placeholder='Enter your MAC here',
         validation={'MAC should be 12 characters!': lambda value: len(value) == 12})
        with ui.stepper_navigation():
            mac_check_button = ui.button('Check', on_click=lambda e: get_mac_fqdn(mac_input.value, mac_check_button, mac_spinner, mac_label, stepper, table = table))
            mac_back_button = ui.button('Back', on_click=stepper.previous, color='primary')
        mac_label = ui.label('')
        mac_spinner = ui.spinner('dots', size='lg', color='red')
        mac_label.visible = False
        mac_spinner.visible = False
    with ui.step('Result'):
        table = ui.table(columns=columns, rows=[{}], row_key='name')
        with ui.stepper_navigation():
            ui.button('Delete', color='red')
            ui.button('Back', on_click=stepper.previous, color='primary')

ui.run()