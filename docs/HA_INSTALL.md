# Home Assistant install & troubleshooting

## Step 0: Clear bad repository entries

Your logs show `git@github.com:...` and pasted error text — the store still has **invalid** URLs.

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**
2. **Remove every line** that is not exactly:
   ```text
   https://github.com/niclashellberg/ordo-ems
   ```
3. Remove any line containing `git@`, `api.github.com`, or `Failed to to call`
4. Add **only** this URL (copy/paste, no spaces):
   ```text
   https://github.com/niclashellberg/ordo-ems
   ```
5. **Check for updates**

Do **not** paste SSH URLs or error messages into the repository field.

---

## Step 1: Remove broken add-on install

If install failed before:

1. **Settings → Add-ons → Kremla Energy MPC**
2. If present: **Stop → Uninstall**
3. **Settings → Add-ons → Add-on store → ⋮ → Check for updates**
4. Install **Kremla Energy MPC** version **0.1.4** or newer (builds on Pi, no HiGHS compile)

First install: about **5–10 minutes** on Pi 5 (pip wheels only).

**v0.1.4** fixes a broken `config/example.yaml` symlink that caused Docker `COPY` to fail during build.

---

## Step 2: Verify GitHub from HA (you had 200 — good)

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://api.github.com/repos/niclashellberg/ordo-ems
```

---

## Option B: Local add-on (no GitHub store)

1. Copy folder `kremla_energy_mpc` from the repo to:
   ```text
   /addons/local/kremla_energy_mpc/
   ```
2. **Check for updates** → install under **Local add-ons**

---

## Optional: pre-built image (GHCR)

Version **0.1.3** builds on the Pi by default. To use a pre-built image later:

1. Run GitHub Action **Publish add-on image**
2. **Packages → kremla-energy-mpc → Public**
3. Add to `config.yaml`: `image: ghcr.io/niclashellberg/kremla-energy-mpc`

Until the package is **public**, HA cannot pull it (you get install/build errors).

---

## Configuration on the server

| What | Where |
|------|--------|
| UI options | Add-on → Configuration tab |
| Entity IDs, plant | `/data/options.yaml` in the container — template: `config/example.yaml` |

```bash
docker ps | grep kremla
docker exec -it <container_name> sh
cat /data/options.yaml
```

---

## If install still fails

**Settings → System → Logs → Supervisor** — look for `kremla_energy_mpc` and copy lines containing:

- `pip install`
- `COPY failed`
- `No space left`
- `manifest unknown`

Common fixes: free disk space on the Pi, uninstall old add-on, **Rebuild** after updating to **0.1.3**.
