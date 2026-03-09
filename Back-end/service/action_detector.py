import re
from typing import List, Dict, Any, Set
import zipfile
import io
from collections import defaultdict

class ActionDetector:
    
    # SQL Patterns with categories and sub-types
    SQL_PATTERNS = {
        # DDL - Structure
        'create_table': {
            'pattern': r'CREATE\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Table creation',
            'format': "Table creation {}"
        },
        'alter_table': {
            'pattern': r'ALTER\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Table modification',
            'format': "Table modification {}"
        },
        'drop_table': {
            'pattern': r'DROP\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Table deletion',
            'format': "Table deletion {}"
        },
        'truncate_table': {
            'pattern': r'TRUNCATE\s+TABLE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Table truncation',
            'format': "Table truncation {}"
        },
        'rename_table': {
            'pattern': r'RENAME\s+TABLE\s+(\w+)\s+TO\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Table renaming',
            'format': "Table renaming {} → {}"
        },
        
        # DDL - Index
        'create_index': {
            'pattern': r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Index creation',
            'format': "Index creation {} on table {}"
        },
        'drop_index': {
            'pattern': r'DROP\s+INDEX\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Index deletion',
            'format': "Index deletion {}"
        },
        
        # DDL - Views
        'create_view': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)',
            'categorie': 'DDL',
            'description': 'View creation',
            'format': "View creation {}"
        },
        'drop_view': {
            'pattern': r'DROP\s+VIEW\s+(\w+)',
            'categorie': 'DDL',
            'description': 'View deletion',
            'format': "View deletion {}"
        },
        
        # DDL - Sequences
        'create_sequence': {
            'pattern': r'CREATE\s+SEQUENCE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Sequence creation',
            'format': "Sequence creation {}"
        },
        'drop_sequence': {
            'pattern': r'DROP\s+SEQUENCE\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Sequence deletion',
            'format': "Sequence deletion {}"
        },
        
        # DDL - Synonyms
        'create_synonym': {
            'pattern': r'CREATE\s+(?:PUBLIC\s+)?SYNONYM\s+(\w+)',
            'categorie': 'DDL',
            'description': 'Synonym creation',
            'format': "Synonym creation {}"
        },
        
        # DML - Data Manipulation
        'insert': {
            'pattern': r'INSERT\s+INTO\s+(\w+)',
            'categorie': 'DML',
            'description': 'Data insertion',
            'format': "Insertion into {}"
        },
        'update': {
            'pattern': r'UPDATE\s+(\w+)\s+SET',
            'categorie': 'DML',
            'description': 'Data update',
            'format': "Update on {}"
        },
        'delete': {
            'pattern': r'DELETE\s+FROM\s+(\w+)',
            'categorie': 'DML',
            'description': 'Data deletion',
            'format': "Deletion from {}"
        },
        'merge': {
            'pattern': r'MERGE\s+INTO\s+(\w+)',
            'categorie': 'DML',
            'description': 'Data merge',
            'format': "Merge into {}"
        },
        'upsert': {
            'pattern': r'(?:INSERT\s+OR\s+REPLACE|REPLACE\s+INTO|ON\s+DUPLICATE\s+KEY)',
            'categorie': 'DML',
            'description': 'Insertion/Update (Upsert)',
            'format': "Upsert in table"
        },
        
        # DCL - Permissions
        'grant': {
            'pattern': r'GRANT\s+([\w\s,]+)\s+ON\s+(\w+)\s+TO\s+(\w+)',
            'categorie': 'DCL',
            'description': 'Permission grant',
            'format': "Grant {} on {} to {}"
        },
        'revoke': {
            'pattern': r'REVOKE\s+([\w\s,]+)\s+ON\s+(\w+)\s+FROM\s+(\w+)',
            'categorie': 'DCL',
            'description': 'Permission revoke',
            'format': "Revoke {} on {} from {}"
        },
        
        # TCL - Transactions
        'commit': {
            'pattern': r'^\s*COMMIT\b',
            'categorie': 'TCL',
            'description': 'Transaction commit',
            'format': "Commit transaction"
        },
        'rollback': {
            'pattern': r'^\s*ROLLBACK\b',
            'categorie': 'TCL',
            'description': 'Transaction rollback',
            'format': "Rollback transaction"
        },
        'savepoint': {
            'pattern': r'SAVEPOINT\s+(\w+)',
            'categorie': 'TCL',
            'description': 'Savepoint creation',
            'format': "Savepoint {}"
        },
        
        # Programming
        'create_procedure': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Procedure creation',
            'format': "Procedure creation {}"
        },
        'create_function': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Function creation',
            'format': "Function creation {}"
        },
        'create_package': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Package creation',
            'format': "Package creation {}"
        },
        'create_trigger': {
            'pattern': r'CREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Trigger creation',
            'format': "Trigger creation {}"
        },
        'drop_procedure': {
            'pattern': r'DROP\s+PROCEDURE\s+(\w+)',
            'categorie': 'PLSQL',
            'description': 'Procedure deletion',
            'format': "Procedure deletion {}"
        },
        
        # Constraints
        'add_constraint': {
            'pattern': r'ALTER\s+TABLE\s+(\w+)\s+ADD\s+(?:CONSTRAINT\s+(\w+)\s+)?(PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)',
            'categorie': 'DDL',
            'description': 'Constraint addition',
            'format': "Add constraint on {}"
        },
        'drop_constraint': {
            'pattern': r'ALTER\s+TABLE\s+(\w+)\s+DROP\s+(?:CONSTRAINT\s+)?(\w+)',
            'categorie': 'DDL',
            'description': 'Constraint deletion',
            'format': "Drop constraint on {}"
        }
    }
    
    # Shell Patterns with categories
    SHELL_PATTERNS = {
        # File management
        'cp': {
            'pattern': r'cp\s+(\S+)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'File copy',
            'format': "Copy {} → {}"
        },
        'mv': {
            'pattern': r'mv\s+(\S+)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Move/Rename file',
            'format': "Move {} → {}"
        },
        'rm': {
            'pattern': r'rm\s+[\s\S]+',
            'categorie': 'FICHIER',
            'description': 'File deletion',
            'format': "Delete files"
        },
        'rm_rf': {
            'pattern': r'rm\s+-(?:rf|fr)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Recursive deletion',
            'format': "Recursive deletion {}"
        },
        'mkdir': {
            'pattern': r'mkdir\s+(?:-p\s+)?(\S+)',
            'categorie': 'FICHIER',
            'description': 'Directory creation',
            'format': "Directory creation {}"
        },
        'touch': {
            'pattern': r'touch\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'File creation',
            'format': "File creation {}"
        },
        'ln': {
            'pattern': r'ln\s+(?:-s\s+)?(\S+)\s+(\S+)',
            'categorie': 'FICHIER',
            'description': 'Link creation',
            'format': "Link {} → {}"
        },
        
        # Permissions
        'chmod': {
            'pattern': r'chmod\s+(?:-R\s+)?(\d+|[ugo]+[+-=][rwx]+)\s+(\S+)',
            'categorie': 'PERMISSION',
            'description': 'Permission modification',
            'format': "Permission {} on {}"
        },
        'chown': {
            'pattern': r'chown\s+(?:-R\s+)?(\S+)\s+(\S+)',
            'categorie': 'PERMISSION',
            'description': 'Owner modification',
            'format': "Change owner {} for {}"
        },
        'chgrp': {
            'pattern': r'chgrp\s+(?:-R\s+)?(\S+)\s+(\S+)',
            'categorie': 'PERMISSION',
            'description': 'Group modification',
            'format': "Change group {} for {}"
        },
        
        # Systemd Services
        'systemctl_start': {
            'pattern': r'systemctl\s+start\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service start',
            'format': "Start service {}"
        },
        'systemctl_stop': {
            'pattern': r'systemctl\s+stop\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service stop',
            'format': "Stop service {}"
        },
        'systemctl_restart': {
            'pattern': r'systemctl\s+restart\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service restart',
            'format': "Restart service {}"
        },
        'systemctl_reload': {
            'pattern': r'systemctl\s+reload\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service reload',
            'format': "Reload service {}"
        },
        'systemctl_enable': {
            'pattern': r'systemctl\s+enable\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service enable',
            'format': "Enable service {}"
        },
        'systemctl_disable': {
            'pattern': r'systemctl\s+disable\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service disable',
            'format': "Disable service {}"
        },
        'systemctl_status': {
            'pattern': r'systemctl\s+status\s+(\S+)',
            'categorie': 'SERVICE_SYSTEMD',
            'description': 'Service status',
            'format': "Check status {}"
        },
        
        # Traditional Services
        'service_start': {
            'pattern': r'service\s+(\S+)\s+start',
            'categorie': 'SERVICE_SYSV',
            'description': 'Service start',
            'format': "Start service {}"
        },
        'service_stop': {
            'pattern': r'service\s+(\S+)\s+stop',
            'categorie': 'SERVICE_SYSV',
            'description': 'Service stop',
            'format': "Stop service {}"
        },
        'service_restart': {
            'pattern': r'service\s+(\S+)\s+restart',
            'categorie': 'SERVICE_SYSV',
            'description': 'Service restart',
            'format': "Restart service {}"
        },
        'service_reload': {
            'pattern': r'service\s+(\S+)\s+reload',
            'categorie': 'SERVICE_SYSV',
            'description': 'Service reload',
            'format': "Reload service {}"
        },
        'service_status': {
            'pattern': r'service\s+(\S+)\s+status',
            'categorie': 'SERVICE_SYSV',
            'description': 'Service status',
            'format': "Check status {}"
        },
        
        # Compression
        'tar_create': {
            'pattern': r'tar\s+(?:-c|--create).+',
            'categorie': 'ARCHIVE',
            'description': 'Tar archive creation',
            'format': "Create tar archive"
        },
        'tar_extract': {
            'pattern': r'tar\s+(?:-x|--extract).+',
            'categorie': 'ARCHIVE',
            'description': 'Tar archive extraction',
            'format': "Extract tar archive"
        },
        'zip_create': {
            'pattern': r'zip\s+(?:-r\s+)?(\S+)\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Zip archive creation',
            'format': "Create {} → {}"
        },
        'unzip': {
            'pattern': r'unzip\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Zip archive extraction',
            'format': "Extract {}"
        },
        'gzip': {
            'pattern': r'gzip\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Gzip compression',
            'format': "Compress {}"
        },
        'gunzip': {
            'pattern': r'gunzip\s+(\S+)',
            'categorie': 'ARCHIVE',
            'description': 'Gzip decompression',
            'format': "Decompress {}"
        },
        
        # Package installation
        'apt_install': {
            'pattern': r'apt(?:-get)?\s+install\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Package installation',
            'format': "Install {}"
        },
        'apt_remove': {
            'pattern': r'apt(?:-get)?\s+remove\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Package removal',
            'format': "Remove {}"
        },
        'apt_update': {
            'pattern': r'apt(?:-get)?\s+update',
            'categorie': 'PACKAGE',
            'description': 'Package index update',
            'format': "Update package index"
        },
        'apt_upgrade': {
            'pattern': r'apt(?:-get)?\s+upgrade(?:\s+-y)?',
            'categorie': 'PACKAGE',
            'description': 'System upgrade',
            'format': "Upgrade packages"
        },
        'yum_install': {
            'pattern': r'yum\s+install\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Package installation',
            'format': "Install {}"
        },
        'yum_remove': {
            'pattern': r'yum\s+remove\s+(?:-y\s+)?(\S+)',
            'categorie': 'PACKAGE',
            'description': 'Package removal',
            'format': "Remove {}"
        },
        
        # Text editing
        'sed': {
            'pattern': r'sed\s+(?:-i\s+)?[\'"]([^\'"]+)[\'"]\s+(\S+)',
            'categorie': 'TEXTE',
            'description': 'Text modification',
            'format': "Substitute '{}' in {}"
        },
        'awk': {
            'pattern': r'awk\s+[\'"][^\'"]+[\'"]\s+(\S+)',
            'categorie': 'TEXTE',
            'description': 'Text processing',
            'format': "Awk processing on {}"
        },
        'grep': {
            'pattern': r'grep\s+(?:-r\s+)?[\'"]([^\'"]+)[\'"]\s+(\S+)',
            'categorie': 'RECHERCHE',
            'description': 'Text search',
            'format': "Search '{}' in {}"
        },
        'find': {
            'pattern': r'find\s+(\S+)\s+-name\s+[\'"]([^\'"]+)[\'"]',
            'categorie': 'RECHERCHE',
            'description': 'File search',
            'format': "Search {} in {}"
        }
    }
    
    # Configuration Patterns with categories
    CONFIG_PATTERNS = {
        # Database
        'datasource_jdbc': {
            'pattern': r'<datasource|<jdbc|jdbc\.|database\.',
            'categorie': 'DATABASE',
            'description': 'Datasource configuration',
            'format': "JDBC Datasource configuration"
        },
        'datasource_jndi': {
            'pattern': r'jndi|java:comp/env',
            'categorie': 'DATABASE',
            'description': 'JNDI configuration',
            'format': "JNDI Datasource configuration"
        },
        'connection_pool': {
            'pattern': r'max(?:imum)?-?pool|min(?:imum)?-?pool|connectionTimeout|validationQuery',
            'categorie': 'DATABASE',
            'description': 'Connection pool configuration',
            'format': "Connection pool configuration"
        },
        
        # Network
        'port_http': {
            'pattern': r'port\s*=\s*(?:80|8080|8000|8081)|httpPort',
            'categorie': 'RESEAU',
            'description': 'HTTP port configuration',
            'format': "HTTP port configuration"
        },
        'port_https': {
            'pattern': r'port\s*=\s*(?:443|8443)|httpsPort',
            'categorie': 'RESEAU',
            'description': 'HTTPS port configuration',
            'format': "HTTPS port configuration"
        },
        'port_autres': {
            'pattern': r'port\s*=\s*\d+|port>\d+',
            'categorie': 'RESEAU',
            'description': 'Port configuration',
            'format': "Port configuration"
        },
        'host': {
            'pattern': r'host\s*=|serverName|address',
            'categorie': 'RESEAU',
            'description': 'Host configuration',
            'format': "Host configuration"
        },
        
        # Authentication
        'auth_basic': {
            'pattern': r'basic\s+auth|BASIC',
            'categorie': 'AUTH',
            'description': 'Basic authentication',
            'format': "Basic auth configuration"
        },
        'auth_ldap': {
            'pattern': r'ldap|LDAP',
            'categorie': 'AUTH',
            'description': 'LDAP authentication',
            'format': "LDAP configuration"
        },
        'auth_kerberos': {
            'pattern': r'kerberos|KRB5',
            'categorie': 'AUTH',
            'description': 'Kerberos authentication',
            'format': "Kerberos configuration"
        },
        'auth_oauth': {
            'pattern': r'oauth|OAuth|OIDC|openid',
            'categorie': 'AUTH',
            'description': 'OAuth authentication',
            'format': "OAuth configuration"
        },
        'credentials': {
            'pattern': r'password|username|user\s*=|credential',
            'categorie': 'AUTH',
            'description': 'Credentials configuration',
            'format': "Credentials configuration"
        },
        
        # Logging
        'log_level': {
            'pattern': r'log(?:ger)?\.level|log(?:ger)?-level|<level>',
            'categorie': 'LOGGING',
            'description': 'Logging level configuration',
            'format': "Logging level configuration"
        },
        'log_file': {
            'pattern': r'log(?:ger)?\.file|log(?:ger)?-file|fileHandler',
            'categorie': 'LOGGING',
            'description': 'Log file configuration',
            'format': "Log file configuration"
        },
        'log_rotation': {
            'pattern': r'rotation|maxFileSize|maxBackup|rolling',
            'categorie': 'LOGGING',
            'description': 'Log rotation configuration',
            'format': "Log rotation configuration"
        },
        'log_appender': {
            'pattern': r'appender|Appender|<appender',
            'categorie': 'LOGGING',
            'description': 'Log appender configuration',
            'format': "Appender configuration"
        },
        
        # Cache
        'cache_ehcache': {
            'pattern': r'ehcache|Ehcache|<cache',
            'categorie': 'CACHE',
            'description': 'Ehcache configuration',
            'format': "Ehcache configuration"
        },
        'cache_redis': {
            'pattern': r'redis|Redis',
            'categorie': 'CACHE',
            'description': 'Redis configuration',
            'format': "Redis cache configuration"
        },
        'cache_memcached': {
            'pattern': r'memcached|Memcached',
            'categorie': 'CACHE',
            'description': 'Memcached configuration',
            'format': "Memcached cache configuration"
        },
        'cache_parameters': {
            'pattern': r'cache\.|timeToLive|maxEntries|ttl',
            'categorie': 'CACHE',
            'description': 'Cache parameters configuration',
            'format': "Cache parameters configuration"
        },
        
        # Timeout
        'timeout_connection': {
            'pattern': r'connectionTimeout|connectTimeout',
            'categorie': 'TIMEOUT',
            'description': 'Connection timeout',
            'format': "Connection timeout configuration"
        },
        'timeout_request': {
            'pattern': r'requestTimeout|readTimeout|socketTimeout',
            'categorie': 'TIMEOUT',
            'description': 'Request timeout',
            'format': "Request timeout configuration"
        },
        'timeout_session': {
            'pattern': r'sessionTimeout|session-timeout',
            'categorie': 'TIMEOUT',
            'description': 'Session timeout',
            'format': "Session timeout configuration"
        },
        'timeout_transaction': {
            'pattern': r'transactionTimeout|txTimeout',
            'categorie': 'TIMEOUT',
            'description': 'Transaction timeout',
            'format': "Transaction timeout configuration"
        },
        
        # JVM
        'jvm_heap': {
            'pattern': r'Xms|Xmx|-XX:\+HeapDump',
            'categorie': 'JVM',
            'description': 'JVM memory configuration',
            'format': "JVM memory configuration"
        },
        'jvm_gc': {
            'pattern': r'GC|GarbageCollection|-XX:\+Use\w+GC',
            'categorie': 'JVM',
            'description': 'JVM GC configuration',
            'format': "Garbage collector configuration"
        },
        'jvm_arguments': {
            'pattern': r'JAVA_OPTS|JAVA_ARGS|jvmArgs',
            'categorie': 'JVM',
            'description': 'JVM arguments',
            'format': "JVM arguments configuration"
        },
        
        # Security
        'ssl_tls': {
            'pattern': r'ssl|tls|keystore|truststore|certificate',
            'categorie': 'SECURITE',
            'description': 'SSL/TLS configuration',
            'format': "SSL/TLS configuration"
        },
        'cors': {
            'pattern': r'cors|CORS|cross-origin',
            'categorie': 'SECURITE',
            'description': 'CORS configuration',
            'format': "CORS configuration"
        },
        'csrf': {
            'pattern': r'csrf|CSRF|XSRF',
            'categorie': 'SECURITE',
            'description': 'CSRF configuration',
            'format': "CSRF configuration"
        }
    }
    
    @staticmethod
    async def detecter_actions_dans_zip(file_content: bytes) -> Dict[str, Any]:
        
        global_actions = []
        actions_by_file = []
        detected_types = set()
        categories_stats = defaultdict(int)
        
        present_files = []
        try:
            zip_file = io.BytesIO(file_content)
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                for zip_info in zip_ref.infolist():
                    if not zip_info.is_dir():
                        present_files.append(zip_info.filename)
                        
                        with zip_ref.open(zip_info) as f:
                            text_stream = io.TextIOWrapper(f, encoding='utf-8', errors='ignore')
                            
                            
                            actions = ActionDetector._detecter_actions_dans_fichier(
                                zip_info.filename, text_stream
                            )
                        
                        if actions:
                            actions_by_file.append({
                                'fichier': zip_info.filename,
                                'actions': actions
                            })
                            
                            # Add to global actions with context
                            for action in actions:
                                global_actions.append({
                                    'description': action['description'],
                                    'categorie': action['categorie'],
                                    'type': action.get('type', 'GENERAL'),
                                    'contexte': zip_info.filename
                                })
                                categories_stats[action['categorie']] += 1
                        
                        
                        file_type = ActionDetector._detecter_type_fichier(zip_info.filename)
                        if file_type:
                            detected_types.add(file_type)
                            
        except Exception as e:
            raise Exception(f"Action detection error: {str(e)}")
        
       
        return {
            'actions_globales': global_actions,
            'actions_par_fichier': actions_by_file,
            'fichiers_presents': present_files,
            'types_detectes': list(detected_types),
            'nombre_actions': len(global_actions),
            'statistiques_categories': dict(categories_stats)
        }
    
    @staticmethod
    def _detecter_actions_dans_fichier(nom_fichier: str, text_stream) -> List[Dict[str, str]]:
        
        actions = []
        # 1. STRUCTURAL DETECTION (File copy/replace action)
        actions.extend(ActionDetector._detecter_actions_structurelles(nom_fichier))

        # 2. CONTENT DETECTION (What the file actually executes)
        extension = nom_fichier.split('.')[-1].lower() if '.' in nom_fichier else ''
        
        # SQL Actions
        if extension == 'sql':
            actions.extend(ActionDetector._detecter_actions_sql(text_stream))
        
        # Shell Actions
        elif extension in ['sh', 'bash']:
            actions.extend(ActionDetector._detecter_actions_shell(text_stream))
        
        # Configuration Actions
        elif extension in ['xml', 'properties', 'conf', 'yml', 'yaml', 'cfg', 'ini']:
            actions.extend(ActionDetector._detecter_actions_config(text_stream))
        
        # Web Actions
        elif extension in ['war', 'ear', 'jar']:
            actions.append({
                'description': f"Application deployment {extension.upper()}",
                'categorie': 'APPLICATION',
                'type': 'WEB'
            })
            
        return actions

    @staticmethod
    def _detecter_actions_sql(text_stream) -> List[Dict[str, str]]:
        
        actions = []
        seen_actions = set()
        instruction_buffer = ""
        
        for line in text_stream:
            
            instruction_buffer += " " + line.strip()
            
            
            if ';' in line or line.strip().upper().startswith(('COMMIT', 'ROLLBACK')):
                instruction_upper = instruction_buffer.upper()
                
               
                for action_key, action_info in ActionDetector.SQL_PATTERNS.items():
                    match = re.search(action_info['pattern'], instruction_upper, re.IGNORECASE)
                    if match:
                        try:
                            description = action_info['format'].format(*match.groups()) if match.groups() else action_info['format']
                        except:
                            description = action_info['description']
                        
                        action_key_unique = f"{action_info['categorie']}:{description}"
                        
                        if action_key_unique not in seen_actions:
                            seen_actions.add(action_key_unique)
                            actions.append({
                                'description': description,
                                'categorie': action_info['categorie'],
                                'type': action_key
                            })
                            
                
                instruction_buffer = ""
                
        return actions

    @staticmethod
    def _detecter_actions_shell(text_stream) -> List[Dict[str, str]]:
        
        actions = []
        seen_actions = set()
        
        for line in text_stream:
            line = line.strip()
            # Ignore comments and empty lines
            if line.startswith('#') or not line:
                continue
                
            for action_key, action_info in ActionDetector.SHELL_PATTERNS.items():
                match = re.search(action_info['pattern'], line)
                if match:
                    try:
                        description = action_info['format'].format(*match.groups()) if match.groups() else action_info['format']
                    except:
                        description = action_info['description']
                    
                    action_key_unique = f"{action_info['categorie']}:{description}"
                    
                    if action_key_unique not in seen_actions:
                        seen_actions.add(action_key_unique)
                        actions.append({
                            'description': description,
                            'categorie': action_info['categorie'],
                            'type': action_key
                        })
        return actions

    @staticmethod
    def _detecter_actions_config(text_stream) -> List[Dict[str, str]]:
       
        actions = []
        seen_actions = set()
        
        for line in text_stream:
            for action_key, action_info in ActionDetector.CONFIG_PATTERNS.items():
                if re.search(action_info['pattern'], line, re.IGNORECASE):
                    action_key_unique = f"{action_info['categorie']}:{action_info['description']}"
                    
                    if action_key_unique not in seen_actions:
                        seen_actions.add(action_key_unique)
                        actions.append({
                            'description': action_info['format'],
                            'categorie': action_info['categorie'],
                            'type': action_key
                        })
        return actions
    
    @staticmethod
    def _detecter_type_fichier(nom_fichier: str) -> str:
        nom_lower = nom_fichier.lower()
        
        # Check UNIX first
        if any(x in nom_lower for x in ['bin/', 'lib/', 'ctl/', 'usr/', 'etc/']):
            return 'UNIX'
            
        # Check DB
        elif '.sql' in nom_lower or '.sh' in nom_lower or '/db/' in nom_lower or nom_lower.startswith('db/'):
            return 'DB'
            
        elif any(x in nom_lower for x in ['.war', '.ear', '.jar', 'powercard', 'webapps', '/bo/']):
            return 'WEB'
            
        elif any(x in nom_lower for x in ['.xml', '.properties', '.conf', '.yml']):
            return 'CONFIG'
            
        return None
    
    @staticmethod
    def _detecter_actions_structurelles(nom_fichier: str) -> List[Dict[str, str]]:
      
        actions = []
        
        unix_directories = [
            'usr/bin/', 'usr/sbin/', 'usr/lib/', 'usr/lib64/', 
            'usr/local/', 'usr/share/', 'usr/include/', 'usr/src/',
            'bin/', 'sbin/', 'lib/', 'etc/', 'opt/'
        ]
        
        if any(rep in nom_fichier for rep in unix_directories):
            actions.append({
                'description': f"File update / deployment: {nom_fichier}",
                'categorie': 'DEPLOIEMENT_UNIX',
                'type': 'REMPLACEMENT_OU_AJOUT'
            })
            
        return actions