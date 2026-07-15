from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.patchs import Patch
from database import get_db

from service.notification_service import create_notification
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import func
import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from models import Patch, Server,Environment, PatchDetector, User
from schemas import PatchCreate 
import json
from .zip_analyzer import ZipAnalyzer
from service.notification_service import create_notification
from .patch_validator import PatchValidator
import re
from models import (
    Patch,
    Server,
    Environment,
    PatchDetector,
    User,
    RollbackExecution,
)


def get_servers_by_client_and_env(client_id: int, environment_id: int, db: Session):
    servers = db.query(Server).filter(
        Server.client_id == client_id,
        Server.environment_id == environment_id
    ).all()
    
    return [
        {
            "id": s.id, 
            "name": s.name, 
            "ip_address": s.ip_address, 
            "type_server": s.type_server,
            "os": s.os
        } for s in servers
    ]
    
def save_bulk_patches(
    db: Session,
    patches_data: list[PatchCreate],
    current_user_id: int,
    files_mapping: dict,
    analysis_data: dict = None,
    component_files_mapping=None
):
    created_patches = []
    user_home = os.path.expanduser("~")
    action_logs_dir = os.path.join(user_home, "PatchManager_Data", "patch_actions")
    os.makedirs(action_logs_dir, exist_ok=True)

    validator = PatchValidator()
    actions_file_path = None

    if analysis_data and analysis_data.get('actions'):
        current_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        actions_filename = f"analysis_{current_timestamp}_actions.json"
        actions_file_path = os.path.join(action_logs_dir, actions_filename)
        with open(actions_file_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data.get('actions'), f, ensure_ascii=False, indent=4)

    for patch_request in patches_data:
        
     
        original_name = patch_request.file_name

        component_files_mapping = component_files_mapping or {}

        patch_type = str(patch_request.patch_type or "").upper().strip()
        component = str(patch_request.component or "").upper().strip()
        component_key = f"{patch_type}|{component}"

        inner_mapping_for_file = component_files_mapping.get(original_name) or {}

        if component_key in inner_mapping_for_file:
            file_info = inner_mapping_for_file[component_key]
        else:
            file_info = files_mapping.get(original_name)

        if not file_info:
            raise ValueError(
                f"Fichier physique manquant pour le patch : {original_name} "
                f"(type={patch_type}, component={component})"
            )

        zip_path = file_info["file_path"]
        final_zip_path = zip_path.replace("\\", "/")
        patch_file_size = os.path.getsize(zip_path)
        
        if not patch_request.server_id:
            raise ValueError("Aucun serveur sélectionné pour ce patch.")

        target_server = db.query(Server).filter(
            Server.id == patch_request.server_id,
            Server.client_id == patch_request.client_id,
            Server.environment_id == patch_request.environment_id
        ).first()

        if not target_server:
            raise ValueError(
                f"Serveur invalide : server_id={patch_request.server_id}, "
                f"client_id={patch_request.client_id}, "
                f"environment_id={patch_request.environment_id}"
            )

        assigned_server_id = target_server.id
        unique_patch_name = f"{patch_request.name}_{patch_request.component}"
        db_patch = Patch(
            name=unique_patch_name,
            description=patch_request.description,
            original_filename=original_name,
            file_path=final_zip_path,  
            file_size=patch_file_size,  
            patch_type=patch_request.patch_type,
            component=patch_request.component,
            status=patch_request.status,
            user_id=patch_request.user_id,
            client_id=patch_request.client_id,
            environment_id=patch_request.environment_id,
            server_id=assigned_server_id
        )

        db.add(db_patch)
        db.flush()

        if analysis_data:
            db_detector = PatchDetector(
                patch_id=db_patch.id,
                server_id=assigned_server_id,
                file_path=final_zip_path,
                file_size=patch_file_size,
                file_type='ZIP',
                actions=actions_file_path
            )
            db.add(db_detector)

        created_patches.append(db_patch)

    # 3. Transaction validation
    db.commit()

    for patch in created_patches:
        db.refresh(patch)
    patch_count = len(created_patches)
    if patch_count > 0:
        create_notification(db, current_user_id, f"{patch_count} nouveau(x) patch(s) ajouté(s).", "success", "PATCH")
    return created_patches



def delete_patch(patch_id: int, db: Session,current_user_id: int):
  
    patch = db.query(Patch).filter(Patch.id == patch_id).first()
    
    if not patch:
        create_notification(db, current_user_id, f"Suppression échouée : Patch ID {patch_id} introuvable.", "error", "PATCH")
        raise HTTPException(status_code=404, detail="Patch introuvable")

    db.query(PatchDetector).filter(PatchDetector.patch_id == patch_id).delete(synchronize_session=False)

    db.delete(patch)
    db.commit()
    create_notification(db, current_user_id, f"patch {patch.name} est supprimé de la base de données.", "warning", "PATCH")

    return {"status": "success", "message": "Enregistrement du patch supprimé de la base de données"}




