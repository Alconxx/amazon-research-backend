from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import math
import time

# Opcional: Keepa (si decides usarlo)
# pip install keepa
try:
    import keepa
except Exception:
    keepa = None

app = FastAPI(title="Amazon Research API", version="1.0")

# --- CORS: permite que tu web llame a tu API ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "")  # para proteger tu API (simple)
KEEPA_KEY = os.getenv("KEEPA_KEY", "")

class CompetitorIn(BaseModel):
    asin: str = Field(..., min_length=10, max_length=10)
    url: str

class AnalyzeRequest(BaseModel):
    keyword: str = Field(..., min_length=3)
    competitors: List[CompetitorIn] = Field(default_factory=list)

class CompetitorOut(BaseModel):
    asin: str
    url: str
    price: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    bsr: Optional[int] = None
    category: Optional[str] = None
    est_monthly_sales: Optional[int] = None

class AnalyzeResponse(BaseModel):
    keyword: str
    generatedAt: str
    competitors: List[CompetitorOut]
    notes: List[str]
    # Puedes extender aquí con score final, etc.

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# --- Estimación ventas desde BSR ---
# Nota: Amazon no publica fórmula oficial; se usa conversión aproximada dependiente de categoría. [2](https://easyparser.com/blog/amazon-bsr-monthly-sales-estimation)[3](https://sagecalculator.com/amazon-best-sellers-rank-calculator/)
# Implementamos una curva simple tipo potencia por categoría, configurable.
DEFAULT_CURVES = {
    # coeficientes de ejemplo: sales ≈ a * (bsr ** -b)
    # Ajustables por categoría con datos históricos (ideal con Keepa).
    "default": {"a": 80000, "b": 0.75},
    "Home & Kitchen": {"a": 120000, "b": 0.78},
    "Beauty & Personal Care": {"a": 95000, "b": 0.77},
    "Sports & Outdoors": {"a": 90000, "b": 0.76},
}

def estimate_monthly_sales(bsr: int, category: Optional[str]) -> int:
    if not bsr or bsr <= 0:
        return 0
    c = DEFAULT_CURVES.get(category or "", DEFAULT_CURVES["default"])
    a, b = c["a"], c["b"]
    est = a * (bsr ** (-b))
    # piso razonable
    return max(0, int(round(est)))

def require_api_key(api_key_header: str | None):
    if not API_KEY:
        return  # si no configuras API_KEY, queda abierto (no recomendado en prod)
    if api_key_header != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

def keepa_client():
    if not KEEPA_KEY or keepa is None:
        return None
    return keepa.Keepa(KEEPA_KEY)

def fetch_from_keepa(asins: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Devuelve un dict por ASIN con: precio (si disponible), rating, reviews, bsr, category.
    Keepa provee historial de Sales Rank / rating / review count. [4](https://keepa.com/)[5](https://keepaapi.readthedocs.io/en/latest/index.html)
    """
    client = keepa_client()
    if client is None:
        return {}

    products = client.query(asins)  # puede devolver lista en el mismo orden
    out = {}
    for p in products:
        asin = p.get("asin")
        if not asin:
            continue

        # Campos típicos de Keepa (pueden variar por marketplace/config):
        # rating y reviewCount suelen venir en p['stats'] o p['data']; depende del payload.
        stats = p.get("stats", {}) or {}
        out[asin] = {
            "bsr": stats.get("salesRank"),
            "review_count": stats.get("reviewCount"),
            "rating": stats.get("rating"),
            # category puede venir como nombre si haces mapping; aquí dejamos placeholder
            "category": None,
            # precio: Keepa maneja arrays históricos; aquí dejamos None si no lo mapeas aún
            "price": None,
        }
    return out

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, x_api_key: str | None = None):
    require_api_key(x_api_key)

    notes = []
    asins = [c.asin for c in req.competitors][:50]  # límite de seguridad

    data = fetch_from_keepa(asins)
    if not data:
        notes.append("Sin fuente de datos configurada (por ejemplo, KEEPA_KEY). Devolviendo solo estructura.")

    competitors_out: List[CompetitorOut] = []
    for c in req.competitors:
        d = data.get(c.asin, {})
        bsr = d.get("bsr")
        category = d.get("category")
        est_sales = estimate_monthly_sales(bsr, category) if bsr else None

        competitors_out.append(
            CompetitorOut(
                asin=c.asin,
                url=c.url,
                price=d.get("price"),
                rating=d.get("rating"),
                review_count=d.get("review_count"),
                bsr=bsr,
                category=category,
                est_monthly_sales=est_sales,
            )
        )
    # Aquí puedes añadir: score final, promedios, barrera de entrada, etc.
    return AnalyzeResponse(
        keyword=req.keyword,
        generatedAt=now_iso(),
        competitors=competitors_out,
        notes=notes,
    )
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")
``
