"""HTTP API for Claude / external tools (explanation & overrides)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.config import AppConfig, load_config
from src.loop.controller import EnergyController
from src.overrides.schema import sauna_override, validate_override

logger = logging.getLogger(__name__)

app = FastAPI(title="Kremla Energy MPC", version="0.1.0")
_controller: Optional[EnergyController] = None
_app_config: Optional[AppConfig] = None


@app.on_event("startup")
async def _startup() -> None:
    from pathlib import Path
    import os

    global _app_config
    cfg_path = Path(os.environ.get("CONFIG_PATH", "/data/options.yaml"))
    if not cfg_path.exists():
        cfg_path = Path(__file__).resolve().parents[2] / "config" / "example.yaml"
    _app_config = load_config(cfg_path)
    if token := os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HA_TOKEN"):
        _app_config.homeassistant_token = token
    ctrl = init_controller(_app_config)
    await ctrl.start()


def get_controller() -> EnergyController:
    if _controller is None:
        raise HTTPException(503, "controller not started")
    return _controller


def init_controller(cfg: AppConfig) -> EnergyController:
    global _controller
    _controller = EnergyController(cfg)
    return _controller


class ExplainRequest(BaseModel):
    """Optional payload; if omitted, uses last solve from the live loop."""

    context: Optional[dict[str, Any]] = None
    question: str = "Explain the current energy plan in plain language for the homeowner."


class ExplainResponse(BaseModel):
    explanation: str
    context: dict[str, Any]
    model: str = ""


class OverrideRequest(BaseModel):
    override: dict[str, Any]


class SaunaRequest(BaseModel):
    start_step: int = Field(..., ge=0)
    energy_wh: float = 10_000.0
    power_w: float = 6000.0


class ParseOverrideRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/context")
def get_context() -> dict[str, Any]:
    return get_controller().explain_context()


@app.post("/api/v1/explain", response_model=ExplainResponse)
async def explain(req: ExplainRequest) -> ExplainResponse:
    ctrl = get_controller()
    ctx = req.context or ctrl.explain_context()
    api_key = os.environ.get("ANTHROPIC_API_KEY") or ctrl.cfg.api.anthropic_api_key
    model = ctrl.cfg.api.anthropic_model

    if not api_key:
        return ExplainResponse(
            explanation=_template_explain(ctx),
            context=ctx,
            model="template",
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            system=(
                "You explain home energy MPC schedules. Use only the JSON context. "
                "Mention binding constraints from duals when present. Never suggest "
                "setpoints different from first_step."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"{req.question}\n\n```json\n{json.dumps(ctx, indent=2)}\n```",
                }
            ],
        )
        text = msg.content[0].text if msg.content else ""
        return ExplainResponse(explanation=text, context=ctx, model=model)
    except Exception as e:
        logger.exception("anthropic explain failed")
        return ExplainResponse(
            explanation=f"{_template_explain(ctx)}\n\n(LLM error: {e})",
            context=ctx,
            model="template+fallback",
        )


@app.post("/api/v1/overrides")
def add_override(req: OverrideRequest) -> dict[str, Any]:
    ov = get_controller().add_override(req.override)
    return {"ok": True, "override": ov.__dict__}


@app.post("/api/v1/overrides/sauna")
def add_sauna(req: SaunaRequest) -> dict[str, Any]:
    ctrl = get_controller()
    dt_h = ctrl.cfg.loop.timestep_minutes / 60.0
    ovs = sauna_override(req.start_step, req.energy_wh, dt_h, req.power_w)
    for ov in ovs:
        ctrl.state.pending_overrides.append(ov)
    return {"ok": True, "count": len(ovs)}


@app.delete("/api/v1/overrides")
def clear_overrides() -> dict[str, bool]:
    get_controller().clear_overrides()
    return {"ok": True}


@app.post("/api/v1/parse-override")
async def parse_override(req: ParseOverrideRequest) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(501, "ANTHROPIC_API_KEY required for parse-override")
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=512,
        system=(
            "Parse the user request into ONE JSON override object with fields: "
            "kind (car_deadline|house_reserve|extra_load), target_wh, deadline_step, "
            "start_step, end_step, power_w, hard. Return ONLY valid JSON."
        ),
        messages=[{"role": "user", "content": req.text}],
    )
    raw = msg.content[0].text if msg.content else "{}"
    data = json.loads(raw.strip().strip("`").removeprefix("json"))
    ov = validate_override(data)
    return {"override": ov.__dict__}


def _template_explain(ctx: dict[str, Any]) -> str:
    if not ctx.get("feasible"):
        return "No feasible plan. Check car deadline, sauna timing, or battery reserve overrides."
    fs = ctx.get("first_step", {})
    return (
        f"Plan is feasible (horizon cost {ctx.get('cost', 'n/a'):.2f}). "
        f"Next 15 min: charge house {fs.get('p_hc_w', 0):.0f} W, "
        f"discharge {fs.get('p_hd_w', 0):.0f} W, "
        f"charge car {fs.get('p_car_w', 0):.0f} W, "
        f"grid import {fs.get('p_import_w', 0):.0f} W, "
        f"export {fs.get('p_export_w', 0):.0f} W."
    )
