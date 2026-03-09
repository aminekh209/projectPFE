from typing import Dict, Any, List

class PatchValidator:
    
    def valider_patch(self, analyse_data: Dict, patch_type: str, component: str) -> Dict[str, Any]:
        erreurs = []
        avertissements = []
        
        # If there is no analysis data (e.g., no uploaded ZIP), we let it pass or handle it otherwise
        if not analyse_data:
            return {'valide': True, 'erreurs': [], 'avertissements': []}
            
        donnees_utiles = analyse_data.get('actions', analyse_data)
        
        # 1. Global Type Verification
        types_detectes = donnees_utiles.get('types_detectes', [])
        
        # CORRECT CODE (With tolerance for DB scripts):
        if patch_type == 'DB' and 'UNIX' in types_detectes and 'DB' not in types_detectes:
            pass # This is normal, it's a shell script for the DB
        elif patch_type not in types_detectes and patch_type != 'OTHER':
            types_str = ', '.join(types_detectes) if types_detectes else 'No type recognized'
            erreurs.append(f"Inconsistency: You declared a patch of type '{patch_type}', but the scanner detected: [{types_str}].")

        # 2. Retrieve file names found in the ZIP
        # Extract file names from the 'fichiers_presents' list
        fichiers_scannes = donnees_utiles.get('fichiers_presents', [])
        
        # Security fallback in case the analysis was done with an older version of the scanner
        if not fichiers_scannes:
            fichiers_scannes = [item['fichier'] for item in analyse_data.get('actions_par_fichier', [])]

        # 3. Specific verifications based on user-declared type
        if patch_type == 'DB':
            self._verifier_config_db(fichiers_scannes, erreurs, avertissements)
        elif patch_type == 'UNIX':
            self._verifier_config_unix(fichiers_scannes, erreurs, avertissements)
        elif patch_type == 'WEB':
            self._verifier_config_web(fichiers_scannes, component, erreurs, avertissements)
            
        return {
            'valide': len(erreurs) == 0, # It is valid ONLY if the error list is empty
            'erreurs': erreurs,
            'avertissements': avertissements
        }

    def _verifier_config_db(self, fichiers: List[str], erreurs: List, avertissements: List):
        fichiers_sh = [f for f in fichiers if f.endswith(('.sh', '.bash'))]
        
        # 1. DB Rule: .sh scripts are required
        if not fichiers_sh:
            erreurs.append("DB Security: No execution script (.sh) was found to apply the database patch.")
            
        if any('usr/' in f.lower() for f in fichiers):
            erreurs.append("Critical inconsistency: A DB patch must not contain UNIX system directories (like /usr/). This is most likely a UNIX patch.")
            
        # 3. Standard PowerCard warnings
        if not any('prepatch' in f.lower() for f in fichiers):
            avertissements.append("Missing prepatch script (Generally required for DB patches).")
        if not any('postpatch' in f.lower() for f in fichiers):
            avertissements.append("Missing postpatch script (Recommended to compile invalid objects).")

    def _verifier_config_unix(self, fichiers: List[str], erreurs: List, avertissements: List):
        
        if not any('usr/' in f.lower() for f in fichiers):
            erreurs.append("UNIX Security: The required system directory structure ('/usr/') is missing from the archive. This is not a valid PowerCard UNIX patch.")
            
        if not any(f.endswith(('.sh', '.bash')) for f in fichiers):
            avertissements.append("No shell execution script (.sh) found. The patch will only consist of file copying.")

    def _verifier_config_web(self, fichiers: List[str], component: str, erreurs: List, avertissements: List):
        fichiers_web = [f for f in fichiers if f.endswith(('.war', '.ear', '.jar'))]
        
        if not fichiers_web:
            erreurs.append("WEB Security: No application file (.war, .ear, .jar) found in the archive.")
            
        if component == 'BO' and not any('powercard' in f.lower() for f in fichiers):
            avertissements.append("BO Component: The name 'powercard' does not appear in any file.")