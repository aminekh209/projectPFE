import re
from typing import List, Dict, Any
import zipfile
import io
from collections import defaultdict

class ActionDetectionError(Exception):
    pass

class ActionDetector:
    ORACLE_OBJECT = r'(?:"[^"]+"|[A-Z_][A-Z0-9_$#]*)(?:\s*\.\s*(?:"[^"]+"|[A-Z_][A-Z0-9_$#]*))?'

    SQL_PATTERNS = {
        # =========================
        # TABLE DDL
        # =========================

        'create_table_as_select': {
            'pattern': rf'\bCREATE\s+(?:GLOBAL\s+TEMPORARY\s+)?TABLE\s+({ORACLE_OBJECT})\s+AS\s+SELECT\b',
            'categorie': 'DDL',
            'object_type': 'TABLE',
            'action_type': 'CREATE_CTAS',
            'risk_level': 'MEDIUM',
            'description': 'CTAS table creation',
            'format': 'CTAS table creation {}'
        },


        'create_table': {
            'pattern': rf'\bCREATE\s+(?:GLOBAL\s+TEMPORARY\s+)?TABLE\s+({ORACLE_OBJECT})\b(?!\s+AS\s+SELECT)',
            'categorie': 'DDL',
            'object_type': 'TABLE',
            'action_type': 'CREATE',
            'risk_level': 'LOW',
            'description': 'Table creation',
            'format': 'Table creation {}'
        },


        'alter_table': {
            'pattern': rf'\bALTER\s+TABLE\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'TABLE',
            'action_type': 'ALTER',
            'risk_level': 'HIGH',
            'description': 'Table modification',
            'format': 'Table modification {}'
        },

        'drop_table': {
            'pattern': rf'\bDROP\s+TABLE\s+({ORACLE_OBJECT})(?:\s+CASCADE\s+CONSTRAINTS)?(?:\s+PURGE)?\b',
            'categorie': 'DDL',
            'object_type': 'TABLE',
            'action_type': 'DROP',
            'risk_level': 'CRITICAL',
            'description': 'Table deletion',
            'format': 'Table deletion {}'
        },

        'truncate_table': {
            'pattern': rf'\bTRUNCATE\s+TABLE\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'TABLE',
            'action_type': 'TRUNCATE',
            'risk_level': 'CRITICAL',
            'description': 'Table truncation',
            'format': 'Table truncation {}'
        },

        'rename_table': {
            'pattern': rf'\bRENAME\s+({ORACLE_OBJECT})\s+TO\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'TABLE',
            'action_type': 'RENAME',
            'risk_level': 'HIGH',
            'description': 'Table renaming',
            'format': 'Table renaming {} → {}'
        },

        # =========================
        # CONSTRAINTS
        # =========================
        'add_constraint': {
            'pattern': rf'\bALTER\s+TABLE\s+({ORACLE_OBJECT})\s+ADD\s+(?:CONSTRAINT\s+({ORACLE_OBJECT})\s+)?(?:PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|CHECK)\b',
            'categorie': 'DDL',
            'object_type': 'CONSTRAINT',
            'action_type': 'ADD_CONSTRAINT',
            'risk_level': 'HIGH',
            'description': 'Constraint addition',
            'format': 'Add constraint on {}'
        },

        'drop_constraint': {
            'pattern': rf'\bALTER\s+TABLE\s+({ORACLE_OBJECT})\s+DROP\s+(?:CONSTRAINT\s+)?({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'CONSTRAINT',
            'action_type': 'DROP_CONSTRAINT',
            'risk_level': 'HIGH',
            'description': 'Constraint deletion',
            'format': 'Drop constraint {} on {}'
        },

        # =========================
        # INDEX
        # =========================
        'create_index': {
            'pattern': rf'\bCREATE\s+(?:UNIQUE\s+|BITMAP\s+)?INDEX\s+({ORACLE_OBJECT})\s+ON\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'INDEX',
            'action_type': 'CREATE',
            'risk_level': 'LOW',
            'description': 'Index creation',
            'format': 'Index creation {} on table {}'
        },

        'drop_index': {
            'pattern': rf'\bDROP\s+INDEX\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'INDEX',
            'action_type': 'DROP',
            'risk_level': 'MEDIUM',
            'description': 'Index deletion',
            'format': 'Index deletion {}'
        },

        'alter_index': {
            'pattern': rf'\bALTER\s+INDEX\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'INDEX',
            'action_type': 'ALTER',
            'risk_level': 'MEDIUM',
            'description': 'Index modification',
            'format': 'Index modification {}'
        },

        # =========================
        # VIEW / MATERIALIZED VIEW
        # =========================
        'create_view': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?VIEW\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'VIEW',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'MEDIUM',
            'description': 'View creation or replacement',
            'format': 'View creation/replacement {}'
        },

        'drop_view': {
            'pattern': rf'\bDROP\s+VIEW\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'VIEW',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'View deletion',
            'format': 'View deletion {}'
        },

        'create_materialized_view': {
            'pattern': rf'\bCREATE\s+MATERIALIZED\s+VIEW\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'MATERIALIZED_VIEW',
            'action_type': 'CREATE',
            'risk_level': 'MEDIUM',
            'description': 'Materialized view creation',
            'format': 'Materialized view creation {}'
        },

        'drop_materialized_view': {
            'pattern': rf'\bDROP\s+MATERIALIZED\s+VIEW\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'MATERIALIZED_VIEW',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Materialized view deletion',
            'format': 'Materialized view deletion {}'
        },

        # =========================
        # SEQUENCE
        # =========================
        'create_sequence': {
            'pattern': rf'\bCREATE\s+SEQUENCE\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'SEQUENCE',
            'action_type': 'CREATE',
            'risk_level': 'LOW',
            'description': 'Sequence creation',
            'format': 'Sequence creation {}'
        },

        'alter_sequence': {
            'pattern': rf'\bALTER\s+SEQUENCE\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'SEQUENCE',
            'action_type': 'ALTER',
            'risk_level': 'MEDIUM',
            'description': 'Sequence modification',
            'format': 'Sequence modification {}'
        },

        'drop_sequence': {
            'pattern': rf'\bDROP\s+SEQUENCE\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'SEQUENCE',
            'action_type': 'DROP',
            'risk_level': 'MEDIUM',
            'description': 'Sequence deletion',
            'format': 'Sequence deletion {}'
        },

        # =========================
        # SYNONYM
        # =========================
        'create_synonym': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:PUBLIC\s+)?SYNONYM\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'SYNONYM',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'LOW',
            'description': 'Synonym creation or replacement',
            'format': 'Synonym creation/replacement {}'
        },

        'drop_synonym': {
            'pattern': rf'\bDROP\s+(?:PUBLIC\s+)?SYNONYM\s+({ORACLE_OBJECT})\b',
            'categorie': 'DDL',
            'object_type': 'SYNONYM',
            'action_type': 'DROP',
            'risk_level': 'MEDIUM',
            'description': 'Synonym deletion',
            'format': 'Synonym deletion {}'
        },

        # =========================
        # PL/SQL OBJECTS
        # =========================
        'dynamic_sql_concat': {
            'pattern': r'\bEXECUTE\s+IMMEDIATE\b[^;]*\|\|',
            'categorie': 'PLSQL',
            'object_type': 'DYNAMIC_SQL',
            'action_type': 'EXECUTE_IMMEDIATE_CONCAT',
            'risk_level': 'HIGH',
            'description': 'Dynamic SQL built by concatenation',
            'format': 'Dynamic SQL built by concatenation'
        },
        'create_procedure': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'PROCEDURE',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'MEDIUM',
            'description': 'Procedure creation or replacement',
            'format': 'Procedure creation/replacement {}'
        },

        'create_function': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'FUNCTION',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'MEDIUM',
            'description': 'Function creation or replacement',
            'format': 'Function creation/replacement {}'
        },

        'create_package_body': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+BODY\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'PACKAGE BODY',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'HIGH',
            'description': 'Package body creation or replacement',
            'format': 'Package body creation/replacement {}'
        },

        'create_package': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?PACKAGE\s+(?!BODY\b)({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'PACKAGE',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'HIGH',
            'description': 'Package creation or replacement',
            'format': 'Package creation/replacement {}'
        },

        'create_trigger': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?TRIGGER\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'TRIGGER',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'HIGH',
            'description': 'Trigger creation or replacement',
            'format': 'Trigger creation/replacement {}'
        },
        'create_type_body': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?TYPE\s+BODY\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'TYPE BODY',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'HIGH',
            'description': 'Type body creation or replacement',
            'format': 'Type body creation/replacement {}'
        },

        'create_type': {
            'pattern': rf'\bCREATE\s+(?:OR\s+REPLACE\s+)?TYPE\s+(?!BODY\b)({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'TYPE',
            'action_type': 'CREATE_OR_REPLACE',
            'risk_level': 'HIGH',
            'description': 'Type creation or replacement',
            'format': 'Type creation/replacement {}'
        },

        'drop_type_body': {
            'pattern': rf'\bDROP\s+TYPE\s+BODY\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'TYPE BODY',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Type body deletion',
            'format': 'Type body deletion {}'
        },

        'drop_type': {
            'pattern': rf'\bDROP\s+TYPE\s+(?!BODY\b)({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'TYPE',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Type deletion',
            'format': 'Type deletion {}'
        },

        'drop_procedure': {
            'pattern': rf'\bDROP\s+PROCEDURE\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'PROCEDURE',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Procedure deletion',
            'format': 'Procedure deletion {}'
        },

        'drop_function': {
            'pattern': rf'\bDROP\s+FUNCTION\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'FUNCTION',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Function deletion',
            'format': 'Function deletion {}'
        },

        'drop_package_body': {
            'pattern': rf'\bDROP\s+PACKAGE\s+BODY\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'PACKAGE BODY',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Package body deletion',
            'format': 'Package body deletion {}'
        },

        'drop_package': {
            'pattern': rf'\bDROP\s+PACKAGE\s+(?!BODY\b)({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'PACKAGE',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Package deletion',
            'format': 'Package deletion {}'
        },

        'drop_trigger': {
            'pattern': rf'\bDROP\s+TRIGGER\s+({ORACLE_OBJECT})\b',
            'categorie': 'PLSQL',
            'object_type': 'TRIGGER',
            'action_type': 'DROP',
            'risk_level': 'HIGH',
            'description': 'Trigger deletion',
            'format': 'Trigger deletion {}'
        },

        # =========================
        # DML
        # =========================
        'insert': {
            'pattern': rf'\bINSERT\s+INTO\s+({ORACLE_OBJECT})\b',
            'categorie': 'DML',
            'object_type': 'TABLE',
            'action_type': 'INSERT',
            'risk_level': 'LOW',
            'description': 'Data insertion',
            'format': 'Insertion into {}'
        },

        'update': {
            'pattern': rf'\bUPDATE\s+({ORACLE_OBJECT})\s+SET\b',
            'categorie': 'DML',
            'object_type': 'TABLE',
            'action_type': 'UPDATE',
            'requires_where_check': True,
            'risk_level': 'HIGH',
            'description': 'Data update',
            'format': 'Update on {}'
        },

        'delete': {
            'pattern': rf'\bDELETE\s+FROM\s+({ORACLE_OBJECT})\b',
            'categorie': 'DML',
            'object_type': 'TABLE',
            'action_type': 'DELETE',
            'requires_where_check': True,
            'risk_level': 'HIGH',
            'description': 'Data deletion',
            'format': 'Deletion from {}'
        },

        'merge': {
            'pattern': rf'\bMERGE\s+INTO\s+({ORACLE_OBJECT})\b',
            'categorie': 'DML',
            'object_type': 'TABLE',
            'action_type': 'MERGE',
            'risk_level': 'CRITICAL',
            'description': 'Data merge',
            'format': 'Merge into {}'
        },

        # =========================
        # DCL / TCL
        # =========================
        'grant': {
            'pattern': rf'\bGRANT\s+(.+?)\s+ON\s+({ORACLE_OBJECT})\s+TO\s+({ORACLE_OBJECT})\b',
            'categorie': 'DCL',
            'object_type': 'PRIVILEGE',
            'action_type': 'GRANT',
            'risk_level': 'MEDIUM',
            'description': 'Permission grant',
            'format': 'Grant {} on {} to {}'
        },

        'revoke': {
            'pattern': rf'\bREVOKE\s+(.+?)\s+ON\s+({ORACLE_OBJECT})\s+FROM\s+({ORACLE_OBJECT})\b',
            'categorie': 'DCL',
            'object_type': 'PRIVILEGE',
            'action_type': 'REVOKE',
            'risk_level': 'MEDIUM',
            'description': 'Permission revoke',
            'format': 'Revoke {} on {} from {}'
        },

        'commit': {
            'pattern': r'\bCOMMIT\b',
            'categorie': 'TCL',
            'object_type': 'TRANSACTION',
            'action_type': 'COMMIT',
            'risk_level': 'LOW',
            'description': 'Transaction commit',
            'format': 'Commit transaction'
        },

        'rollback': {
            'pattern': r'\bROLLBACK\b',
            'categorie': 'TCL',
            'object_type': 'TRANSACTION',
            'action_type': 'ROLLBACK',
            'risk_level': 'LOW',
            'description': 'Transaction rollback',
            'format': 'Rollback transaction'
        },

        'savepoint': {
            'pattern': rf'\bSAVEPOINT\s+({ORACLE_OBJECT})\b',
            'categorie': 'TCL',
            'object_type': 'TRANSACTION',
            'action_type': 'SAVEPOINT',
            'risk_level': 'LOW',
            'description': 'Savepoint creation',
            'format': 'Savepoint {}'
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
                            for action in actions:
                                global_action = {
                                    'description': action['description'],
                                    'categorie': action['categorie'],
                                    'type': action.get('type', 'GENERAL'),
                                    'object_type': action.get('object_type'),
                                    'action_type': action.get('action_type'),
                                    'requires_where_check': action.get('requires_where_check'),
                                    'has_where': action.get('has_where'),
                                    'matched_object': action.get('matched_object'),
                                    'needs_prepatch_analysis': action.get('needs_prepatch_analysis'),
                                    'is_dynamic_sql': action.get('is_dynamic_sql', False),
                                    'contexte': zip_info.filename
                                }

                                if action.get('risk_level'):
                                    global_action['risk_level'] = action.get('risk_level')

                                global_actions.append(global_action)
                                categories_stats[action['categorie']] += 1
                        
                        
                        file_type = ActionDetector._detecter_type_fichier(zip_info.filename)
                        if file_type and file_type != 'UNKNOWN':
                            detected_types.add(file_type)
                            
        except Exception as e:
            raise ActionDetectionError(f"Action detection error: {str(e)}")
        
       
        return {
            'actions_globales': global_actions,
            'actions_par_fichier': actions_by_file,
            'fichiers_presents': present_files,
            'types_detectes': list(detected_types),
            'nombre_actions': len(global_actions),
            'statistiques_categories': dict(categories_stats)
        }
    
    @staticmethod
    def fusionner_resultats_actions(
        *results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fusionne plusieurs résultats d'analyse :

        - actions SQL ;
        - actions UNIX structurelles ;
        - actions WEB structurelles.

        Les doublons sont supprimés.
        """

        global_actions = []
        actions_by_file_map = {}
        present_files = set()
        detected_types = set()

        seen_global_actions = set()

        for result in results:
            if not result:
                continue

            for file_name in result.get(
                "fichiers_presents",
                []
            ):
                present_files.add(file_name)

            for patch_type in result.get(
                "types_detectes",
                []
            ):
                if patch_type:
                    detected_types.add(
                        str(patch_type).upper()
                    )

            for action in result.get(
                "actions_globales",
                []
            ):
                action_key = (
                    str(action.get("type") or ""),
                    str(action.get("action_type") or ""),
                    str(action.get("matched_object") or ""),
                    str(action.get("contexte") or ""),
                    str(action.get("description") or ""),
                )

                if action_key in seen_global_actions:
                    continue

                seen_global_actions.add(action_key)
                global_actions.append(action)

            for file_group in result.get(
                "actions_par_fichier",
                []
            ):
                filename = str(
                    file_group.get("fichier") or ""
                )

                if not filename:
                    continue

                if filename not in actions_by_file_map:
                    actions_by_file_map[filename] = []

                existing_keys = {
                    (
                        str(item.get("type") or ""),
                        str(item.get("action_type") or ""),
                        str(item.get("matched_object") or ""),
                        str(item.get("description") or ""),
                    )
                    for item in actions_by_file_map[filename]
                }

                for action in file_group.get(
                    "actions",
                    []
                ):
                    action_key = (
                        str(action.get("type") or ""),
                        str(action.get("action_type") or ""),
                        str(action.get("matched_object") or ""),
                        str(action.get("description") or ""),
                    )

                    if action_key in existing_keys:
                        continue

                    existing_keys.add(action_key)
                    actions_by_file_map[filename].append(
                        action
                    )

        categories_stats = defaultdict(int)

        for action in global_actions:
            category = str(
                action.get("categorie") or "AUTRE"
            )

            categories_stats[category] += 1

        actions_by_file = [
            {
                "fichier": filename,
                "actions": actions,
            }
            for filename, actions
            in actions_by_file_map.items()
        ]

        type_order = ["DB", "UNIX", "WEB"]

        ordered_types = [
            patch_type
            for patch_type in type_order
            if patch_type in detected_types
        ]

        return {
            "actions_globales": global_actions,
            "actions_par_fichier": actions_by_file,
            "fichiers_presents": sorted(
                present_files
            ),
            "types_detectes": ordered_types,
            "nombre_actions": len(global_actions),
            "statistiques_categories": dict(
                categories_stats
            ),
        }



    @staticmethod
    def detecter_actions_deploiement_depuis_structure(
        structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Génère les actions UNIX et WEB à partir de la structure du ZIP.

        Aucun contenu de fichier UNIX, WAR, EAR ou JAR n'est lu.
        La détection repose uniquement sur :
        - le chemin ;
        - le nom ;
        - l'extension ;
        - la catégorie ;
        - la taille.
        """

        global_actions = []
        actions_by_file = []
        categories_stats = defaultdict(int)
        present_files = []

        web_extensions = {
            ".war",
            ".ear",
            ".jar",
        }

        web_markers = (
            "/web/",
            "/app/",
            "/deploy/",
            "/jboss/",
            "/wildfly/",
            "/webapps/",
        )

        for file_info in structure.get("fichiers", []):
            filename = str(
                file_info.get("nom") or ""
            ).replace("\\", "/")

            if not filename:
                continue

            extension = str(
                file_info.get("extension") or ""
            ).lower()

            

            file_size = int(
                file_info.get("taille") or 0
            )

            normalized_path = (
                f"/{filename.lower().lstrip('/')}"
            )

            present_files.append(filename)

            # Les fichiers SQL sont déjà traités profondément.
            if extension == ".sql":
                continue

            # Les ZIP internes servent seulement de conteneurs.
            if extension == ".zip":
                continue

            has_db_path = (
                "/db/" in normalized_path
                or "/database/" in normalized_path
            )

            has_unix_path = (
                "/usr/" in normalized_path
            )

            has_web_path = any(
                marker in normalized_path
                for marker in web_markers
            )

            file_actions = []

            # =====================================
            # Déploiement d'une application WEB
            # =====================================
            if (
                extension in web_extensions
                or (
                    has_web_path
                    and extension in {
                        ".js",
                        ".css",
                        ".html",
                    }
                )
            ):
                artifact_type = (
                    extension.lstrip(".").upper()
                    if extension
                    else "WEB"
                )

                basename = filename.rsplit("/", 1)[-1]

                file_actions.append({
                    "description": (
                        f"Application deployment "
                        f"{artifact_type}: {basename}"
                    ),
                    "categorie": "APPLICATION",
                    "type": "WEB",
                    "object_type": artifact_type,
                    "action_type": "DEPLOY",
                    "matched_object": filename,
                    "needs_prepatch_analysis": True,
                    "content_analyzed": False,
                    "file_size": file_size,
                    "risk_level": "MEDIUM",
                })

            # =====================================
            # Déploiement d'un fichier UNIX
            # =====================================
            elif has_unix_path:
                file_actions.append({
                    "description": (
                        f"UNIX file : "
                        f"{filename}"
                    ),
                    "categorie": "FICHIER",
                    "type": "UNIX",
                    "object_type": "FILE",
                    "action_type": "DEPLOY_OR_UPDATE",
                    "matched_object": filename,
                    "needs_prepatch_analysis": True,
                    "content_analyzed": False,
                    "file_size": file_size,
                    "risk_level": "MEDIUM",
                })
            if not file_actions:
                continue

            actions_by_file.append({
                "fichier": filename,
                "actions": file_actions,
            })

            for action in file_actions:
                global_action = {
                    **action,
                    "contexte": filename,
                }

                global_actions.append(global_action)
                categories_stats[action["categorie"]] += 1

        return {
            "actions_globales": global_actions,
            "actions_par_fichier": actions_by_file,
            "fichiers_presents": present_files,
            "types_detectes": [],
            "nombre_actions": len(global_actions),
            "statistiques_categories": dict(categories_stats),
        }


    @staticmethod
    def _detecter_actions_dans_fichier(nom_fichier: str, text_stream) -> List[Dict[str, str]]:
        
        actions = []
        actions.extend(ActionDetector._detecter_actions_structurelles(nom_fichier))
        extension = nom_fichier.split('.')[-1].lower() if '.' in nom_fichier else ''
        if extension == 'sql':
            actions.extend(ActionDetector._detecter_actions_sql(text_stream))
        elif extension in ['sh', 'bash']:
            already_unix_deployment = any(
                action.get('categorie') == 'DEPLOIEMENT UNIX'
                for action in actions
            )

            if not already_unix_deployment:
                actions.append({
                    'description': f"Shell script detected: {nom_fichier}",
                    'categorie': 'SCRIPT',
                    'type': 'SHELL',
                    'needs_prepatch_analysis': True
                })
        elif extension in ['war', 'ear', 'jar']:
            actions.append({
                'description': f"Application deployment {extension.upper()}",
                'categorie': 'APPLICATION',
                'type': 'WEB',
                'needs_prepatch_analysis': True
            })
            
        return actions
    @staticmethod
    def _strip_sql_comments(sql: str) -> str:
        """
        Supprime les commentaires SQL simples:
        - commentaires ligne: -- ...
        - commentaires bloc: /* ... */

        Attention:
        Cette fonction est suffisante pour la création patch.
        Elle n'est pas destinée à remplacer un parser Oracle complet.
        """
        if not sql:
            return ""

        # Supprimer les commentaires bloc /* ... */
        sql = re.sub(r'/\*.*?\*/', ' ', sql, flags=re.DOTALL)

        # Supprimer les commentaires ligne -- ...
        lines = []
        for line in sql.splitlines():
            line = re.sub(r'--.*$', '', line)
            lines.append(line)

        return "\n".join(lines)


    @staticmethod
    def _strip_sql_string_literals(sql: str) -> str:
        """
        Supprime/remplace les chaînes SQL entre quotes.
        Objectif: éviter de détecter WHERE, DROP, ALTER, etc. dans du texte.

        Exemple:
        UPDATE T SET COMMENTAIRE = 'WHERE TEST'
        devient:
        UPDATE T SET COMMENTAIRE = ' '
        """
        if not sql:
            return ""

        # Remplace les chaînes Oracle '...' en gérant les quotes doublées ''
        return re.sub(r"'(?:''|[^'])*'", "''", sql, flags=re.DOTALL)


    @staticmethod
    def _has_real_where(sql: str) -> bool:
        """
        Détecte WHERE hors commentaires et hors chaînes de caractères.
        Suffisant pour création patch.
        """
        cleaned = ActionDetector._strip_sql_comments(sql)
        cleaned = ActionDetector._strip_sql_string_literals(cleaned)

        return bool(re.search(r'\bWHERE\b', cleaned, re.IGNORECASE))
    
    @staticmethod
    def _get_critical_risk_level(action_key: str, action_info: Dict[str, Any]) -> str | None:
        action_type = str(action_info.get("action_type") or "").upper()

        if (
            action_type in ["ALTER", "TRUNCATE", "DROP"]
            or action_type.startswith("DROP_")
            or action_key.startswith("drop_")
            or action_key.startswith("alter_")
            or action_key == "truncate_table"
        ):
            return "CRITICAL"

        return None
    @staticmethod
    def _detecter_actions_sql(text_stream) -> List[Dict[str, Any]]:
        actions = []
        seen_actions = set()
        instruction_buffer = ""

        for line in text_stream:
            clean_line = line.strip()

            if not clean_line:
                continue

            instruction_buffer += "\n" + clean_line

            if ';' in clean_line or clean_line.upper().startswith(('COMMIT', 'ROLLBACK')) or clean_line == '/':
                # 1. Nettoyage des commentaires
                instruction_without_comments = ActionDetector._strip_sql_comments(instruction_buffer)

                # Si après suppression des commentaires il ne reste rien, on ignore
                if not instruction_without_comments.strip():
                    instruction_buffer = ""
                    continue

                instruction_upper = instruction_without_comments.upper()

                # 2. Instruction normale
                instructions_to_scan = [instruction_upper]

                # 3. SQL dynamique simple : EXECUTE IMMEDIATE '...'
                dynamic_sql_matches = re.findall(
                    r"EXECUTE\s+IMMEDIATE\s+'((?:''|[^'])*)'",
                    instruction_without_comments,
                    re.IGNORECASE | re.DOTALL
                )

                for dyn_sql in dynamic_sql_matches:
                    dyn_sql_clean = dyn_sql.replace("''", "'").upper()

                    # Nettoyage aussi du SQL dynamique
                    dyn_sql_clean = ActionDetector._strip_sql_comments(dyn_sql_clean)

                    if dyn_sql_clean.strip():
                        instructions_to_scan.append(dyn_sql_clean)

                # 4. Scanner instruction normale + SQL dynamique
                for sql_to_scan in instructions_to_scan:
                    # Version sans strings pour éviter de détecter des mots SQL dans du texte
                    sql_for_patterns = ActionDetector._strip_sql_string_literals(sql_to_scan)

                    for action_key, action_info in ActionDetector.SQL_PATTERNS.items():
                        scan_target = sql_to_scan if action_key == 'dynamic_sql_concat' else sql_for_patterns

                        match = re.search(
                            action_info['pattern'],
                            scan_target,
                            re.IGNORECASE | re.DOTALL
                        )

                        if not match:
                            continue

                        try:
                            description = (
                                action_info['format'].format(*match.groups())
                                if match.groups()
                                else action_info['format']
                            )
                        except (IndexError, KeyError, ValueError):
                            description = action_info['description']

                        # WHERE réel : hors commentaires et hors chaînes de caractères
                        has_where = ActionDetector._has_real_where(sql_to_scan)

                        risk_level = ActionDetector._get_critical_risk_level(action_key, action_info)

                        is_dynamic_sql = True if action_key == 'dynamic_sql_concat' else (sql_to_scan != instruction_upper)

                        action_key_unique = (
                            f"{action_info['categorie']}:"
                            f"{action_key}:"
                            f"{description}:"
                            f"{'DYNAMIC' if is_dynamic_sql else 'STATIC'}"
                        )

                        if action_key_unique in seen_actions:
                            continue

                        seen_actions.add(action_key_unique)

                        action_payload = {
                            'description': description,
                            'categorie': action_info['categorie'],
                            'type': action_key,
                            'object_type': action_info.get('object_type'),
                            'action_type': action_info.get('action_type'),
                            'requires_where_check': action_info.get('requires_where_check', False),
                            'has_where': has_where,
                            'matched_object': match.group(1) if match.groups() else None,
                            'needs_prepatch_analysis': action_info.get('needs_prepatch_analysis', True),
                            'is_dynamic_sql': is_dynamic_sql
                        }

                        if risk_level:
                            action_payload['risk_level'] = risk_level

                        actions.append(action_payload)

                instruction_buffer = ""

        return actions
    
    
    @staticmethod
    def _detecter_type_fichier(
        nom_fichier: str
    ) -> str | None:
        nom_normalise = str(
            nom_fichier or ""
        ).replace("\\", "/").lower()

        normalized_path = (
            f"/{nom_normalise.lstrip('/')}"
        )

        # UNIX uniquement sous usr/.
        if "/usr/" in normalized_path:
            return "UNIX"

        # Un .sh seul n'est pas une preuve de patch DB
        # ni une preuve de patch UNIX.
        if (
            nom_normalise.endswith(".sql")
            or nom_normalise.endswith(".dmp")
            or nom_normalise.endswith(".bak")
            or "/db/" in normalized_path
            or "/database/" in normalized_path
        ):
            return "DB"

        if nom_normalise.endswith(
            (".war", ".ear", ".jar")
        ):
            return "WEB"

        return None
    
    @staticmethod
    def _detecter_actions_structurelles(nom_fichier: str) -> List[Dict[str, Any]]:
        actions = []

        nom_lower = nom_fichier.lower()

        unix_directories = [
            'usr/bin/',
            'usr/sbin/',
            'usr/lib/',
            'usr/lib64/',
            'usr/local/',
            'usr/share/',
            'usr/include/',
            'usr/src/',
            'usr/ctl/',
            'bin/',
            'sbin/',
            'lib/',
            'etc/',
            'opt/'
        ]

        if any(rep in nom_lower for rep in unix_directories):
            actions.append({
                'description': f"File update / deployment: {nom_fichier}",
                'categorie': 'DEPLOIEMENT UNIX',
                'type': 'REMPLACEMENT_OU_AJOUT',
                'needs_prepatch_analysis': True
            })

        return actions