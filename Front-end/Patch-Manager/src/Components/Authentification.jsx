import React, { useState } from 'react';
import { ShieldCheck, Mail, Lock, Loader2, AlertCircle } from 'lucide-react';

const Authentification = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({ email: '', password: '' });

 const handleLogin = (e) => {
  e.preventDefault();
  setError('');
  setIsLoading(true);
  
  // Simulation de l'appel API
  setTimeout(() => {
    if (formData.email === "amine@emsi.ma" && formData.password === "admin123") {
      setIsLoading(false);
      alert("Accès autorisé !");
    } else {
      setIsLoading(false);
      setError("Identifiants invalides.");
    }
  }, 1500);
};

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#020617] text-white font-sans">
      <div className="bg-white/5 backdrop-blur-2xl border border-white/10 p-8 rounded-3xl shadow-2xl w-full max-w-md">
        <div className="text-center mb-10">
          <ShieldCheck className="w-12 h-12 text-blue-500 mx-auto mb-4" />
          <h1 className="text-3xl font-black italic">PATCH-MANAGER</h1>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input 
              type="email" 
              required
              className="w-full bg-white/5 border border-white/10 pl-12 pr-4 py-3.5 rounded-xl outline-none focus:border-blue-500 transition-all"
              placeholder="votre.email@emsi.ma"
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input 
              type="password" 
              required
              className="w-full bg-white/5 border border-white/10 pl-12 pr-4 py-3.5 rounded-xl outline-none focus:border-blue-500 transition-all"
              placeholder="••••••••••••"
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
          </div>

          <button 
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 font-bold py-4 rounded-xl transition-all"
          >
            {isLoading ? "Chargement..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Authentification;