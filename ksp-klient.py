import sys
import os
import subprocess
import json
from typing import Union, AnyStr, Optional


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

class KSPkspApiService:
    base_url: str = "https://ksp.mff.cuni.cz/api/"
    token_path: str = os.path.join(os.path.expanduser("~"), ".config", "ksp-api-token")

    def __init__(
        self, base_url: Optional[str] = None, 
        token_path: Optional[str] = None
    ) -> None:
        if base_url is not None:
            self.base_url = base_url
        if token_path is not None:
            self.token_path = token_path
        
        fileExists(self.token_path)
        token: str = ""
        with open(self.token_path, "r") as f:
            token = f.readline().strip()
        
        self.headers: dict = {"Authorization": f"Bearer {token}"}
        
    def getList(self) -> Response:
        return requests.get(self.base_url + 'tasks/list', headers=self.headers)

    def getStatus(self, task: str) -> Response:
        return requests.get(self.base_url + "tasks/status", headers=self.headers,
            params = {"task" : task})
    
    def getTest(
        self, task: str, subtask: Union[int, str],
        generate: bool = True
    ) -> Response:
        return requests.post(self.base_url + "tasks/input", 
            params = {
                "task" : task, 
                "subtask" : subtask, 
                "generate" : ("true" if generate else "false")
            }, headers=self.headers)

    def submit(self, task: str, subtask: Union[int, str], content: AnyStr) -> Response:
        newHeaders = self.headers
        newHeaders['Content-Type'] = 'text/plain'
        return requests.post(self.base_url + "tasks/submit",
            data = content, headers=newHeaders, 
            params = { "task" : task, "subtask" : subtask})

    def generate(self, task: str, subtask: Union[int, str]) -> Response:
        return requests.post(self.base_url + "tasks/generate",
            headers=self.headers,
            params = { "task" : task, "subtask" : subtask})


def printNiceJson(json_text):
    print(json.dumps(json_text, indent=4, ensure_ascii=False))


def handleHelp():
    print("""vypsat všechny úlohy možné k odevzdání - list
vypsat stav úlohy - status <úloha>
odeslat odpověď - submit <úloha> <číslo testu> <cesta k souboru>
vygenerovat a stáhnout testovací vstup - downloadnew <úloha> <číslo testu>
spustit tvoje řešení na všech testovacích vstupech - run <úloha> <argumenty jak spustit zdoják>
""")
    sys.exit(0)


def handleList():
    r = kspApiService.getList()
    printNiceJson(r.json())


def handleStatus():
    if len(sys.argv) == 2:
        print("""Nedostatečný počet argumentů
status <úloha>
např: python3 ksp-klient.py status 32-Z4-1""")
        sys.exit(0)
        
    r = kspApiService.getStatus(sys.argv[2])
    printNiceJson(r.json())


def handleSubmit():
    if len(sys.argv) < 5:
        print("""Nedostatečný počet argumentů
submit <úloha> <číslo testu> <cesta k souboru>
např: python3 ksp-klient.py submit 32-Z4-1 1 01.out""")
        sys.exit(0)
    
    user_output = ""
    file_name = sys.argv[4]

    fileExists(file_name)
    with open(file_name, "r") as f:
        user_output = f.read()

    r = kspApiService.submit(sys.argv[2], sys.argv[3], user_output)
    print(r.text)


def handleDownloadNew():
    if len(sys.argv) < 4:
        print("""Nedostatečný počet argumentů
downloadnew <úloha> <číslo testu>
např: python3 ksp-klient.py downloadnew 32-Z4-1 1""")
        sys.exit(0)
        
    r = kspApiService.getTest(sys.argv[2], sys.argv[3])
    print(r.text)


def handleRun():
    if len(sys.argv) < 4:
        print("""Nedostatečný počet argumentů
run <úloha> <argumenty jak spustit zdoják>
např. python3 ksp-klient.py run 32-Z4-1 python3 solver.py""")
        sys.exit(0)

    sol_args = sys.argv[3:]
    task = sys.argv[2]
    numberSubtasks = len(kspApiService.getStatus(task).json()["subtasks"])
    for subtask in range(1, numberSubtasks+1):
        _input = kspApiService.getTest(task, subtask).text
        output = subprocess.check_output(sol_args, input=_input.encode())
        response = kspApiService.submit(task, subtask, output.decode())
        print(f"Tvá odpověď na podúkol {subtask} je {response.json()['verdict']}")


kspApiService = KSPkspApiService()

if len(sys.argv) == 1 or sys.argv[1] not in ["list", "status", "submit", "downloadnew", "run"]:
    handleHelp()
    
elif sys.argv[1] == "list":
    handleList()
    
elif sys.argv[1] == "status":
    handleStatus()

elif sys.argv[1] == "submit":
    handleSubmit()

elif sys.argv[1] == "downloadnew":
    handleDownloadNew()

elif sys.argv[1] == "run":
    handleRun()
        
