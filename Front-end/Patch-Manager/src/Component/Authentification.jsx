import { useState } from 'react';
import { Eye, EyeOff, Lock, Mail, ShieldCheck, AlertCircle, Loader2, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Authentification({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
  };

  const containerVariants = {
    hidden: { opacity: 0, x: -30 },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: { 
        duration: 0.6,
        ease: "easeOut",
        when: "beforeChildren",
        staggerChildren: 0.15
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.4, ease: "easeOut" }
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col md:flex-row bg-[#F8FAFC]">
      <motion.div 
        className="hidden md:flex md:w-1/2 lg:w-3/5 bg-[#0F172A] p-12 flex-col justify-between relative overflow-hidden"
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#475569 1px, transparent 1px)', backgroundSize: '30px 30px' }}></div>
        
        <div className="relative z-10">
          <motion.div variants={itemVariants} className="flex items-center gap-3 mb-12">
            <div className="bg-blue-600 p-2 rounded-lg">
              <ShieldCheck className="text-white w-8 h-8" />
            </div>
            <span className="text-white text-2xl font-bold tracking-tight">Patch <span className="text-blue-500">Manager</span></span>
          </motion.div>
          
          <div className="max-w-md">
            <motion.h2 variants={itemVariants} className="text-4xl font-bold text-white leading-tight mb-6">
              Automatisation sécurisée des patchs applicatifs 
            </motion.h2>
            <motion.p variants={itemVariants} className="text-slate-400 text-lg">
              Supervisez, appliquez et contrôlez vos correctifs sur vos serveurs DB, UNIX et Web depuis une interface centralisée, avec vérification prépatch, contrôle post-patch, rollback intelligent et notifications automatiques.
            </motion.p>
          </div>
        </div>

        <motion.div 
          variants={itemVariants}
          className="relative z-10 border-t border-slate-800 pt-8"
        >
          <div className="flex gap-8">
            <motion.div variants={itemVariants}>
              <p className="text-white font-bold text-xl">Multi-environnements</p>
              <p className="text-slate-500 text-sm">DB, UNIX et Web</p>
            </motion.div>
            <motion.div variants={itemVariants}>
              <p className="text-white font-bold text-xl">Rollback Intelligent</p>
              <p className="text-slate-500 text-sm">Revenir à l’état précédent en cas d’erreur</p>
            </motion.div>
            <motion.div variants={itemVariants}>
              <p className="text-white font-bold text-xl">Vérification Pré/Post</p>
              <p className="text-slate-500 text-sm">Contrôle automatique avant et après patch</p>
            </motion.div>
            <motion.div variants={itemVariants}>
              <p className="text-white font-bold text-xl">Dashboard Centralisé</p>
              <p className="text-slate-500 text-sm">Supervision et notifications automatiques</p>
            </motion.div>
          </div>
        </motion.div>
      </motion.div>


      <div className="flex-1 flex items-center justify-center p-6 bg-white">
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-sm"
        >
        
          <div className="md:hidden flex items-center gap-2 mb-8 justify-center">
            <ShieldCheck className="text-blue-600 w-8 h-8" />
            <span className="text-slate-900 text-xl font-bold">PatchManager</span>
          </div>

          <div className="mb-10 text-center md:text-left">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Connexion</h1>
            <p className="text-slate-500">Accédez à votre compte d'administration</p>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="mb-6 p-4 bg-red-50 border border-red-100 rounded-lg flex items-start gap-3 text-red-700 text-sm"
              >
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <p>{error}</p>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Identifiant professionnel
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type="email" 
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2.5 pl-10 pr-4 text-slate-900 text-sm outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                  placeholder="nom@entreprise.com"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-sm font-semibold text-slate-700">Mot de passe</label>
                <button type="button" className="text-xs font-medium text-blue-600 hover:text-blue-700">
                  Mot de passe oublié ?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2.5 pl-10 pr-10 text-slate-900 text-sm outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all"
                  placeholder="••••••••"
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button 
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#0F172A] hover:bg-[#1e293b] text-white font-semibold py-3 rounded-lg shadow-sm transition-all flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>Se connecter <ChevronRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <div className="mt-10 pt-8 border-t border-slate-100">
            <p className="text-center text-xs text-slate-400">© 2026 Patch Management System v 1.0.0</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}