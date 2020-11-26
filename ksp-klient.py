#!/usr/bin/python3
# Klient pro odesílání open-datových úloh pomocí KSP API
# Tento program lze používat a distribuovat pod licencí Creative Commons CC-BY-NC-SA 3.0.

import sys
import os
import subprocess
import json
import gettext
import datetime
from typing import AnyStr, Optional

try:
    import requests
    from requests import Response
except ModuleNotFoundError:
    print("Nemáš nainstalovaný modul requests - pip install requests")
    sys.exit(1)


def translateToCzech(message: str) -> str:
    message = message.replace("usage", "použití")
    message = message.replace("show this help message and exit",
                              "zobraz tuto nápovědu a ukonči program")
    message = message.replace("error:", "chyba:")
    message = message.replace("the following arguments are required:",
                              "tyto následující argumenty jsou vyžadovány:")
    message = message.replace('optional arguments', 'volitelné argumenty')
    message = message.replace('positional arguments', 'poziční argumenty')
    message = message.replace('invalid choice: %(value)r (choose from %(choices)s)',
                              'neplatná volba: %(value)r (zvolte z %(choices)s)')
    return message

gettext.gettext = translateToCzech

## this must be imported after translation set up
import argparse
from argparse import Namespace

def fileExists(name: str) -> None:
    if not os.path.exists(name):
        print(f"Soubor {name} neexistuje")
        sys.exit(1)


def requestWrapper(fce):
    def wrapper(*args, **kvargs):
        ret = fce(*args, **kvargs)
        # TODO: Print it in verbose mode
        # print(ret.url)
        if ret.status_code != 200:
            try:
                print(ret.json())
            except ValueError:
                print(ret.text)
            sys.exit(1)
        return ret

    return wrapper


requests.get = requestWrapper(requests.get)
requests.post = requestWrapper(requests.post)

class KSPApiService:
    api_url: str = "https://ksp.mff.cuni.cz/api/"
    token_path: str = os.path.join(os.path.expanduser("~"), ".config", "ksp-api-token")

    def __init__(
        self, api_url: Optional[str] = None,
        token_path: Optional[str] = None,
        training_ground: Optional[bool] = False
    ) -> None:
        if api_url is not None:
            self.api_url = api_url
        if token_path is not None:
            self.token_path = token_path

        fileExists(self.token_path)
        token: str = ""
        with open(self.token_path, "r") as f:
            token = f.readline().strip()

        self.headers: dict = {"Authorization": f"Bearer {token}",}
        self.training_ground = training_ground

    def getList(self) -> Response:
        param = {}
        if self.training_ground:
            param['set'] = 'cviciste'
        return requests.get(self.api_url + 'tasks/list', headers=self.headers,
            params = param)

    def getStatus(self, task: str) -> Response:
        return requests.get(self.api_url + "tasks/status", headers=self.headers,
            params = {"task" : task})

    def getTest(
        self, task: str, subtask: int,
        generate: bool = True
    ) -> Response:
        return requests.post(self.api_url + "tasks/input",
            params = {
                "task" : task,
                "subtask" : subtask,
                "generate" : ("true" if generate else "false")
            }, headers=self.headers)

    def submit(self, task: str, subtask: int, content: AnyStr) -> Response:
        newHeaders = self.headers
        newHeaders['Content-Type'] = 'text/plain'

        if type(content) == str:
            content = content.encode('utf-8')

        return requests.post(self.api_url + "tasks/submit",
            data = content, headers=newHeaders,
            params = { "task" : task, "subtask" : subtask})

    def generate(self, task: str, subtask: int) -> Response:
        return requests.post(self.api_url + "tasks/generate",
            headers=self.headers,
            params = { "task" : task, "subtask" : subtask})


def printNiceJson(json_text):
    print(json.dumps(json_text, indent=4, ensure_ascii=False))


def czechTime(value, first_form, second_form, third_form):
    value = round(value)
    if value == 0:
        return ''
    if value == 1:
        return f'{value} {first_form}'
    elif value < 5:
        return f'{value} {second_form}'
    else:
        return f'{value} {third_form}'


def formatTime(subtask: dict):
    if subtask['input_generated']:
        if subtask['input_valid_until'].startswith('9999'):
            return 'stále'

        timedelta = datetime.datetime.fromisoformat(subtask['input_valid_until']) - datetime.datetime.now().astimezone()
        
        days, hours = divmod(timedelta.total_seconds(), 60*60*24)
        hours, minutes = divmod(hours, 60*60)
        minutes, seconds = divmod(minutes, 60)
        
        #print(days, hours, minutes, seconds)

        day_str = czechTime(days, 'den', 'dny', 'dnů')
        hour_str = czechTime(hours, 'hodina', 'hodiny', 'hodin')
        minute_str = czechTime(minutes, 'minuta', 'minuty', 'minut')
        second_str = czechTime(seconds, 'sekunda', 'sekundy', 'sekund')
        ret = []
        for x in [day_str, hour_str, minute_str, second_str]:
            if x != '':
                ret.append(x)

        if len(ret) < 3:
            return ' a '.join(ret)
        else:
            return ', '.join(ret[:-1]) + f' a {ret[-1]}' 
    else:
        return 'Nevygenerováno'


