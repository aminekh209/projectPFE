from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import tempfile
import os
import shutil
import json
import zipfile
from datetime import datetime
from service.action_detector import ActionDetector
from service.file_scanner import FileScanner
from service.report_generator import ReportGenerator
from database import get_db # Adaptez l'import selon votre projet
from Schemas.patch_schema import PatchCreate
from service.patch_service import PatchService
from Models import Client, Environment
from typing import Optional
from Models.servers import Server
router = APIRouter(prefix="/patches", tags=["patches"])


@router.get("/servers")
def get_all_servers(db: Session = Depends(get_db)):
    # On renvoie uniquement les serveurs actifs
    return db.query(Server).filter(Server.is_active == True).all()
@router.get("/clients")
def get_clients(db: Session = Depends(get_db)):
    """Récupère tous les clients de la base de données"""
    clients = db.query(Client).all()
    # On renvoie l'id et le nom pour remplir la liste déroulante React
    return [{"id": c.id, "nom": c.name} for c in clients]

@router.get("/environments/{client_id}")
def get_environments_by_client(client_id: int, db: Session = Depends(get_db)):
    """Récupère les environnements spécifiques à un client"""
    envs = db.query(Environment).filter(Environment.client_id == client_id).all()
    return [{"id": e.id, "nom": e.name, "type": e.env_type} for e in envs]

@router.post("/analyser")
async def analyser_patch(file: UploadFile = File(...)):
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un ZIP")
    
    try:
        content = await file.read()
        
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            
            structure = FileScanner.scanner_fichiers_zip(tmp_path)
            actions = await ActionDetector.detecter_actions_dans_zip(content)
            
            return {
                "nom_fichier": file.filename,
                "taille": len(content),
                "date_analyse": datetime.now().isoformat(),
                "structure": structure,
                "actions": actions
            }
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse: {str(e)}")

@router.post("/preview")
async def preview_patch(file: UploadFile = File(...)):
   
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un ZIP")
    
    try:
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Appels aux services uniquement
            structure = FileScanner.scanner_fichiers_zip(tmp_path)
            actions = await ActionDetector.detecter_actions_dans_zip(content)
            
            return {
                "nom_fichier": file.filename,
                "taille": len(content),
                "structure": structure,
                "actions": actions
            }
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prévisualisation: {str(e)}")

@router.post("/valider")
async def valider_patch(file: UploadFile = File(...)):
    """
    Validation du patch
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un ZIP")
    
    try:
        content = await file.read()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Appels aux services uniquement
            structure = FileScanner.scanner_fichiers_zip(tmp_path)
            actions = await ActionDetector.detecter_actions_dans_zip(content)
            
            return {
                "nom_fichier": file.filename,
                "structure": structure,
                "actions": actions
            }
        finally:
            os.unlink(tmp_path)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la validation: {str(e)}")

@router.post("/rapport")
async def generer_rapport(file: UploadFile = File(...)):
    """
    Génération d'un rapport PDF détaillé
    """
    # Validation du fichier
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un ZIP")
    
    # Lecture du contenu
    content = await file.read()
    
    # Vérification que le fichier n'est pas vide
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Fichier ZIP vide")
    
    # Délégation totale au service
    return await ReportGenerator.generer_rapports(content, file.filename)
            

@router.get("/statistiques")
async def get_statistiques():
    """
    Statistiques sur les types de patches
    """
    try:
        return {
            "types_patches": [
                {"code": "DB", "nom": "Base de données"},
                {"code": "UNIX", "nom": "UNIX/Système"},
                {"code": "WEB", "nom": "Application Web"},
                {"code": "CONFIG", "nom": "Configuration"}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

patch_service_instance = PatchService()    

@router.post("/create")
async def create_patch_endpoint(
    file: UploadFile = File(...),
    patch_data: str = Form(...),
    analysis_data: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # 1. Sauvegarde définitive (Ceci ne s'exécute QUE quand on clique sur Save !)
        os.makedirs("uploads/patches", exist_ok=True)
        file_location = f"uploads/patches/{file.filename}"
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Extraction du ZIP
        nom_dossier = file.filename.replace('.zip', '')
        extraction_path = f"uploads/patches/extracted/{nom_dossier}"
        os.makedirs(extraction_path, exist_ok=True)
        
        with zipfile.ZipFile(file_location, 'r') as zip_ref:
            zip_ref.extractall(extraction_path)

        # 3. Récupération du chemin de base absolu
        base_path = os.path.abspath(extraction_path).replace('\\', '/')

        # 4. Conversion JSON -> Python
        parsed_data = json.loads(patch_data)
        validated_patches = [PatchCreate(**item) for item in parsed_data]
        parsed_analysis = json.loads(analysis_data) if analysis_data else None
        
        print(f"\n DÉBOGAGE : Le serveur a reçu {len(validated_patches)} configuration(s) à sauvegarder !\n")
        
        
        saved_patches = patch_service_instance.save_bulk_patches(
            db=db, 
            patches_data=validated_patches, 
            zip_path=file_location,          
            extracted_path=base_path, 
            analysis_data=parsed_analysis
        )
        
        return {
            "message": "Patches sauvegardés avec succès",
            "count": len(saved_patches),
            "file_path": file_location
        }

    except Exception as e:
        print(f"\n ERREUR D'INSERTION : {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")