def get_patches_pending_grouped_by_user_and_date(user_id: int, db: Session):
    patches = (
        db.query(Patch)
        .filter(Patch.user_id == user_id, Patch.status == "PENDING")
        .order_by(Patch.created_at.asc())
        .all()
    )

    grouped = {}

    for patch in patches:
        date_time = patch.created_at.replace(second=0, microsecond=0)

        if date_time not in grouped:
            user = patch.user
            grouped[date_time] = {
                "user_id": user_id,
                "nom": user.lastname if user else None,
                "prenom": user.firstname if user else None,
                "username": user.username if user else None,
                "created_at": date_time,
                "patches": []
            }

        server = patch.server
        environment = server.environment if server else None
        client = environment.client if environment else None

        grouped[date_time]["patches"].append({
            "id": patch.id,
            "status": patch.status,
            "client_name": client.name if client else None,
            "environment_name": environment.env_type if environment else None,
            "name_patch": patch.name,
            "filename": patch.original_filename,
            "id_server": patch.server_id,
            "size": patch.file_size,
            "component": patch.component,
            "file_path": patch.file_path,
            "description": patch.description,
            "environment": environment.env_type if environment else None,
            "os": server.os if server else None,
            "ip_address": server.ip_address if server else None,
            "username": server.username if server else None,
            "type_server": server.type_server if server else None,
            "type_patch": patch.patch_type if patch.patch_type else None,
            "name_server": server.name if server else None
        })

    return list(grouped.values())
def get_patches_grouped_by_user_and_date(user_id: int, db: Session):
    patches = (
        db.query(Patch)
        .filter(Patch.user_id == user_id)
        .order_by(Patch.created_at.asc())
        .all()
    )

    patch_ids = [patch.id for patch in patches]

    latest_rollback_by_patch = {}

    if patch_ids:
        # Chercher uniquement la dernière tentative de rollback
        # enregistrée pour chaque patch.
        latest_rollback_ids = (
            db.query(
                RollbackExecution.patch_id.label("patch_id"),
                func.max(RollbackExecution.id).label("rollback_id"),
            )
            .filter(
                RollbackExecution.patch_id.in_(patch_ids)
            )
            .group_by(
                RollbackExecution.patch_id
            )
            .subquery()
        )

        latest_rollbacks = (
            db.query(RollbackExecution)
            .join(
                latest_rollback_ids,
                RollbackExecution.id
                == latest_rollback_ids.c.rollback_id,
            )
            .all()
        )

        latest_rollback_by_patch = {
            rollback.patch_id: rollback
            for rollback in latest_rollbacks
        }

    grouped = {}

    for patch in patches:
        date_time = patch.created_at.replace(
            second=0,
            microsecond=0
        )

        latest_rollback = latest_rollback_by_patch.get(
            patch.id
        )

        rollback_status = (
            (latest_rollback.status or "")
            .upper()
            .strip()
            if latest_rollback
            else None
        )

        patch_status = (
            (patch.status or "")
            .upper()
            .strip()
        )

        rollback_failed = (
            patch_status == "EXECUTED"
            and rollback_status == "FAILED"
        )

        if date_time not in grouped:
            user = patch.user

            grouped[date_time] = {
                "user_id": user_id,
                "nom": user.lastname if user else None,
                "prenom": user.firstname if user else None,
                "username": user.username if user else None,
                "created_at": date_time,
                "patches": [],
            }

        server = patch.server
        environment = server.environment if server else None
        client = environment.client if environment else None

        grouped[date_time]["patches"].append({
            "id": patch.id,
            "status": patch.status,

            # Informations sur la dernière tentative de rollback
            "rollback_status": rollback_status,
            "rollback_failed": rollback_failed,
            "rollback_execution_id": (
                latest_rollback.id
                if latest_rollback
                else None
            ),

            "client_name": client.name if client else None,
            "environment_name": (
                environment.env_type
                if environment
                else None
            ),
            "name_patch": patch.name,
            "filename": patch.original_filename,
            "id_server": patch.server_id,
            "size": patch.file_size,
            "component": patch.component,
            "file_path": patch.file_path,
            "description": patch.description,
            "environment": (
                environment.env_type
                if environment
                else None
            ),
            "os": server.os if server else None,
            "ip_address": (
                server.ip_address
                if server
                else None
            ),
            "username": (
                server.username
                if server
                else None
            ),
            "type_server": (
                server.type_server
                if server
                else None
            ),
            "type_patch": (
                patch.patch_type
                if patch.patch_type
                else None
            ),
            "name_server": (
                server.name
                if server
                else None
            ),
        })

    return list(grouped.values())

def get_patches_user_and_date(db: Session):
    patches = db.query(Patch).all()
    grouped = {}

    for patch in patches:
        time_str = patch.created_at.strftime("%Y-%m-%d %H:%M:%S") if patch.created_at else None
        key = (patch.user_id, time_str)

        if key not in grouped:
            user = patch.user 
            grouped[key] = {
                "user_id": patch.user_id,
                "nom": user.lastname if user else None,
                "prenom": user.firstname if user else None,
                "username": user.username if user else None,
                "created_at": patch.created_at,
                "patches": []
            }

        server = patch.server

        grouped[key]["patches"].append({
            "id": patch.id,
            "name_patch": patch.name,
            "description": patch.description,
            "size": patch.file_size,
            "filename":patch.original_filename,
            "patch_type": patch.patch_type,
            "component": patch.component,
            "status": patch.status,
            "id_server": patch.server_id,
            "name_server": server.name if server else None,
            "os": server.os if server else None,
            "ip_address": server.ip_address if server else None,
            "username_server": server.username if server else None,
            "type_server": server.type_server if server else None,
            "environment": server.environment.env_type if server else None,
            "server_status": server.status if server else None
        })

    return list(grouped.values())