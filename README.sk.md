# claude-in-chrome-unblock

[English](README.md) · **Slovensky**

Vypne v rozšírení **Claude in Chrome** blokovanie stránok podľa safety
kategórií. Napríklad `tinder.com` sa potom normálne načíta namiesto hlášky
*„The content on this page isn't available when Claude is active for safety
reasons."*

## Čo to vlastne robí

Rozšírenie pre každú URL volá
`POST https://api.anthropic.com/api/web/url_hash_check/browser_extension` a
podľa vrátenej kategórie sa rozhoduje:

| kategória | správanie |
|---|---|
| `category0` | bezpečné, nič sa nedeje |
| `category1` | **blokované** – tab sa presmeruje na `blocked.html` |
| `category2` | blokované rovnako ako 1 |
| `category3` | povoľovací prompt pred prístupom |
| `category4` | copyright notice („mám právo na obsah") |
| `category_org_blocked`, `category_unknown_error` | blokované |

Patch obalí `getCategory()` a vráti `category0` pre všetko okrem
`category3`/`category4`, ktoré necháva tak — tam za blokovanie nejde, len o
prompt a notice.

Zdroj blokovania je čisto klientský JS, takže sa to dá vypnúť bez servera:

```js
static async getCategory(e){
  if(!C.DISABLE_BLOCKLIST) return C.getRawCategory(e);
  const t = C.getRawCategory(e), n = C.unblockCategory;
  return t.then(n, n);
}
```

Kategórie sa aj tak načítavajú (kvôli `category3`/`category4` správaniu), len
sa premenujú na `category0`.

## Detekcia agenta (voliteľné, nezávislé od bloklistu)

Vypnutie bloklistu spraví, že `tinder.com` sa načíta, ale Tinder Clauda v Chrome
rozpozná aj sám a ukáže *„Automated tools aren't allowed"*. S Anthropicovým
bloklistom to nemá nič spoločné — prejaví sa aj s čistou kópiou zo storu.

Tinder má chunk `agent-signals`, ktorý fingerprintuje stránku a pri náleze
markeru, ktorý Claude v Chrome do stránky pridáva, pošle `likelyAgent: true`
v hlavičke `X-Agent-Signals`. Pre Clauda je to pravidlo `claude_chrome_artifact`:
`div` v `body` s **nulou atribútov**, bez detí, s closed shadow rootom
a `display: contents`.

Rozšírenie atribúty toho divu strieka pri každej aktualizácii, preto patch pridá
jeden atribút hneď za tú slučku:

```js
for(const t of e.getAttributeNames())e.removeAttribute(t);
e.setAttribute("data-unblock","1");
```

Jeden atribút stačí, aby pravidlo nesedelo. Glow border, stop tlačidlo, kurzor
ani tag tým nepadajú — sú v closed shadow roote, kam Tinderov `getElementById`
aj tak nevidí.

Patch je možné preskočiť: Tinder potom okno ukáže pri načítaní, zavrieš ho cez
„Got it" a zvyšok sa správa rovnako.

## Inštalácia

Predpoklady: Linux alebo macOS s Chrome/Chromium a nainštalovaným rozšírením
[Claude in Chrome](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn),
Python 3, Node (kvôli `node --check`).

Najprv zavri Chrome, potom:

```bash
git clone https://github.com/wilderko/claude-in-chrome-unblock.git
cd claude-in-chrome-unblock
./install.sh
```

Potom spusti Chrome. Rozšírenie sa načíta z odblokovanej kópie.

### Prečo unpacked a nie prepis súborov

Priama úprava súborov v priečinku z obchodu vyzerá, že funguje — do prvého
reštartu. Chrome pri štarte overí `_metadata` hashe, kópiu označí za
`Corrupted extension ... reinstalled` a stiahne si čistú verziu.

Skript preto rozšírenie skopíruje mimo `Extensions/` a v `Preferences` ho
prepne na `location: 4` (unpacked), kde sa hashe neoverujú. Manifest si
necháva pôvodný `key`, takže ID rozšírenia aj prihlásenie na claude.ai
zostávajú rovnaké a nič sa nepretrhne.

## Použitie

Po inštalácii netreba nič — rozšírenie sa správa normálne, len neblokuje.
Side panel, klikacie nástroje aj čítanie stránok fungujú ďalej.

Overenie, že to sedí: otvor `chrome://extensions` a skontroluj, že Claude beží
z priečinka `ClaudeExtUnblocked` a nie z obchodu.

`check.py` overí všetko vyššie z príkazového riadku: exit `0` v poriadku,
`1` pokazené, `2` žiadny profil Chrome. `--fix` opraví pri zavretom Chrome. Ak
Tinder automatizuješ z Claude Code, dá sa zapojiť do `SessionStart` hooku:

```json
{"hooks":{"SessionStart":[{"hooks":[{"type":"command",
 "command":"python3 /cesta/k/check.py >/dev/null || echo 'treba preinštalovať'"}]}]}}
```

## Aktualizácie rozšírenia

Toto sa neaktualizuje samo. Keď v obchode vyjde nová verzia, spusti:

```bash
./install.sh          # pri zatvorenom Chrome
```

Skript si novú verziu z obchodu zoberie automaticky. Ak v obchode nič nie je,
použije priložený snapshot `extension/`.

Keďže patch stojí na minifikovaných názvoch (`mcpPermissions-*.js`) aj na
konkrétnom tvare kódu v `agent-visual-indicator.js-*.js`, pri výraznej zmene
buildu sa môže stať, že skript napíše `don't recognise the structure`,
`getCategory not found` alebo `agent marker anchor not found`. Vtedy treba
pozrieť dané súbory a doladiť `patch_js()` / `patch_agent_marker()` — logika je
vždy rovnaká, mení sa len ukotvenie.

## Odinštalovanie

```bash
./uninstall.sh        # pri zatvorenom Chrome
```

Vráti `Preferences` na store verziu a kópiu z `ClaudeExtUnblocked` zmaže.
Chrome si po spustení čistú verziu z obchodu sťahuje sám — po prvom štarte
môže pár sekúnd trvať, kým sa rozšírenie objaví. Záloha `Preferences` zostáva
ako `Preferences.unblock.bak`.

## Obmedzenia

- **`category_org_blocked`** — blokácia z politiky firemného účtu ide cez
  `isUrlBlockedByManagedPolicy()` a ostáva. (Dá sa doplniť rovnakým spôsobom.)
- **Developer mode** — unpacked inštalácia ho má zapnutý, Chrome pri štarte
  zobrazí bublinu „Turn off developer mode". Dá sa ignorovať.
- **Kód Anthropicu** — v repo je ich minifikovaný build, `extension/` je len
  kópia pre prípad, že z obchodu nič nepríde.
- Overené na Claude in Chrome **1.0.106**, Linux, flatpak aj natívny profil.

## Súbory

| súbor | čo to je |
|---|---|
| `install.sh` / `uninstall.sh` | obal, ktorý zastaví, ak beží Chrome |
| `patch.py` | hľadanie profilov, patch bloklistu aj markeru, prepnutie `Preferences`, `--revert` |
| `check.py` | overí inštaláciu a patche, `--fix` opraví pri zavretom Chrome |
| `extension/` | snapshot rozšírenia 1.0.106 s aplikovaným patchom |

## Licencia

Kód Anthropicu v `extension/` patrí Anthropicu. Skripty v tomto repe sú MIT.
