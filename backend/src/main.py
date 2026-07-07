import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from src.api.auth import router as auth_router
from src.api.strava import router as strava_router
from src.api.plans import router as plans_router
from src.api.calendar import router as calendar_router
from src.api.sessions import router as sessions_router
from src.api.settings import router as settings_router

app = FastAPI(
    title="AI-Powered Running Coach",
    description="A personalized running training plan generator and calendar",
    version="1.0.0"
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(strava_router, prefix="/api/v1")
app.include_router(plans_router, prefix="/api/v1")
app.include_router(calendar_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# CORS middleware configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "Running Coach API is healthy"}

# Fallback path to frontend static assets
frontend_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return JSONResponse(status_code=404, content={"message": "Frontend static assets directory not found"})
