import os
import zipfile
import shutil
import tempfile
from typing import Dict, Any
from pathlib import Path, PurePosixPath


class ZipScanError(Exception):
    pass


class FileScanner:
    EXTENSIONS = {
        'database': ['.sql', '.dmp', '.bak'],
        'unix': ['.sh', '.bash', '.so', '.bin', '.o', '.a', '.ko'],
        'web': ['.war', '.ear', '.jar', '.js', '.css', '.html'],
        'config': ['.xml', '.properties', '.conf', '.yml', '.yaml', '.cfg', '.ini'],
        'script': ['.py', '.pl', '.rb', '.php', '.js']
    }

    UNIX_PATHS = ['bin/', 'lib/', 'ctl/', 'usr/', 'etc/', 'opt/']

    MAX_NESTED_DEPTH = 5
    MAX_FILES = 3000
    MAX_TOTAL_SIZE = 500 * 1024 * 1024  # 500 MB

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
                        fichier = FileScanner._analyser_fichier(info)
                        resultat['fichiers'].append(fichier)
                        resultat['statistiques']['total'] += 1

                        cat = fichier['categorie']
                        resultat['statistiques'][cat] = resultat['statistiques'].get(cat, 0) + 1

                        if fichier['extension']:
                            resultat['extensions'].add(fichier['extension'])

                        dossier = '/'.join(fichier['nom'].split('/')[:-1])
                        if dossier:
                            resultat['dossiers'].add(dossier)

        except Exception as e:
            raise ZipScanError(f"Erreur lors du scan du ZIP: {str(e)}") from e

        resultat['dossiers'] = list(resultat['dossiers'])
        resultat['extensions'] = list(resultat['extensions'])

        return resultat

    @staticmethod
    def scanner_fichiers_zip_recursive(zip_path: str) -> Dict[str, Any]:
        """
        Analyse un ZIP avec extraction récursive des ZIP internes.
        Exemple:
        patch.zip
          PATCH_DB_BO.zip
            appel.sql

        Le scanner verra:
        PATCH_DB_BO.zip
        PATCH_DB_BO/appel.sql
        """
        normalized_zip_path = FileScanner.build_recursive_normalized_zip(zip_path)

        try:
            return FileScanner.scanner_fichiers_zip(normalized_zip_path)
        finally:
            if normalized_zip_path and os.path.exists(normalized_zip_path):
                os.unlink(normalized_zip_path)

    
    @staticmethod
    def scanner_structure_et_construire_zip_sql(
        zip_path: str
    ) -> tuple[Dict[str, Any], str]:
        """
        Parcourt tout le ZIP et les ZIP internes.

        - Tous les fichiers sont ajoutés à la structure.
        - Seuls les fichiers .sql sont copiés dans un ZIP léger.
        - Les WAR, EAR, JAR et binaires ne sont jamais extraits.
        """

        if not zipfile.is_zipfile(zip_path):
            raise ZipScanError("Fichier ZIP invalide ou corrompu")

        resultat = {
            "nom": os.path.basename(zip_path),
            "taille": os.path.getsize(zip_path),
            "fichiers": [],
            "dossiers": set(),
            "extensions": set(),
            "statistiques": {
                "total": 0,
                "database": 0,
                "unix": 0,
                "web": 0,
                "config": 0,
                "script": 0,
                "autre": 0,
            },
        }

        sql_fd, sql_zip_path = tempfile.mkstemp(
            suffix="_sql_only.zip"
        )
        os.close(sql_fd)

        counters = {
            "total_files": 0,
            "total_size": 0,
            "sql_files": 0,
            "sql_size": 0,
        }

        try:
            with zipfile.ZipFile(
                sql_zip_path,
                "w",
                compression=zipfile.ZIP_DEFLATED
            ) as sql_zip:

                FileScanner._scanner_zip_selectif_recursive(
                    zip_source=zip_path,
                    resultat=resultat,
                    sql_zip=sql_zip,
                    counters=counters,
                    prefix="",
                    depth=0,
                )

            resultat["dossiers"] = sorted(resultat["dossiers"])
            resultat["extensions"] = sorted(resultat["extensions"])

            resultat["analyse_sql"] = {
                "nombre_fichiers_sql": counters["sql_files"],
                "taille_sql_totale": counters["sql_size"],
            }

            return resultat, sql_zip_path

        except Exception:
            if os.path.exists(sql_zip_path):
                os.unlink(sql_zip_path)
            raise
    

    @staticmethod
    def _scanner_zip_selectif_recursive(
        zip_source,
        resultat: Dict[str, Any],
        sql_zip: zipfile.ZipFile,
        counters: Dict[str, int],
        prefix: str,
        depth: int,
    ):
        """
        Parcourt un ZIP sans extraire ses fichiers sur le disque.

        Les ZIP internes sont parcourus récursivement.
        Les fichiers SQL sont copiés dans sql_zip.
        Les autres fichiers sont uniquement référencés dans la structure.
        """

        if depth > FileScanner.MAX_NESTED_DEPTH:
            raise ZipScanError(
                f"Profondeur maximale dépassée: "
                f"{FileScanner.MAX_NESTED_DEPTH}"
            )

        try:
            with zipfile.ZipFile(zip_source, "r") as zip_ref:
                for info in zip_ref.infolist():
                    if info.is_dir():
                        continue

                    member_name = FileScanner._normaliser_nom_membre_zip(
                        info.filename
                    )

                    if not member_name:
                        continue

                    full_name = (
                        f"{prefix}{member_name}"
                        if prefix
                        else member_name
                    )

                    extension = PurePosixPath(full_name).suffix.lower()

                    counters["total_files"] += 1

                    if extension != ".zip":
                        counters["total_size"] += info.file_size

                    if counters["total_files"] > FileScanner.MAX_FILES:
                        raise ZipScanError(
                            f"ZIP trop volumineux: plus de "
                            f"{FileScanner.MAX_FILES} fichiers"
                        )

                    if counters["total_size"] > FileScanner.MAX_TOTAL_SIZE:
                        raise ZipScanError(
                            "ZIP trop volumineux après analyse récursive"
                        )

                    fichier = FileScanner._analyser_entree_zip(
                        info=info,
                        full_name=full_name,
                    )

                    resultat["fichiers"].append(fichier)
                    resultat["statistiques"]["total"] += 1

                    categorie = fichier["categorie"]

                    resultat["statistiques"][categorie] = (
                        resultat["statistiques"].get(categorie, 0) + 1
                    )

                    if extension:
                        resultat["extensions"].add(extension)

                    dossier = str(
                        PurePosixPath(full_name).parent
                    )

                    if dossier and dossier != ".":
                        resultat["dossiers"].add(dossier)

                    # Analyse profonde uniquement des fichiers SQL.
                    if extension == ".sql":
                        FileScanner._copier_sql_dans_zip(
                            source_zip=zip_ref,
                            source_info=info,
                            sql_zip=sql_zip,
                            target_name=full_name,
                        )

                        counters["sql_files"] += 1
                        counters["sql_size"] += info.file_size

                    # Parcours uniquement des véritables ZIP internes.
                    if (
                        extension == ".zip"
                        and depth < FileScanner.MAX_NESTED_DEPTH
                    ):
                        FileScanner._scanner_zip_interne(
                            parent_zip=zip_ref,
                            nested_info=info,
                            resultat=resultat,
                            sql_zip=sql_zip,
                            counters=counters,
                            full_name=full_name,
                            depth=depth,
                        )

        except zipfile.BadZipFile as exc:
            raise ZipScanError(
                "Fichier ZIP invalide ou corrompu"
            ) from exc
    


    @staticmethod
    def _scanner_zip_interne(
        parent_zip: zipfile.ZipFile,
        nested_info: zipfile.ZipInfo,
        resultat: Dict[str, Any],
        sql_zip: zipfile.ZipFile,
        counters: Dict[str, int],
        full_name: str,
        depth: int,
    ):
        """
        Copie uniquement le ZIP interne dans un fichier temporaire déroulant.

        Son contenu n'est pas extrait sur le disque.
        """

        # Jusqu'à 32 Mo, le fichier peut rester en mémoire.
        # Au-delà, Python le place automatiquement sur disque.
        with tempfile.SpooledTemporaryFile(
            max_size=32 * 1024 * 1024,
            mode="w+b",
        ) as nested_file:

            with parent_zip.open(nested_info, "r") as source:
                shutil.copyfileobj(
                    source,
                    nested_file,
                    length=1024 * 1024,
                )

            nested_file.seek(0)

            if not zipfile.is_zipfile(nested_file):
                return

            nested_file.seek(0)

            nested_prefix = (
                str(PurePosixPath(full_name).with_suffix("")) + "/"
            )

            FileScanner._scanner_zip_selectif_recursive(
                zip_source=nested_file,
                resultat=resultat,
                sql_zip=sql_zip,
                counters=counters,
                prefix=nested_prefix,
                depth=depth + 1,
            )

    

    @staticmethod
    def detecter_types_depuis_structure(
        structure: Dict[str, Any]
    ) -> list[str]:
        """
        Détecte les types du patch depuis sa structure.

        Règles :
        - DB   : présence d'un SQL, DMP, BAK ou d'un dossier db/database.
        - UNIX : présence réelle d'un fichier sous le dossier usr/.
        - WEB  : présence d'un artefact WEB ou d'un dossier WEB reconnu.

        Un simple fichier run.sh hors de usr/ ne transforme pas
        un patch DB en patch UNIX.
        """

        detected_types = set()

        for fichier in structure.get("fichiers", []):
            filename = str(
                fichier.get("nom") or ""
            ).replace("\\", "/").lower()

            extension = str(
                fichier.get("extension") or ""
            ).lower()

            normalized_path = (
                f"/{filename.lstrip('/')}"
            )

            has_db_path = (
                "/db/" in normalized_path
                or "/database/" in normalized_path
            )

            # UNIX uniquement lorsqu'un fichier est réellement
            # présent sous un dossier usr/.
            #
            # Exemples acceptés :
            # usr/bin/programme
            # usr/lib/library.so
            # PATCH_UNIX_BO/usr/ctl/start.sh
            has_unix_path = (
                "/usr/" in normalized_path
            )

            has_web_path = any(
                marker in normalized_path
                for marker in (
                    "/web/",
                    "/app/",
                    "/deploy/",
                    "/jboss/",
                    "/wildfly/",
                    "/webapps/",
                )
            )

            # =========================
            # Type DB
            # =========================
            if (
                extension in {
                    ".sql",
                    ".dmp",
                    ".bak",
                }
                or has_db_path
            ):
                detected_types.add("DB")

            # =========================
            # Type UNIX
            # =========================
            # Ne jamais utiliser uniquement l'extension .sh.
            if has_unix_path:
                detected_types.add("UNIX")

            # =========================
            # Type WEB
            # =========================
            if (
                extension in {
                    ".war",
                    ".ear",
                    ".jar",
                    
                }
                or has_web_path
            ):
                detected_types.add("WEB")

        order = ["DB", "UNIX", "WEB"]

        return [
            patch_type
            for patch_type in order
            if patch_type in detected_types
        ]


    @staticmethod
    def _normaliser_nom_membre_zip(member_name: str) -> str:
        """
        Nettoie et sécurise le chemin contenu dans le ZIP.
        """

        normalized = str(member_name or "").replace("\\", "/")

        if not normalized:
            return ""

        path = PurePosixPath(normalized)

        if path.is_absolute() or ".." in path.parts:
            raise ZipScanError(
                f"Chemin interdit dans le ZIP: {member_name}"
            )

        return path.as_posix().lstrip("/")
    

    @staticmethod
    def _analyser_entree_zip(
        info: zipfile.ZipInfo,
        full_name: str
    ) -> Dict[str, Any]:
        """
        Analyse une entrée trouvée dans le ZIP principal
        ou dans un ZIP interne.
        """

        extension = PurePosixPath(
            full_name
        ).suffix.lower()

        categorie = FileScanner._determiner_categorie(
            full_name,
            extension,
        )

        type_fichier = FileScanner._determiner_type(
            extension
        )

        return {
            "nom": full_name,
            "taille": info.file_size,
            "extension": extension,
            "categorie": categorie,
            "type": type_fichier,
            "date_modification": info.date_time,
            "compressé": (
                info.compress_type
                != zipfile.ZIP_STORED
            ),
        }
    
    @staticmethod
    def _copier_sql_dans_zip(
        source_zip: zipfile.ZipFile,
        source_info: zipfile.ZipInfo,
        sql_zip: zipfile.ZipFile,
        target_name: str,
    ):
        """
        Copie un SQL par blocs dans le ZIP léger.
        """

        target_info = zipfile.ZipInfo(target_name)
        target_info.compress_type = zipfile.ZIP_DEFLATED

        with source_zip.open(source_info, "r") as source:
            with sql_zip.open(target_info, "w") as target:
                shutil.copyfileobj(
                    source,
                    target,
                    length=1024 * 1024,
                )

    @staticmethod
    def _determiner_categorie(
        nom: str,
        extension: str
    ) -> str:
        """
        Un fichier est classé UNIX uniquement lorsqu'il est
        réellement présent sous le dossier usr/.

        Un run.sh à la racine reste un script et ne transforme
        pas le patch en patch UNIX.
        """

        normalized_name = str(
            nom or ""
        ).replace("\\", "/").lower()

        normalized_path = (
            f"/{normalized_name.lstrip('/')}"
        )

        # Structure UNIX réelle.
        if "/usr/" in normalized_path:
            return "unix"

        # Classification des autres extensions.
        # La catégorie UNIX est volontairement ignorée ici,
        # car l'extension seule ne suffit pas.
        for category, extensions in FileScanner.EXTENSIONS.items():
            if category == "unix":
                continue

            if extension in extensions:
                return category

        # Les scripts shell hors de usr/ restent des scripts.
        if extension in {".sh", ".bash"}:
            return "script"

        return "autre"


    


    @staticmethod
    def build_recursive_normalized_zip(zip_path: str) -> str:
        """
        Retourne le chemin d'un ZIP temporaire reconstruit après extraction récursive.
        Ce ZIP normalisé peut être utilisé aussi par ActionDetector.
        """
        if not zipfile.is_zipfile(zip_path):
            raise ZipScanError("Fichier ZIP invalide ou corrompu")

        extract_dir = tempfile.mkdtemp(prefix="patch_recursive_extract_")
        normalized_fd, normalized_zip_path = tempfile.mkstemp(suffix=".zip")
        os.close(normalized_fd)

        try:
            FileScanner._safe_extract_zip(zip_path, extract_dir)
            FileScanner._extract_nested_zips_recursively(extract_dir, depth=0)
            FileScanner._validate_extracted_limits(extract_dir)
            FileScanner._zip_folder(extract_dir, normalized_zip_path)

            return normalized_zip_path

        except Exception:
            if os.path.exists(normalized_zip_path):
                os.unlink(normalized_zip_path)
            raise

        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    @staticmethod
    def _safe_extract_zip(zip_path: str, extract_dir: str):
        """
        Extraction sécurisée contre ZipSlip.
        Empêche un fichier ZIP de sortir du dossier extract_dir avec ../
        """
        extract_base = Path(extract_dir).resolve()

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.infolist():
                member_name = member.filename.replace("\\", "/")

                if not member_name:
                    continue

                target_path = (extract_base / member_name).resolve()

                if not str(target_path).startswith(str(extract_base)):
                    raise ZipScanError(f"Chemin interdit dans le ZIP: {member.filename}")

                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zip_ref.open(member) as source, open(target_path, "wb") as target:
                    shutil.copyfileobj(source, target)

    @staticmethod
    def _extract_nested_zips_recursively(base_dir: str, depth: int = 0):
        if depth >= FileScanner.MAX_NESTED_DEPTH:
            return

        base_path = Path(base_dir)

        zip_files = sorted([
            p for p in base_path.rglob("*")
            if p.is_file() and p.suffix.lower() == ".zip"
        ])

        for zip_file in zip_files:
            output_dir = zip_file.with_suffix("")

            if output_dir.exists():
                continue

            output_dir.mkdir(parents=True, exist_ok=True)

            try:
                FileScanner._safe_extract_zip(str(zip_file), str(output_dir))
                FileScanner._extract_nested_zips_recursively(str(output_dir), depth + 1)
            except zipfile.BadZipFile:
                continue
            except Exception as e:
                raise ZipScanError(f"Erreur extraction ZIP interne {zip_file.name}: {str(e)}") from e

    @staticmethod
    def _validate_extracted_limits(base_dir: str):
        total_files = 0
        total_size = 0

        for root, _, files in os.walk(base_dir):
            for file in files:
                total_files += 1
                full_path = os.path.join(root, file)

                try:
                    total_size += os.path.getsize(full_path)
                except Exception:
                    pass

                if total_files > FileScanner.MAX_FILES:
                    raise ZipScanError(
                        f"ZIP trop volumineux: plus de {FileScanner.MAX_FILES} fichiers après extraction"
                    )

                if total_size > FileScanner.MAX_TOTAL_SIZE:
                    raise ZipScanError(
                        "ZIP trop volumineux après extraction récursive"
                    )

    @staticmethod
    def _zip_folder(source_dir: str, output_zip_path: str):
        source_path = Path(source_dir).resolve()

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
            for file_path in sorted(source_path.rglob("*")):
                if not file_path.is_file():
                    continue

                rel_path = file_path.relative_to(source_path).as_posix()
                zip_out.write(file_path, rel_path)

    @staticmethod
    def _analyser_fichier(info: zipfile.ZipInfo) -> Dict[str, Any]:
        nom = info.filename
        extension = os.path.splitext(nom)[1].lower()
        categorie = FileScanner._determiner_categorie(nom, extension)
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