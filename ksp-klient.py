#!/usr/bin/python3
# Klient pro odesílání open-datových úloh pomocí KSP API
# Tento program lze používat a distribuovat pod licencí MIT

import sys
import os
import subprocess
import json
import gettext
import datetime
import enum
import tempfile
import re
from typing import Any, AnyStr, Optional, Union, Iterator, IO

try:
    import requests
    from requests import Response
except ModuleNotFoundError:
    print("Nemáš nainstalovaný modul requests - pip install requests")
    sys.exit(1)


def translate_to_czech(message: str) -> str:
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


gettext.gettext = translate_to_czech

## this must be imported after translation set up
import argparse
from argparse import Namespace


def error(*args, **kvargs):
    def eprint(*args, **kvargs):
        print(*args, file=sys.stderr, **kvargs)

    color_end = ""
    if sys.stderr.isatty():
        eprint("\033[31m", end="")
        color_end = "\033[0m"
    eprint(*args, color_end, **kvargs)


def print_nice_json(json_text):
    print(json.dumps(json_text, indent=4, ensure_ascii=False))


class KSPApiService:
    api_url: str = "https://ksp.mff.cuni.cz/api/"
    token_path: str = os.path.join(os.path.expanduser("~"), ".config", "ksp-api-token")

    def __init__(
        self, api_url: Optional[str] = None,
        token_path: Optional[str] = None,
        verbose: int = 0,
        ca_bundle_path: Optional[str] = None
    ) -> None:
        if api_url is not None:
            self.api_url = api_url
        if token_path is not None:
            self.token_path = token_path
        self.ca_bundle_path = ca_bundle_path

        try:
            with open(self.token_path, "r") as f:
                self.token = f.readline().strip()
        except Exception as e:
            error(f"Chyba při čtení souboru {self.token_path}.")
            error(f"Důvod: {e}")
            error(f"Tento soubor otevíráme, aby jsme mohli použít tvůj API token při komunikaci se serverem.")
            sys.exit(1)

        self.verbose = verbose

    def call_api(
        self,
        operation,  # (url completion, callable fce from request package)
        extra_headers: dict = {},
        extra_params: dict = {},
        data: Optional[AnyStr] = None,
        stream: bool = False
    ) -> Response:
        headers = {"Authorization": f"Bearer {self.token}", **extra_headers}

        url = self.api_url + operation[0]
        http_method = operation[1]

        if self.verbose > 0:
            print(f"Posílám požadavek na: {url}")

        try:
            extra_kvargs: dict = {}
            extra_kvargs['stream'] = stream
            if self.ca_bundle_path is not None:
                extra_kvargs['verify'] = self.ca_bundle_path

            response: Response = http_method(
                url,
                headers=headers,
                params=extra_params,
                data=data,
                **extra_kvargs)
        except (requests.exceptions.ConnectionError, OSError) as e:
            error("Chyba: Nelze se připojit k serveru")

            if self.verbose > 0:
                print(e)

            sys.exit(1)

        if response.status_code != 200:
            if response.headers['content-type'] == 'application/json':
                error(f"Chyba: {response.json()['errorMsg']}")
            else:
                error(f"Chyba: {response.status_code} - {response.reason}")

                if self.verbose > 0:
                    print(response.text)

            sys.exit(1)

        return response

    def call_api_json(
        self,
        operation,  # (url completion, callable fce from request package)
        extra_headers: dict = {},
        extra_params: dict = {},
        data: Optional[AnyStr] = None
    ) -> Any:
        response = self.call_api(
            operation,
            extra_headers=extra_headers,
            extra_params=extra_params,
            data=data)

        if response.headers['content-type'] != 'application/json':
            error("Odpověď od serveru není json!")
            sys.exit(1)
        else:
            json_ret = response.json()

        if self.verbose > 1:
            print_nice_json(json_ret)

        return json_ret

    def get_list(self, training_ground: bool) -> Any:
        param = {}
        if training_ground:
            param['set'] = 'cviciste'
        return self.call_api_json(('tasks/list', requests.get), extra_params=param)

    def get_status(self, task: str) -> Any:
        return self.call_api_json(('tasks/status', requests.get),
            extra_params={"task": task})

    def _test(
        self, task: str, subtask: int,
        generate: bool = True, stream: bool = False
    ) -> Response:
        response = self.call_api(('tasks/input', requests.post),
            extra_params={
                "task": task,
                "subtask": subtask,
                "generate": ("true" if generate else "false")
            },
            stream=stream
        )

        return response

    def get_test(
        self, task: str, subtask: int,
        generate: bool = True
    ) -> bytes:
        response = self._test(task, subtask, generate=generate)
        return response.content

    def get_test_iterator(
        self, task: str, subtask: int,
        generate: bool = True, chunk_size: int = 1024
    ) -> Iterator[bytes]:
        response = self._test(task, subtask, generate=generate, stream=True)
        return response.iter_content(chunk_size=chunk_size)

    def save_test_to_tmp(
        self, task: str, subtask: int,
        generate: bool = True, chunk_size: int = 1024,
        delete_on_close: bool = True
    ) -> IO:
        iterator = self.get_test_iterator(task, subtask, generate=generate, chunk_size=chunk_size)

        sanitized_task = re.sub("[^a-zA-Z0-9_-]", "_", task)
        file = tempfile.NamedTemporaryFile(prefix=f'ksp-input-{sanitized_task}-{subtask}_', suffix='.in',
            delete=delete_on_close)

        if self.verbose > 0:
            print(f"Úplná cesta k temp souboru: {file.name}")

        for chunk in iterator:
            file.write(chunk)

        file.seek(0)
        return file

    def submit(self, task: str, subtask: int, content: Union[str, bytes]) -> Any:
        if isinstance(content, str):
            content = content.encode('utf-8')

        return self.call_api_json(('tasks/submit', requests.post),
            extra_headers={"Content-Type": "text/plain"},
            extra_params={"task": task, "subtask": subtask},
            data=content)

    def generate(self, task: str, subtask: int) -> str:
        response = self.call_api(('tasks/generate', requests.post),
            extra_params={"task": task, "subtask": subtask})
        return response.text


