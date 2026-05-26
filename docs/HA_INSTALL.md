# Home Assistant install & troubleshooting

## Add the repository (correct URL)

In **Settings → Add-ons → Add-on store → ⋮ → Repositories**, use **only**:

```text
https://github.com/niclashellberg/ordo-ems
```

| Do not use | Why |
|------------|-----|
| `git@github.com:niclashellberg/ordo-ems.git` | SSH is invalid for the store |
| `https://api.github.com/repos/...` | API URL, not a repository URL |
| `github.com/niclashellberg/ordo-ems` (no `https://`) | Fails validation |

Then **Check for updates** and wait ~30 seconds.

### If you still see `GitHub returned 404`

The repo is public: https://github.com/niclashellberg/ordo-ems

From **SSH & Terminal** on the Home Assistant host, run:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Accept: application/vnd.github+json" \
  -H "User-Agent: HomeAssistant" \
  https://api.github.com/repos/niclashellberg/ordo-ems
```

- **200** — GitHub is reachable; remove the old repository entry in HA, re-add the HTTPS URL above.
- **404** — Wrong name, private repo, or network/DNS blocking `api.github.com` on your LAN.

---

## Install Kremla Energy MPC (v0.1.2+)

Uses a **pre-built image** from GitHub Container Registry (no cvxpy compile on the Pi).

1. Confirm the [Publish add-on image](https://github.com/niclashellberg/ordo-ems/actions/workflows/publish-addon-image.yml) workflow has run successfully on `main`.
2. **GitHub → your profile → Packages → `kremla-energy-mpc` → Package settings → Change visibility → Public** (required once).
3. In HA: install **Kremla Energy MPC** under **Ordo EMS**.

If pull fails with “manifest unknown”, the image is not public yet or the workflow has not finished.

---

## Option B: Local add-on (no GitHub store)

Use this if the add-on store cannot reach GitHub.

1. On your PC, copy the folder `kremla_energy_mpc` from the repo.
2. On HAOS, place it at:
   ```text
   /addons/local/kremla_energy_mpc/
   ```
   (Samba share **addons**, or SSH & Terminal.)
3. **Settings → Add-ons → Add-on store → ⋮ → Check for updates**
4. Install **Kremla Energy MPC** under **Local add-ons**.

Structure:

```text
/addons/local/kremla_energy_mpc/
  config.yaml
  Dockerfile
  run.sh
  requirements.txt
  src/
  config/example.yaml
```

---

## Configuration files on the server

| What | Where on HAOS |
|------|----------------|
| Add-on UI options (Nord Pool, API key, …) | Written by Supervisor to the add-on data volume as `options.json` |
| Full entity / plant YAML | `/data/options.yaml` inside the running add-on container |
| Template | Repo file `config/example.yaml` |

To edit `/data/options.yaml`:

```bash
docker exec -it addon_local_kremla_energy_mpc sh
vi /data/options.yaml
```

(Container name may differ; check **Settings → Add-ons → Kremla Energy MPC → Info**.)

---

## Build errors (Supervisor logs)

**Supervisor 2026.04+** ignores `build.yaml` and no longer sets `BUILD_FROM`. The Dockerfile must use an explicit `FROM` line (fixed in v0.1.2).

If you still **Rebuild** locally instead of using the GHCR image, expect 15–25 minutes on a Pi and enough free disk (~2 GB).
