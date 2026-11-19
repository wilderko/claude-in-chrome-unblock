# claude-in-chrome-unblock

**English** · [Slovensky](README.sk.md)

Disables the site blocklist in the **Claude in Chrome** extension. Sites such
as `tinder.com` then load normally instead of showing *"The content on this
page isn't available when Claude is active for safety reasons."*

## What it actually does

For every URL the extension calls
`POST https://api.anthropic.com/api/web/url_hash_check/browser_extension` and
decides based on the returned category:

| category | behaviour |
|---|---|
| `category0` | safe, nothing happens |
| `category1` | **blocked** – tab is redirected to `blocked.html` |
| `category2` | blocked, same as 1 |
| `category3` | permission prompt before access |
| `category4` | copyright notice ("I have the right to this content") |
| `category_org_blocked`, `category_unknown_error` | blocked |

The patch wraps `getCategory()` and returns `category0` for everything except
`category3`/`category4`, which it leaves alone — those are not blocks, just a
prompt and a notice.

The blocklist is pure client-side JS, so it can be disabled without a server:

```js
static async getCategory(e){
  if(!C.DISABLE_BLOCKLIST) return C.getRawCategory(e);
  const t = C.getRawCategory(e), n = C.unblockCategory;
  return t.then(n, n);
}
```

Categories are still fetched (to keep the `category3`/`category4` behaviour),
they are only renamed to `category0`.

## Agent detection (optional, separate from the blocklist)

Disabling the blocklist makes `tinder.com` load, but Tinder still recognises
Claude in Chrome on its own and shows *"Automated tools aren't allowed"*. This
is unrelated to Anthropic's blocklist and works with a stock store copy too.

Tinder ships an `agent-signals` chunk that fingerprints the page and sets
`likelyAgent: true` in the `X-Agent-Signals` request header when it finds a
marker Claude in Chrome adds. For Claude the relevant rule is
`claude_chrome_artifact`: a `div` in `body` with **no attributes**, no children,
a closed shadow root and `display: contents`.

The extension strips that div's attributes on every update, so the patch adds
one attribute right after the stripping loop:

```js
for(const t of e.getAttributeNames())e.removeAttribute(t);
e.setAttribute("data-unblock","1");
```

One attribute is enough to miss the rule. The glow border, stop button, cursor
and tab-group pill keep working — they live in the closed shadow root, where
Tinder's `getElementById` cannot see them anyway.

Skipping this patch is safe: Tinder then shows its notice on load, which you
dismiss with "Got it", and everything else behaves the same.

## Installation

Requirements: Linux or macOS with Chrome/Chromium and the
[Claude in Chrome](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn)
extension installed, Python 3, Node (for `node --check`).

Close Chrome first, then:

```bash
git clone https://github.com/wilderko/claude-in-chrome-unblock.git
cd claude-in-chrome-unblock
./install.sh
```

Start Chrome afterwards. The extension loads from the unblocked copy.

### Why an unpacked copy instead of editing files in place

Editing the files in the store directory appears to work — until the first
restart. On startup Chrome verifies the `_metadata` hashes, marks the copy as
`Corrupted extension ... reinstalled` and downloads a clean version.

So the script copies the extension outside `Extensions/` and flips the
`Preferences` entry to `location: 4` (unpacked), where hashes are not checked.
The manifest keeps its original `key`, so the extension ID and the claude.ai
login stay intact and nothing breaks.

## Usage

Nothing to do after installing — the extension behaves normally, it just does
not block. The side panel, click tools and page reading keep working.

To verify it took effect, open `chrome://extensions` and check that Claude runs
from the `ClaudeExtUnblocked` directory rather than from the store.

`check.py` verifies all of the above from the command line: exit `0` healthy,
`1` broken, `2` no Chrome profile. `--fix` repairs when Chrome is closed. Wire
it into a `SessionStart` hook if you automate Tinder from Claude Code:

```json
{"hooks":{"SessionStart":[{"hooks":[{"type":"command",
 "command":"python3 /path/to/check.py >/dev/null || echo 'reinstall needed'"}]}]}}
```

## Extension updates

This does not update by itself. When a new version ships in the store, run:

```bash
./install.sh          # with Chrome closed
```

The script picks the new store version automatically. If the store has nothing,
it falls back to the bundled `extension/` snapshot.

Because the patch relies on minified names (`mcpPermissions-*.js`) and on a
specific code shape in `agent-visual-indicator.js-*.js`, a large build change can
make the script print `don't recognise the structure`, `getCategory not found` or
`agent marker anchor not found`. In that case look at the files and adjust
`patch_js()` / `patch_agent_marker()` — the logic is always the same, only the
anchor changes.

## Uninstalling

```bash
./uninstall.sh        # with Chrome closed
```

Switches `Preferences` back to the store version and deletes the
`ClaudeExtUnblocked` copy. Chrome downloads a clean version on its own after
startup — it may take a few seconds on first launch before the extension
reappears. The `Preferences` backup is kept as `Preferences.unblock.bak`.

## Limitations

- **`category_org_blocked`** — blocks from an organisation's account policy go
  through `isUrlBlockedByManagedPolicy()` and remain. (Can be patched the same
  way.)
- **Developer mode** — unpacked installs require it; Chrome shows a "Turn off
  developer mode" bubble on startup. Safe to ignore.
- **Anthropic's code** — the repo carries their minified build; `extension/` is
  only a fallback for when the store delivers nothing.
- Tested on Claude in Chrome **1.0.106**, Linux, both flatpak and native
  profiles.

## Files

| file | what it is |
|---|---|
| `install.sh` / `uninstall.sh` | wrappers that stop early if Chrome is running |
| `patch.py` | profile discovery, blocklist and marker patching, `Preferences` switch, `--revert` |
| `check.py` | verifies the install and patch, `--fix` repairs with Chrome closed |
| `extension/` | snapshot of 1.0.106 with the patch applied |

## Licence

The Anthropic code in `extension/` belongs to Anthropic. The scripts in this
repo are MIT.
