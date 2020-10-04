import sys
import os
import subprocess
from typing import Union, AnyStr


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
    def wrapper(url, *args, **kvargs):
        ret = fce(url, *args, **kvargs)
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

base_url = "https://ksp.mff.cuni.cz/api/"

token = ""
token_path = os.path.join(os.path.expanduser("~"), ".config", ".token")

fileExists(token_path)
with open(token_path, "r") as f:
	token = f.readline().strip()

headers = {"Authorization": f"Bearer {token}"}


def getStatus(task: str) -> Response:
    return requests.get(base_url + "tasks/status", headers=headers,
        params = {"task" : task})
    

def getTest(task: str, subtask: Union[int, str], generate: bool = True) -> Response:
    return requests.post(base_url + "tasks/input", 
    params = {
        "task" : task, 
        "subtask" : subtask, 
        "generate" : ("true" if generate else "false")
    }, headers=headers)
        

def submit(task: str, subtask: Union[int, str], content: AnyStr) -> Response:
    newHeaders = headers
    newHeaders['Content-Type'] = 'text/plain'
    return requests.post(base_url + "tasks/submit",
	    data = content, headers=newHeaders, 
        params = { "task" : task, "subtask" : subtask})


def generate(task: str, subtask: Union[int, str]) -> Response:
    return requests.post(base_url + "tasks/generate",
        headers=headers,
        params = { "task" : task, "subtask" : subtask})


if len(sys.argv) == 1 or sys.argv[1] not in ["list", "status", "submit", "downloadnew", "run"]:
    print("""vypsat všechny úlohy možné k odevzdání - list
vypsat stav úlohy - status <úloha>
odeslat odpověď - submit <úloha> <číslo testu> <cesta k souboru>
vygenerovat a stáhnout testovací vstup - downloadnew <úloha> <číslo testu>
spustit tvoje řešení na všech testovacích vstupech - run <úloha> <argumenty jak spustit zdoják>
""")
    sys.exit(0)
    
elif sys.argv[1] == "list":
    r = requests.get(base_url + 'tasks/list', headers=headers)
    print(r.json())
    
elif sys.argv[1] == "status":
    if len(sys.argv) == 2:
        print("""Nedostatečný počet argumentů
status <úloha>
např: python3 ksp-klient.py status 32-Z4-1""")
        sys.exit(0)
        
    r = getStatus(sys.argv[2])
    print(r.json())

elif sys.argv[1] == "submit":
    if len(sys.argv) < 5:
        print("""Nedostatečný počet argumentů
submit <úloha> <číslo testu> <cesta k souboru>
např: python3 ksp-klient.py submit 32-Z4-1 1 01.out""")
        sys.exit(0)
        
    headers['Content-Type'] = 'text/plain'
    user_output = ""
    file_name = sys.argv[4]

    fileExists(file_name)
    with open(file_name, "r") as f:
        user_output = f.read()
    r = submit(sys.argv[2], sys.argv[3], user_output)
    print(r.text)

elif sys.argv[1] == "downloadnew":
    if len(sys.argv) < 4:
        print("""Nedostatečný počet argumentů
downloadnew <úloha> <číslo testu>
např: python3 ksp-klient.py downloadnew 32-Z4-1 1""")
        sys.exit(0)
        
    r = getTest(sys.argv[2], sys.argv[3])
    print(r.text)
    
elif sys.argv[1] == "run":
    if len(sys.argv) < 4:
        print("""Nedostatečný počet argumentů
run <úloha> <argumenty jak spustit zdoják>
např. python3 ksp-klient.py run 32-Z4-1 python3 solver.py""")
        sys.exit(0)

    sol_args = sys.argv[3:]
    task = sys.argv[2]
    numberSubtasks = len(getStatus(task).json()["subtasks"])
    for subtask in range(1, numberSubtasks+1):
        _input = getTest(task, subtask).text
        output = subprocess.check_output(sol_args, input=_input.encode())
        response = submit(task, subtask, output.decode())
        print(f"Tvá odpověď na podúkol {subtask} je {response.json()['verdict']}")
        
