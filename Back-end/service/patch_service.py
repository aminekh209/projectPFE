from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import shutil
from pathlib import Path
from sqlalchemy.orm import Session
from Models.patchs import Patch
from Models.patch_detector import PatchDetector
from Models.servers import Server
from Models.users import User
from Schemas.patch_schema import PatchCreate 
import json
import re  
from .zip_analyzer import ZipAnalyzer
from .patch_validator import PatchValidator


class PatchService:
    def save_bulk_patches(self, db: Session, patches_data: list[PatchCreate], zip_path: str, extracted_path: str, analysis_data: dict = None):
        
        created_patches = []
        user_home = os.path.expanduser("~")
        action_logs_dir = os.path.join(user_home, "PatchManager_Data", "patch_actions")
        os.makedirs(action_logs_dir, exist_ok=True)
        
        validator = PatchValidator()
        actions_file_path = None
        
        # 1. Save analysis (Logs)
        if analysis_data and analysis_data.get('actions'):
            current_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            actions_filename = f"analysis_{current_timestamp}_actions.json"
            actions_file_path = os.path.join(action_logs_dir, actions_filename)
            
            with open(actions_file_path, "w", encoding="utf-8") as f:
                json.dump(analysis_data.get('actions'), f, ensure_ascii=False, indent=4)
                
        # 2. Process each patch request
        for patch_request in patches_data:
            
            # --- SECURITY VALIDATION ---
            validation_result = validator.valider_patch(analysis_data, patch_request.patch_type, patch_request.component)
            
            if not validation_result['valide']:
                error_messages = " | ".join(validation_result['erreurs'])
                raise ValueError(f"Security rejection for patch '{patch_request.name}' ({patch_request.component}): {error_messages}")
            
            if validation_result['avertissements']:
                print(f" WARNINGS for {patch_request.name} : {validation_result['avertissements']}")
                
            # --- SERVER ASSIGNMENT ---
            target_server = db.query(Server).filter(
                Server.client_id == patch_request.client_id,
                Server.environment_id == patch_request.environment_id,
                Server.server_type == patch_request.patch_type,
                Server.is_active == True
            ).first()

            if not target_server:
                raise ValueError(f"Critical error: No server of type {patch_request.patch_type} is configured for this Client/Environment.")

            assigned_server_id = target_server.id
            component_base_path = extracted_path 
            
            # --- INTELLIGENT COMPONENT PATH SEARCH ---
            if analysis_data:
                parsed_actions = analysis_data.get('actions', analysis_data)
                archive_files = parsed_actions.get('fichiers_presents', [])
                
                if archive_files:
                    target_component = patch_request.component.upper()
                    
                    component_files = [
                        f for f in archive_files 
                        if f"/{target_component}/" in f.upper() or f.upper().startswith(f"{target_component}/")
                    ]
                    
                    if not component_files:
                        raise ValueError(f"Security error: The component '{patch_request.component}' configured for '{patch_request.name}' was not found in the provided ZIP file. Registration cancelled.")
                    
                    # Use the first found file as a reference to extract the folder path
                    reference_file_path = component_files[0]
                    path_match = re.search(rf"^(.*?/?{re.escape(patch_request.component)}(?:/|$))", reference_file_path, re.IGNORECASE)
                    
                    if path_match:
                        extracted_component_dir = path_match.group(1).rstrip('/')
                        component_base_path = os.path.join(extracted_path, extracted_component_dir)

            # --- PREPARATION OF INSERTION DATA ---
            final_absolute_path = os.path.abspath(component_base_path).replace('\\', '/')
            patch_file_size = os.path.getsize(zip_path)
            unique_patch_name = f"{patch_request.name}_{patch_request.component}"
            
            # --- DATABASE INSERTION ---
            db_patch = Patch(
                name=unique_patch_name,
                description=patch_request.description,
                original_filename=patch_request.file_name,
                file_path=final_absolute_path, 
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
                    file_path=final_absolute_path,
                    file_size=patch_file_size,
                    file_type='DOSSIER',
                    actions=actions_file_path
                )
                db.add(db_detector)

            created_patches.append(db_patch)

        # 3. Transaction validation
        db.commit()
        
        for patch in created_patches:
            db.refresh(patch)
        
        return created_patches