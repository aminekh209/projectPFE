import re
from typing import List, Dict, Any, Set
import zipfile
import io
from collections import defaultdict

class ActionDetector:
    
    # Patterns SQL avec catégories et sous-types
    SQL_PATTERNS = {
        # DDL - Structure
        'create_table': {
            'pattern': r'CREATE\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Création de table',
            'format': "Création table {}"
        },
        'alter_table': {
            'pattern': r'ALTER\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Modification de table',
            'format': "Modification table {}"
        },
        'drop_table': {
            'pattern': r'DROP\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Suppression de table',
            'format': "Suppression table {}"
        },
        'truncate_table': {
            'pattern': r'TRUNCATE\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Vidage de table',
            'format': "Vidage table {}"
        },
        'rename_table': {
            'pattern': r'RENAME\s+TABLE\s+(\w+)\s+TO\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Renommage de table',
            'format': "Renommage table {} → {}"
        },
        
        # DDL - Index
        'create_index': {
            'pattern': r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Création index',
            'format': "Création index {} sur table {}"
        },
        'drop_index': {
            'pattern': r'DROP\s+INDEX\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Suppression index',
            'format': "Suppression index {}"
        },
        
        # DDL - Vues
        'create_view': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Création vue',
            'format': "Création vue {}"
        },
        'drop_view': {
            'pattern': r'DROP\s+VIEW\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Suppression vue',
            'format': "Suppression vue {}"
        },
        
        # DDL - Séquences
        'create_sequence': {
            'pattern': r'CREATE\s+SEQUENCE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Création séquence',
            'format': "Création séquence {}"
        },
        'drop_sequence': {
            'pattern': r'DROP\s+SEQUENCE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Suppression séquence',
            'format': "Suppression séquence {}"
        },
        
        # DDL - Synonymes
        'create_synonym': {
            'pattern': r'CREATE\s+(?:PUBLIC\s+)?SYNONYM\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Création synonyme',
            'format': "Création synonyme {}"
        },
        
        # DML - Manipulation données
        'insert': {
            'pattern': r'INSERT\s+INTO\s+(\w+)',
            'categorie': 'DML',
            'description': 'Insertion données',
            'format': "Insertion dans {}"
        },
        'update': {
            'pattern': r'UPDATE\s+(\w+)\s+SET',
            'categorie': 'DML',
            'description': 'Mise à jour données',
            'format': "Mise à jour {}"
        },
        'delete': {
            'pattern': r'DELETE\s+FROM\s+(\w+)',
            'categorie': 'DML',
            'description': 'Suppression données',
            'format': "Suppression de {}"
        },
        'merge': {
            'pattern': r'MERGE\s+INTO\s+(\w+)',
            'categorie': 'DML',
            'description': 'Fusion données',
            'format': "Fusion dans {}"
        },
        'upsert': {
            'pattern': r'(?:INSERT\s+OR\s+REPLACE|REPLACE\s+INTO|ON\s+DUPLICATE\s+KEY)',
            'categorie': 'DML',
            'description': 'Insertion/Mise à jour',
            'format': "Upsert dans table"
        },
        
        # DCL - Permissions
        'grant': {
            'pattern': r'GRANT\s+([\w\s,]+)\s+ON\s+(\w+)\s+TO\s+(\w+)',
            'categorie': 'DCL',
            'description': 'Attribution permissions',
            'format': "Grant {} sur {} à {}"
        },
        'revoke': {
            'pattern': r'REVOKE\s+([\w\s,]+)\s+ON\s+(\w+)\s+FROM\s+(\w+)',
            'categorie': 'DCL',
            'description': 'Révocation permissions',
            'format': "Revoke {} sur {} de {}"
        },
        
        # TCL - Transactions
        'commit': {
            'pattern': r'^\s*COMMIT\b',
            'categorie': 'TCL',
            'description': 'Validation transaction',
            'format': "Commit transaction"
        },
        'rollback': {
            'pattern': r'^\s*ROLLBACK\b',
            'categorie': 'TCL',
            'description': 'Annulation transaction',
            'format': "Rollback transaction"
        },
        'savepoint': {
            'pattern': r'SAVEPOINT\s+(\w+)',
            'categorie': 'TCL',
            'description': 'Création point de sauvegarde',
            'format': "Savepoint {}"
        },
        
        # Programmation
        'create_procedure': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Création procédure',
            'format': "Création procédure {}"
        },
        'create_function': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Création fonction',
            'format': "Création fonction {}"
        },
        'create_package': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Création package',
            'format': "Création package {}"
        },
        'create_trigger': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Création trigger',
            'format': "Création trigger {}"
        },
        'drop_procedure': {
            'pattern': r'DROP\s+PROCEDURE\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Suppression procédure',
            'format': "Suppression procédure {}"
        },
        
        # Contraintes
        'add_constraint': {
            'pattern': r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+(?:CONSTRAINT\s+(\w+)\s+)?(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)',
            'categorie': 'DDL',
            'description': 'Ajout contrainte',
            'format': "Ajout contrainte sur {}"
        },
        'drop_constraint': {
            'pattern': r'ALTER\s+TABLE\s+(\w+)\s+DROP\s+(?:CONSTRAINT\s+)?(\w+)',
            'categorie': 'DDL',
            'description': 'Suppression contrainte',
            'format': "Suppression contrainte sur {}"
        }
    }
    
    # Patterns Shell avec catégories
    SHELL_PATTERNS = {
        # Gestion fichiers
        'cp': {
            'pattern': r'cp\s+(\S+)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Copie de fichiers',
            'format': "Copie {} → {}"
        },
        'mv': {
            'pattern': r'mv\s+(\S+)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Déplacement/renommage',
            'format': "Déplacement {} → {}"
        },
        'rm': {
            'pattern': r'rm\s+[\s\S]+',
            'categorie': 'FICHIER',
            'description': 'Suppression fichiers',
            'format': "Suppression fichiers"
        },
        'rm_rf': {
            'pattern': r'rm\s+-(?:rf|fr)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Suppression récursive',
            'format': "Suppression récursive {}"
        },
        'mkdir': {
            'pattern': r'mkdir\s+(?:-p\s+)?(\S+)',
            'categorie': 'FICHIER',
            'description': 'Création dossier',
            'format': "Création dossier {}"
        },
        'touch': {
            'pattern': r'touch\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Création fichier',
            'format': "Création fichier {}"
        },
        'ln': {
            'pattern': r'ln\s+(?:-s\s+)?(\S+)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Création lien',
            'format': "Lien {} → {}"
        },
        
        # Permissions
        'chmod': {
            'pattern': r'chmod\s+(?:-R\s+)?(\d+|[ugo]+[+-=][rwx]+)\s+(\S+)',
            'categorie': 'PERMISSION',
            'description': 'Modification permissions',
            'format': "Permission {} sur {}"
        },
        'chown': {
            'pattern': r'chown\s+(?:-R\s+)?(\S+)\s+(\S+)',
            'categorie': 'PERMISSION',
            'description': 'Modification propriétaire',
            'format': "Changement propriétaire {} pour {}"
        },
        'chgrp': {
            'pattern': r'chgrp\s+(?:-R\s+)?(\S+)\s+(\S+)',
            'categorie': 'PERMISSION',
            'description': 'Modification groupe',
            'format': "Changement groupe {} pour {}"
        },
        
        # Services Systemd
        'systemctl_start': {
            'pattern': r'systemctl\s+start\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Démarrage service',
            'format': "Démarrage service {}"
        },
        'systemctl_stop': {
            'pattern': r'systemctl\s+stop\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Arrêt service',
            'format': "Arrêt service {}"
        },
        'systemctl_restart': {
            'pattern': r'systemctl\s+restart\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Redémarrage service',
            'format': "Redémarrage service {}"
        },
        'systemctl_reload': {
            'pattern': r'systemctl\s+reload\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Rechargement service',
            'format': "Rechargement service {}"
        },
        'systemctl_enable': {
            'pattern': r'systemctl\s+enable\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Activation service',
            'format': "Activation service {}"
        },
        'systemctl_disable': {
            'pattern': r'systemctl\s+disable\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Désactivation service',
            'format': "Désactivation service {}"
        },
        'systemctl_status': {
            'pattern': r'systemctl\s+status\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Statut service',
            'format': "Vérification statut {}"
        },
        
        # Services traditionnels
        'service_start': {
            'pattern': r'service\s+(\S+)\s+start',
            'categorie': 'SERVICE_SYSV',
            'description': 'Démarrage service',
            'format': "Démarrage service {}"
        },
        'service_stop': {
            'pattern': r'service\s+(\S+)\s+stop',
            'categorie': 'SERVICE_SYSV',
            'description': 'Arrêt service',
            'format': "Arrêt service {}"
        },
        'service_restart': {
            'pattern': r'service\s+(\S+)\s+restart',
            'categorie': 'SERVICE_SYSV',
            'description': 'Redémarrage service',
            'format': "Redémarrage service {}"
        },
        'service_reload': {
            'pattern': r'service\s+(\S+)\s+reload',
            'categorie': 'SERVICE_SYSV',
            'description': 'Rechargement service',
            'format': "Rechargement service {}"
        },
        'service_status': {
            'pattern': r'service\s+(\S+)\s+status',
            'categorie': 'SERVICE_SYSV',
            'description': 'Statut service',
            'format': "Vérification statut {}"
        },
        
        # Compression
        'tar_create': {
            'pattern': r'tar\s+(?:-c|--create).+',
            'categorie': 'ARCHIVE',
            'description': 'Création archive tar',
            'format': "Création archive tar"
        },
        'tar_extract': {
            'pattern': r'tar\s+(?:-x|--extract).+',
            'categorie': 'ARCHIVE',
            'description': 'Extraction archive tar',
            'format': "Extraction archive tar"
        },
        'zip_create': {
            'pattern': r'zip\s+(?:-r\s+)?(\S+)\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Création archive zip',
            'format': "Création {} → {}"
        },
        'unzip': {
            'pattern': r'unzip\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Extraction archive zip',
            'format': "Extraction {}"
        },
        'gzip': {
            'pattern': r'gzip\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Compression gzip',
            'format': "Compression {}"
        },
        'gunzip': {
            'pattern': r'gunzip\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Décompression gzip',
            'format': "Décompression {}"
        },
        
        # Installation paquets
        'apt_install': {
            'pattern': r'apt(?:-get)?\s+install\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Installation paquet',
            'format': "Installation {}"
        },
        'apt_remove': {
            'pattern': r'apt(?:-get)?\s+remove\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Suppression paquet',
            'format': "Suppression {}"
        },
        'apt_update': {
            'pattern': r'apt(?:-get)?\s+update',
            'categorie': 'PACKAGE',
            'description': 'Mise à jour index',
            'format': "Mise à jour index paquets"
        },
        'apt_upgrade': {
            'pattern': r'apt(?:-get)?\s+upgrade(?:\s+-y)?',
            'categorie': 'PACKAGE',
            'description': 'Mise à jour système',
            'format': "Mise à jour paquets"
        },
        'yum_install': {
            'pattern': r'yum\s+install\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Installation paquet',
            'format': "Installation {}"
        },
        'yum_remove': {
            'pattern': r'yum\s+remove\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Suppression paquet',
            'format': "Suppression {}"
        },
        
        # Édition texte
        'sed': {
            'pattern': r'sed\s+(?:-i\s+)?[\'"]([^\'"]+)[\'"]\s+(\S+)',
            'categorie': 'TEXTE',
            'description': 'Modification texte',
            'format': "Substitution '{}' dans {}"
        },
        'awk': {
            'pattern': r'awk\s+[\'"][^\'"]+[\'"]\s+(\S+)',
            'categorie': 'TEXTE',
            'description': 'Traitement texte',
            'format': "Traitement awk sur {}"
        },
        'grep': {
            'pattern': r'grep\s+(?:-r\s+)?[\'"]([^\'"]+)[\'"]\s+(\S+)',
            'categorie': 'RECHERCHE',
            'description': 'Recherche texte',
            'format': "Recherche '{}' dans {}"
        },
        'find': {
            'pattern': r'find\s+(\S+)\s+-name\s+[\'"]([^\'"]+)[\'"]',
            'categorie': 'RECHERCHE',
            'description': 'Recherche fichiers',
            'format': "Recherche {} dans {}"
        }
    }
    
    # Patterns Configuration avec catégories
    CONFIG_PATTERNS = {
        # Base de données
        'datasource_jdbc': {
            'pattern': r'<datasource|<jdbc|jdbc\.|database\.',
            'categorie': 'DATABASE',
            'description': 'Configuration source de données',
            'format': "Configuration JDBC Datasource"
        },
        'datasource_jndi': {
            'pattern': r'jndi|java:comp/env',
            'categorie': 'DATABASE',
            'description': 'Configuration JNDI',
            'format': "Configuration JNDI Datasource"
        },
        'connection_pool': {
            'pattern': r'max(?:imum)?-?pool|min(?:imum)?-?pool|connectionTimeout|validationQuery',
            'categorie': 'DATABASE',
            'description': 'Configuration pool connexions',
            'format': "Configuration pool de connexions"
        },
        
        # Réseau
        'port_http': {
            'pattern': r'port\s*=\s*(?:80|8080|8000|8081)|httpPort',
            'categorie': 'RESEAU',
            'description': 'Configuration port HTTP',
            'format': "Configuration port HTTP"
        },
        'port_https': {
            'pattern': r'port\s*=\s*(?:443|8443)|httpsPort',
            'categorie': 'RESEAU',
            'description': 'Configuration port HTTPS',
            'format': "Configuration port HTTPS"
        },
        'port_autres': {
            'pattern': r'port\s*=\s*\d+|port>\d+',
            'categorie': 'RESEAU',
            'description': 'Configuration port',
            'format': "Configuration port"
        },
        'host': {
            'pattern': r'host\s*=|serverName|address',
            'categorie': 'RESEAU',
            'description': 'Configuration hôte',
            'format': "Configuration hôte"
        },
        
        # Authentification
        'auth_basic': {
            'pattern': r'basic\s+auth|BASIC',
            'categorie': 'AUTH',
            'description': 'Authentification basique',
            'format': "Configuration auth basique"
        },
        'auth_ldap': {
            'pattern': r'ldap|LDAP',
            'categorie': 'AUTH',
            'description': 'Authentification LDAP',
            'format': "Configuration LDAP"
        },
        'auth_kerberos': {
            'pattern': r'kerberos|KRB5',
            'categorie': 'AUTH',
            'description': 'Authentification Kerberos',
            'format': "Configuration Kerberos"
        },
        'auth_oauth': {
            'pattern': r'oauth|OAuth|OIDC|openid',
            'categorie': 'AUTH',
            'description': 'Authentification OAuth',
            'format': "Configuration OAuth"
        },
        'credentials': {
            'pattern': r'password|username|user\s*=|credential',
            'categorie': 'AUTH',
            'description': 'Configuration identifiants',
            'format': "Configuration credentials"
        },
        
        # Logging
        'log_level': {
            'pattern': r'log(?:ger)?\.level|log(?:ger)?-level|<level>',
            'categorie': 'LOGGING',
            'description': 'Configuration niveau logs',
            'format': "Configuration niveau logging"
        },
        'log_file': {
            'pattern': r'log(?:ger)?\.file|log(?:ger)?-file|fileHandler',
            'categorie': 'LOGGING',
            'description': 'Configuration fichier logs',
            'format': "Configuration fichier logs"
        },
        'log_rotation': {
            'pattern': r'rotation|maxFileSize|maxBackup|rolling',
            'categorie': 'LOGGING',
            'description': 'Configuration rotation logs',
            'format': "Configuration rotation logs"
        },
        'log_appender': {
            'pattern': r'appender|Appender|<appender',
            'categorie': 'LOGGING',
            'description': 'Configuration appender logs',
            'format': "Configuration appender"
        },
        
        # Cache
        'cache_ehcache': {
            'pattern': r'ehcache|Ehcache|<cache',
            'categorie': 'CACHE',
            'description': 'Configuration Ehcache',
            'format': "Configuration cache Ehcache"
        },
        'cache_redis': {
            'pattern': r'redis|Redis',
            'categorie': 'CACHE',
            'description': 'Configuration Redis',
            'format': "Configuration cache Redis"
        },
        'cache_memcached': {
            'pattern': r'memcached|Memcached',
            'categorie': 'CACHE',
            'description': 'Configuration Memcached',
            'format': "Configuration cache Memcached"
        },
        'cache_parameters': {
            'pattern': r'cache\.|timeToLive|maxEntries|ttl',
            'categorie': 'CACHE',
            'description': 'Configuration paramètres cache',
            'format': "Configuration paramètres cache"
        },
        
        # Timeout
        'timeout_connection': {
            'pattern': r'connectionTimeout|connectTimeout',
            'categorie': 'TIMEOUT',
            'description': 'Timeout connexion',
            'format': "Configuration timeout connexion"
        },
        'timeout_request': {
            'pattern': r'requestTimeout|readTimeout|socketTimeout',
            'categorie': 'TIMEOUT',
            'description': 'Timeout requête',
            'format': "Configuration timeout requête"
        },
        'timeout_session': {
            'pattern': r'sessionTimeout|session-timeout',
            'categorie': 'TIMEOUT',
            'description': 'Timeout session',
            'format': "Configuration timeout session"
        },
        'timeout_transaction': {
            'pattern': r'transactionTimeout|txTimeout',
            'categorie': 'TIMEOUT',
            'description': 'Timeout transaction',
            'format': "Configuration timeout transaction"
        },
        
        # JVM
        'jvm_heap': {
            'pattern': r'Xms|Xmx|-XX:\+HeapDump',
            'categorie': 'JVM',
            'description': 'Configuration mémoire JVM',
            'format': "Configuration mémoire JVM"
        },
        'jvm_gc': {
            'pattern': r'GC|GarbageCollection|-XX:\+Use\w+GC',
            'categorie': 'JVM',
            'description': 'Configuration GC JVM',
            'format': "Configuration garbage collector"
        },
        'jvm_arguments': {
            'pattern': r'JAVA_OPTS|JAVA_ARGS|jvmArgs',
            'categorie': 'JVM',
            'description': 'Arguments JVM',
            'format': "Configuration arguments JVM"
        },
        
        # Sécurité
        'ssl_tls': {
            'pattern': r'ssl|tls|keystore|truststore|certificate',
            'categorie': 'SECURITE',
            'description': 'Configuration SSL/TLS',
            'format': "Configuration SSL/TLS"
        },
        'cors': {
            'pattern': r'cors|CORS|cross-origin',
            'categorie': 'SECURITE',
            'description': 'Configuration CORS',
            'format': "Configuration CORS"
        },
        'csrf': {
            'pattern': r'csrf|CSRF|XSRF',
            'categorie': 'SECURITE',
            'description': 'Configuration CSRF',
            'format': "Configuration CSRF"
        }
    }
    
    @staticmethod
    async def detecter_actions_dans_zip(file_content: bytes) -> Dict[str, Any]:
        """
        Détecter toutes les actions dans un fichier ZIP (Architecture Streaming optimisée)
        """
        actions_globales = []
        actions_par_fichier = []
        types_detectes = set()
        categories_stats = defaultdict(int)
        
        fichiers_presents = []
        try:
            zip_file = io.BytesIO(file_content)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                for zip_info in zip_ref.infolist():
                    if not zip_info.is_dir():
                        fichiers_presents.append(zip_info.filename)
                        # ✅ SOLUTION ANTI-CRASH : Utilisation d'un flux (stream) au lieu de tout charger en RAM
                        with zip_ref.open(zip_info) as f:
                            text_stream = io.TextIOWrapper(f, encoding='utf-8', errors='ignore')
                            
                            # Détecter les actions dans ce fichier (via le flux)
                            actions = ActionDetector._detecter_actions_dans_fichier(
                                zip_info.filename, text_stream
                            )
                        
                        if actions:
                            actions_par_fichier.append({
                                'fichier': zip_info.filename,
                                'actions': actions
                            })
                            
                            # Ajouter aux actions globales avec contexte
                            for action in actions:
                                actions_globales.append({
                                    'description': action['description'],
                                    'categorie': action['categorie'],
                                    'type': action.get('type', 'GENERAL'),
                                    'contexte': zip_info.filename
                                })
                                categories_stats[action['categorie']] += 1
                        
                        # Détecter le type
                        type_fichier = ActionDetector._detecter_type_fichier(zip_info.filename)
                        if type_fichier:
                            types_detectes.add(type_fichier)
                            
        except Exception as e:
            raise Exception(f"Erreur détection actions: {str(e)}")
        
        return {
            'actions_globales': actions_globales,
            'actions_par_fichier': actions_par_fichier,
            'fichiers_presents': fichiers_presents,
            'types_detectes': list(types_detectes),
            'nombre_actions': len(actions_globales),
            'statistiques_categories': dict(categories_stats)
        }
    
    @staticmethod
    def _detecter_actions_dans_fichier(nom_fichier: str, text_stream) -> List[Dict[str, str]]:
        """
        Détecter les actions dans un fichier spécifique via flux de texte
        """
        actions = []
        # 🔥 1. DÉTECTION STRUCTURELLE (L'action de copier/remplacer le fichier lui-même)
        actions.extend(ActionDetector._detecter_actions_structurelles(nom_fichier))

        # 🔥 2. DÉTECTION DU CONTENU (Ce que fait le fichier de l'intérieur)
        extension = nom_fichier.split('.')[-1].lower() if '.' in nom_fichier else ''
        
        # Actions SQL
        if extension == 'sql':
            actions.extend(ActionDetector._detecter_actions_sql(text_stream))
        
        # Actions Shell
        elif extension in ['sh', 'bash']:
            actions.extend(ActionDetector._detecter_actions_shell(text_stream))
        
        # Actions Configuration
        elif extension in ['xml', 'properties', 'conf', 'yml', 'yaml', 'cfg', 'ini']:
            actions.extend(ActionDetector._detecter_actions_config(text_stream))
        
        # Actions Web
        elif extension in ['war', 'ear', 'jar']:
            actions.append({
                'description': f"Déploiement application {extension.upper()}",
                'categorie': 'APPLICATION',
                'type': 'WEB'
            })
            
        return actions

    @staticmethod
    def _detecter_actions_sql(text_stream) -> List[Dict[str, str]]:
        """
        Détecte les actions SQL en gérant intelligemment le multi-lignes avec un buffer.
        """
        actions = []
        actions_vues = set()
        buffer_instruction = ""
        
        for ligne in text_stream:
            # 1. Accumulation du texte (multi-lignes)
            buffer_instruction += " " + ligne.strip()
            
            # 2. Une instruction se termine par ';' ou est un mot-clé de transaction
            if ';' in ligne or ligne.strip().upper().startswith(('COMMIT', 'ROLLBACK')):
                instruction_upper = buffer_instruction.upper()
                
                # 3. Test des Regex sur l'instruction COMPLÈTE
                for action_key, action_info in ActionDetector.SQL_PATTERNS.items():
                    match = re.search(action_info['pattern'], instruction_upper, re.IGNORECASE)
                    if match:
                        try:
                            description = action_info['format'].format(*match.groups()) if match.groups() else action_info['format']
                        except:
                            description = action_info['description']
                        
                        action_key_unique = f"{action_info['categorie']}:{description}"
                        
                        if action_key_unique not in actions_vues:
                            actions_vues.add(action_key_unique)
                            actions.append({
                                'description': description,
                                'categorie': action_info['categorie'],
                                'type': action_key
                            })
                            
                # 4. On vide le tampon pour la prochaine instruction
                buffer_instruction = ""
                
        return actions

    @staticmethod
    def _detecter_actions_shell(text_stream) -> List[Dict[str, str]]:
        """
        Détecter les actions dans un script shell.
        """
        actions = []
        actions_vues = set()
        
        for ligne in text_stream:
            ligne = ligne.strip()
            # Ignorer les commentaires ou lignes vides
            if ligne.startswith('#') or not ligne:
                continue
                
            for action_key, action_info in ActionDetector.SHELL_PATTERNS.items():
                match = re.search(action_info['pattern'], ligne)
                if match:
                    try:
                        description = action_info['format'].format(*match.groups()) if match.groups() else action_info['format']
                    except:
                        description = action_info['description']
                    
                    action_key_unique = f"{action_info['categorie']}:{description}"
                    
                    if action_key_unique not in actions_vues:
                        actions_vues.add(action_key_unique)
                        actions.append({
                            'description': description,
                            'categorie': action_info['categorie'],
                            'type': action_key
                        })
        return actions

    @staticmethod
    def _detecter_actions_config(text_stream) -> List[Dict[str, str]]:
        """
        Détecter les actions dans un fichier de configuration.
        """
        actions = []
        actions_vues = set()
        
        for ligne in text_stream:
            for action_key, action_info in ActionDetector.CONFIG_PATTERNS.items():
                if re.search(action_info['pattern'], ligne, re.IGNORECASE):
                    action_key_unique = f"{action_info['categorie']}:{action_info['description']}"
                    
                    if action_key_unique not in actions_vues:
                        actions_vues.add(action_key_unique)
                        actions.append({
                            'description': action_info['format'],
                            'categorie': action_info['categorie'],
                            'type': action_key
                        })
        return actions
    
    @staticmethod
    def _detecter_type_fichier(nom_fichier: str) -> str:
        nom_lower = nom_fichier.lower()
        
        # On vérifie l'UNIX en premier (très important pour ne pas confondre avec DB)
        if any(x in nom_lower for x in ['bin/', 'lib/', 'ctl/', 'usr/', 'etc/']):
            return 'UNIX'
            
        # 🔥 MODIFICATION : DB s'applique aux .sql, .sh, ou s'il y a un dossier /DB/
        elif '.sql' in nom_lower or '.sh' in nom_lower or '/db/' in nom_lower or nom_lower.startswith('db/'):
            return 'DB'
            
        elif any(x in nom_lower for x in ['.war', '.ear', '.jar', 'powercard', 'webapps', '/bo/']):
            return 'WEB'
            
        elif any(x in nom_lower for x in ['.xml', '.properties', '.conf', '.yml']):
            return 'CONFIG'
            
        return None
    
    @staticmethod
    def _detecter_actions_structurelles(nom_fichier: str) -> List[Dict[str, str]]:
        """
        Détecte l'action physique de déploiement d'un fichier (Ajout ou Remplacement)
        basée sur les arborescences standard UNIX / Linux.
        """
        actions = []
        
        # Les répertoires standards UNIX que vous avez mentionnés
        repertoires_unix = [
            'usr/bin/', 'usr/sbin/', 'usr/lib/', 'usr/lib64/', 
            'usr/local/', 'usr/share/', 'usr/include/', 'usr/src/',
            'bin/', 'sbin/', 'lib/', 'etc/', 'opt/'
        ]
        
        # Vérifie si le fichier se trouve dans un de ces dossiers UNIX
        if any(rep in nom_fichier for rep in repertoires_unix):
            actions.append({
                'description': f"Mise à jour / Déploiement du fichier : {nom_fichier}",
                'categorie': 'DEPLOIEMENT_UNIX',
                'type': 'REMPLACEMENT_OU_AJOUT'
            })
            
        return actions