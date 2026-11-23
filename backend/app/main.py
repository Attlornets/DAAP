"""
RouteForge - Multi-Modal Route & Logistics Optimizer Backend Application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

app = FastAPI(
    title="RouteForge API",
    description="Multi-Modal Logistics & Route Optimizer under Time-Dependent Traffic, Capacity, and Delivery Windows (VRPTW).",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "service": "RouteForge API",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "scenarios": "/api/scenarios",
            "routing": "/api/route",
            "benchmark_routing": "/api/benchmark/routing",
            "vrptw_solve": "/api/vrptw/solve",
            "vrptw_benchmark": "/api/vrptw/benchmark"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
