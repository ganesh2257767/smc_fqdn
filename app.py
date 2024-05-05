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
rows = [
    {'gw_name': '1003866', 'fqdn': 'v00152F2877BA.ny77.voip.eng.cv.net', 'dn': '5164923932, 5164923933', 'mac': '00152F2877BA'},
]


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
                        label.text ="Getting gateway names"
                        await run.io_bound(smc_obj.get_gw_names_list, url_get_all_resi_gw)
                        stepper.next()
                        # ui.notify('Logged in', position='center', type='positive')
        except requests.exceptions.ConnectionError as e:
            print("Exception occurred, quitting!", e)


async def get_all_gateways(button: ui.button = None, spinner: ui.spinner = None, label: ui.label = None, stepper: ui.stepper = None):
    with disable_enable_button(button):
        with start_loading_animation(spinner):
            with show_hide_label(label):
                await run.io_bound(requests.get, 'https://httpbin.org/delay/1')
                ui.notify('Done getting all Gateways', position='center', type='positive')
                stepper.next()


def reset(stepper: ui.stepper):
    stepper.previous()
    stepper.previous()


with ui.stepper().props('vertical').classes('w-full') as stepper:
    with ui.step('Login to SMC'):
        ui.button('Login', on_click=lambda e: login_smc(button=e.sender, spinner=spinner1, label=label1, stepper=stepper))
        label1 = ui.label('')
        spinner1 = ui.spinner('dots', size='lg', color='red')
        label1.visible = False
        spinner1.visible = False
    with ui.step('Get all DNs'):
        ui.button('Get', on_click=lambda e: get_all_gateways(e.sender, spinner2, label2, stepper))
        label2 = ui.label('Please wait, getting all Gateways...')
        spinner2 = ui.spinner('dots', size='lg', color='red')
        label2.visible = False
        spinner2.visible = False
    with ui.step('MAC'):
        ui.input(label='', placeholder='Enter your MAC here',
         validation={'MAC should be 12 characters!': lambda value: len(value) == 12})
        with ui.stepper_navigation():
            ui.button('Next', on_click=stepper.next)
            ui.button('Back', on_click=stepper.previous, color='primary')
    with ui.step('Result'):
        ui.table(columns=columns, rows=rows, row_key='name')
        with ui.stepper_navigation():
            ui.button('Delete', color='red')
            ui.button('Back', on_click=stepper.previous, color='primary')

ui.run()