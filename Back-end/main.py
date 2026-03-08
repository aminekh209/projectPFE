from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Routers import patch_router
from Models import users, servers, prepatch, patchs, patch_executions, patch_detector, execution_log, client, environment
from database import engine, Base
# Import des routeurs

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs
app.include_router(patch_router)
Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {
        "message": "Bienvenue sur l'API d'analyse de patches",
        "endpoints": {
            "analyser": "/patches/analyser",
            "preview": "/patches/preview",
            "valider": "/patches/valider",
            "rapport": "/patches/rapport",
            "statistiques": "/patches/statistiques"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "services": {
            "action_detector": "disponible",
            "file_scanner": "disponible"
        }
    }