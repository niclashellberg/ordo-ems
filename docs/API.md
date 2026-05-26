# HTTP API (Claude / automations)

The add-on listens on port **8765** (ingress enabled). Use for explanations and
overrides — never for direct hardware setpoints.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/api/v1/context` | Last solve + horizon JSON for Claude |
| POST | `/api/v1/explain` | Natural-language explanation (Anthropic if key set) |
| POST | `/api/v1/overrides` | Add structured override |
| POST | `/api/v1/overrides/sauna` | Queue ~10 kWh sauna `extra_load` steps |
| DELETE | `/api/v1/overrides` | Clear pending overrides |
| POST | `/api/v1/parse-override` | NL → JSON override (requires API key) |

## Example: explain last plan

```bash
curl -s http://homeassistant.local:8123/api/hassio_ingress/<addon>//api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{"question": "Why is the car charging now?"}'
```

Or from LAN (if port exposed):

```bash
curl -s http://<pi>:8765/api/v1/explain -d '{}'
```

## Example: sauna tonight (step index from context)

```bash
curl -X POST http://<pi>:8765/api/v1/overrides/sauna \
  -H "Content-Type: application/json" \
  -d '{"start_step": 52, "energy_wh": 10000, "power_w": 6000}'
```

## Example: car deadline override (manual)

```json
POST /api/v1/overrides
{
  "override": {
    "kind": "car_deadline",
    "target_wh": 90000,
    "deadline_step": 64,
    "hard": true
  }
}
```

Set `ANTHROPIC_API_KEY` in the add-on options or environment for Claude-backed
`/api/v1/explain` and `/api/v1/parse-override`. Without a key, `/explain` returns
a deterministic template from the solve result.
