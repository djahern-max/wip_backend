from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.api.wip import router as wip_router  # Import from the wip.py file we created
from app.core.config import settings

app = FastAPI(title="WIP Management System")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(wip_router, prefix="/api/v1")  # Add the WIP router


@app.get("/")
def read_root():
    return {"message": "WIP Management System API"}
