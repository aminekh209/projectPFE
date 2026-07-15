from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import extract
from database import get_db
from models import Patch, User, Server, Client, Environment, AuditLog
from service import (
    get_patches_grouped_by_user_and_date,
    get_patches_user_and_date,
    save_bulk_patches,
    FileScanner,
    ActionDetector,
    ReportGenerator,
    delete_patch,
    get_patches_pending_grouped_by_user_and_date,
    get_servers_by_client_and_env
)
from typing import Dict
from schemas import PatchCreate
from utils.auth import get_current_user
import uuid
import io
import re
import asyncio



import os
import tempfile
import json
import aiofiles
from datetime import datetime, timezone
from typing import Optional, Annotated, List
from threading import Lock

import zipfile
import shutil
from pathlib import Path

router = APIRouter(prefix="/patchs", tags=["Patchs"])

ERROR_INVALID_ZIP = "Le fichier doit être un ZIP"

patch_analysis_jobs = {}
patch_analysis_jobs_lock = Lock()


def update_patch_analysis_job(
    job_id: str,
    **values
):
    """
    Met à jour la progression d'une analyse ZIP.
    """

    with patch_analysis_jobs_lock:
        job = patch_analysis_jobs.get(job_id)

        if not job:
            return

        job.update(values)
        job["updated_at"] = (
            datetime.now(timezone.utc).isoformat()
        )


async def _analyse_zip_path(
    zip_path: str,
    original_filename: str,
    deep_scan: bool = True,
    progress_callback=None,
):
    """
    Analyse un ZIP déjà présent sur le disque.

    Cette fonction est utilisée :
    - par l'ancienne route /analyser ;
    - par la nouvelle analyse en arrière-plan.
    """

    sql_zip_path = None

    def emit_progress(
        percent: int,
        step: str,
        message: str,
    ):
        if progress_callback:
            progress_callback(
                percent,
                step,
                message,
            )

    try:
        original_size = os.path.getsize(zip_path)

        emit_progress(
            5,
            "VALIDATING_ZIP",
            "Validating ZIP file...",
        )

        if original_size == 0:
            raise ValueError("Fichier ZIP vide")

        if not zipfile.is_zipfile(zip_path):
            raise ValueError(
                "Fichier ZIP invalide ou corrompu"
            )

        emit_progress(
            10,
            "SCANNING_STRUCTURE",
            "Scanning ZIP structure...",
        )

        structure, sql_zip_path = (
            FileScanner
            .scanner_structure_et_construire_zip_sql(
                zip_path
            )
        )

        emit_progress(
            55,
            "STRUCTURE_SCANNED",
            "ZIP structure scanned successfully.",
        )

        detected_types = (
            FileScanner.detecter_types_depuis_structure(
                structure
            )
        )

        emit_progress(
            65,
            "DETECTING_TYPES",
            "DB, UNIX and WEB types detected.",
        )

        if not deep_scan:
            preview_actions = {
                "types_detectes": detected_types,
                "actions_globales": [],
                "actions_par_fichier": [],
                "fichiers_presents": [],
                "nombre_actions": 0,
                "statistiques_categories": {},
                "scan_details": {
                    "mode": "STRUCTURE_ONLY",
                    "original_zip_size": original_size,
                    "sql_analysis_zip_size": 0,
                    "sql_files_analyzed": 0,
                },
            }

            emit_progress(
                100,
                "DONE",
                "Patch preview completed.",
            )

            return (
                original_size,
                structure,
                preview_actions,
            )

        sql_count = (
            structure
            .get("analyse_sql", {})
            .get("nombre_fichiers_sql", 0)
        )

        emit_progress(
            70,
            "ANALYZING_SQL",
            (
                f"Analyzing {sql_count} SQL "
                f"file(s)..."
            ),
        )

        if sql_count > 0:
            with open(sql_zip_path, "rb") as sql_file:
                sql_content = sql_file.read()

            sql_actions = (
                await ActionDetector
                .detecter_actions_dans_zip(
                    sql_content
                )
            )

            sql_analysis_size = len(sql_content)

        else:
            sql_actions = {
                "types_detectes": [],
                "actions_globales": [],
                "actions_par_fichier": [],
                "fichiers_presents": [],
                "nombre_actions": 0,
                "statistiques_categories": {},
            }

            sql_analysis_size = 0

        emit_progress(
            82,
            "SQL_ANALYZED",
            "SQL analysis completed.",
        )

        deployment_actions = (
            ActionDetector
            .detecter_actions_deploiement_depuis_structure(
                structure
            )
        )

        emit_progress(
            90,
            "DETECTING_DEPLOYMENTS",
            "UNIX and WEB deployments detected.",
        )

        actions = (
            ActionDetector
            .fusionner_resultats_actions(
                sql_actions,
                deployment_actions,
            )
        )

        actions["types_detectes"] = detected_types

        actions["scan_details"] = {
            "mode": (
                "SQL_DEEP_PLUS_STRUCTURAL_DEPLOYMENT"
            ),
            "original_zip_size": original_size,
            "sql_analysis_zip_size": (
                sql_analysis_size
            ),
            "sql_files_analyzed": sql_count,
            "unix_web_content_analyzed": False,
        }

        emit_progress(
            97,
            "BUILDING_RESULT",
            "Building final analysis result...",
        )

        return original_size, structure, actions

    finally:
        if (
            sql_zip_path
            and os.path.exists(sql_zip_path)
        ):
            os.unlink(sql_zip_path)