def czech_time(value: Union[float, int], first_form: str, second_form: str, third_form: str) -> str:
    value = round(value)
    if value == 0:
        return ''
    if value == 1:
        return f'{value} {first_form}'
    elif value < 5:
        return f'{value} {second_form}'
    else:
        return f'{value} {third_form}'


def format_time(subtask: dict) -> str:
    if subtask['input_generated']:
        if subtask['input_valid_until'].startswith('9999'):
            return 'stále'

        timedelta = datetime.datetime.fromisoformat(subtask['input_valid_until']) - datetime.datetime.now().astimezone()

        days, hours = divmod(timedelta.total_seconds(), 60*60*24)
        hours, minutes = divmod(hours, 60*60)
        minutes, seconds = divmod(minutes, 60)

        #print(days, hours, minutes, seconds)

        day_str = czech_time(days, 'den', 'dny', 'dnů')
        hour_str = czech_time(hours, 'hodina', 'hodiny', 'hodin')
        minute_str = czech_time(minutes, 'minuta', 'minuty', 'minut')
        second_str = czech_time(seconds, 'sekunda', 'sekundy', 'sekund')
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


def print_table_status(json_text: dict) -> None:
    print(f'Název úlohy: {json_text["name"]}')
    print(f'Získané body: {json_text["points"]}/{json_text["max_points"]}')
    print(f'{"Test":<5}| {"Délka platnosti":<32}| {"Body":<8}| {"Výsledek"}')
    print('-'*60)
    for subtask in json_text['subtasks']:
        points = f'{subtask["points"]}/{subtask["max_points"]}'
        verdict = subtask.get('verdict', "")
        print(f'{subtask["id"]:<5}| {format_time(subtask):<32}| {points:<8}| {verdict}')


def handle_list(arguments: Namespace) -> None:
    print_nice_json(kspApiService.get_list(arguments.cviciste))


def handle_status(arguments: Namespace) -> None:
    print_table_status(kspApiService.get_status(arguments.task))


def handle_submit(arguments: Namespace) -> None:
    user_output = arguments.file.read()

    r = kspApiService.submit(arguments.task, arguments.subtask, user_output)
    print_nice_json(r)


def handle_generate(arguments: Namespace) -> None:
    iterator = kspApiService.get_test_iterator(arguments.task, arguments.subtask,
        chunk_size=arguments.chunk_size)
    for chunk in iterator:
        if arguments.output_file == sys.stdout:
            arguments.output_file.buffer.write(chunk)
        else:
            arguments.output_file.write(chunk)


def try_decode_bytes(data: Union[bytes, bytearray]) -> Optional[str]:
    try:
        return data.decode()
    except UnicodeDecodeError:
        return None


def handle_run(arguments: Namespace) -> None:
    task = arguments.task
    subtasks = arguments.subtasks
    if subtasks is None:
        numberSubtasks = len(kspApiService.get_status(task)["subtasks"])
        subtasks = range(1, numberSubtasks+1)
    for subtask in subtasks:
        file = kspApiService.save_test_to_tmp(task, subtask, delete_on_close=arguments.delete_on_close)
        try:
            output = subprocess.check_output(arguments.sol_args, stdin=file, stderr=subprocess.PIPE)
            resp = kspApiService.submit(task, subtask, output)
            print(f"Podúloha {subtask}: {resp['verdict']} ({resp['points']}/{resp['max_points']}b)")
        except subprocess.CalledProcessError as e:
            # report error
            msg = f"Podúloha {subtask}: Tvoje řešítko spadlo... :("
            if e.returncode:
                msg += f" Program skončil s návratovým kódem {e.returncode}"
            error(msg)

            # if some output was captured, print it
            if e.stdout or e.stderr:
                error("Před ukončením Tvůj program vypsal následující výstup:")
                if e.stdout:
                    error("--------- Standardní výstup Tvého programu ---------")
                    enconded_bytes = try_decode_bytes(e.stdout)
                    params = {} if enconded_bytes == None else {"end": ""}
                    error(enconded_bytes or e.stdout, **params)
                    error("--------- Konec standardního výstupu ---------------")
                if e.stderr:
                    error("--------- Chybový výstup Tvého programu ------------")
                    enconded_bytes = try_decode_bytes(e.stderr)
                    params = {} if enconded_bytes == None else {"end": ""}
                    error(enconded_bytes or e.stderr, **params)
                    error("--------- Konec chybového výstupu ---------")
        finally:
            file.close()


