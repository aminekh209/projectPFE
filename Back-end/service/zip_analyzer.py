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
    """
    Analyseur principal de fichiers ZIP
    """
    
    def __init__(self):
        self.file_scanner = FileScanner()
        self.action_detector = ActionDetector()
    
    async def analyser_zip(self, file: UploadFile) -> Dict[str, Any]:
        """
        Analyser complètement un fichier ZIP uploadé
        """
        # Sauvegarder temporairement le fichier
        contenu = await file.read()
        
        # Calculer le hash
        hash_fichier = hashlib.sha256(contenu).hexdigest()
        
        # Sauvegarder dans un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            tmp_file.write(contenu)
            tmp_path = tmp_file.name
        
        try:
            # Scanner la structure
            structure = FileScanner.scanner_fichiers_zip(tmp_path)
            
            # Détecter les actions
            actions = await ActionDetector.detecter_actions_dans_zip(contenu)
            
            # Analyser la compatibilité
            compatibilite = self._analyser_compatibilite(structure, actions)
            
            # Générer le rapport d'analyse
            rapport = self._generer_rapport_analyse(
                file.filename,
                structure,
                actions,
                compatibilite,
                hash_fichier
            )
            
            return rapport
            
        finally:
            # Nettoyer le fichier temporaire
            os.unlink(tmp_path)
    
    def _analyser_compatibilite(self, structure: Dict, actions: Dict) -> Dict[str, Any]:
        """
        Analyser la compatibilité du patch
        """
        types_patch = actions.get('types_detectes', [])
        
        # Vérifier les prérequis
        prepatch_requis = any('prepatch' in f['nom'] for f in structure['fichiers'])
        postpatch_requis = any('postpatch' in f['nom'] for f in structure['fichiers'])
        
        # Évaluer le risque
        niveau_risque = self._evaluer_niveau_risque(actions.get('actions_globales', []))
        
        # Vérifier la structure UNIX
        structure_unix_complete = self._verifier_structure_unix(structure)
        
        return {
            'types_patch': types_patch,
            'prepatch_requis': prepatch_requis,
            'postpatch_requis': postpatch_requis,
            'niveau_risque': niveau_risque,
            'structure_unix_complete': structure_unix_complete,
            'compatible': len(types_patch) > 0
        }
    
    def _evaluer_niveau_risque(self, actions: List[str]) -> str:
        """
        Évaluer le niveau de risque des actions
        """
        actions_risque_eleve = ['DROP', 'DELETE', 'rm ', 'stop']
        actions_risque_moyen = ['ALTER', 'UPDATE', 'chmod', 'restart']
        
        for action in actions:
            if any(risque in action for risque in actions_risque_eleve):
                return 'élevé'
            if any(risque in action for risque in actions_risque_moyen):
                return 'moyen'
        
        return 'faible'
    
    def _verifier_structure_unix(self, structure: Dict) -> bool:
        """
        Vérifier si la structure UNIX est complète
        """
        dossiers = structure.get('dossiers', [])
        requis = ['bin', 'lib', 'ctl']
        
        presents = []
        for dossier in dossiers:
            for r in requis:
                if r in dossier:
                    presents.append(r)
        
        return len(set(presents)) >= 3
    
    def _generer_rapport_analyse(self, nom_fichier: str, structure: Dict, 
                                actions: Dict, compatibilite: Dict, 
                                hash_fichier: str) -> Dict[str, Any]:
        """
        Générer le rapport d'analyse complet
        """
        return {
            'nom_fichier': nom_fichier,
            'hash': hash_fichier,
            'taille': structure['taille'],
            'statistiques': structure['statistiques'],
            'types_detectes': actions['types_detectes'],
            'actions': {
                'globales': actions['actions_globales'],
                'par_fichier': actions['actions_par_fichier'],
                'nombre': actions['nombre_actions']
            },
            'compatibilite': compatibilite,
            'structure': {
                'dossiers': structure['dossiers'],
                'extensions': structure['extensions'],
                'fichiers': structure['fichiers']
            },
            'recommandations': self._generer_recommandations(compatibilite, structure)
        }
    
    def _generer_recommandations(self, compatibilite: Dict, structure: Dict) -> List[str]:
        """
        Générer des recommandations basées sur l'analyse
        """
        recommandations = []
        
        if not compatibilite['prepatch_requis']:
            recommandations.append("⚠️ Script prepatch.sql recommandé pour les vérifications pré-installation")
        
        if not compatibilite['postpatch_requis']:
            recommandations.append("⚠️ Script postpatch.sql recommandé pour les vérifications post-installation")
        
        if 'UNIX' in compatibilite['types_patch'] and not compatibilite['structure_unix_complete']:
            recommandations.append("🔧 Structure UNIX incomplète (bin/, lib/, ctl/ requis)")
        
        if compatibilite['niveau_risque'] == 'élevé':
            recommandations.append("⚠️ Patch à haut risque - Validation obligatoire avant déploiement")
        
        return recommandations