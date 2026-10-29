# Slevy – agregátor cen

Jednoduchá stránka pro seniory: napíšete, co chcete koupit, a uvidíte, ve kterém obchodě v okolí je to teď v akci, za kolik a do kdy. Pilot pokrývá Náchodsko.

## Jak to funguje

Každé ráno se automaticky spustí stahování (GitHub Actions, soubor `.github/workflows/denne-akce.yml`):

1. **Kaufland** – akce přímo z webu Kauflandu, včetně ceny s kartou a seznamu zboží platného v náchodské prodejně.
2. **Penny** – výběr akcí z webu Penny a seznam prodejen se souřadnicemi. Zbytek letáku zatím chybí.
3. **Lidl** – potraviny jsou jen v letáku. Stránky letáku čte model Claude. Funguje až po vložení klíče `ANTHROPIC_API_KEY` (viz níže).
4. **Albert** – zatím chybí.

Každá akce se přiřadí k jednomu z 25 základních produktů (`products.json`) a projde kontrolami (cena za kilo v rozumném rozsahu, akční cena nižší než původní, čitelné balení). Co kontrolou neprojde, se na stránce neukáže a zapíše se do `data/ke-kontrole.json`.

Výsledek je v `docs/data/akce.json` a stránka `docs/index.html` ho jen čte.

## Soubory

| Soubor | K čemu je |
| --- | --- |
| `config.json` | oblast (střed, okruh), obce na výběr, řetězce |
| `products.json` | 25 produktů a pravidla, co do nich patří a co ne |
| `branches_static.json` | prodejny Lidlu a Albertu (Kaufland a Penny se stahují samy) |
| `scraper/` | stahování a zpracování |
| `docs/` | stránka pro veřejnost |
| `data/stav.json` | jak dopadl poslední běh u každého zdroje |
| `data/ke-kontrole.json` | akce, které neprošly kontrolou |

## Spuštění na vlastním počítači

```
python -m unittest discover tests
python -m scraper.run
```

Stačí Python 3.11 nebo novější, žádné další balíčky.

## Klíč pro čtení letáků

V repozitáři: **Settings → Secrets and variables → Actions → New repository secret**, název `ANTHROPIC_API_KEY`, hodnota = klíč z console.anthropic.com. Klíč nikdo neuvidí a do kódu se nedostane.

## Známá omezení

- Ceny Kauflandu se berou z hlavní verze letáku. Které zboží v Náchodě platí, víme přesně, ale cena se může regionálně lišit.
- Penny dává na web jen část letáku (asi 30 položek týdně).
- Data jsou z veřejných webů obchodů a u každé akce je odkaz na zdroj. Před veřejným spuštěním je potřeba právní posouzení (viz plán projektu).
