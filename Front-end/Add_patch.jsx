import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Database, Server, Globe, ChevronDown, X, AlertCircle, CheckCircle, HardDrive, Box, Layers, Cpu, PlusCircle, RefreshCw, AlertTriangle, Terminal, Settings, Code, Wrench, FolderOpen, FileArchive, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNotification } from '../Component/NotificationContext';
import { API_BASE_URL } from "../services/api";

export default function CreationPatch() {
  // États pour les informations du patch
  const [nomPatch, setNomPatch] = useState('');
  const [descriptionPatch, setDescriptionPatch] = useState('');
  const navigate = useNavigate();
  
  // États pour les listes déroulantes
  const [clients, setClients] = useState([]);
  const [clientSelectionne, setClientSelectionne] = useState('');
  const [environnementsClient, setEnvironnementsClient] = useState([]);
  const [environnementSelectionne, setEnvironnementSelectionne] = useState('');
  
  // État pour accumuler les fichiers physiques qui vont être envoyés
  const [fichiersSoumis, setFichiersSoumis] = useState([]);
  
  // État pour les résultats des choix temporaires
  const [configurationsTemporaires, setConfigurationsTemporaires] = useState([]);
  
  // État pour le fichier uploadé
  const [fichierZip, setFichierZip] = useState(null);
  const [analyseZip, setAnalyseZip] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progressUpload, setProgressUpload] = useState(0);
  
  // État pour le tableau des clients (configurations validées)
  const [tableauClients, setTableauClients] = useState({});
  
  // États pour la modale de suppression
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [clientToDelete, setClientToDelete] = useState(null);
  
  // États pour la suppression partielle
  const [typeASupprimer, setTypeASupprimer] = useState('');
  const [quantiteASupprimer, setQuantiteASupprimer] = useState(1);
  
  // État pour la vue active (fichiers ou actions)
  const [vueActive, setVueActive] = useState('fichiers');
  const [actionPage, setActionPage] = useState(1);
  const ACTIONS_PER_PAGE = 10;
  
  // Compteur de patches
  const [nombrePatches, setNombrePatches] = useState(0);

  // États pour le chargement
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);


  const [serveursFiltres, setServeursFiltres] = useState([]);
  const [serverSelectionne, setServerSelectionne] = useState('');

  const [manualComponent, setManualComponent] = useState('');

  // État pour la modale de succès
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertConfig, setAlertConfig] = useState({ 
    message: '', 
    title: 'Error', 
    type: 'error' // 'error' ou 'warning'
  });

  // Types de patches disponibles depuis l'API
  const [typesPatches, setTypesPatches] = useState([]);

  const { fetchNotifications } = useNotification();
  const [typesDejaCrees, setTypesDejaCrees] = useState([]);
  const [existingPatchCheck, setExistingPatchCheck] = useState(null);
  const [createdPatchIds, setCreatedPatchIds] = useState([]);

  // Fonction utilitaire pour appeler la modale facilement
  const showAlert = (message, title = 'Error', type = 'error') => {
    setAlertConfig({ message, title, type });
    setIsAlertModalOpen(true);
  };
  useEffect(() => {
    setActionPage(1);
  }, [analyseZip, vueActive]);
  // 1. Chargement des types de patches depuis l'API
  useEffect(() => {
    const fetchTypesPatches = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/patchs/statistiques`);
        if (!response.ok) throw new Error('Error while loading types');
        const data = await response.json();
        setTypesPatches(data.types_patches);
      } catch (err) {
        console.error('Error loading types:', err);
      }
    };
    
    fetchTypesPatches();
  }, []);
  
  useEffect(() => {
    if (clientSelectionne && environnementSelectionne) {
      const fetchServeursFiltres = async () => {
        try {
          // Appel à la nouvelle route créée dans le backend
          const response = await fetch(`${API_BASE_URL}/patchs/servers-by-env/${clientSelectionne}/${environnementSelectionne}`);
          if (response.ok) {
            const data = await response.json();
            setServeursFiltres(data);
          }
        } catch (err) {
          console.error('Erreur lors du chargement des serveurs:', err);
        }
      };
      
      fetchServeursFiltres();
    } else {
      setServeursFiltres([]);
      setServerSelectionne('');
    }
  }, [clientSelectionne, environnementSelectionne]);
  // LOGIQUE DE DÉTECTION : On cherche le serveur qui correspond aux sélections actuelles
  // const serveurCible = servers.find(s => 
  //   s.client_id === parseInt(clientSelectionne) && 
  //   s.environment_id === parseInt(environnementSelectionne) && 
  //   s.type_server=== typeEnvironnement
  // );

  // 2. Chargement des clients depuis la base de données
  useEffect(() => {
    const fetchClients = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/clients`);
        if (response.ok) {
          const data = await response.json();
          setClients(data);
        }
      } catch (err) {
        console.error('Error loading clients:', err);
      }
    };
    
    fetchClients();
  }, []);

  // 3. Chargement des environnements quand un client est sélectionné
  useEffect(() => {
    if (clientSelectionne) {
      const fetchEnvironments = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/environments/${clientSelectionne}`);
          if (response.ok) {
            const data = await response.json();
            setEnvironnementsClient(data);
          }
        } catch (err) {
          console.error('Error loading environments:', err);
        }
      };
      
      fetchEnvironments();
      resetSelections();
    } else {
      setEnvironnementsClient([]);
      resetSelections();
    }
  }, [clientSelectionne]);

  const resetSelections = () => {
  setEnvironnementSelectionne('');
  setServerSelectionne('');
};

const PATCH_TYPE_ORDER = ['DB', 'UNIX', 'WEB'];

const COMPONENT_ORDER = ["BO", "FE"];

const getDetectedTypesOrdered = () => {
  const types = analyseZip?.actions?.types_detectes || [];

  return PATCH_TYPE_ORDER.filter(type =>
    types.map(t => t.toUpperCase()).includes(type)
  );
};

const detectedTypesOrdered = getDetectedTypesOrdered();
const normalizeText = (value) =>
  String(value || "").replaceAll("\\", "/").toLowerCase();

const getFilePatchType = (file) => {
  const path = normalizeText(file.nom || file.path || file.name || "");
  const ext = normalizeText(file.extension || "");

  const hasDbFolder =
    path.includes("/db/") ||
    path.startsWith("db/") ||
    path.includes("/database/") ||
    path.startsWith("database/");

  const hasUnixFolder =
    path.includes("/usr/") ||
    path.startsWith("usr/");

  const hasWebFolder =
    path.includes("/web/") ||
    path.startsWith("web/") ||
    path.includes("/app/") ||
    path.includes("/deploy/") ||
    path.includes("jboss") ||
    path.includes("wildfly");

  // priorité au dossier
  if (hasDbFolder) return "DB";
  if (hasUnixFolder) return "UNIX";
  if (hasWebFolder) return "WEB";

  // fallback par extension seulement si aucun dossier clair
  if (ext === ".sql") return "DB";
  if ([".war", ".ear", ".jar"].includes(ext)) return "WEB";

  return null;
};

const detectComponentsForType = (patchType) => {
  const type = String(patchType || "").toUpperCase();

  const files = analyseZip?.structure?.fichiers || [];
  const actions = analyseZip?.actions?.actions_globales || [];

  const componentsFound = new Set();

  const archiveNameText = normalizeText(
  `${fichierZip?.name || ""} ${analyseZip?.nom_fichier || ""}`
);

const texts = [
    archiveNameText,

    ...files.map((file) => {
      const path = normalizeText(file.nom || file.path || file.name || "");
      const fileType = getFilePatchType(file);

      return fileType === type ? path : "";
    }),

    ...actions
      .filter((action) => String(action.type || "").toUpperCase() === type)
      .map((action) =>
        normalizeText(`${action.description || ""} ${action.contexte || ""}`)
      ),
  ];

  const hasComponentToken = (text, tokens) => {
    const normalized = normalizeText(text);

    const parts = normalized
      .split(/[\/\\_\-\s.]+/)
      .filter(Boolean);

    return parts.some(part => tokens.includes(part));
  };

  texts.forEach((text) => {
  const normalized = normalizeText(text);

  if (
    hasComponentToken(normalized, ["bo", "backoffice"]) ||
    normalized.includes("back-office")
  ) {
    componentsFound.add("BO");
  }

  if (
    hasComponentToken(normalized, ["fe", "frontend"]) ||
    normalized.includes("front-end")
  ) {
    componentsFound.add("FE");
  }
});

  return COMPONENT_ORDER.filter((component) => componentsFound.has(component));
};

const getInnerZipFiles = () => {
  const files = analyseZip?.structure?.fichiers || [];

  return files
    .filter((file) => {
      const path = normalizeText(file.nom || file.path || file.name || "");
      const ext = normalizeText(file.extension || "");

      return ext === ".zip" || path.endsWith(".zip");
    })
    .map((file, index) => {
      const path = file.nom || file.path || file.name || `inner_zip_${index + 1}.zip`;

      return {
        key: `INNERZIP-${index + 1}`,
        name: path.split("/").pop(),
      };
    });
};

const detectedTargetsOrdered = detectedTypesOrdered.flatMap((type) => {
  const components = detectComponentsForType(type);

  if (components.length > 0) {
    return components.map((component) => ({
      type,
      component,
      key: `${type}-${component}`,
      componentDetectionFailed: false
    }));
  }

  const innerZips = getInnerZipFiles();

  if (innerZips.length > 1) {
    return innerZips.map((zip) => ({
      type,
      component: null,
      key: `${type}-MANUAL-${zip.key}`,
      sourceZipName: zip.name,
      componentDetectionFailed: true
    }));
  }

  return [{
    type,
    component: null,
    key: `${type}-MANUAL`,
    sourceZipName: innerZips[0]?.name || null,
    componentDetectionFailed: true
  }];
});
const detectedTypesKey = detectedTypesOrdered.join('|');

const typesDejaCreesNormalises = typesDejaCrees.map(t => t.toUpperCase());

const targetsConfiguresDansSummary = Object.values(tableauClients)
  .flatMap(types => Object.values(types))
  .filter(config =>
    config.zipName === fichierZip?.name &&
    String(config.clientId) === String(clientSelectionne) &&
    String(config.environnementId) === String(environnementSelectionne)
  )
  .map(config =>
    config.targetKey ||
    `${String(config.type || "").toUpperCase()}-${String(config.composant || "").toUpperCase()}`
  );

const targetsDejaConfiguresPourContexte = new Set(targetsConfiguresDansSummary);

const remainingDetectedTargets = detectedTargetsOrdered.filter((target) => {
  return !targetsDejaConfiguresPourContexte.has(target.key);
});

const currentDetectedTarget = remainingDetectedTargets[0] || null;

const currentAutoDetectedType = currentDetectedTarget?.type || "";
const isComponentDetectionFailed = currentDetectedTarget?.componentDetectionFailed === true;

const typeComposantAuto = isComponentDetectionFailed
  ? manualComponent
  : currentDetectedTarget?.component || "";
const isAllTypesConfigured =
  detectedTargetsOrdered.length > 0 &&
  remainingDetectedTargets.length === 0 &&
  clientSelectionne &&
  environnementSelectionne;

const configuredTypesCount =
  detectedTargetsOrdered.length - remainingDetectedTargets.length;



const getDetectedTypeString = (typesArray) => {
  if (!typesArray || typesArray.length === 0) return null;

  return PATCH_TYPE_ORDER.filter(type =>
    typesArray.map(t => t.toUpperCase()).includes(type)
  ).join(' / ');
};

const getAllowedServerTypes = (patchType) => {
  if (patchType === 'DB') return ['DB', 'UNIX'];
  if (patchType === 'UNIX') return ['UNIX'];
  if (patchType === 'WEB') return ['WEB'];
  return [];
};

const serveursCompatibles = serveursFiltres.filter(server => {
  if (!currentAutoDetectedType) return false;

  const serverType = server.type_server?.toUpperCase();
  return getAllowedServerTypes(currentAutoDetectedType).includes(serverType);
});

useEffect(() => {
  setManualComponent('');
}, [fichierZip, analyseZip, clientSelectionne, environnementSelectionne]);

useEffect(() => {
  const fetchTypesDejaCrees = async () => {
    if (!fichierZip || !clientSelectionne || !environnementSelectionne) {
    setTypesDejaCrees([]);
    setExistingPatchCheck(null);
    return;
  }

    try {
      const params = new URLSearchParams({
        file_name: fichierZip.name,
        client_id: clientSelectionne,
        environment_id: environnementSelectionne,
      });

      const response = await fetch(`${API_BASE_URL}/patchs/existing-types?${params.toString()}`);

      if (!response.ok) {
        setTypesDejaCrees([]);
        return;
      }

      const data = await response.json();

      setExistingPatchCheck(data);
      setTypesDejaCrees(data?.existing_types || []);
    } catch (err) {
      console.error('Erreur chargement types déjà créés:', err);
      setTypesDejaCrees([]);
      setExistingPatchCheck(null);
    }
  };

  fetchTypesDejaCrees();
}, [fichierZip, clientSelectionne, environnementSelectionne]);



  const getStructureDetail = (type, composant) => {
    if (type === 'UNIX') {
      return 'usr → ctl, bin, lib';
    } else if (type === 'WEB') {
      return composant === 'BO' ? 'powercard' : 'FE';
    }
    return composant === 'BO' ? 'Back-office' : 'Front-end';
  };

  const UPLOAD_PROGRESS_WEIGHT = 50;
  const ANALYSIS_PROGRESS_WEIGHT = 50;

  const uploadPatchForAnalysis = (file) => {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file);

      const xhr = new XMLHttpRequest();

      xhr.open(
        'POST',
        `${API_BASE_URL}/patchs/analyser/start`
      );

      xhr.withCredentials = true;

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;

        const uploadPercent = Math.round(
          (event.loaded / event.total) * 100
        );

        const hybridProgress = Math.round(
          (uploadPercent * UPLOAD_PROGRESS_WEIGHT) / 100
        );

        setProgressUpload((previousProgress) =>
          Math.max(
            previousProgress,
            Math.min(
              UPLOAD_PROGRESS_WEIGHT,
              hybridProgress
            )
          )
        );
      };

      xhr.upload.onload = () => {
        setProgressUpload((previousProgress) =>
          Math.max(
            previousProgress,
            UPLOAD_PROGRESS_WEIGHT
          )
        );
      };

      xhr.onload = () => {
        let responseData = null;

        try {
          responseData = xhr.responseText
            ? JSON.parse(xhr.responseText)
            : null;
        } catch {
          responseData = null;
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(responseData);
          return;
        }

        reject(
          new Error(
            responseData?.detail ||
            'Unable to process the patch.'
          )
        );
      };

      xhr.onerror = () => {
        reject(
          new Error(
            'Network error while processing the patch.'
          )
        );
      };

      xhr.onabort = () => {
        reject(
          new Error(
            'Patch processing was cancelled.'
          )
        );
      };

      xhr.send(formData);
    });
  };

  const waitForPatchAnalysis = async (jobId) => {
    while (true) {
      const response = await fetch(
        `${API_BASE_URL}/patchs/analyser/status/${encodeURIComponent(jobId)}`,
        {
          method: 'GET',
          credentials: 'include',
          cache: 'no-store',
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => null);

        throw new Error(
          errorData?.detail ||
          'Unable to retrieve patch processing status.'
        );
      }

      const job = await response.json();

      const backendPercent = Math.max(
        0,
        Math.min(
          100,
          Number(job.progress_percent || 0)
        )
      );

      const hybridProgress =
        UPLOAD_PROGRESS_WEIGHT +
        Math.round(
          (backendPercent * ANALYSIS_PROGRESS_WEIGHT) / 100
        );

      setProgressUpload((previousProgress) =>
        Math.max(
          previousProgress,
          Math.min(
            job.status === 'SUCCESS' ? 100 : 99,
            hybridProgress
          )
        )
      );

      if (job.status === 'SUCCESS') {
        setProgressUpload(100);
        return job.result;
      }

      if (job.status === 'FAILED') {
        throw new Error(
          job.error ||
          'Patch processing failed.'
        );
      }

      await new Promise((resolve) => {
        setTimeout(resolve, 200);
      });
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];

    if (!file) return;

    e.target.value = '';

    if (!file.name.toLowerCase().endsWith('.zip')) {
      showAlert(
        'Please select a valid ZIP file (.zip only).',
        'Invalid Format',
        'warning'
      );
      return;
    }

    setIsUploading(true);
    setProgressUpload(0);
    setFichierZip(file);
    setAnalyseZip(null);
    setServerSelectionne('');
    setError(null);

    try {
      const startResult = await uploadPatchForAnalysis(file);

      if (!startResult?.job_id) {
        throw new Error(
          'The backend did not return an analysis job ID.'
        );
      }

      setProgressUpload((previousProgress) =>
        Math.max(
          previousProgress,
          UPLOAD_PROGRESS_WEIGHT
        )
      );

      const analyse = await waitForPatchAnalysis(
        startResult.job_id
      );

      setAnalyseZip(analyse);
      setProgressUpload(100);

      await new Promise((resolve) => {
        setTimeout(resolve, 600);
      });

      setIsUploading(false);
    } catch (error) {
      console.error(
        'Patch upload/analysis error:',
        error
      );

      setError(error.message);
      setIsUploading(false);
      setProgressUpload(0);
      setFichierZip(null);
      setAnalyseZip(null);
    }
  };

  const ajouterConfiguration = () => {
  const champsManquants = [];

  if (!clientSelectionne) champsManquants.push("Client");
  if (!environnementSelectionne) champsManquants.push("Environment");
  if (!currentAutoDetectedType) champsManquants.push("Auto-detected Type");
  if (!serverSelectionne) champsManquants.push("Assigned execution server");
  if (!typeComposantAuto) champsManquants.push("Auto-detected Component");
  if (!fichierZip) champsManquants.push("ZIP File");

  if (champsManquants.length > 0) {
    showAlert(
      `Please complete the following missing fields:\n- ${champsManquants.join('\n- ')}`,
      'Missing Information',
      'warning'
    );
    return;
  }

  if (nombrePatches >= 10) {
    showAlert(
      'You have reached the maximum limit of 10 patches per configuration.',
      'Limit Reached',
      'warning'
    );
    return;
  }

  const server = serveursFiltres.find(s => s.id === parseInt(serverSelectionne));

  if (!server) {
    showAlert('Selected server not found.', 'Invalid Server', 'error');
    return;
  }

  const serverType = server.type_server?.toUpperCase();
  const allowedServerTypes = getAllowedServerTypes(currentAutoDetectedType);

  if (!allowedServerTypes.includes(serverType)) {
    showAlert(
      `Invalid server for this patch type.\n\nPatch type: ${currentAutoDetectedType}\nSelected server type: ${serverType}\nAllowed server types: ${allowedServerTypes.join(', ')}`,
      'Server Type Mismatch',
      'error'
    );
    return;
  }

  const client = clients.find(c => c.id === parseInt(clientSelectionne));
  const environnement = environnementsClient.find(e => e.id === parseInt(environnementSelectionne));

  const nouvelleConfig = {
    id: Date.now(),
    client: client?.nom,
    clientId: clientSelectionne,
    environnement: environnement?.type,
    environnementId: environnementSelectionne,
    type: currentAutoDetectedType,
    composant: typeComposantAuto,
    structure: getStructureDetail(currentAutoDetectedType, typeComposantAuto),
    zipName: fichierZip?.name,
    serverId: serverSelectionne,
    serverName: server?.name,
    serverType: server?.type_server,
    targetKey: currentDetectedTarget?.key,
  };
  setFichiersSoumis(prev => {
    if (!prev.find(f => f.name === fichierZip.name)) {
      return [...prev, fichierZip];
    }
    return prev;
  });

  const isLastTargetForCurrentContext = remainingDetectedTargets.length <= 1;

  setTableauClients(prev => {
  const nouveauTableau = { ...prev };

  if (!nouveauTableau[nouvelleConfig.client]) {
    nouveauTableau[nouvelleConfig.client] = {};
  }

  const isLastTargetForCurrentContext = remainingDetectedTargets.length <= 1;

  const cleUnique = `${nouvelleConfig.targetKey}_${nouvelleConfig.composant}_${nouvelleConfig.serverId}`;

  const countActuel = nouveauTableau[nouvelleConfig.client][cleUnique]?.count || 0;

  nouveauTableau[nouvelleConfig.client] = {
    ...nouveauTableau[nouvelleConfig.client],
    [cleUnique]: {
      type: nouvelleConfig.type,
      composant: nouvelleConfig.composant,
      targetKey: nouvelleConfig.targetKey,
      zipName: nouvelleConfig.zipName,
      clientId: nouvelleConfig.clientId,
      environnementId: nouvelleConfig.environnementId,
      serverName: nouvelleConfig.serverName,
      serverId: nouvelleConfig.serverId,
      count: countActuel + 1
    }
  };

  return nouveauTableau;
});

setNombrePatches(prev => prev + 1);
setManualComponent('');


if (isLastTargetForCurrentContext) {
  setClientSelectionne('');
  setEnvironnementSelectionne('');
  setServerSelectionne('');
  setServeursFiltres([]);
  setAnalyseZip(null);
  setFichierZip(null);
  setTypesDejaCrees([]);
  setExistingPatchCheck(null);
} else {
  setServerSelectionne('');
}
  
};


  const demanderSuppressionClient = (nomClient) => {
    setClientToDelete(nomClient);
    
    const typesDisponibles = Object.keys(tableauClients[nomClient] || {});
    if (typesDisponibles.length > 0) {
      setTypeASupprimer(typesDisponibles[0]);
      setQuantiteASupprimer(1);
    }
    
    setIsDeleteModalOpen(true);
  };

  const annulerSuppressionClient = () => {
    setIsDeleteModalOpen(false);
    setClientToDelete(null);
    setTypeASupprimer('');
    setQuantiteASupprimer(1);
  };

  const confirmerSuppressionClient = () => {
    if (!clientToDelete || !typeASupprimer) return;

    const nouveauTableau = { ...tableauClients };
    const typeInfo = nouveauTableau[clientToDelete][typeASupprimer];

    if (typeInfo) {
      if (typeInfo.count <= quantiteASupprimer) {
        delete nouveauTableau[clientToDelete][typeASupprimer];
      } else {
        nouveauTableau[clientToDelete][typeASupprimer] = {
          ...typeInfo,
          count: typeInfo.count - quantiteASupprimer
        };
      }
    }

    if (Object.keys(nouveauTableau[clientToDelete]).length === 0) {
      delete nouveauTableau[clientToDelete];
    }

    setTableauClients(nouveauTableau);
    setNombrePatches(prev => Math.max(0, prev - quantiteASupprimer));
    setIsDeleteModalOpen(false);
    setClientToDelete(null);
  };

  const genererRapport = async () => {
    if (!fichierZip) return;
    
    const formData = new FormData();
    formData.append('file', fichierZip);
    
    try {
      setLoading(true);
      const url = `${API_BASE_URL}/patches/rapport?t=${Date.now()}`;
      
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      });
      
      if (!response.ok) throw new Error('Error generating the report');
      
      const blob = await response.blob();
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'rapport.pdf';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (match && match[1]) {
          filename = match[1].replace(/['"]/g, '');
        }
      } else {
        const now = new Date();
        const timestamp = `${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2,'0')}${now.getDate().toString().padStart(2,'0')}_${now.getHours().toString().padStart(2,'0')}${now.getMinutes().toString().padStart(2,'0')}${now.getSeconds().toString().padStart(2,'0')}`;
        filename = `Rapport_${fichierZip.name.replace('.zip', '')}_${timestamp}.pdf`;
      }
      
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
      }, 1000);
      
    } catch (err) {
      console.error('Report error:', err);
      // ✅ REMPLACEMENT ALERTE
      showAlert(`Error while generating the report: ${err.message}`, 'Report Generation Error', 'error');
    } finally {
      setLoading(false);
    }
  };


  const actionCategoryStats = analyseZip?.actions?.statistiques_categories || {};

  const getActionCategoryCount = (keyword) => {
    const entry = Object.entries(actionCategoryStats).find(([label]) =>
      normalizeText(label).includes(keyword)
    );
  
    return entry ? entry[1] : 0;
  };
  
  const countFilesInsideFolder = (folderName) => {
    const files = analyseZip?.structure?.fichiers || [];
    const folder = String(folderName || "").toLowerCase();
  
    return files.filter((file) => {
      const path = `/${normalizeText(file.nom || file.path || file.name || "")}`;
  
      return path.includes(`/${folder}/`);
    }).length;
  };
  
  const unixDeployCount = countFilesInsideFolder("usr");
  
  const webDeployCount =
    analyseZip?.structure?.statistiques?.web ??
    analyseZip?.structure?.statistiques?.WEB ??
    getActionCategoryCount("web files");
  
    const visibleActionCategoryStats = Object.entries(actionCategoryStats).filter(
      ([categorie]) => {
        const label = normalizeText(categorie);
        const compactLabel = label.replace(/[^a-z0-9]/g, "");
    
        return (
          !label.includes("unix files") &&
          !label.includes("web files") &&
          compactLabel !== "plsql"
        );
      }
    );
  const fetchCreatedPatchIdsFromPending = async (patchesToCreate) => {
  const response = await fetch(`${API_BASE_URL}/patchs/pending-patches`, {
    credentials: "include"
  });

  if (!response.ok) {
    throw new Error("Unable to retrieve created patch from pending patches.");
  }

  const groups = await response.json();

  const allPendingPatches = groups.flatMap(group =>
    (group.patches || []).map(patch => ({
      ...patch,
      group_created_at: group.created_at
    }))
  );

  const foundIds = [];

  patchesToCreate.forEach((createdPatch) => {
    const expectedName = `${createdPatch.name}_${createdPatch.component}`;

    const matchingPatch = allPendingPatches
      .filter((patch) =>
        patch.name_patch === expectedName &&
        patch.filename === createdPatch.file_name &&
        String(patch.id_server) === String(createdPatch.server_id) &&
        String(patch.type_patch).toUpperCase() === String(createdPatch.patch_type).toUpperCase() &&
        String(patch.component).toUpperCase() === String(createdPatch.component).toUpperCase()
      )
      .sort((a, b) => new Date(b.group_created_at) - new Date(a.group_created_at))[0];

    if (matchingPatch?.id) {
      foundIds.push(matchingPatch.id);
    }
  });

  return foundIds;
};



  const handleSubmit = async (e) => {
    e.preventDefault();
    if (Object.keys(tableauClients).length === 0) return;

    setLoading(true);

    const patchesToCreate = [];
    
    Object.values(tableauClients).forEach((types) => {
      Object.entries(types).forEach(([type, info]) => {
        patchesToCreate.push({
          name: nomPatch,
          description: descriptionPatch,
          file_name: info.zipName,
          client_id: parseInt(info.clientId),
          environment_id: parseInt(info.environnementId),
          server_id: info.serverId ? parseInt(info.serverId) : null, 
          patch_type: info.type,
          component: info.composant,
          duplication_count: info.count,
          status: "PENDING",
          // user_id: parseInt(info.clientId),
        });
      });
    });
    const usedZipNames = new Set(patchesToCreate.map(p => p.file_name));
    const filesToSend = fichiersSoumis.filter(f => usedZipNames.has(f.name));
    const formData = new FormData();
    filesToSend.forEach(file => {
      formData.append('files', file); // Attention: 'files' au pluriel pour correspondre à FastAPI
    });
    formData.append('patch_data', JSON.stringify(patchesToCreate));
    
    if (analyseZip) {
      formData.append('analysis_data', JSON.stringify(analyseZip));
    }

    try {
      for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(key, {
            fileName: value.name,
            size: value.size,
            type: value.type
          });
        } else {
          console.log(key, value);
        }
      }
      const response = await fetch(`${API_BASE_URL}/patchs/create`, {
        method: 'POST',
        body: formData,
        credentials: "include"
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 401) {
          throw new Error("Session expirée ou non autorisée. Veuillez vous reconnecter.");
        }
        throw new Error(errorData.detail || 'Error creating the patch');
      }


      await response.json();

      const newPatchIds = await fetchCreatedPatchIdsFromPending(patchesToCreate);

      setCreatedPatchIds(newPatchIds);

      await fetchNotifications();

      setIsSuccessModalOpen(true);
      
      // Réinitialiser le formulaire
      setNomPatch('');
      setDescriptionPatch('');
      setTableauClients({});
      setConfigurationsTemporaires([]);
      setNombrePatches(0);
      setFichierZip(null);
      setAnalyseZip(null);
      setFichiersSoumis([]);
      setServerSelectionne('');
      setTypesDejaCrees([]);

    } catch (err) {
      console.error("Save error:", err);
      // ✅ REMPLACEMENT ALERTE
      showAlert(err.message, 'Save Error', 'error'); 
    } finally {
      setLoading(false);
    }
  };

  const getTypeIcon = (patch_type) => {
    switch(patch_type) {
      case 'DB': return <Database className="w-4 h-4" />;
      case 'UNIX': return <Server className="w-4 h-4" />;
      case 'WEB': return <Globe className="w-4 h-4" />;
      default: return <Layers className="w-4 h-4" />;
    }
  };

  const getActionIcon = (categorie) => {
    switch(categorie) {
      case 'DDL': case 'DML': case 'DCL': case 'TCL': case 'PLSQL': return <Database className="w-4 h-4 text-blue-500" />;
      case 'FICHIER': case 'PERMISSION': case 'SERVICE_SYSTEMD': case 'SERVICE_SYSV': case 'ARCHIVE': case 'PACKAGE': return <Terminal className="w-4 h-4 text-green-500" />;
      case 'DATABASE': case 'RESEAU': case 'AUTH': case 'LOGGING': case 'CACHE': case 'TIMEOUT': case 'JVM': case 'SECURITE': return <Settings className="w-4 h-4 text-orange-500" />;
      case 'APPLICATION': return <Globe className="w-4 h-4 text-purple-500" />;
      default: return <Wrench className="w-4 h-4 text-slate-500" />;
    }
  };

  const getComposantIcon = (composant) => {
    switch(composant) {
      case 'BO': return <HardDrive className="w-4 h-4" />;
      case 'FE': return <Cpu className="w-4 h-4" />;
      default: return <Box className="w-4 h-4" />;
    }
  };

  const getFileIcon = (extension) => {
    switch(extension) {
      case '.sql': return <Database className="w-4 h-4 text-blue-500" />;
      case '.sh': case '.bash': return <Terminal className="w-4 h-4 text-green-500" />;
      case '.war': case '.ear': case '.jar': return <Globe className="w-4 h-4 text-purple-500" />;
      case '.xml': case '.properties': case '.conf': case '.yml': case '.yaml': return <Settings className="w-4 h-4 text-orange-500" />;
      case '.so': case '.dll': case '.bin': return <Code className="w-4 h-4 text-slate-500" />;
      default: return <FileText className="w-4 h-4 text-slate-400" />;
    }
  };

  const formatTaille = (octets) => {
    if (octets < 1024) return octets + ' o';
    if (octets < 1024 * 1024) return (octets / 1024).toFixed(2) + ' Ko';
    return (octets / (1024 * 1024)).toFixed(2) + ' Mo';
  };

  const organiserParDossier = (fichiers) => {
    const structure = {};
    fichiers.forEach(fichier => {
      const parties = fichier.nom.split('/');
      let current = structure;
      for (let i = 0; i < parties.length - 1; i++) {
        const dossier = parties[i];
        if (!current[dossier]) {
          current[dossier] = { type: 'dossier', contenu: {} };
        }
        current = current[dossier].contenu;
      }
      const nomFichier = parties[parties.length - 1];
      current[nomFichier] = { type: 'fichier', ...fichier };
    });
    return structure;
  };

  const ArborescenceFichiers = ({ structure, niveau = 0 }) => {
    return Object.entries(structure).map(([nom, element]) => {
      if (element.type === 'dossier') {
        return (
          <div key={nom} className="ml-4">
            <div className="flex items-center gap-2 py-1 text-slate-600">
              <FolderOpen className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium">{nom}/</span>
            </div>
            <ArborescenceFichiers structure={element.contenu} niveau={niveau + 1} />
          </div>
        );
      } else {
        return (
          <motion.div
            key={nom}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="ml-8 flex items-start gap-2 py-2 px-3 hover:bg-slate-100 rounded-lg transition-colors group"
          >
            {getFileIcon(element.extension)}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">{nom}</span>
                <span className="text-xs text-slate-400">{formatTaille(element.taille)}</span>
              </div>
            </div>
          </motion.div>
        );
      }
    });
  };
  const actionsList = analyseZip?.actions?.actions_globales || [];

const totalActionPages = Math.max(
  1,
  Math.ceil(actionsList.length / ACTIONS_PER_PAGE)
);

const currentActionPage = Math.min(actionPage, totalActionPages);

const paginatedActions = actionsList.slice(
  (currentActionPage - 1) * ACTIONS_PER_PAGE,
  currentActionPage * ACTIONS_PER_PAGE
);

const actionStart =
  actionsList.length === 0
    ? 0
    : (currentActionPage - 1) * ACTIONS_PER_PAGE + 1;

const actionEnd = Math.min(
  currentActionPage * ACTIONS_PER_PAGE,
  actionsList.length
);
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <h2 className="text-lg font-semibold text-red-800 mb-2">Connection error</h2>
            <p className="text-red-600">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }


  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-slate-800 mb-2">New Patch Creation</h1>
            <p className="text-slate-500">Fill in the information below to create and configure your patch</p>
          </div>
          <div className="bg-blue-100 text-blue-800 px-4 py-2 rounded-lg font-semibold">
            Patches added : {nombrePatches}/10
          </div>
        </div>

        {loading && (
          <div className="fixed top-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 z-50">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Loading...
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Patch information
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Patch name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={nomPatch}
                  onChange={(e) => setNomPatch(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  placeholder="ex: PATCH-SEC-2024-001"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Description
                </label>
                <input
                  type="text"
                  value={descriptionPatch}
                  onChange={(e) => setDescriptionPatch(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  placeholder="Description courte du patch"
                />
              </div>
            </div>
          </div>

          {/* Section 2 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-600" />
              Patch file <span className="text-sm font-normal text-slate-500 ml-2">(Upload required before configuration)</span>
            </h2>
            
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-blue-400 transition-colors">
              <input
                type="file"
                accept=".zip"
                onChange={handleFileUpload}
                className="hidden"
                id="zip-upload"
                disabled={isUploading || loading}
              />
              <label
                htmlFor="zip-upload"
                className={`cursor-pointer flex flex-col items-center gap-3 ${isUploading || loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <Upload className="w-10 h-10 text-slate-400" />
                <div>
                  <p className="text-slate-700 font-medium">
                    {isUploading ? 'Uploading...' : 'Click to upload your ZIP file'}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    Accepted format: ZIP only
                  </p>
                </div>
              </label>
            </div>

            {isUploading && (
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin text-blue-600" />
                    <span className="text-sm font-medium text-slate-700">
                      Processing patch
                    </span>
                  </div>

                  <span className="text-sm font-bold text-blue-600">
                    {progressUpload}%
                  </span>
                </div>

                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${progressUpload}%` }}
                    transition={{
                      duration: 0.2,
                      ease: 'easeOut'
                    }}
                    className="h-full bg-blue-600"
                  />
                </div>
              </div>
            )}

            <AnimatePresence>
              {analyseZip && !isUploading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="mt-6 bg-slate-50 rounded-lg border border-slate-200 overflow-hidden"
                >
                  <div className="p-6 bg-white border-b border-slate-200">
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">Analysis complete - {analyseZip.nom_fichier}</span>
                      <span className="text-xs text-slate-500 ml-2">({formatTaille(analyseZip.taille)})</span>
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Total (files)</p>
                        <p className="font-bold text-slate-800">
                          {analyseZip.structure.statistiques.total || 0}
                        </p>
                      </div>

                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Database (files)</p>
                        <p className="font-bold text-blue-600">
                          {analyseZip.structure.statistiques.database || 0}
                        </p>
                      </div>

                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Number of UNIX files to deploy</p>
                        <p className="font-bold text-slate-800">
                          {unixDeployCount || 0}
                        </p>
                      </div>

                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Number of WEB files to deploy</p>
                        <p className="font-bold text-slate-800">
                          {webDeployCount || 0}
                        </p>
                      </div>
                    </div>
                    
                    {visibleActionCategoryStats.length > 0 && (
                      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
                        {visibleActionCategoryStats.map(([categorie, count]) => (
                          <div key={categorie} className="bg-slate-50 p-2 rounded-lg text-center">
                            <p className="text-xs text-slate-500">{categorie}</p>
                            <p className="font-bold text-slate-800">{count}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {analyseZip.actions.types_detectes && analyseZip.actions.types_detectes.length > 0 && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
                        <p className="text-sm font-medium text-blue-800 mb-2">Detected patch types :</p>
                        <div className="flex flex-wrap gap-2">
                          {analyseZip.actions.types_detectes.map(type => (
                            <span key={type} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium flex items-center gap-1">
                              {getTypeIcon(type)}
                              {type}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex border-b border-slate-200 bg-white">
                    <button
                      type="button"
                      onClick={() => setVueActive('fichiers')}
                      className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
                        vueActive === 'fichiers' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <FileArchive className="w-4 h-4" />
                      Files ({analyseZip.structure.fichiers.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setVueActive('actions')}
                      className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors ${
                        vueActive === 'actions' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <AlertCircle className="w-4 h-4" />
                      Actions ({analyseZip.actions.nombre_actions})
                    </button>
                  </div>

                  <div className="p-6">
                    {vueActive === 'fichiers' && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
                          <FolderOpen className="w-4 h-4" />
                          File tree
                        </h4>
                        <div className="bg-white rounded-lg border border-slate-200 p-4 max-h-96 overflow-y-auto">
                          <ArborescenceFichiers structure={organiserParDossier(analyseZip.structure.fichiers)} />
                        </div>
                      </div>
                    )}

                    {vueActive === 'actions' && (
                      <div>
                        <h4 className="text-sm font-medium text-slate-700 mb-4 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4" />
                          Detected actions
                        </h4>
                        
                        {actionsList.length > 0 ? (
  <>
    <div className="space-y-3">
      {paginatedActions.map((action, idx) => {
        const realIndex = (currentActionPage - 1) * ACTIONS_PER_PAGE + idx;

        return (
          <motion.div
            key={realIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03 }}
            className="flex items-start gap-3 p-4 bg-white rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors"
          >
            <div className="mt-0.5">
              {getActionIcon(action.categorie)}
            </div>

            <div className="flex-1">
              <div className="flex items-start justify-between">
                <span className="text-sm font-medium text-slate-800">
                  {action.description}
                </span>

                <span className="text-xs px-2 py-1 bg-slate-100 text-slate-600 rounded-full ml-2">
                  {action.categorie}
                </span>
              </div>

              {action.type && (
                <div className="mt-1 flex items-center gap-2">
                  <span className="text-xs text-slate-500">
                    Type: {action.type}
                  </span>

                  {action.contexte && (
                    <>
                      <span className="text-slate-300">•</span>
                      <span className="text-xs text-slate-500">
                        File: {action.contexte.split('/').pop()}
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>

    {actionsList.length > ACTIONS_PER_PAGE && (
      <div className="mt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-slate-200 pt-4">
        <p className="text-sm text-slate-500">
          Showing {actionStart} - {actionEnd} of {actionsList.length} actions
        </p>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => setActionPage(prev => Math.max(1, prev - 1))}
            disabled={currentActionPage === 1}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          {Array.from({ length: totalActionPages }, (_, i) => i + 1).map(page => (
            <button
              key={page}
              type="button"
              onClick={() => setActionPage(page)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                page === currentActionPage
                  ? "bg-blue-600 text-white border-blue-600"
                  : "border-slate-200 text-slate-600 hover:bg-slate-100"
              }`}
            >
              {page}
            </button>
          ))}

          <button
            type="button"
            onClick={() => setActionPage(prev => Math.min(totalActionPages, prev + 1))}
            disabled={currentActionPage === totalActionPages}
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    )}
  </>
) : (
  <div className="text-center py-8 text-slate-500 bg-white rounded-lg border border-slate-200">
    <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
    <p>No specific action detected in the files</p>
  </div>
)}
                      </div>
                    )}
                  </div>

                  {/* <div className="p-4 bg-slate-50 border-t border-slate-200">
                    <button
                      type="button"
                      onClick={genererRapport}
                      disabled={!fichierZip || isUploading || loading}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <FileText className="w-4 h-4" />
                      Generate a detailed report
                    </button>
                  </div> */}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

         {/* Section 3 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-600" />
              Environment configuration
            </h2>

            {/* LIGNE 1 : CLIENT | ENVIRONMENT | COMPONENT */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Platform
                </label>
                <select
                  value={clientSelectionne}
                  onChange={(e) => setClientSelectionne(e.target.value)}
                  disabled={nombrePatches >= 10 || !fichierZip}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select a Platform</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>{client.nom}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Environment
                </label>
                <select
                  value={environnementSelectionne}
                  onChange={(e) => setEnvironnementSelectionne(e.target.value)}
                  disabled={!clientSelectionne || nombrePatches >= 10 || !fichierZip}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select an environment</option>
                  {environnementsClient.map(env => (
                    <option key={env.id} value={env.id}>{env.type}</option>
                  ))}
                </select>
              </div>

              <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Assigned server
                  </label>
                  <select
                    value={serverSelectionne}
                    onChange={(e) => setServerSelectionne(e.target.value)}
                    disabled={!environnementSelectionne || serveursCompatibles.length === 0 || nombrePatches >= 10 || !fichierZip || !currentAutoDetectedType || isAllTypesConfigured}
                    className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="">Select a server</option>
                    {serveursCompatibles.map(srv => (
                      <option key={srv.id} value={srv.id}>
                        {srv.name} ({srv.ip_address}) - {srv.type_server}
                      </option>
                    ))}
                  </select>

                  {environnementSelectionne && currentAutoDetectedType && serveursCompatibles.length === 0 && (
                    <p className="text-xs font-medium text-amber-600 mt-1.5 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      No compatible server available for {currentAutoDetectedType}
                    </p>
                  )}
                </div>
            </div>

            {/* LIGNE 2 : AUTO-DETECTED | TYPE À CONFIGURER | ASSIGNED SERVER */}
            <div className="mb-6 p-5 rounded-xl border border-indigo-100 bg-indigo-50/30">
              <h3 className="text-sm font-semibold text-indigo-900 mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4 text-indigo-500" />
                Patch Type Configuration
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Auto-detected Type
                  </label>

                  <div className="w-full px-4 py-2.5 bg-slate-100 border border-slate-200 rounded-lg text-indigo-700 font-bold flex items-center gap-2 h-[46px] shadow-inner">
                    {currentDetectedTarget ? (
                            <>
                              <Cpu className="w-5 h-5 text-indigo-500" />
                              <span>{currentAutoDetectedType}</span>
                            </>
                          ) : (
                            <span className="text-slate-400 font-normal italic text-sm">
                              {detectedTargetsOrdered.length === 0 ? 'Waiting for analysis...' : 'Completed'}
                            </span>
                          )}
                  </div>
                  {typesDejaCreesNormalises.length > 0 &&
                    remainingDetectedTargets.length > 0 &&
                    detectedTypesOrdered.some(type => typesDejaCreesNormalises.includes(type)) && (
                      <p className="mt-2 text-xs font-medium text-amber-600 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Already configured type(s):{" "}
                        {detectedTypesOrdered
                          .filter(type => typesDejaCreesNormalises.includes(type))
                          .join(" / ")}
                      </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Type
                  </label>

                  <div className="w-full px-4 py-2.5 bg-slate-100 border border-slate-200 rounded-lg text-indigo-700 font-bold flex items-center gap-2 h-[46px] shadow-inner">
                    {currentDetectedTarget ? (
                      <>
                        {getTypeIcon(currentAutoDetectedType)}
                        <span>
                          {currentAutoDetectedType}
                          {typeComposantAuto ? `-${typeComposantAuto}` : ''}
                        </span>
                        <span className="ml-auto text-xs font-medium text-slate-500">
                          {Math.min(configuredTypesCount + 1, detectedTargetsOrdered.length)} / {detectedTargetsOrdered.length}
                        </span>
                      </>
                    ) : (
                      <span className="text-slate-400 font-normal italic text-sm">
                        {detectedTargetsOrdered.length === 0 ? 'Waiting for analysis...' : 'Completed'}
                      </span>
                    )}
                  </div>
                  {isComponentDetectionFailed && (
                    <div className="mt-4 p-4 rounded-xl border border-amber-200 bg-amber-50">
                      <p className="text-sm font-medium text-amber-700 mb-3 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4" />
                        Component detection failed. Please select the component manually.
                      </p>

                      <select
                        value={manualComponent}
                        onChange={(e) => setManualComponent(e.target.value)}
                        disabled={!currentAutoDetectedType || loading || isUploading}
                        className="w-full px-4 py-2.5 bg-white border border-amber-200 rounded-lg focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <option value="">Select component</option>
                        <option value="BO">BO</option>
                        <option value="FE">FE</option>
                      </select>
                    </div>
                  )}
                </div>

                
              </div>
            </div>

            

 
            
            {/* Avertissement si ZIP manquant */}
            {!fichierZip && (
              <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <p className="text-sm text-amber-700">Please upload a ZIP file first to configure the environments</p>
              </div>
            )}
            
            <div className="flex gap-3 mb-6">
              <button
                type="button"
                onClick={ajouterConfiguration}
                disabled={
                    !clientSelectionne ||
                    !environnementSelectionne ||
                    !serverSelectionne ||
                    !currentAutoDetectedType ||
                    !typeComposantAuto ||
                    !fichierZip ||
                    loading ||
                    isUploading ||
                    nombrePatches >= 10 ||
                    isAllTypesConfigured
                  }
                className="flex items-center gap-2 px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PlusCircle className="w-4 h-4" />
                Add configuration for {
                  currentDetectedTarget
                    ? `${currentAutoDetectedType}${typeComposantAuto ? `-${typeComposantAuto}` : ''}`
                    : 'detected target'
                } ({nombrePatches}/10)
              </button>
              
              
            </div>

           
          </div>

          {/* Section 4 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <h2 className="text-xl font-semibold text-slate-800 mb-4">Client summary</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">Client</th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">
                      <div className="flex items-center gap-2"><Database className="w-4 h-4" /> DB</div>
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">
                      <div className="flex items-center gap-2"><Server className="w-4 h-4" /> UNIX</div>
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">
                      <div className="flex items-center gap-2"><Globe className="w-4 h-4" /> WEB</div>
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700">
                      <div className="flex items-center gap-2"><FileText className="w-4 h-4" /> ZIP file</div>
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-slate-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(tableauClients).map(([client, types]) => (
                   <tr key={client} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-4 font-medium text-slate-800">{client}</td>
                      
                      {/* Colonne DB */}
                      <td className="py-3 px-4">
                        {Object.values(types).filter(t => t.type === 'DB').map((info, idx) => (
                          <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm mr-2 mb-1">
                            {getComposantIcon(info.composant)} {info.composant}
                            {info.count > 1 && <span className="ml-1 font-bold text-xs bg-blue-200 px-1.5 py-0.5 rounded-full">x{info.count}</span>}
                          </span>
                        ))}
                      </td>

                      {/* Colonne UNIX */}
                      <td className="py-3 px-4">
                        {Object.values(types).filter(t => t.type === 'UNIX').map((info, idx) => (
                          <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded text-sm mr-2 mb-1">
                            {getComposantIcon(info.composant)} {info.composant}
                            {info.count > 1 && <span className="ml-1 font-bold text-xs bg-green-200 px-1.5 py-0.5 rounded-full">x{info.count}</span>}
                          </span>
                        ))}
                      </td>

                      {/* Colonne WEB */}
                      <td className="py-3 px-4">
                        {Object.values(types).filter(t => t.type === 'WEB').map((info, idx) => (
                          <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded text-sm mr-2 mb-1">
                            {getComposantIcon(info.composant)} {info.composant}
                            {info.count > 1 && <span className="ml-1 font-bold text-xs bg-purple-200 px-1.5 py-0.5 rounded-full">x{info.count}</span>}
                          </span>
                        ))}
                      </td>

                      {/* Colonne ZIP */}
                      <td className="py-3 px-4">
                        {Object.values(types).length > 0 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 text-slate-700 rounded text-sm">
                            <FileText className="w-3 h-3" />
                            {Object.values(types)[0].zipName} - {Object.values(types)[0].serverName}
                          </span>
                        ) : <span className="text-slate-400 text-sm">-</span>}
                      </td>

                      {/* Bouton Corbeille */}
                      <td className="py-3 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => demanderSuppressionClient(client)}
                          className="p-2 text-red-500 hover:bg-red-50 hover:text-red-700 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-5 h-5 mx-auto" />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {Object.keys(tableauClients).length === 0 && (
                    <tr>
                      <td colSpan="6" className="py-8 text-center text-slate-500">
                        No configuration validated at the moment
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={Object.keys(tableauClients).length === 0 || loading || isUploading}
              className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Save
              <ChevronDown className="w-4 h-4 rotate-270" />
            </button>
          </div>
        </form>
      </div>
      
      {/* Modale de confirmation de suppression partielle */}
      <AnimatePresence>
        {isDeleteModalOpen && clientToDelete && tableauClients[clientToDelete] && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
            >
              <div className="p-6">
                <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full mb-4">
                  <Trash2 className="w-6 h-6 text-red-600" />
                </div>
                <h3 className="text-xl font-bold text-center text-slate-800 mb-2">
                  Remove configurations
                </h3>
                <p className="text-center text-slate-500 mb-6">
                  Client : <span className="font-semibold text-slate-700">{clientToDelete}</span>
                </p>

                <div className="mb-6 space-y-4 text-left bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Patch type to delete
                    </label>
                    <select
                      value={typeASupprimer}
                      onChange={(e) => {
                        setTypeASupprimer(e.target.value);
                        setQuantiteASupprimer(1);
                      }}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500/20 focus:border-red-500 transition-all appearance-none"
                    >
                      {Object.entries(tableauClients[clientToDelete]).map(([cleUnique, info]) => (
                        <option key={cleUnique} value={cleUnique}>
                          {info.type} - {info.composant} (Current quantity : {info.count})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Number of duplicates to remove
                    </label>
                    <select
                      value={quantiteASupprimer}
                      onChange={(e) => setQuantiteASupprimer(Number(e.target.value))}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-red-500/20 focus:border-red-500 transition-all appearance-none"
                    >
                      {typeASupprimer && tableauClients[clientToDelete][typeASupprimer] && 
                        Array.from(
                          { length: tableauClients[clientToDelete][typeASupprimer].count }, 
                          (_, i) => i + 1
                        ).map(num => (
                          <option key={num} value={num}>{num}</option>
                        ))
                      }
                    </select>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={annulerSuppressionClient}
                    className="flex-1 px-4 py-2.5 bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={confirmerSuppressionClient}
                    className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete ({quantiteASupprimer})
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Modale de succès après création du patch */}
      <AnimatePresence>
        {isSuccessModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="relative bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setIsSuccessModalOpen(false)}
                className="absolute top-4 right-4 p-2 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                aria-label="Close success modal"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="p-6 text-center">
                <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-4">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-2">
                  Success !
                </h3>
                <p className="text-slate-600 mb-6">
                  The patch was saved successfully.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setIsSuccessModalOpen(false);

                    navigate('/pre-patch', {
                      state: {
                        selectedPatchId: createdPatchIds[0],
                        selectedPatchIds: createdPatchIds,
                        workflowMode: 'SEQUENTIAL',
                        currentPatchIndex: 0,
                        autoRunVerification: true
                      }
                    });
                  }}
                  className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
                >
                  Go to Pre-Patch
                </button>
                <button
                  type="button"
                  onClick={() => setIsSuccessModalOpen(false)}
                  className="w-full mt-3 px-4 py-3 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-100 hover:text-slate-900 transition-all duration-200"
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      
      <AnimatePresence>
        {isAlertModalOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden"
            >
              <div className="p-6">
                <div className={`w-16 h-16 mx-auto rounded-full flex items-center justify-center mb-4 ${
                  alertConfig.type === 'error' ? 'bg-red-100' : 'bg-amber-100'
                }`}>
                  {alertConfig.type === 'error' ? (
                    <AlertCircle className="w-8 h-8 text-red-600" />
                  ) : (
                    <AlertTriangle className="w-8 h-8 text-amber-500" />
                  )}
                </div>
                
                <h3 className="text-xl font-bold text-center text-slate-800 mb-2">
                  {alertConfig.title}
                </h3>
                
                {/* whitespace-pre-wrap conserve les retours à la ligne natifs envoyés par le backend */}
                <p className="text-center text-slate-600 mb-6 whitespace-pre-wrap">
                  {alertConfig.message}
                </p>
                
                <button
                  type="button"
                  onClick={() => setIsAlertModalOpen(false)}
                  className={`w-full px-4 py-3 text-white font-medium rounded-lg transition-colors ${
                    alertConfig.type === 'error' 
                      ? 'bg-red-600 hover:bg-red-700' 
                      : 'bg-amber-500 hover:bg-amber-600'
                  }`}
                >
                  Close
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}