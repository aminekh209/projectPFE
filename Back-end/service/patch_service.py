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
from .zip_analyzer import ZipAnalyzer
from .patch_validator import PatchValidator


class PatchService:
    
    
    # def __init__(self, upload_dir: str = "uploads"):
    #     self.upload_dir = upload_dir
    #     self.zip_analyzer = ZipAnalyzer()
    #     self.patch_validator = PatchValidator()
        
    #     # Créer le dossier uploads s'il n'existe pas
    #     os.makedirs(upload_dir, exist_ok=True)
    
    # async def creer_patch(self, nom: str, description: str, fichier, 
    #                       configurations: List[Dict]) -> Dict[str, Any]:
        
    #     # Sauvegarder le fichier
    #     chemin_fichier = await self._sauvegarder_fichier(fichier)
        
    #     # Analyser le ZIP
    #     analyse = await self.zip_analyzer.analyser_zip(fichier)
        
    #     # Valider les configurations
    #     validation = await self.patch_validator.valider_patch(fichier, configurations)
        
    #     # Créer l'objet patch
    #     patch = {
    #         'id': self._generer_id(),
    #         'code_patch': self._generer_code_patch(),
    #         'nom': nom,
    #         'description': description,
    #         'date_creation': datetime.now().isoformat(),
    #         'statut': 'en_creation' if validation['global_valide'] else 'invalide',
    #         'fichier': {
    #             'nom': fichier.filename,
    #             'chemin': chemin_fichier,
    #             'analyse': analyse
    #         },
    #         'configurations': configurations,
    #         'validation': validation,
    #         'historique': [
    #             {
    #                 'date': datetime.now().isoformat(),
    #                 'action': 'creation',
    #                 'utilisateur': 'systeme',
    #                 'details': 'Création du patch'
    #             }
    #         ]
    #     }
        
    #     return patch
    
    # async def _sauvegarder_fichier(self, fichier) -> str:
       
        
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     nom_fichier = f"{timestamp}_{fichier.filename}"
    #     chemin = os.path.join(self.upload_dir, nom_fichier)
        
       
    #     contenu = await fichier.read()
    #     with open(chemin, 'wb') as f:
    #         f.write(contenu)
        
    #     return chemin
    
    # def _generer_id(self) -> int:
        
    #     import random
    #     return random.randint(1000, 9999)
    
    # def _generer_code_patch(self) -> str:
        
    #     from datetime import datetime
    #     import hashlib
    #     import os
        
    #     timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    #     random_hash = hashlib.md5(os.urandom(8)).hexdigest()[:6].upper()
    #     return f"PATCH-{timestamp}-{random_hash}"
    
    # def get_patch(self, patch_id: int) -> Optional[Dict]:
        
    #     pass
    
    # def get_patches(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        
    #     pass
    
    # def update_patch(self, patch_id: int, data: Dict) -> Optional[Dict]:
        
    #     pass
    
    # def delete_patch(self, patch_id: int) -> bool:
        
    #     pass

    # =================================================================
    # NOUVELLE MÉTHODE CORRIGÉE (Indentation + ajout de 'self')
    # =================================================================
    
    def save_bulk_patches(self, db: Session, patches_data: list[PatchCreate], zip_path: str, extracted_path: str, analysis_data: dict = None):
        
        created_patches = []
        user_home = os.path.expanduser("~")
        DOSSIER_ACTIONS = os.path.join(user_home, "PatchManager_Data", "patch_actions")
        os.makedirs(DOSSIER_ACTIONS, exist_ok=True)
        validator = PatchValidator()
        actions_file_path = None
        if analysis_data and analysis_data.get('actions'):
            # Utilise un timestamp pour éviter les écrasements si le même ZIP est réutilisé plus tard
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
            nom_fichier_json = f"analyse_{timestamp_str}_actions.json"
            actions_file_path = os.path.join(DOSSIER_ACTIONS, nom_fichier_json)
            
            with open(actions_file_path, "w", encoding="utf-8") as f:
                json.dump(analysis_data.get('actions'), f, ensure_ascii=False, indent=4)
        for p_data in patches_data:
           # 🔥 2. LE BOUCLIER DE SÉCURITÉ
            # On vérifie si ce que l'utilisateur veut (p_data.patch_type) correspond au contenu (analysis_data)
            validation_result = validator.valider_patch(analysis_data, p_data.patch_type, p_data.component)
            
            if not validation_result['valide']:
                # Si c'est invalide, on bloque tout en levant une erreur !
                # On regroupe toutes les erreurs dans une seule phrase
                erreurs_str = " | ".join(validation_result['erreurs'])
                raise ValueError(f"Rejet de sécurité pour le patch '{p_data.name}' : {erreurs_str}")
            
            # 🔥 3. Optionnel : Afficher les avertissements dans les logs du serveur
            if validation_result['avertissements']:
                print(f"⚠️ AVERTISSEMENTS pour {p_data.name} : {validation_result['avertissements']}")
            server_target = db.query(Server).filter(
                Server.client_id == p_data.client_id,
                Server.environment_id == p_data.environment_id,
                Server.server_type == p_data.patch_type,
                Server.is_active == True
            ).first()

            # 🔥 SÉCURITÉ ABSOLUE : Si aucun serveur n'est trouvé, on bloque tout !
            if not server_target:
                raise ValueError(f"Critical error: No server of type  {p_data.patch_type}is configured for this Client/Environment.")

            found_server_id = server_target.id
            patch_size = os.path.getsize(zip_path)
            # Création de l'objet SQLAlchemy pour la base de données
            db_patch = Patch(
                name=p_data.name,
                description=p_data.description,
                original_filename=p_data.file_name,
                file_path=extracted_path,
                file_size=patch_size,
                patch_type=p_data.patch_type,
                component=p_data.component,
                status=p_data.status,
                user_id=p_data.user_id,
                client_id=p_data.client_id,
                environment_id=p_data.environment_id,
                server_id=found_server_id
                # duplication_count=p_data.duplication_count # (Décommentez si vous avez ajouté ce champ)
            )
            db.add(db_patch)
            db.flush()
            
            if analysis_data:
                db_detector = PatchDetector(
                    patch_id=db_patch.id,
                    server_id=found_server_id,          # On récupère l'ID fraîchement généré
                    file_path=extracted_path,
                    file_size=patch_size,
                    file_type='DOSSIER',
                    actions=actions_file_path
                )
                db.add(db_detector)


            created_patches.append(db_patch)

        # On commit toutes les insertions en une seule transaction
        db.commit()
        
        # On rafraîchit les objets pour récupérer les IDs générés par PostgreSQL
        for patch in created_patches:
            db.refresh(patch)
        
        return created_patches