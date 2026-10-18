import os
import sys

# 让 `from core import engine` 可用（api/index.py 位于项目根目录下一层）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core import engine, __version__

app = FastAPI(title="SciCalc Plot Engine", version=__version__)

# 前端与后端可能跨域部署（本地 dev: 5173 ↔ 8000），放开 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvaluateReq(BaseModel):
    expr: str
    angle: str = "rad"


class ValidateReq(BaseModel):
    expr: str


class SampleReq(BaseModel):
    expr: str
    x_min: float
    x_max: float
    steps: int
    angle: str = "rad"


@app.get("/api/health")
def health():
    return {"ok": True, "service": "sci-calc-engine", "version": __version__}


@app.post("/api/evaluate")
def api_evaluate(req: EvaluateReq):
    return engine.evaluate(req.expr, req.angle)


@app.post("/api/validate")
def api_validate(req: ValidateReq):
    return engine.validate(req.expr)


@app.post("/api/sample")
def api_sample(req: SampleReq):
    return engine.sample_function(req.expr, req.x_min, req.x_max, req.steps, req.angle)
