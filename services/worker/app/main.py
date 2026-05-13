from fastapi import FastAPI

app = FastAPI(title="RealtyOps Worker", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "worker"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "RealtyOps Worker bootstrap"}
