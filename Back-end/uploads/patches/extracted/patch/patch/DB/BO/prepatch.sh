#!/bin/bash
# Script de déploiement complexe pour tester le détecteur d'actions
# Auteur: Team DevOps
# Date: 2024-03-01
# Version: 2.5.0

set -e  # Arrêt en cas d'erreur
set -u  # Erreur si variable non définie

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
readonly APP_NAME="mon-application"
readonly APP_VERSION="2.5.0"
readonly APP_HOME="/opt/${APP_NAME}"
read readonly BACKUP_DIR="/var/backups/${APP_NAME}"
readonly LOG_DIR="/var/log/${APP_NAME}"
readonly CONFIG_DIR="/etc/${APP_NAME}"
readonly DATA_DIR="/var/lib/${APP_NAME}"
readonly TEMP_DIR="/tmp/${APP_NAME}_$$"

# Variables globales
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/deploy_${TIMESTAMP}.log"
ERROR_COUNT=0
WARNING_COUNT=0

# Fonction de logging
log() {
    local level=$1
    local message=$2
    local color=$NC
    
    case $level in
        "INFO") color=$BLUE ;;
        "SUCCESS") color=$GREEN ;;
        "WARNING") color=$YELLOW ;;
        "ERROR") color=$RED ;;
    esac
    
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}${NC}" | tee -a "$LOG_FILE"
}

# Fonction de vérification des prérequis
check_prerequisites() {
    log "INFO" "Vérification des prérequis..."
    
    # Vérification des commandes nécessaires
    local required_commands=("java" "curl" "wget" "tar" "gzip" "unzip" "mysql" "systemctl" "awk" "sed" "grep" "find")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -ne 0 ]; then
        log "ERROR" "Commandes manquantes: ${missing_commands[*]}"
        return 1
    fi
    
    # Vérification de l'espace disque
    local available_space=$(df /opt | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1048576 ]; then  # Moins de 1GB
        log "WARNING" "Espace disque faible: ${available_space}KB disponibles"
        ((WARNING_COUNT++))
    fi
    
    # Vérification de la mémoire
    local total_mem=$(free -m | awk 'NR==2 {print $2}')
    if [ "$total_mem" -lt 2048 ]; then
        log "WARNING" "Mémoire totale faible: ${total_mem}MB"
        ((WARNING_COUNT++))
    fi
    
    log "SUCCESS" "Prérequis vérifiés avec succès"
    return 0
}

# Fonction de création des répertoires
create_directories() {
    log "INFO" "Création des répertoires..."
    
    # Création avec permissions spécifiques
    mkdir -p "$APP_HOME" "$BACKUP_DIR" "$LOG_DIR" "$CONFIG_DIR" "$DATA_DIR" "$TEMP_DIR"
    chmod 755 "$APP_HOME"
    chmod 750 "$BACKUP_DIR"
    chmod 755 "$LOG_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 775 "$DATA_DIR"
    
    # Création de liens symboliques
    ln -sf "$APP_HOME" "/usr/local/${APP_NAME}"
    ln -sf "$LOG_DIR" "/var/log/${APP_NAME}_latest"
    
    log "SUCCESS" "Répertoires créés avec succès"
}

# Fonction de téléchargement des fichiers
download_files() {
    log "INFO" "Téléchargement des fichiers..."
    
    cd "$TEMP_DIR"
    
    # Téléchargement avec curl et wget pour tester
    curl -L -o "app-${APP_VERSION}.tar.gz" "https://example.com/releases/app-${APP_VERSION}.tar.gz" || {
        log "ERROR" "Échec du téléchargement avec curl"
        ((ERROR_COUNT++))
    }
    
    wget -q "https://example.com/releases/app-${APP_VERSION}.war" || {
        log "WARNING" "Échec du téléchargement avec wget, tentative avec curl..."
        curl -L -o "app-${APP_VERSION}.war" "https://example.com/releases/app-${APP_VERSION}.war"
    }
    
    # Téléchargement des fichiers de configuration
    curl -o "application.properties" "https://example.com/config/application.properties"
    wget -O "logback.xml" "https://example.com/config/logback.xml"
    
    log "SUCCESS" "Fichiers téléchargés"
}

