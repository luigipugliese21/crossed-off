# crossed off.

A stationery-desk to-do book in one HTML file. Open `index.html` directly and it saves to that browser,
or run the little sync server so your computer and iPhone share one notebook.

## Use it on your iPhone (Tailscale + Safari)

1. **Bring your current lists along.** In the copy you use now, click **save a copy** (footer).
   You get `crossed-off-YYYY-MM-DD.json` in Downloads.
2. **Start the server** on your computer (Python 3, nothing to install):
   ```sh
   python3 server.py --seed ~/Downloads/crossed-off-YYYY-MM-DD.json
   ```
   Next time just run `python3 server.py`. Your notebook lives in `data/state.json` (not committed).
3. **On the iPhone**, with Tailscale connected, open Safari at
   `http://<computer-name>:8787` (MagicDNS name, or the `100.x.y.z` address from the Tailscale app).
4. **Share → Add to Home Screen.** It opens full-screen with its own icon, like an app.

Also open `http://localhost:8787` on the computer from now on (instead of the file), so both devices stay in sync.
The footer shows `synced ✓`, `syncing…` or `offline — will sync later`.

- Changes sync within a second; the other device picks them up when you switch back to it (or within 15s).
- If both devices edit while one is offline, the first to reach the server wins and the other shows a note.
- Optional HTTPS: `tailscale serve --bg 8787` then use `https://<computer-name>.<tailnet>.ts.net`.
