
import os
import zipfile
import tempfile
from typing import Dict, Any, List
from fastapi import UploadFile
import hashlib
import json

from .file_scanner import FileScanner
from .action_detector import ActionDetector
import aiofiles

class ZipAnalyzer:
    
    def __init__(self):
        self.file_scanner = FileScanner()
        self.action_detector = ActionDetector()
    
    async def analyser_zip(
        self,
        file: UploadFile
    ) -> Dict[str, Any]:
        """
        Analyse le ZIP avec la politique suivante :

        - Détection DB / UNIX / WEB sur tous les fichiers.
        - Analyse profonde uniquement des fichiers SQL.
        - Les WAR, EAR, JAR et binaires ne sont pas extraits.
        - Le fichier uploadé est lu par blocs pour limiter la mémoire.
        """

        tmp_path = None
        sql_zip_path = None

        original_size = 0
        file_hash = hashlib.sha256()

        try:
            # Créer le fichier ZIP temporaire principal.
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
            os.close(tmp_fd)

            # Copier l'upload par blocs de 1 Mo.
            # Cela évite await file.read() sur un fichier de 200 Mo.
            async with aiofiles.open(tmp_path, "wb") as tmp_file:
                while True:
                    chunk = await file.read(1024 * 1024)

                    if not chunk:
                        break

                    original_size += len(chunk)
                    file_hash.update(chunk)

                    await tmp_file.write(chunk)

            if original_size == 0:
                raise ValueError("Fichier ZIP vide")

            # Scanner toute la structure et construire
            # un petit ZIP contenant uniquement les SQL.
            structure_data, sql_zip_path = (
                FileScanner
                .scanner_structure_et_construire_zip_sql(
                    tmp_path
                )
            )

            # Détection globale DB / UNIX / WEB
            # basée sur les chemins et extensions.
            detected_types = (
                FileScanner.detecter_types_depuis_structure(
                    structure_data
                )
            )

            sql_count = (
                structure_data
                .get("analyse_sql", {})
                .get("nombre_fichiers_sql", 0)
            )

            sql_total_size = (
                structure_data
                .get("analyse_sql", {})
                .get("taille_sql_totale", 0)
            )

            if sql_count > 0:
                with open(sql_zip_path, "rb") as sql_file:
                    sql_content = sql_file.read()

                sql_actions = (
                    await self.action_detector
                    .detecter_actions_dans_zip(
                        sql_content
                    )
                )

                sql_analysis_zip_size = len(sql_content)

            else:
                sql_actions = {
                    "types_detectes": [],
                    "actions_globales": [],
                    "actions_par_fichier": [],
                    "fichiers_presents": [],
                    "nombre_actions": 0,
                    "statistiques_categories": {},
                }

                sql_analysis_zip_size = 0

            deployment_actions = (
                self.action_detector
                .detecter_actions_deploiement_depuis_structure(
                    structure_data
                )
            )

            actions_data = (
                self.action_detector
                .fusionner_resultats_actions(
                    sql_actions,
                    deployment_actions,
                )
            )

            actions_data["types_detectes"] = detected_types

            actions_data["scan_details"] = {
                "mode": "SQL_DEEP_PLUS_STRUCTURAL_DEPLOYMENT",
                "original_zip_size": original_size,
                "sql_analysis_zip_size": sql_analysis_zip_size,
                "sql_total_uncompressed_size": sql_total_size,
                "sql_files_analyzed": sql_count,
                "unix_web_content_analyzed": False,
            }

            
            compatibility_data = self._analyser_compatibilite(
                structure_data,
                actions_data
            )

            report = self._generer_rapport_analyse(
                file.filename,
                structure_data,
                actions_data,
                compatibility_data,
                file_hash.hexdigest()
            )

            return report

        finally:
            # Supprimer le ZIP SQL temporaire.
            if (
                sql_zip_path
                and os.path.exists(sql_zip_path)
            ):
                os.unlink(sql_zip_path)

            # Supprimer le ZIP uploadé temporaire.
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _analyser_compatibilite(self, structure: Dict, actions: Dict) -> Dict[str, Any]:
        """
        Analyze the compatibility and requirements of the patch
        """
        patch_types = actions.get('types_detectes', [])
        
        # Check prerequisites (Case-insensitive check for prepatch/postpatch)
        prepatch_required = any('prepatch' in str(f.get('nom', '')).lower() for f in structure.get('fichiers', []))
        postpatch_required = any('postpatch' in str(f.get('nom', '')).lower() for f in structure.get('fichiers', []))
        
        # Evaluate the risk level based on the detected actions
        risk_level = self._evaluer_niveau_risque(actions.get('actions_globales', []))
        
        # Verify if the UNIX structure meets the standard requirements
        complete_unix_structure = self._verifier_structure_unix(structure)
        
        # Dictionary keys remain in French to maintain Frontend compatibility
        return {
            'types_patch': patch_types,
            'prepatch_requis': prepatch_required,
            'postpatch_requis': postpatch_required,
            'niveau_risque': risk_level,
            'structure_unix_complete': complete_unix_structure,
            'compatible': len(patch_types) > 0
        }
    
    def _evaluer_niveau_risque(self, actions: List[Dict]) -> str:
        """
        Evaluate the risk level of the detected actions
        """
        high_risk_keywords = ['DROP', 'DELETE', 'rm ', 'stop']
        medium_risk_keywords = ['ALTER', 'UPDATE', 'chmod', 'restart']
        
        for action_obj in actions:
            # Safely extract the description to check for risk keywords
            action_text = str(action_obj.get('description', '')).upper()
            
            if any(risk.upper() in action_text for risk in high_risk_keywords):
                return 'high' # Élevé
            if any(risk.upper() in action_text for risk in medium_risk_keywords):
                return 'medium' # Moyen
        
        return 'low' # Faible
    
    def _verifier_structure_unix(self, structure: Dict) -> bool:
        """
        Verify if the UNIX directory structure is complete
        """
        folders = structure.get('dossiers', [])
        required_folders = ['bin', 'lib', 'ctl']
        
        present_folders = []
        for folder in folders:
            for req in required_folders:
                if req in folder:
                    present_folders.append(req)
        
        # Check if we found at least 3 distinct required folders
        return len(set(present_folders)) >= 3
    
    def _generer_rapport_analyse(
    self,
    filename: str,
    structure: Dict,
    actions: Dict,
    compatibility: Dict,
        file_hash: str
    ) -> Dict[str, Any]:
        """
        Génère le rapport d'analyse dans un format compatible
        avec le frontend actuel et les anciens consommateurs.
        """

        detected_types = actions.get("types_detectes", [])
        global_actions = actions.get("actions_globales", [])
        file_actions = actions.get("actions_par_fichier", [])
        action_count = actions.get("nombre_actions", 0)
        category_stats = actions.get("statistiques_categories", {})
        scan_details = actions.get("scan_details", {})

        return {
            "nom_fichier": filename,
            "hash": file_hash,
            "taille": structure.get("taille", 0),
            "statistiques": structure.get("statistiques", {}),

            # Conservé à la racine pour l'ancienne compatibilité.
            "types_detectes": detected_types,

            "actions": {
                # Nouveau format utilisé par le frontend.
                "types_detectes": detected_types,
                "actions_globales": global_actions,
                "actions_par_fichier": file_actions,
                "nombre_actions": action_count,
                "statistiques_categories": category_stats,
                "scan_details": scan_details,

                # Ancien format conservé temporairement.
                "globales": global_actions,
                "par_fichier": file_actions,
                "nombre": action_count,
            },

            "compatibilite": compatibility,

            "structure": {
                "dossiers": structure.get("dossiers", []),
                "extensions": structure.get("extensions", []),
                "fichiers": structure.get("fichiers", []),
                "statistiques": structure.get("statistiques", {}),
                "analyse_sql": structure.get("analyse_sql", {}),
            },

            "recommandations": self._generer_recommandations(
                compatibility,
                structure
            ),
        }
    
    def _generer_recommandations(self, compatibility: Dict, structure: Dict) -> List[str]:
        """
        Generate text recommendations based on the analysis results
        """
        recommendations = []
        
        if not compatibility['prepatch_requis']:
            recommendations.append("⚠️ A prepatch script is highly recommended for pre-installation checks.")
        
        if not compatibility['postpatch_requis']:
            recommendations.append("⚠️ A postpatch script is highly recommended for post-installation checks.")
        
        if 'UNIX' in compatibility['types_patch'] and not compatibility['structure_unix_complete']:
            recommendations.append("🔧 Incomplete UNIX structure (bin/, lib/, and ctl/ directories are usually required).")
        
        if compatibility['niveau_risque'] == 'high':
            recommendations.append("⚠️ High-risk patch detected - Mandatory manual validation required before deployment.")
        
        return recommendations
