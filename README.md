# ksp-klient

Je konzolová aplikace pro odesílání opendata úloh.

## Před spuštěním
-----

Pro spuštění aplikace potřebujete mít nainstalovaný
* python s verzí minimálně 3.7
* python balíček requests - `pip install requests`
* python balíček gettext - `pip install gettext`

Dále je potřeba si vygenerovat KSP API token na
této [url](https://ksp.mff.cuni.cz/auth/apitoken.cgi) (po přihlášení)
a uložit ho si souboru s názvem `ksp-api-token` do adresářové struktury
`~/.config/`.

## První spuštění
---

* Pokud jste na Unix-like systému, tak program spustíte jednoduše
pomocí příkazu `./ksp-klient.py`.
* Pokud program spouštíš na Windows, tak program
spuštíš takto: `python3 ksp-klient.py`.

## Použití
---

Klient poskytuje základní funkce pro komunikaci s KSP serverem.
Aplikace poskytuje následující operace:
* `list` - vypíše všechny úlohy, které lze aktuálně odevzdávat,
pokud před list přidáte přepínač -c, tak se vám zobrazí všechny
úlohy, které lze odevzdávat do cvičiště
    * použití: `./ksp-klient.py list` nebo `./ksp-klient.py -c list`
* `status` - vypíše stav dané úlohy - název úlohy, kolik jsi dostal bodů,
poté následují informace o jednotlivých podúloh
    * general použití: `./ksp-klient.py status <úloha> `
    * použití: `./ksp-klient.py status 32-Z4-1`
* `submit` - odešle tvůj soubor, který vygeneroval tvůj program na
server KSP a následně vypíše, jestli byla tvoje odpověď správná
a kolik bodů jsi dostal.
    * U příkazu specifikuješ, jakou úlohu a podúlohu chceš odevzdat
    a cestu k tvému souboru, který chceš odevzdat
    * general použití: `./ksp-klient.py submit <úloha> <podúloha> <cesta k soubory>`
    * použití: `./ksp-klient.py submit 32-Z4-1 1 01.out`
* `generate` - vygeneruje a stáhne nový vstup pro danou úlohu
a podúlohu. Stáhnutý vstup vypíše program na standartní vstup,
který můžeš následně přesměrovat do souboru.
    * general použití: `./ksp-klient.py generate <úloha> <podúloha>`
    * použití: `./ksp-klient.py generate 32-Z4-1 1`
    * použití s přesměrování standartního vstup: `./ksp-klient.py generate 32-Z4-1 1 > 01.in`
* `run` - program pro každou podúlohu u dané úlohy stáhne, spustí tvůj program,
který řeší danou úlohu, a odevzdá zpět na server KSP. Zde bude více ukázek, pro různé
jazyky, protože se spouštějí jinak.
    * general použití: `./ksp-klient.py run <úloha> <argumenty, jak spustit tvůj program>`
    * python: `./ksp-klient.py run 32-Z4-1 python3 program.py`
    * c++, c (vše co generuje binárky), kde a.out je binárka: `./ksp-klient.py run 32-Z4-1 ./a.out`
    * java, kde JavaProgram je výstup `javac JavaProgram.java`: `./ksp-klient.py run 32-Z4-1 java JavaProgram`
