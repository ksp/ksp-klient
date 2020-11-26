# ksp-klient

Je konzolová aplikace pro odesílání open-datových úloh.

## Před spuštěním

Pro spuštění aplikace potřebuješ mít nainstalované:
* Python verze minimálně 3.6
* pythoní balíček requests - `pip install requests` (případně z balíčkovacího
  systému vaší linuxové distribuce)

Dále si potřebuješ vygenerovat KSP API token [zde](https://ksp.mff.cuni.cz/auth/apitoken.cgi) (po přihlášení)
a uložit ho si souboru s názvem `~/.config/ksp-api-token`. Pokud na Tvém počítači pracuje víc lidí,
dej pozor, aby neměli právo tento soubor číst.

## První spuštění

* Pokud jsi na Unix-like systému, tak program spustíš jednoduše
  příkazem `./ksp-klient.py`.
* Pokud program spouštíš na Windows, tak třeba takto:
  `python3 ksp-klient.py`.

## Použití

Klient poskytuje základní funkce pro řešení open-datových úloh
a nahrazuje webové rozhraní Odevzdávátka.

* `list` - vypíše všechny úlohy, které lze aktuálně odevzdávat,
  pokud před list přidáte přepínač -c, tak se vám zobrazí všechny
  úlohy, které lze odevzdávat do Cvičiště.
    * použití: `./ksp-klient.py list` nebo `./ksp-klient.py -c list`
* `status` - vypíše stav dané úlohy - název úlohy, kolik jsi dostal bodů,
  poté následují informace o jednotlivých podúlohách.
    * použití: `./ksp-klient.py status <úloha> `
    * příklad: `./ksp-klient.py status 32-Z4-1`
* `generate` - vygeneruje a stáhne nový vstup pro danou úlohu
  a podúlohu. Stažený soubor vypíše na svůj standardní výstup,
  který si můžeš přesměrovat do souboru.
    * použití: `./ksp-klient.py generate <úloha> <podúloha>`
    * příklad: `./ksp-klient.py generate 32-Z4-1 1`
    * s přesměrováním: `./ksp-klient.py generate 32-Z4-1 1 >01.in`
* `submit` - odešle výstup pro určenou podúlohu na server KSP, načež vypíše,
  jestli byla Tvá odpověď správná a kolik bodů jsi dostal.
    * U příkazu specifikuješ, jakou úlohu a podúlohu chceš odevzdat
      a cestu k souboru s odpovědí.
    * použití: `./ksp-klient.py submit <úloha> <podúloha> <cesta k soubory>`
    * příklad: `./ksp-klient.py submit 32-Z4-1 1 01.out`
* `run` - pro každou podúlohu dané úlohy stáhne vstup, spustí s ním Tvůj program
  a výstup programu odešle jako odpověď.
    * použití: `./ksp-klient.py run <úloha> <argumenty, jak spustit tvůj program>`
    * příklad pro Python: `./ksp-klient.py run 32-Z4-1 python3 program.py`
    * příklad pro spustitelný program (třeba přeložené C++): `./ksp-klient.py run 32-Z4-1 ./program`
    * příklad pro Javu: `./ksp-klient.py run 32-Z4-1 java program` (kde `program` je výstup
      překladače `javac program.java`)
