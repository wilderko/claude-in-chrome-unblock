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

## Extension updates

This does not update by itself. When a new version ships in the store, run:

```bash
./install.sh          # with Chrome closed
```

The script picks the new store version automatically. If the store has nothing,
it falls back to the bundled `extension/` snapshot.

Because the patch relies on minified names (`mcpPermissions-*.js`), a large
build change can make the script print `don't recognise the structure` or
`getCategory not found`. In that case look at the file and adjust `patch_js()` —
the logic is always the same, only the wrapper changes.

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
| `patch.py` | profile discovery, patching, `Preferences` switch, `--revert` |
| `extension/` | snapshot of 1.0.106 with the patch applied |

## Licence

The Anthropic code in `extension/` belongs to Anthropic. The scripts in this
repo are MIT.
