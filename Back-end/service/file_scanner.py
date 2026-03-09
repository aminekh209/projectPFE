import os
import zipfile
from typing import List, Dict, Any, Set
from pathlib import Path
import re

class FileScanner:
    
    
    # Extensions par catégorie
    EXTENSIONS = {
        'database': ['.sql', '.dmp', '.bak'],
        'unix': ['.sh', '.bash', '.so', '.bin', '.o', '.a', '.ko'],
        'web': ['.war', '.ear', '.jar', '.js', '.css', '.html'],
        'config': ['.xml', '.properties', '.conf', '.yml', '.yaml', '.cfg', '.ini'],
        'script': ['.py', '.pl', '.rb', '.php', '.js']
    }
    
    # Patterns pour détecter les chemins spécifiques UNIX
    UNIX_PATHS = ['bin/', 'lib/', 'ctl/', 'usr/', 'etc/', 'opt/']
    
    @staticmethod
    def scanner_fichiers_zip(zip_path: str) -> Dict[str, Any]:
       
        resultat = {
            'nom': os.path.basename(zip_path),
            'taille': os.path.getsize(zip_path),
            'fichiers': [],
            'dossiers': set(),
            'extensions': set(),
            'statistiques': {
                'total': 0,
                'database': 0,
                'unix': 0,
                'web': 0,
                'config': 0,
                'script': 0,
                'autre': 0
            }
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    if not info.is_dir():
                        # Analyser le fichier
                        fichier = FileScanner._analyser_fichier(info)
                        resultat['fichiers'].append(fichier)
                        
                        # Mettre à jour les statistiques
                        resultat['statistiques']['total'] += 1
                        cat = fichier['categorie']
                        resultat['statistiques'][cat] = resultat['statistiques'].get(cat, 0) + 1
                        
                        # Ajouter l'extension
                        if fichier['extension']:
                            resultat['extensions'].add(fichier['extension'])
                        
                        # Ajouter le dossier
                        dossier = '/'.join(fichier['nom'].split('/')[:-1])
                        if dossier:
                            resultat['dossiers'].add(dossier)
                            
        except Exception as e:
            raise Exception(f"Erreur lors du scan du ZIP: {str(e)}")
        
        # Convertir les sets en listes pour JSON
        resultat['dossiers'] = list(resultat['dossiers'])
        resultat['extensions'] = list(resultat['extensions'])
        
        return resultat
    
    @staticmethod
    def _analyser_fichier(info: zipfile.ZipInfo) -> Dict[str, Any]:
        """
        Analyser un fichier individuel
        """
        nom = info.filename
        extension = os.path.splitext(nom)[1].lower()
        
        # Déterminer la catégorie
        categorie = FileScanner._determiner_categorie(nom, extension)
        
        # Déterminer le type
        type_fichier = FileScanner._determiner_type(extension)
        
        return {
            'nom': nom,
            'taille': info.file_size,
            'extension': extension,
            'categorie': categorie,
            'type': type_fichier,
            'date_modification': info.date_time,
            'compressé': info.compress_size > 0
        }
    
    @staticmethod
    def _determiner_categorie(nom: str, extension: str) -> str:
       
        # Vérifier par extension
        for cat, exts in FileScanner.EXTENSIONS.items():
            if extension in exts:
                return cat
        
        # Vérifier par chemin UNIX
        for path in FileScanner.UNIX_PATHS:
            if path in nom:
                return 'unix'
        
        return 'autre'
    
    @staticmethod
    def _determiner_type(extension: str) -> str:
       
        if extension in ['.sh', '.bash', '.py', '.pl', '.rb', '.php', '.js']:
            return 'script'
        elif extension in ['.so', '.dll', '.bin', '.o', '.a', '.exe']:
            return 'binaire'
        elif extension in ['.xml', '.properties', '.conf', '.yml', '.yaml', '.cfg', '.ini']:
            return 'configuration'
        elif extension in ['.sql', '.dmp', '.bak']:
            return 'base_donnees'
        elif extension in ['.war', '.ear', '.jar']:
            return 'application_web'
        else:
            return 'fichier'