async def _extract_patch_data(
    file: UploadFile,
    deep_scan: bool = False
):
    """
    Ancienne méthode synchrone conservée pour :
    - /analyser ;
    - /preview ;
    - /valider.
    """

    if (
        not file.filename
        or not file.filename.lower().endswith(".zip")
    ):
        raise HTTPException(
            status_code=400,
            detail=ERROR_INVALID_ZIP,
        )

    tmp_path = None

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".zip"
        )
        os.close(tmp_fd)

        async with aiofiles.open(
            tmp_path,
            "wb"
        ) as tmp_file:

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                await tmp_file.write(chunk)

        return await _analyse_zip_path(
            zip_path=tmp_path,
            original_filename=file.filename,
            deep_scan=deep_scan,
        )

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def run_patch_analysis_background(
    job_id: str,
    tmp_path: str,
    original_filename: str,
):
    """
    Exécute l'analyse dans le threadpool de FastAPI.

    Le scan ZIP ne bloque donc pas les endpoints
    de polling /analyser/status/{job_id}.
    """

    def progress_callback(
        percent: int,
        step: str,
        message: str,
    ):
        update_patch_analysis_job(
            job_id,
            status="IN_PROGRESS",
            progress_percent=percent,
            current_step=step,
            message=message,
        )

    try:
        update_patch_analysis_job(
            job_id,
            status="IN_PROGRESS",
            progress_percent=1,
            current_step="STARTING",
            message="Starting patch analysis...",
            error=None,
        )

        file_size, structure, actions = asyncio.run(
            _analyse_zip_path(
                zip_path=tmp_path,
                original_filename=original_filename,
                deep_scan=True,
                progress_callback=progress_callback,
            )
        )

        result = {
            "nom_fichier": original_filename,
            "taille": file_size,
            "date_analyse": (
                datetime.now(timezone.utc).isoformat()
            ),
            "scan_mode": (
                "sql-deep-structural-deployment"
            ),
            "structure": structure,
            "actions": actions,
        }

        update_patch_analysis_job(
            job_id,
            status="SUCCESS",
            progress_percent=100,
            current_step="DONE",
            message="Patch analysis completed.",
            result=result,
            error=None,
        )

    except Exception as exc:
        update_patch_analysis_job(
            job_id,
            status="FAILED",
            progress_percent=100,
            current_step="FAILED",
            message="Patch analysis failed.",
            result=None,
            error=str(exc),
        )

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@router.post("/analyser/start")
async def start_patch_analysis(
    background_tasks: BackgroundTasks,
    file: Annotated[
        UploadFile,
        File(...)
    ],
):
    """
    Reçoit le ZIP puis démarre son analyse
    dans une tâche séparée.
    """

    if (
        not file.filename
        or not file.filename.lower().endswith(".zip")
    ):
        raise HTTPException(
            status_code=400,
            detail=ERROR_INVALID_ZIP,
        )

    tmp_path = None
    analysis_started = False
    uploaded_size = 0

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(
            suffix=".zip"
        )
        os.close(tmp_fd)

        async with aiofiles.open(
            tmp_path,
            "wb"
        ) as target:

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                uploaded_size += len(chunk)
                await target.write(chunk)

        if uploaded_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Fichier ZIP vide",
            )

        if not zipfile.is_zipfile(tmp_path):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Fichier ZIP invalide ou corrompu"
                ),
            )

        job_id = uuid.uuid4().hex
        now_iso = (
            datetime.now(timezone.utc)
            .isoformat()
        )

        with patch_analysis_jobs_lock:
            patch_analysis_jobs[job_id] = {
                "job_id": job_id,
                "status": "QUEUED",
                "progress_percent": 0,
                "current_step": "QUEUED",
                "message": (
                    "Patch analysis has been queued."
                ),
                "result": None,
                "error": None,
                "filename": file.filename,
                "uploaded_size": uploaded_size,
                "created_at": now_iso,
                "updated_at": now_iso,
            }

        background_tasks.add_task(
            run_patch_analysis_background,
            job_id,
            tmp_path,
            file.filename,
        )

        analysis_started = True

        return {
            "job_id": job_id,
            "status": "QUEUED",
            "uploaded_size": uploaded_size,
            "message": (
                "ZIP uploaded. Patch analysis started."
            ),
        }

    finally:
        await file.close()

        if (
            not analysis_started
            and tmp_path
            and os.path.exists(tmp_path)
        ):
            os.unlink(tmp_path)

