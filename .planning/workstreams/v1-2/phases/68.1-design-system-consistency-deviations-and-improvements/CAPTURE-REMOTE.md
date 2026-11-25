# Capturing the deployed companion (read-only)

`capture_pages.py --remote` visits every companion page on the deployed site
with your own session and writes a JSON matrix plus a few screenshots. It only
issues GET requests and opens dialogs without pressing any confirm or submit
control; any non-GET request the browser attempts is aborted.

## Prerequisites

- Python 3 and Node with the Playwright package (the script drives the system
  Chrome or Chromium; nothing is installed for you).
- Google Chrome or Chromium on the machine. On macOS the script finds Chrome,
  Chromium, Brave and Edge in /Applications; set `SKYPANE_CAPTURE_CHROME` to a
  browser binary to override.
- macOS setup, once: `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install -g playwright`
  (the package only; the script drives your own Chrome). The script finds it
  through `npm root -g`; set `SKYPANE_CAPTURE_NODE_PATH` to the node_modules
  directory holding `playwright` if it lives elsewhere.
- A signed-in administrator session on the deployed site (admin pages redirect
  or return 403 for other users; that is recorded, not treated as an error).

## Put your session cookie in a private file

1. Sign in to the site in your browser.
2. Open developer tools, Application (or Storage) tab, Cookies, and copy the
   value of `sp_session`.
3. Create the file yourself, never paste the value into chat:

   ```
   umask 077
   cat > ~/skypane.cookie        # paste the value, press Enter, then Ctrl-D
   chmod 600 ~/skypane.cookie
   ```

The script refuses a cookie file that is readable by group or others.

## Run

```
python3 -I capture_pages.py --remote https://skypane.algernon.is --cookie-file ~/skypane.cookie --out ~/skypane-capture
```

Add `--only home,fleet-list` to limit the pages. Frame ids are discovered from
`/fleet` and `/`; pages whose frame cannot be found are written as
"skipped: no frame id" and listed in the JSON.

## Afterwards

- The output contains real flight, frame and user data. Do not commit it.
- Review it before sharing; send the JSON plus only the screenshots you are
  comfortable sharing.
- Delete the cookie file (`rm ~/skypane.cookie`) and log out of the site so the
  session is revoked.
