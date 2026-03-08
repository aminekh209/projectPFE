import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour gérer les erreurs
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Service pour les patches
export const patchService = {
  // Créer un patch
  createPatch: async (formData) => {
    const response = await api.post('/api/patches/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Lister les patches
  getPatches: async () => {
    const response = await api.get('/api/patches/');
    return response.data;
  },

  // Obtenir un patch
  getPatch: async (id) => {
    const response = await api.get(`/api/patches/${id}`);
    return response.data;
  },

  // Supprimer un patch
  deletePatch: async (id) => {
    const response = await api.delete(`/api/patches/${id}`);
    return response.data;
  },
};

// Service pour les clients
export const clientService = {
  getClients: async () => {
    const response = await api.get('/api/clients/');
    return response.data;
  },

  getEnvironnements: async (clientId) => {
    const response = await api.get(`/api/clients/${clientId}/environnements`);
    return response.data;
  },
};

// Service pour l'upload
export const uploadService = {
  uploadZip: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('fichier', file);

    const response = await api.post('/api/upload/zip', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return response.data;
  },

  analyzeZip: async (file) => {
    const formData = new FormData();
    formData.append('fichier', file);

    const response = await api.post('/api/upload/zip/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default api;