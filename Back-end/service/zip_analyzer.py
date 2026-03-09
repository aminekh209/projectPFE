import os
import zipfile
import tempfile
from typing import Dict, Any, List
from fastapi import UploadFile
import hashlib
import json

from .file_scanner import FileScanner
from .action_detector import ActionDetector

class ZipAnalyzer:
    
    def __init__(self):
        self.file_scanner = FileScanner()
        self.action_detector = ActionDetector()
    
    async def analyser_zip(self, file: UploadFile) -> Dict[str, Any]:
        """
        Completely analyze an uploaded ZIP file
        """
        # Temporarily save the file content in memory
        file_content = await file.read()
        
        # Calculate the SHA-256 hash for file integrity
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Save to a temporary file for the FileScanner
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        try:
            # Scan the physical structure of the ZIP
            structure_data = FileScanner.scanner_fichiers_zip(tmp_path)
            
            # Detect actions and commands inside the files
            actions_data = await ActionDetector.detecter_actions_dans_zip(file_content)
            
            # Analyze compatibility and compliance
            compatibility_data = self._analyser_compatibilite(structure_data, actions_data)
            
            # Generate the final analysis report
            report = self._generer_rapport_analyse(
                file.filename,
                structure_data,
                actions_data,
                compatibility_data,
                file_hash
            )
            
            return report
            
        finally:
            # Clean up the temporary file to free up disk space
            if os.path.exists(tmp_path):
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
    
    def _generer_rapport_analyse(self, filename: str, structure: Dict, 
                                actions: Dict, compatibility: Dict, 
                                file_hash: str) -> Dict[str, Any]:
        """
        Generate the complete analysis report dictionary
        """
        # Dictionary keys remain in French to maintain Frontend compatibility
        return {
            'nom_fichier': filename,
            'hash': file_hash,
            'taille': structure['taille'],
            'statistiques': structure['statistiques'],
            'types_detectes': actions['types_detectes'],
            'actions': {
                'globales': actions['actions_globales'],
                'par_fichier': actions['actions_par_fichier'],
                'nombre': actions['nombre_actions']
            },
            'compatibilite': compatibility,
            'structure': {
                'dossiers': structure['dossiers'],
                'extensions': structure['extensions'],
                'fichiers': structure['fichiers']
            },
            'recommandations': self._generer_recommandations(compatibility, structure)
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