def example_usage(text: str) -> str:
    return f'Příklad použití: {text}'


def int_list(string):
    result = []
    for range_string in string.split(","):
        if "-" in range_string:
            range_parts = range_string.partition("-")
            if "-" in range_parts[2]:
                raise ValueError
            range_start = int(range_parts[0])
            range_end = int(range_parts[2])
            if range_end < range_start:
                raise argparse.ArgumentTypeError("začátek intervalu nemůže být větší než konec")
            value = range(range_start, range_end+1)
            if len(value) > 1000000:
                raise argparse.ArgumentTypeError("interval je moc velký")
            result.extend(value)
        else:
            result.append(int(range_string))
    return result


parser = argparse.ArgumentParser(description='Klient na odevzdávání open-data úloh pomocí KSP API')

parser.add_argument('-v', '--verbose', help='Zobrazit debug log', action='count', default=0)
parser.add_argument('-a', '--api-url', help='Použít jiný server (např. pro testovací účely)')
parser.add_argument('-t', '--token-path', help='Nastavit jinou cestu k souboru s tokenem')
parser.add_argument('-b', '--ca-bundle-path', help='Nastavit cestu k souboru s SSL certifikáty, podle kterých se bude ověřovat https spojení')

subparsers = parser.add_subparsers(help='Vyber jednu z následujících operací:', dest='operation_name')
parser_list = subparsers.add_parser('list', help='Zobrazí všechny úlohy, které lze odevzdávat',
                epilog=example_usage('./ksp-klient.py list'))
parser_list.add_argument('-c', '--cviciste', help='Zobrazit úlohy z cvičiště', action='store_true')

parser_status = subparsers.add_parser('status', help='Zobrazí stav dané úlohy',
                epilog=example_usage('./ksp-klient.py status 32-Z4-1'))
parser_status.add_argument("task", help="kód úlohy")

parser_generate = subparsers.add_parser('generate', help='Vygeneruje a stáhne nový testovací vstup',
                epilog=example_usage('./ksp-klient.py generate 32-Z4-1 1'))
parser_generate.add_argument("task", help="kód úlohy")
parser_generate.add_argument("subtask", help="číslo podúlohy", type=int)
parser_generate.add_argument('--chunk-size', help='Nastaví velikost stahovaného bloku', action='store', type=int, default=1024)
parser_generate.add_argument("output_file", help="Název souboru pro uložení vstupu do souboru. Jinak se vstup vypisuje na terminál.",
                nargs="?", default="-", type=argparse.FileType(mode="wb"))

parser_submit = subparsers.add_parser('submit', help='Odešle odpověd na danou podúlohu',
                epilog=example_usage('./ksp-klient.py submit 32-Z4-1 1 01.out'))
parser_submit.add_argument("task", help="kód úlohy")
parser_submit.add_argument("subtask", help="číslo podúlohy", type=int)
parser_submit.add_argument("file", help="cesta k souboru, který chcete odevzdat", type=argparse.FileType(mode="rb"))

parser_run = subparsers.add_parser('run', help='Spustí Tvůj program na všechny podúlohy dané úlohy',
                epilog=example_usage('./ksp-klient.py run 32-Z4-1 python3 solver.py'))
parser_run.add_argument("task", help="kód úlohy")
parser_run.add_argument("sol_args", nargs="+", help="Tvůj program a případně jeho argumenty")
parser_run.add_argument("-s", "--subtasks", help="Spustí Tvůj program pouze na uvedené podúlohy (seznam čísel a intervalů oddělený čárkami, např. '1,2,4-6')", type=int_list)
parser_run.add_argument("--keep-tmp", help="Vstupy se automaticky nesmažou a zůstanou v temp adresáři",
                dest="delete_on_close", action="store_false")

arguments = parser.parse_args()

kspApiService = KSPApiService(api_url=arguments.api_url,
                              token_path=arguments.token_path,
                              verbose=arguments.verbose,
                              ca_bundle_path=arguments.ca_bundle_path)

operations: dict = {'list': handle_list, 'status': handle_status, 'submit': handle_submit,
                    'generate': handle_generate, 'run': handle_run}

if arguments.operation_name is None:
    parser.print_help()
else:
    operations[arguments.operation_name](arguments)
