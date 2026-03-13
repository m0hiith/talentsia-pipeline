from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import stories, agents, reels, schedule
from db.database import init_db

app = FastAPI(
    title="Talentsia Pipeline",
    description="AI-powered Instagram content pipeline — 6 agents, 9 open-source models, 100% self-hosted",
    version="2.0.0",
)

# CORS — allow dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(stories.router)
app.include_router(agents.router)
app.include_router(reels.router)
app.include_router(schedule.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root():
    from db.database import get_table_counts
    counts = get_table_counts()
    return {
        "name": "Talentsia Pipeline",
        "version": "2.0.0",
        "tagline": "Instagram Content AI · 6 Agents · 9 Models · 100% Open Source",
        "status": "running",
        "stats": counts,
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}