def printTableStatus(json_text: dict):
    print(f'Název úlohy: {json_text["name"]}')
    print(f'Získané body: {json_text["points"]}/{json_text["max_points"]}')
    print(f'{"Test":<5}| {"Délka platnosti":<32}| {"Body":<8}| {"Výsledek"}')
    print('-'*60)
    for subtask in json_text['subtasks']:
        points = f'{subtask["points"]}/{subtask["max_points"]}'
        verdict = subtask['verdict'] if 'verdict' in subtask else ''
        print(f'{subtask["id"]:<5}| {formatTime(subtask):<32}| {points:<8}| {verdict}')


def handleList(arguments: Namespace):
    r = kspApiService.getList()
    printNiceJson(r.json())


def handleStatus(arguments: Namespace):
    r = kspApiService.getStatus(arguments.task)
    printTableStatus(r.json())


def handleSubmit(arguments: Namespace):
    user_output = arguments.file.read()

    r = kspApiService.submit(arguments.task, arguments.subtask, user_output)
    printNiceJson(r.json())


def handleGenerate(arguments: Namespace):
    r = kspApiService.getTest(arguments.task, arguments.subtask)
    print(r.text)


def handleRun(arguments: Namespace):
    task = arguments.task
    numberSubtasks = len(kspApiService.getStatus(task).json()["subtasks"])
    for subtask in range(1, numberSubtasks+1):
        _input = kspApiService.getTest(task, subtask).text
        output = subprocess.check_output(arguments.sol_args, input=_input.encode())
        response = kspApiService.submit(task, subtask, output)
        resp = response.json()
        print(f"Podúloha {subtask}: {resp['verdict']} ({resp['points']}/{resp['max_points']}b)")


def exampleUsage(text: str):
    return f'Příklad použití: {text}'


parser = argparse.ArgumentParser(description='Klient na odevzdávání open-data úloh pomocí KSP API')

parser.add_argument('-v', '--verbose', help='Zobrazit debug log', action='store_true')
parser.add_argument('-c', '--cviciste', help='Zobrazit/pracovat i s úlohami z cvičiště', action='store_true')
parser.add_argument('-a', '--api-url', help='Použít jiný server (např. pro testovací účely)')

subparsers = parser.add_subparsers(help='Vyber jednu z následujících operací:', dest='operation_name')
parser_list = subparsers.add_parser('list', help='Zobrazí všechny úlohy, které lze odevzdávat',
                epilog=exampleUsage('./ksp-klient.py list'))

parser_status = subparsers.add_parser('status', help='Zobrazí stav dané úlohy',\
                epilog=exampleUsage('./ksp-klient.py status 32-Z4-1'))
parser_status.add_argument("task", help="kód úlohy")

parser_download_new = subparsers.add_parser('generate', help='Vygeneruje a stáhne nový testovací vstup', \
                epilog=exampleUsage('./ksp-klient.py generate 32-Z4-1 1'))
parser_download_new.add_argument("task", help="kód úlohy")
parser_download_new.add_argument("subtask", help="číslo podúlohy", type=int)

parser_submit = subparsers.add_parser('submit', help='Odešle odpověd na danou podúlohu',
                epilog=exampleUsage('./ksp-klient.py submit 32-Z4-1 1 01.out'))
parser_submit.add_argument("task", help="kód úlohy")
parser_submit.add_argument("subtask", help="číslo podúlohy", type=int)
parser_submit.add_argument("file", help="cesta k souboru, který chcete odevzdat", type=argparse.FileType(mode="rb"))

parser_run = subparsers.add_parser('run', help='Spustí Tvůj program na všechny podúlohy dané úlohy', \
                epilog=exampleUsage('./ksp-klient.py run 32-Z4-1 python3 solver.py'))
parser_run.add_argument("task", help="kód úlohy")
parser_run.add_argument("sol_args", nargs="+", help="Tvůj program a případně jeho argumenty")

arguments = parser.parse_args()

kspApiService = KSPApiService(api_url=arguments.api_url,\
                              training_ground=arguments.cviciste)

operations: dict = {'list' : handleList, 'status': handleStatus, 'submit': handleSubmit, \
                     'generate': handleGenerate, 'run': handleRun}

if arguments.operation_name == None:
    parser.print_help()
else:
    operations[arguments.operation_name](arguments)
