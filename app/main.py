from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, users, contracts, contract_intelligence


app = FastAPI(title=settings.app_name, debug=settings.debug)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(contracts.router, prefix="/contracts", tags=["contracts"])
app.include_router(
    contract_intelligence.router, prefix="/contract-intelligence", tags=["intelligence"]
)


@app.get("/")
async def root():
    return {"message": "WIP Backend API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
