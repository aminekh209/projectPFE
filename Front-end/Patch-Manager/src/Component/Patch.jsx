import { useState, useEffect } from 'react';
import { Upload, FileText, Database, Server, Globe, ChevronDown, X, AlertCircle, CheckCircle, HardDrive, Box, Layers, Cpu, PlusCircle, RefreshCw, AlertTriangle, Terminal, Settings, Code, Wrench, FolderOpen, FileArchive, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Configuration de l'API
const API_BASE_URL = 'http://localhost:8000'; // À adapter selon votre configuration

export default function CreationPatch() {
  // États pour les informations du patch
  const [nomPatch, setNomPatch] = useState('');
  const [descriptionPatch, setDescriptionPatch] = useState('');
  
  // États pour les listes déroulantes
  const [clients, setClients] = useState([]);
  const [clientSelectionne, setClientSelectionne] = useState('');
  const [environnementsClient, setEnvironnementsClient] = useState([]);
  const [environnementSelectionne, setEnvironnementSelectionne] = useState('');
  const [servers, setServers] = useState([]);
  const [typeEnvironnement, setTypeEnvironnement] = useState('');
  const [typeComposant, setTypeComposant] = useState('');
  
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
  
  // Compteur de patches
  const [nombrePatches, setNombrePatches] = useState(0);

  // États pour le chargement
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // État pour la modale de succès
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);

  // 🔥 NOUVEAUX ÉTATS POUR LA MODALE D'ALERTE UNIVERSELLE
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [alertConfig, setAlertConfig] = useState({ 
    message: '', 
    title: 'Error', 
    type: 'error' // 'error' ou 'warning'
  });

  // Types de patches disponibles depuis l'API
  const [typesPatches, setTypesPatches] = useState([]);

  // Fonction utilitaire pour appeler la modale facilement
  const showAlert = (message, title = 'Error', type = 'error') => {
    setAlertConfig({ message, title, type });
    setIsAlertModalOpen(true);
  };

  // 1. Chargement des types de patches depuis l'API
  useEffect(() => {
    const fetchTypesPatches = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/patches/statistiques`);
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
    const fetchServers = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/patches/servers`);
        if (response.ok) {
          const data = await response.json();
          setServers(data);
        }
      } catch (err) {
        console.error('Error loading servers:', err);
      }
    };
    fetchServers();
  }, []);

  // LOGIQUE DE DÉTECTION : On cherche le serveur qui correspond aux sélections actuelles
  const serveurCible = servers.find(s => 
    s.client_id === parseInt(clientSelectionne) && 
    s.environment_id === parseInt(environnementSelectionne) && 
    s.server_type === typeEnvironnement
  );

  // 2. Chargement des clients depuis la base de données
  useEffect(() => {
    const fetchClients = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/patches/clients`);
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
          const response = await fetch(`${API_BASE_URL}/patches/environments/${clientSelectionne}`);
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
    setTypeEnvironnement('');
    setTypeComposant('');
  };

  const getStructureDetail = (type, composant) => {
    if (type === 'UNIX') {
      return 'usr → ctl, bin, lib';
    } else if (type === 'WEB') {
      return composant === 'BO' ? 'powercard' : 'FE';
    }
    return composant === 'BO' ? 'Back-office' : 'Front-end';
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    e.target.value = ''; 
    
    if (file.name.endsWith('.zip')) {
      setIsUploading(true);
      setFichierZip(file);
      setProgressUpload(0);
      setError(null);
      
      const formData = new FormData();
      formData.append('file', file);
      
      let interval; 
      
      try {
        interval = setInterval(() => {
          setProgressUpload(prev => {
            if (prev >= 90) return 90; 
            return prev + 10;
          });
        }, 200);
        
        const response = await fetch(`${API_BASE_URL}/patches/analyser`, {
          method: 'POST',
          body: formData,
        });
        
        if (!response.ok) {
          throw new Error("Critical server error while analyzing the file.");
        }
        
        const analyse = await response.json();
        
        clearInterval(interval);
        setProgressUpload(100);
        
        setTimeout(() => {
          setAnalyseZip(analyse);
          setIsUploading(false);
          setProgressUpload(0);
        }, 500);
        
      } catch (error) {
        console.error('Erreur upload:', error);
        clearInterval(interval); 
        setError(error.message);
        setIsUploading(false);
        setFichierZip(null);
        setProgressUpload(0);
      }
    } else {
      // ✅ REMPLACEMENT ALERTE
      showAlert('Please select a valid ZIP file (.zip only).', 'Invalid Format', 'warning');
    }
  };

  const ajouterConfiguration = () => {
    if (!clientSelectionne || !environnementSelectionne || !typeEnvironnement || !typeComposant || !fichierZip) {
      // ✅ REMPLACEMENT ALERTE
      showAlert('Please complete all selections and upload a ZIP file before adding.', 'Missing Information', 'warning');
      return;
    }

    if (nombrePatches >= 10) {
      // ✅ REMPLACEMENT ALERTE
      showAlert('You have reached the maximum limit of 10 patches per configuration.', 'Limit Reached', 'warning');
      return;
    }

    const client = clients.find(c => c.id === parseInt(clientSelectionne));
    const environnement = environnementsClient.find(e => e.id === parseInt(environnementSelectionne));
    
    const nouvelleConfig = {
      id: Date.now(),
      client: client?.nom,
      clientId: clientSelectionne,
      environnement: environnement?.nom,
      environnementId: environnementSelectionne,
      type: typeEnvironnement,
      composant: typeComposant,
      structure: getStructureDetail(typeEnvironnement, typeComposant),
      zipName: fichierZip?.name
    };
    
    setConfigurationsTemporaires(prev => [...prev, nouvelleConfig]);
    setNombrePatches(prev => prev + 1);
    setClientSelectionne('');      
    setEnvironnementsClient([]);   
    resetSelections();
  };

  const validerConfigurations = () => {
    if (configurationsTemporaires.length === 0) return;

    const nouveauTableau = { ...tableauClients };
    
    configurationsTemporaires.forEach(config => {
      if (!nouveauTableau[config.client]) {
        nouveauTableau[config.client] = {};
      }
      
      const cleUnique = `${config.type}_${config.composant}`;
      
      const countActuel = nouveauTableau[config.client][cleUnique]?.count || 0;

      nouveauTableau[config.client] = {
        ...nouveauTableau[config.client],
        [cleUnique]: {
          type: config.type, 
          composant: config.composant,
          zipName: config.zipName,
          clientId: config.clientId,
          environnementId: config.environnementId,
          serverId: config.serverId,
          count: countActuel + 1
        }
      };
    });

    setTableauClients(nouveauTableau);
    setConfigurationsTemporaires([]);
  };

  const supprimerConfigurationTemporaire = (id) => {
    setConfigurationsTemporaires(prev => prev.filter(c => c.id !== id));
    setNombrePatches(prev => prev - 1);
  };

  const viderConfigurations = () => {
    setConfigurationsTemporaires([]);
    setNombrePatches(0);
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
          user_id: 1 
        });
      });
    });

    const formData = new FormData();
    formData.append('file', fichierZip);
    formData.append('patch_data', JSON.stringify(patchesToCreate));
    
    if (analyseZip) {
      formData.append('analysis_data', JSON.stringify(analyseZip));
    }

    try {
      const response = await fetch(`${API_BASE_URL}/patches/create`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error creating the patch');
      }

      setIsSuccessModalOpen(true);
      
      // Réinitialiser le formulaire
      setNomPatch('');
      setDescriptionPatch('');
      setTableauClients({});
      setConfigurationsTemporaires([]);
      setNombrePatches(0);
      setFichierZip(null);
      setAnalyseZip(null);

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
                    {isUploading ? 'Uploading...' : 'Click to upload or drag and drop'}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    Accepted format: ZIP only
                  </p>
                </div>
              </label>
            </div>

            {isUploading && (
              <div className="mt-4">
                <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${progressUpload}%` }}
                    className="h-full bg-blue-600"
                  />
                </div>
                <p className="text-sm text-slate-600 mt-2 text-center">Analyzing ZIP file... {progressUpload}%</p>
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
                    
                    <div className="grid grid-cols-4 gap-3 mt-4">
                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Total</p>
                        <p className="font-bold text-slate-800">{analyseZip.structure.statistiques.total}</p>
                      </div>
                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Database</p>
                        <p className="font-bold text-blue-600">{analyseZip.structure.statistiques.database || 0}</p>
                      </div>
                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">UNIX</p>
                        <p className="font-bold text-green-600">{analyseZip.structure.statistiques.unix || 0}</p>
                      </div>
                      <div className="bg-slate-50 p-2 rounded-lg text-center">
                        <p className="text-xs text-slate-500">Web</p>
                        <p className="font-bold text-purple-600">{analyseZip.structure.statistiques.web || 0}</p>
                      </div>
                    </div>
                    
                    {analyseZip.actions.statistiques_categories && (
                      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
                        {Object.entries(analyseZip.actions.statistiques_categories).map(([categorie, count]) => (
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
                        
                        {analyseZip.actions.actions_globales && analyseZip.actions.actions_globales.length > 0 ? (
                          <div className="space-y-3">
                            {analyseZip.actions.actions_globales.map((action, idx) => (
                              <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.05 }}
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
                            ))}
                          </div>
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
            
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Client
                </label>
                <select
                  value={clientSelectionne}
                  onChange={(e) => setClientSelectionne(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={nombrePatches >= 10 || !fichierZip}
                >
                  <option value="">Select a client</option>
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
                    <option key={env.id} value={env.id}>{env.nom}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Type
                </label>
                <select
                  value={typeEnvironnement}
                  onChange={(e) => {
                    setTypeEnvironnement(e.target.value);
                    setTypeComposant('');
                  }}
                  disabled={!environnementSelectionne || nombrePatches >= 10 || !fichierZip}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select a type</option>
                  {typesPatches.map(type => (
                    <option key={type.code} value={type.code}>{type.nom} ({type.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Component
                </label>
                <select
                  value={typeComposant}
                  onChange={(e) => setTypeComposant(e.target.value)}
                  disabled={!typeEnvironnement || nombrePatches >= 10 || !fichierZip}
                  className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all appearance-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">Select a component</option>
                  {typeEnvironnement && (
                    <>
                      <option value="BO">Back-office (BO)</option>
                      <option value="FE">Front-end (FE)</option>
                    </>
                  )}
                </select>
              </div>
            </div>
            
            {/* === DÉBUT : NOUVELLE ZONE AFFICHAGE SERVEUR === */}
            <div className={`mb-6 p-4 rounded-xl border-2 transition-all duration-300 flex items-center justify-between ${serveurCible ? 'bg-indigo-50/50 border-indigo-200' : 'bg-slate-50 border-slate-100'}`}>
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center shadow-sm ${serveurCible ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-400'}`}>
                  <Server className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest mb-1">Assigned execution server</p>
                  
                  {clientSelectionne && environnementSelectionne && typeEnvironnement ? (
                    serveurCible ? (
                      <p className="text-sm font-bold text-indigo-950">
                        {serveurCible.hostname} <span className="text-indigo-500 font-medium ml-1">({serveurCible.ip_address})</span>
                      </p>
                    ) : (
                      <p className="text-sm font-bold text-red-500">⚠️ No server configured for these criteria</p>
                    )
                  ) : (
                    <p className="text-sm font-medium text-slate-400 italic">Waiting for your selections...</p>
                  )}
                </div>
              </div>
              {serveurCible && <CheckCircle className="w-7 h-7 text-indigo-500" />}
            </div>
            {/* === FIN : NOUVELLE ZONE AFFICHAGE SERVEUR === */}
            
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
                disabled={!typeComposant || nombrePatches >= 10 || !fichierZip || loading || isUploading}
                className="flex items-center gap-2 px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <PlusCircle className="w-4 h-4" />
                Add this configuration ({nombrePatches}/10)
              </button>
              
              {configurationsTemporaires.length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={validerConfigurations}
                    className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Validate in summary
                  </button>
                  <button
                    type="button"
                    onClick={viderConfigurations}
                    className="flex items-center gap-2 px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Clear configurations
                  </button>
                </>
              )}
            </div>

            <AnimatePresence>
              {configurationsTemporaires.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6 border-t border-slate-200 pt-6"
                >
                  <h3 className="text-sm font-medium text-slate-700 mb-3">
                    Configurations pending validation ({configurationsTemporaires.length}) :
                  </h3>
                  <div className="space-y-2">
                    {configurationsTemporaires.map(config => (
                      <motion.div
                        key={config.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        className="flex items-center justify-between p-3 bg-amber-50 border border-amber-200 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          {getTypeIcon(config.type)}
                          <div>
                            <p className="font-medium text-slate-800">
                              {config.client} - {config.environnement}
                            </p>
                            <p className="text-sm text-slate-600">
                              {config.type} / {config.composant} • {config.structure}
                            </p>
                            <p className="text-xs text-slate-500 mt-1">
                              ZIP: {config.zipName}
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => supprimerConfigurationTemporaire(config.id)}
                          className="p-1 hover:bg-amber-200 rounded-full transition-colors"
                        >
                          <X className="w-4 h-4 text-slate-500" />
                        </button>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
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
                            {Object.values(types)[0].zipName}
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
              className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden"
            >
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
                  onClick={() => setIsSuccessModalOpen(false)}
                  className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors"
                >
                  Continue
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 🔥 MODALE D'ALERTE UNIVERSELLE (Erreurs & Avertissements) */}
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