@router.get("/analyser/status/{job_id}")
def get_patch_analysis_status(
    job_id: str
):
    with patch_analysis_jobs_lock:
        job = patch_analysis_jobs.get(job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Patch analysis job not found",
            )

        return dict(job)
    




@router.get("/all")
def list_patchs(db: Annotated[Session, Depends(get_db)]):
    return db.query(Patch).all()


@router.get("/users-patches")
def get_patches_users(db: Annotated[Session, Depends(get_db)]):
    return get_patches_user_and_date(db)

@router.get("/pending-patches")
def get_patches_pending(current_user: Annotated[User, Depends(get_current_user)],db: Annotated[Session, Depends(get_db)]):
    return get_patches_pending_grouped_by_user_and_date(current_user.id,db)


@router.get("/user-patches")
def get_patches_user(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    return get_patches_grouped_by_user_and_date(current_user.id, db)


@router.get("/servers")
def get_all_servers(db: Annotated[Session, Depends(get_db)]):
    return db.query(Server).all()


@router.get("/clients")
def get_clients(db: Annotated[Session, Depends(get_db)]):
    clients = db.query(Client).all()
    return [{"id": c.id, "nom": c.name} for c in clients]



@router.post("/analyser")
async def analyser_patch(file: Annotated[UploadFile, File(...)]):
    try:
        file_size, structure, actions = await _extract_patch_data(
            file,
            deep_scan=True
        )
        return {
            "nom_fichier": file.filename,
            "taille": file_size,
            "date_analyse": datetime.now().isoformat(),
            "scan_mode": "sql-deep-structural-deployment",
            "structure": structure,
            "actions": actions
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
async def preview_patch(
    file: Annotated[UploadFile, File(...)]
):
    try:
        file_size, structure, actions = (
            await _extract_patch_data(
                file,
                deep_scan=False
            )
        )

        return {
            "nom_fichier": file.filename,
            "taille": file_size,
            "date_analyse": datetime.now().isoformat(),
            "scan_mode": "structure-only",
            "structure": structure,
            "actions": actions,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

        


@router.post("/valider")
async def valider_patch(file: Annotated[UploadFile, File(...)]):
    try:
        _, structure, actions = await _extract_patch_data(file, deep_scan=True)
        return {
            "nom_fichier": file.filename,
            "structure": structure,
            "scan_mode": "sql-deep-structural-deployment",
            "actions": actions
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rapport")
async def generer_rapport(file: Annotated[UploadFile, File(...)]):
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Fichier ZIP vide")

    return await ReportGenerator.generer_rapports(content, file.filename)


@router.get("/statistiques")
async def get_statistiques():
    return {
        "types_patches": [
            {"code": "DB", "nom": "Base de données"},
            {"code": "UNIX", "nom": "UNIX/Système"},
            {"code": "WEB", "nom": "Application Web"},
            {"code": "CONFIG", "nom": "Configuration"}
        ]
    }




@router.get("/existing-types")
def get_existing_patch_types(
    file_name: str,
    client_id: int,
    environment_id: int,
    db: Annotated[Session, Depends(get_db)]
):
    patches = (
        db.query(Patch)
        .filter(
            Patch.original_filename == file_name,
            Patch.client_id == client_id,
            Patch.environment_id == environment_id
        )
        .order_by(Patch.created_at.desc())
        .all()
    )

    pending_statuses = "PENDING"
    executed_statuses = "EXECUTED"
    rollbacked_statuses = "ROLLED-BACK"

    blocking_patches = []
    pending_patches = []
    rollbacked_patches = []

    for patch in patches:
        status = (patch.status or "").upper().strip()
        patch_type = (patch.patch_type or "").upper().strip()

        if not patch_type:
            continue

        patch_info = {
            "id": patch.id,
            "patch_type": patch_type,
            "status": status,
            "name": patch.name,
            "original_filename": patch.original_filename,
        }

        if status in rollbacked_statuses:
            rollbacked_patches.append(patch_info)
            continue

        if status in pending_statuses:
            pending_patches.append(patch_info)
            continue

        if status in executed_statuses:
            blocking_patches.append(patch_info)
            continue

        blocking_patches.append(patch_info)

        

    existing_types = sorted({
        item["patch_type"]
        for item in blocking_patches
    })

    

    has_executed = any(
        item["status"] in executed_statuses
        for item in blocking_patches
    )


    return {
    "allowed": True,
    "reason": "DUPLICATE_ALLOWED",
    "message": "Création autorisée.",
    "existing_types": existing_types,
    "blocking_patches": [],
    "rollbacked_patches": rollbacked_patches,
}




def _detect_component_from_filename(filename: str) -> Optional[str]:
    name = (filename or "").replace("\\", "/").lower()

    parts = re.split(r"[\/\\_\-\s.]+", name)
    parts = [p for p in parts if p]

    if "bo" in parts or "backoffice" in parts or "back-office" in name:
        return "BO"

    if "fe" in parts or "frontend" in parts or "front-end" in name:
        return "FE"

    return None


def _detect_patch_type_from_filename(filename: str) -> Optional[str]:
    name = (filename or "").replace("\\", "/").lower()

    parts = re.split(r"[\/\\_\-\s.]+", name)
    parts = [p for p in parts if p]

    if "db" in parts or "database" in parts:
        return "DB"

    if "unix" in parts:
        return "UNIX"

    if "web" in parts:
        return "WEB"

    return None


def _safe_zip_member_name(member_name: str) -> str:
    clean = os.path.basename((member_name or "").replace("\\", "/"))
    clean = clean.replace(" ", "_")

    if not clean:
        clean = f"nested_{uuid.uuid4().hex}.zip"

    return clean


def _extract_inner_zip_files(
        original_filename: str,
        content: bytes,
        upload_dir: str
    ) -> Dict[str, Dict]:
        """
        Retourne un mapping par component/type.

        Exemple:
        {
        "DB|BO": {
            "original_filename": "patch_parent.zip",
            "saved_filename": "PATCH_DB_BO_00JRTH848484.zip",
            "file_path": "./uploads/patches/<uuid>_patch_parent/PATCH_DB_BO_00JRTH848484.zip",
            "component": "BO",
            "patch_type": "DB"
        },
        "DB|FE": {...}
        }
        """

        mapping = {}

        if not zipfile.is_zipfile(io.BytesIO(content)):
            return mapping

        parent_base = os.path.splitext(original_filename.replace(" ", "_"))[0]
        parent_folder = f"{uuid.uuid4().hex}_{parent_base}"
        parent_upload_dir = os.path.join(upload_dir, parent_folder)
        os.makedirs(parent_upload_dir, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(content), "r") as zip_ref:
            for info in zip_ref.infolist():
                if info.is_dir():
                    continue

                member_name = info.filename.replace("\\", "/")

                if not member_name.lower().endswith(".zip"):
                    continue

                inner_basename = _safe_zip_member_name(member_name)

                component = _detect_component_from_filename(inner_basename)
                patch_type = _detect_patch_type_from_filename(inner_basename)

                if not component:
                    component = _detect_component_from_filename(member_name)

                if not patch_type:
                    patch_type = _detect_patch_type_from_filename(member_name)

                if not component or not patch_type:
                    continue

                inner_path = os.path.join(parent_upload_dir, inner_basename)

                with zip_ref.open(info) as source, open(inner_path, "wb") as target:
                    shutil.copyfileobj(source, target)

                key = f"{patch_type}|{component}"

                mapping[key] = {
                    "id": uuid.uuid4().hex,
                    "original_filename": original_filename,
                    "saved_filename": inner_basename,
                    "file_path": inner_path,
                    "component": component,
                    "patch_type": patch_type,
                    "parent_file": original_filename,
                    "inner_file": inner_basename,
                }

        return mapping


@router.post("/create")
async def create_patch_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    files: Annotated[List[UploadFile], File(...)],
    patch_data: Annotated[str, Form(...)],
    analysis_data: Annotated[Optional[str], Form()] = None,
):
    try:
        patches = json.loads(patch_data)

        for patch in patches:
            patch["user_id"] = current_user.id
        
        upload_dir = "./uploads/patches"
        os.makedirs(upload_dir, exist_ok=True)

        files_mapping = {}
        component_files_mapping = {}

        for file in files:
            original_filename = file.filename
            content = await file.read()

            # 1. Essayer d'extraire les ZIP internes BO/FE
            inner_mapping = _extract_inner_zip_files(
                original_filename=original_filename,
                content=content,
                upload_dir=upload_dir
            )

            # 2. Si ZIP parent contient des ZIP internes exploitables,
            # on garde un mapping par type/component
            if inner_mapping:
                component_files_mapping[original_filename] = inner_mapping
                continue

            # 3. Sinon comportement normal : sauvegarder le ZIP principal
            unique_id = uuid.uuid4().hex
            safe_filename = original_filename.replace(" ", "_")
            new_filename = f"{unique_id}_{safe_filename}"

            file_location = os.path.join(upload_dir, new_filename)

            async with aiofiles.open(file_location, "wb") as buffer:
                await buffer.write(content)

            files_mapping[original_filename] = {
                "id": unique_id,
                "original_filename": original_filename,
                "saved_filename": new_filename,
                "file_path": file_location,
            }

        
        validated_patches = [PatchCreate(**item) for item in patches]
        parsed_analysis = json.loads(analysis_data) if analysis_data else None

        saved_patches = save_bulk_patches(
            db=db,
            patches_data=validated_patches,
            current_user_id=current_user.id,
            files_mapping=files_mapping,
            component_files_mapping=component_files_mapping,
            analysis_data=parsed_analysis
        )

        # --- LOG SUCCESS ---
        # On log l'action globale (ajout en masse)
        file_names = ", ".join(
            list(files_mapping.keys()) + list(component_files_mapping.keys())
        )
        log = AuditLog(
            user_id=current_user.id,
            action_name="ADD_PATCH",
            entity_type="PATCH",
            entity_id=None, # None car c'est une opération multiple
            status="SUCCESS",
            details=f"Successfully uploaded and created {len(saved_patches)} patch(es): {file_names}"
        )
        db.add(log)
        db.commit()

        return {
            "message": "Patchs sauvegardés avec succès",
            "count": len(saved_patches),
            "files_processed": list(files_mapping.keys()),
            "saved_files": files_mapping,
            "saved_component_files": component_files_mapping
        }
    
    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        
        # --- LOG FAILED ---
        error_log = AuditLog(
            user_id=current_user.id,
            action_name="ADD_PATCH",
            entity_type="PATCH",
            entity_id=None,
            status="FAILED",
            details=f"Failed to process and upload patch(es): {str(e)}"
        )
        db.add(error_log)
        db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{patch_id}")
def Delete_Patch( patch_id: int, db: Annotated[Session, Depends(get_db)], current_user: Annotated[User, Depends(get_current_user)]):
    return  delete_patch(patch_id, db, current_user.id) 
       
   


@router.get("/{patch_id}")
def get_patch_by_id(
    patch_id: int,
    db: Annotated[Session, Depends(get_db)]
):
    patch = db.query(Patch).filter(Patch.id == patch_id).first()

    if not patch:
        raise HTTPException(status_code=404, detail="Patch non trouvé")

    return {
        "id": patch.id,
        "name": patch.name,
        "patch_type": patch.patch_type,
        "file_path": patch.file_path,
        "server": {
            "id": patch.server.id if patch.server else None,
            "ip_address": patch.server.ip_address if patch.server else None,
            "username": patch.server.username if patch.server else None,
            "type_server": patch.server.type_server if patch.server else None
        }
    }


@router.get("/environments/{client_id}")
def get_environments_by_client(
    client_id: int,
    db: Annotated[Session, Depends(get_db)]
):
    envs = db.query(Environment).filter(Environment.client_id == client_id).all()
    return [{"id": e.id, "nom": e.name, "type": e.env_type} for e in envs]

@router.get("/servers-by-env/{client_id}/{environment_id}")
def fetch_servers_by_env(
    client_id: int,
    environment_id: int,
    db: Annotated[Session, Depends(get_db)]
):
   
    return get_servers_by_client_and_env(client_id, environment_id, db)




@router.get("/patches/{server_id}")
def fetch_patches_by_server(
    server_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: Optional[int] = None,
    month: Optional[int] = None
):
    query = db.query(Patch).filter(Patch.server_id == server_id, Patch.user_id == current_user.id)

    if year:
        query = query.filter(extract("year", Patch.created_at) == year)

    if month:
        query = query.filter(extract("month", Patch.created_at) == month)

    patches = query.order_by(Patch.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "type_patch": p.patch_type,
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in patches
    ]



