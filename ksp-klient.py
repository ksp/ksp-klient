import sys
import os
import subprocess
import json
import argparse
from argparse import Namespace
from typing import AnyStr, Optional


try:
    import requests
    from requests import Response
except ModuleNotFoundError as e:
    print("Nemáš nainstalovaný modul requests - pip install requests")
    sys.exit(1)


def fileExists(name: str) -> None:
    if not os.path.exists(name):
        print(f"Soubor {name} neexistuje")
        sys.exit(1)


def requestWrapper(fce):
    def wrapper(*args, **kvargs):
        ret = fce(*args, **kvargs)
        print(ret.url)
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
    base_url: str = "https://ksp.mff.cuni.cz/api/"
    token_path: str = os.path.join(os.path.expanduser("~"), ".config", "ksp-api-token")

    def __init__(
        self, base_url: Optional[str] = None, 
        token_path: Optional[str] = None,
        training_ground: Optional[bool] = False
    ) -> None:
        if base_url is not None:
            self.base_url = base_url
        if token_path is not None:
            self.token_path = token_path
        
        fileExists(self.token_path)
        token: str = ""
        with open(self.token_path, "r") as f:
            token = f.readline().strip()
        
        self.headers: dict = {"Authorization": f"Bearer {token}",}
        if training_ground:
            self.headers['set'] = 'cviciste'
        
    def getList(self) -> Response:
        return requests.get(self.base_url + 'tasks/list', headers=self.headers)

    def getStatus(self, task: str) -> Response:
        return requests.get(self.base_url + "tasks/status", headers=self.headers,
            params = {"task" : task})
    
    def getTest(
        self, task: str, subtask: int,
        generate: bool = True
    ) -> Response:
        return requests.post(self.base_url + "tasks/input", 
            params = {
                "task" : task, 
                "subtask" : subtask, 
                "generate" : ("true" if generate else "false")
            }, headers=self.headers)

    def submit(self, task: str, subtask: int, content: AnyStr) -> Response:
        newHeaders = self.headers
        newHeaders['Content-Type'] = 'text/plain'
        return requests.post(self.base_url + "tasks/submit",
            data = content.encode('utf-8'), headers=newHeaders, 
            params = { "task" : task, "subtask" : subtask})

    def generate(self, task: str, subtask: int) -> Response:
        return requests.post(self.base_url + "tasks/generate",
            headers=self.headers,
            params = { "task" : task, "subtask" : subtask})


def printNiceJson(json_text):
    print(json.dumps(json_text, indent=4, ensure_ascii=False))


def handleList(arguments: Namespace):
    r = kspApiService.getList()
    printNiceJson(r.json())


def handleStatus(arguments: Namespace):
    r = kspApiService.getStatus(arguments.task)
    printNiceJson(r.json())


def handleSubmit(arguments: Namespace):
    user_output = arguments.file.read()
    
    r = kspApiService.submit(arguments.task, arguments.subtask, user_output)
    print(r.text)


def handleDownloadNew(arguments: Namespace):        
    r = kspApiService.getTest(arguments.task, arguments.subtask)
    print(r.text)


def handleRun(arguments: Namespace):
    task = arguments.task
    numberSubtasks = len(kspApiService.getStatus(task).json()["subtasks"])
    for subtask in range(1, numberSubtasks+1):
        _input = kspApiService.getTest(task, subtask).text
        output = subprocess.check_output(arguments.sol_args, input=_input.encode())
        response = kspApiService.submit(task, subtask, output.decode())
        print(f"Tvá odpověď na podúkol {subtask} je {response.json()['verdict']}")


def exampleUsage(text: str):
    return f'Příklad použití: {text}'


parser = argparse.ArgumentParser(description='Process some integers.')

parser.add_argument('-v', '--verbose', help='Zobrazit debug log', action='store_true')
parser.add_argument('-c', '--cviciste', help='Zobrazit/pracovat i s úlohama z cvičiště', action='store_true')
parser.add_argument('-b', '--base_url', help='Nastavit jinou url adresu pro dotazy (např. pro testovací účely)')

subparsers = parser.add_subparsers(help='Vyberte jednu z následujících operací', dest='operation_name')
parser_list = subparsers.add_parser('list', help='Zobrazí všechny úlohu, které lze odevzdávat',
                epilog=exampleUsage('python3 ksp-klient.py list'))

parser_status = subparsers.add_parser('status', help='Zobrazí stav dané úlohy',\
                epilog=exampleUsage('python3 ksp-klient.py status 32-Z4-1'))
parser_status.add_argument("task", help="kód úlohy")

parser_submit = subparsers.add_parser('submit', help='Odešle odpověd na server KSP',
                epilog=exampleUsage('python3 ksp-klient.py submit 32-Z4-1 1 01.out'))
parser_submit.add_argument("task", help="kód úlohy")
parser_submit.add_argument("subtask", help="číslo podúkolu", type=int)
parser_submit.add_argument("file", help="cesta k souboru, který chcete odevzdat", type=argparse.FileType(mode="r", encoding="utf-8"))

parser_download_new = subparsers.add_parser('downloadnew', help='Vygeneruje a stáhne nový testovací soubor', \
                epilog=exampleUsage('python3 ksp-klient.py downloadnew 32-Z4-1 1'))
parser_download_new.add_argument("task", help="kód úlohy")
parser_download_new.add_argument("subtask", help="číslo podúkolu", type=int)

parser_run = subparsers.add_parser('run', help='Spustí tvůj program na všechny podúkoly u dané úlohy', \
                epilog=exampleUsage('python3 ksp-klient.py run 32-Z4-1 python3 solver.py'))
parser_run.add_argument("task", help="kód úlohy")
parser_run.add_argument("sol_args", nargs="+", help="argumenty, jak spustit zdoják")

arguments = parser.parse_args()

kspApiService = KSPApiService(base_url=arguments.base_url,\
                              training_ground=arguments.cviciste)

operations: dict = {'list' : handleList, 'status': handleStatus, 'submit': handleSubmit, \
                     'downloadnew': handleDownloadNew, 'run': handleRun}

if arguments.operation_name == None:
    parser.print_help()
else:
    operations[arguments.operation_name](arguments)