# Fonction d'extraction des archives
extract_archives() {
    log "INFO" "Extraction des archives..."
    
    # Extraction tar.gz
    tar -xzf "app-${APP_VERSION}.tar.gz" -C "$TEMP_DIR" || {
        log "ERROR" "Échec de l'extraction tar.gz"
        ((ERROR_COUNT++))
        return 1
    }
    
    # Compression et décompression supplémentaires pour tester
    gzip -c "app-${APP_VERSION}.war" > "app-${APP_VERSION}.war.gz"
    gunzip -c "app-${APP_VERSION}.war.gz" > "app-${APP_VERSION}_decompressed.war"
    
    # Création d'une archive zip
    zip -r "backup-config.zip" "$CONFIG_DIR"/*.properties 2>/dev/null || true
    
    # Extraction du zip
    unzip -o "backup-config.zip" -d "$TEMP_DIR/config_restore" 2>/dev/null || true
    
    log "SUCCESS" "Archives extraites"
}

# Fonction de configuration
configure_application() {
    log "INFO" "Configuration de l'application..."
    
    # Copie des fichiers de configuration
    cp -f "$TEMP_DIR/application.properties" "$CONFIG_DIR/"
    cp -f "$TEMP_DIR/logback.xml" "$CONFIG_DIR/"
    
    # Modification des fichiers avec sed
    sed -i "s/{{APP_HOME}}/$(echo $APP_HOME | sed 's/\//\\\//g')/g" "$CONFIG_DIR/application.properties"
    sed -i "s/{{LOG_DIR}}/$(echo $LOG_DIR | sed 's/\//\\\//g')/g" "$CONFIG_DIR/logback.xml"
    sed -i "s/^#*\(server\.port=\).*/\18080/" "$CONFIG_DIR/application.properties"
    sed -i "s/^#*\(database\.host=\).*/\1localhost/" "$CONFIG_DIR/application.properties"
    sed -i "s/^#*\(database\.port=\).*/\13306/" "$CONFIG_DIR/application.properties"
    
    # Recherche et remplacement avancé avec awk
    awk '/^#/ {next} {gsub(/\$\{[^}]+\}/, "VALUE"); print}' "$CONFIG_DIR/application.properties" > "$CONFIG_DIR/application.properties.tmp"
    mv "$CONFIG_DIR/application.properties.tmp" "$CONFIG_DIR/application.properties"
    
    log "SUCCESS" "Configuration terminée"
}

# Fonction de gestion des permissions
manage_permissions() {
    log "INFO" "Gestion des permissions..."
    
    # Changement de propriétaire
    chown -R appuser:appgroup "$APP_HOME" 2>/dev/null || {
        log "WARNING" "Impossible de changer le propriétaire (utilisateur appuser inexistant)"
        ((WARNING_COUNT++))
    }
    
    # Changement des permissions avec chmod
    find "$APP_HOME" -type f -name "*.sh" -exec chmod 755 {} \;
    find "$APP_HOME" -type f -name "*.war" -exec chmod 644 {} \;
    find "$APP_HOME" -type f -name "*.properties" -exec chmod 640 {} \;
    find "$LOG_DIR" -type f -exec chmod 644 {} \;
    
    # Permissions spéciales
    chmod 4755 "$APP_HOME/bin/setuid-binary" 2>/dev/null || true
    chmod 2755 "$APP_HOME/bin/setgid-binary" 2>/dev/null || true
    
    log "SUCCESS" "Permissions configurées"
}

# Fonction de gestion des services
manage_services() {
    log "INFO" "Gestion des services..."
    
    # Arrêt des services
    systemctl stop "$APP_NAME" 2>/dev/null || {
        log "WARNING" "Service $APP_NAME non trouvé, tentative d'arrêt avec service"
        service "$APP_NAME" stop 2>/dev/null || true
    }
    
    systemctl stop "mysql" 2>/dev/null || service mysql stop 2>/dev/null || true
    systemctl stop "redis" 2>/dev/null || service redis stop 2>/dev/null || true
    
    # Vérification du statut
    systemctl status "$APP_NAME" 2>/dev/null || service "$APP_NAME" status 2>/dev/null || {
        log "INFO" "Service $APP_NAME non actif"
    }
    
    # Rechargement de la configuration
    systemctl reload "nginx" 2>/dev/null || service nginx reload 2>/dev/null || true
    
    # Démarrage des services
    systemctl start "mysql" 2>/dev/null || service mysql start 2>/dev/null || {
        log "ERROR" "Impossible de démarrer MySQL"
        ((ERROR_COUNT++))
    }
    
    systemctl start "redis" 2>/dev/null || service redis start 2>/dev/null || {
        log "WARNING" "Impossible de démarrer Redis"
        ((WARNING_COUNT++))
    }
    
    systemctl start "$APP_NAME" 2>/dev/null || service "$APP_NAME" start 2>/dev/null || {
        log "ERROR" "Impossible de démarrer $APP_NAME"
        ((ERROR_COUNT++))
    }
    
    # Activation au démarrage
    systemctl enable "$APP_NAME" 2>/dev/null || {
        log "WARNING" "Impossible d'activer $APP_NAME au démarrage"
        update-rc.d "$APP_NAME" defaults 2>/dev/null || true
    }
    
    systemctl enable "mysql" 2>/dev/null || update-rc.d mysql defaults 2>/dev/null || true
    systemctl enable "redis" 2>/dev/null || update-rc.d redis defaults 2>/dev/null || true
    
    log "SUCCESS" "Services gérés"
}

