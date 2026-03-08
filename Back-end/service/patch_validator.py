from typing import Dict, Any, List

class PatchValidator:
    
    
    def valider_patch(self, analyse_data: Dict, patch_type: str, component: str) -> Dict[str, Any]:
        erreurs = []
        avertissements = []
        
        # Si on n'a pas de données d'analyse (ex: pas de ZIP uploadé), on laisse passer ou on gère autrement
        if not analyse_data:
            return {'valide': True, 'erreurs': [], 'avertissements': []}
        donnees_utiles = analyse_data.get('actions', analyse_data)
        # 1. Vérification Globale du Type
        types_detectes = donnees_utiles.get('types_detectes', [])
        
        # LE BON CODE (Avec la tolérance pour les scripts DB) :
        if patch_type == 'DB' and 'UNIX' in types_detectes and 'DB' not in types_detectes:
            pass # C'est normal, c'est un script shell pour la DB
        elif patch_type not in types_detectes and patch_type != 'OTHER':
            types_str = ', '.join(types_detectes) if types_detectes else 'Aucun type reconnu'
            erreurs.append(f"Incohérence : Vous avez déclaré un patch de type '{patch_type}', mais le scanner a détecté : [{types_str}].")

        # 2. Récupération des noms de fichiers trouvés dans le ZIP
        # On extrait les noms de fichiers depuis la liste 'actions_par_fichier'
        fichiers_scannes = donnees_utiles.get('fichiers_presents', [])
        
        # Sécurité au cas où l'analyse a été faite avec l'ancienne version
        if not fichiers_scannes:
            fichiers_scannes = [item['fichier'] for item in analyse_data.get('actions_par_fichier', [])]

        # 3. Vérifications Spécifiques selon le type déclaré par l'utilisateur
        if patch_type == 'DB':
            self._verifier_config_db(fichiers_scannes, erreurs, avertissements)
        elif patch_type == 'UNIX':
            self._verifier_config_unix(fichiers_scannes, erreurs, avertissements)
        elif patch_type == 'WEB':
            self._verifier_config_web(fichiers_scannes, component, erreurs, avertissements)
            
        return {
            'valide': len(erreurs) == 0, # C'est valide SEULEMENT si la liste d'erreurs est vide
            'erreurs': erreurs,
            'avertissements': avertissements
        }

    def _verifier_config_db(self, fichiers: List[str], erreurs: List, avertissements: List):
        fichiers_sh = [f for f in fichiers if f.endswith(('.sh', '.bash'))]
        
        # 1. Règle DB : Il faut des scripts .sh
        if not fichiers_sh:
            erreurs.append("Sécurité DB : Aucun script d'exécution (.sh) n'a été trouvé pour appliquer le patch base de données.")
            
        
        if any('usr/' in f.lower() for f in fichiers):
            erreurs.append("Incohérence critique : Un patch DB ne doit pas contenir de répertoires système UNIX (comme /usr/). Il s'agit très probablement d'un patch UNIX.")
            
        # 3. Avertissements standards PowerCard
        if not any('prepatch' in f.lower() for f in fichiers):
            avertissements.append("Script prepatch manquant (Généralement requis pour les patchs DB).")
        if not any('postpatch' in f.lower() for f in fichiers):
            avertissements.append("Script postpatch manquant (Recommandé pour compiler les objets invalides).")

    def _verifier_config_unix(self, fichiers: List[str], erreurs: List, avertissements: List):
        
        if not any('usr/' in f.lower() for f in fichiers):
            erreurs.append("Sécurité UNIX : L'arborescence système requise ('/usr/') est absente de l'archive. Ce n'est pas un patch UNIX PowerCard valide.")
            
        if not any(f.endswith(('.sh', '.bash')) for f in fichiers):
            avertissements.append("Aucun script d'exécution shell (.sh) trouvé. Le patch sera uniquement de la copie de fichiers.")

    def _verifier_config_web(self, fichiers: List[str], component: str, erreurs: List, avertissements: List):
        fichiers_web = [f for f in fichiers if f.endswith(('.war', '.ear', '.jar'))]
        
        if not fichiers_web:
            erreurs.append("Sécurité WEB : Aucun fichier applicatif (.war, .ear, .jar) trouvé dans l'archive.")
            
        if component == 'BO' and not any('powercard' in f.lower() for f in fichiers):
            avertissements.append("Composant BO : Le nom 'powercard' n'apparaît dans aucun fichier.")