# Fonction de gestion de la base de données
manage_database() {
    log "INFO" "Gestion de la base de données..."
    
    local DB_NAME="${APP_NAME}_db"
    local DB_USER="${APP_NAME}_user"
    local DB_PASS="$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 16)"
    
    # Création de la base de données
    mysql -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || {
        log "ERROR" "Impossible de créer la base de données"
        ((ERROR_COUNT++))
        return 1
    }
    
    # Création de l'utilisateur
    mysql -e "CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';" 2>/dev/null
    mysql -e "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';" 2>/dev/null
    mysql -e "GRANT SELECT ON mysql.* TO '$DB_USER'@'localhost';" 2>/dev/null
    mysql -e "FLUSH PRIVILEGES;" 2>/dev/null
    
    # Sauvegarde de la base existante
    mysqldump "$DB_NAME" > "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql" 2>/dev/null || {
        log "INFO" "Pas de sauvegarde existante"
    }
    
    # Compression de la sauvegarde
    gzip -9 "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql" 2>/dev/null || true
    
    # Création des tables
    cat > "$TEMP_DIR/schema.sql" << 'EOF'
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
);

CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT,
    role_id INT,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

CREATE VIEW user_roles_view AS
SELECT u.username, u.email, r.name as role_name
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id;

DELIMITER //
CREATE PROCEDURE GetUserRoles(IN p_username VARCHAR(50))
BEGIN
    SELECT r.name
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    WHERE u.username = p_username;
END //
DELIMITER ;

CREATE TRIGGER before_user_insert
BEFORE INSERT ON users
FOR EACH ROW
SET NEW.created_at = NOW();
EOF
    
    # Import du schéma
    mysql "$DB_NAME" < "$TEMP_DIR/schema.sql" 2>/dev/null || {
        log "ERROR" "Erreur lors de l'import du schéma"
        ((ERROR_COUNT++))
    }
    
    # Insertion des données initiales
    mysql "$DB_NAME" << EOF
INSERT IGNORE INTO roles (name) VALUES ('ADMIN'), ('USER'), ('MANAGER');
INSERT IGNORE INTO users (username, email) VALUES ('admin', 'admin@example.com');
INSERT IGNORE INTO user_roles (user_id, role_id) 
SELECT u.id, r.id FROM users u, roles r WHERE u.username = 'admin' AND r.name = 'ADMIN';
EOF
    
    log "SUCCESS" "Base de données configurée"
}

# Fonction de nettoyage
cleanup() {
    log "INFO" "Nettoyage des fichiers temporaires..."
    
    # Suppression des fichiers temporaires
    rm -rf "$TEMP_DIR"
    rm -f "/tmp/${APP_NAME}_"*
    
    # Nettoyage des vieux logs (plus de 30 jours)
    find "$LOG_DIR" -name "*.log" -mtime +30 -exec rm -f {} \;
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -exec rm -f {} \;
    
    # Nettoyage des fichiers vides
    find "$LOG_DIR" -type f -empty -delete
    
    log "SUCCESS" "Nettoyage terminé"
}

# Fonction de rapport final
generate_report() {
    log "INFO" "Génération du rapport..."
    
    local report_file="${BACKUP_DIR}/deploy_report_${TIMESTAMP}.txt"
    
    cat > "$report_file" << EOF
=== RAPPORT DE DÉPLOIEMENT ===
Application: $APP_NAME
Version: $APP_VERSION
Date: $(date)
Timestamp: $TIMESTAMP

RÉSUMÉ:
- Erreurs: $ERROR_COUNT
- Avertissements: $WARNING_COUNT
- Log file: $LOG_FILE

CONFIGURATION:
- APP_HOME: $APP_HOME
- LOG_DIR: $LOG_DIR
- CONFIG_DIR: $CONFIG_DIR
- DATA_DIR: $DATA_DIR

ESPACE DISQUE:
$(df -h /opt /var)

SERVICES:
$(systemctl list-units --type=service --state=running | grep -E "($APP_NAME|mysql|redis|nginx)" 2>/dev/null || echo "Aucun service trouvé")

DERNIÈRES LIGNES DE LOG:
$(tail -n 20 "$LOG_FILE" 2>/dev/null || echo "Log file non disponible")
EOF
    
    # Compression du rapport
    gzip "$report_file"
    
    log "SUCCESS" "Rapport généré: ${report_file}.gz"
}

# Fonction principale
main() {
    log "INFO" "=== DÉBUT DU DÉPLOIEMENT DE $APP_NAME v$APP_VERSION ==="
    
    # Exécution des étapes
    check_prerequisites || exit 1
    create_directories
    download_files
    extract_archives
    configure_application
    manage_permissions
    manage_services
    manage_database
    cleanup
    generate_report
    
    log "SUCCESS" "=== DÉPLOIEMENT TERMINÉ AVEC $ERROR_COUNT ERREUR(S) ET $WARNING_COUNT AVERTISSEMENT(S) ==="
    
    # Code de retour
    if [ $ERROR_COUNT -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Gestion des signaux
trap 'log "ERROR" "Script interrompu"; cleanup; exit 1' INT TERM

# Exécution
main "$@"