import { useState } from 'react';
import {
  Eye,
  EyeOff,
  Lock,
  User,
  Loader2,
  ArrowRight,
  AlertCircle,
  ShieldCheck,
  Package
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

import { api } from '../services/api';
import companyLogo from '../assets/hps-logo.png';

// --- Framer Motion Configuration ---
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 24 }
  }
};

export default function Authentication({ onLogin }) {
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!username.trim() || !password) {
      setError('Please enter your username and password.');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      const response = await api.post(
        '/auth/login',
        { username: username.trim(), password },
        { withCredentials: true }
      );

      if (typeof onLogin === 'function') {
        onLogin(response.data);
      }

      toast.success('Authentication successful.');
      navigate('/dash', { replace: true });
    } catch (err) {
      let message = 'Unable to connect to the server.';

      if (err.response?.status === 403) {
        message = 'Your account is disabled. Please contact the administrator.';
      } else if (err.response?.status === 400 || err.response?.status === 401) {
        message = 'Incorrect username or password.';
      } else if (typeof err.response?.data?.detail === 'string') {
        message = err.response.data.detail;
      }

      setError(message);
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    if (error) setError('');
  };

  return (
    <main className="relative flex min-h-[100dvh] items-center justify-center overflow-hidden bg-slate-50 px-4 py-8 font-sans">
      
      {/* --- Light & Animated Background --- */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        {/* Subtle Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#cbd5e1_1px,transparent_1px),linear-gradient(to_bottom,#cbd5e1_1px,transparent_1px)] bg-[size:32px_32px] opacity-20" />
        
        {/* Soft glowing shapes */}
        <motion.div 
          animate={{ 
            scale: [1, 1.1, 1],
            opacity: [0.4, 0.6, 0.4] 
          }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -left-32 -top-32 h-[500px] w-[500px] rounded-full bg-red-100 blur-[100px]" 
        />
        <motion.div 
          animate={{ 
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3] 
          }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }}
          className="absolute -bottom-40 -right-24 h-[600px] w-[600px] rounded-full bg-blue-100 blur-[120px]" 
        />
      </div>

      {/* --- Main Container --- */}
      <div className="relative z-10 w-full max-w-[500px]">
        
        {/* White Card with soft shadow */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="relative overflow-hidden rounded-[24px] border border-white bg-white/80 px-8 py-10 shadow-2xl shadow-slate-200/60 backdrop-blur-xl sm:px-10"
        >
          {/* Top brand gradient line */}
          <div className="absolute left-0 top-0 h-1.5 w-full bg-gradient-to-r from-red-700 via-red-500 to-red-700" />

          {/* Header (Logo & Titles) */}
          <motion.header 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="mb-10 flex flex-col items-center text-center"
          >
            {/* Clean Logo without box */}
            <motion.div variants={itemVariants} className="mb-6">
              <img
                src={companyLogo}
                alt="HPS Logo"
                className="h-12 w-auto object-contain drop-shadow-sm"
              />
            </motion.div>

            {/* Grouped Title and Subtitle */}
            <motion.div variants={itemVariants} className="space-y-2">
            <motion.div variants={itemVariants} className="space-y-2">
  <h1 className="text-2xl font-bold tracking-tight text-slate-900">
    Access your account
  </h1>

  <div className="flex items-center justify-center gap-2 text-slate-500">
    <Package className="h-4 w-4" />
    <span className="text-sm font-medium">
      Patch Management Platform
    </span>
  </div>
</motion.div>
</motion.div>
          </motion.header>

          {/* Error Messages */}
          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                key="login-error"
                initial={{ opacity: 0, y: -10, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -10, height: 0 }}
                className="mb-6 overflow-hidden"
              >
                <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />
                  <p>{error}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Form */}
          <motion.form 
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            onSubmit={handleSubmit} 
            className="space-y-5"
          >
            {/* Username */}
            <motion.div variants={itemVariants}>
              <label htmlFor="username" className="sr-only">Username</label>
              <div className="group relative">
                <User className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-red-500" />
                <input
                  id="username"
                  type="text"
                  required
                  autoFocus
                  autoComplete="username"
                  value={username}
                  disabled={isLoading}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    clearError();
                  }}
                  placeholder="Username"
                  className="h-14 w-full rounded-xl border border-slate-200 bg-white pl-12 pr-4 text-sm font-medium text-slate-900 outline-none transition-all placeholder:text-slate-400 hover:border-slate-300 focus:border-red-500 focus:ring-4 focus:ring-red-500/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-60"
                />
              </div>
            </motion.div>

            {/* Password */}
            <motion.div variants={itemVariants}>
              <label htmlFor="password" className="sr-only">Password</label>
              <div className="group relative">
                <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-red-500" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  disabled={isLoading}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    clearError();
                  }}
                  placeholder="Password"
                  className="h-14 w-full rounded-xl border border-slate-200 bg-white pl-12 pr-12 text-sm font-medium text-slate-900 outline-none transition-all placeholder:text-slate-400 hover:border-slate-300 focus:border-red-500 focus:ring-4 focus:ring-red-500/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-60"
                />
                <button
                  type="button"
                  disabled={isLoading}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:cursor-not-allowed"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </motion.div>

            {/* Submit Button */}
            <motion.div variants={itemVariants} className="pt-2">
              <motion.button
                type="submit"
                disabled={isLoading || !username.trim() || !password}
                whileHover={(!isLoading && username.trim() && password) ? { y: -2 } : {}}
                whileTap={(!isLoading && username.trim() && password) ? { scale: 0.98 } : {}}
                className="group relative flex h-14 w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-slate-900 px-5 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition-all hover:bg-red-600 hover:shadow-red-600/20 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </motion.button>
            </motion.div>
          </motion.form>

        </motion.div>

        {/* Footer */}
        <motion.footer 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="mt-8 text-center"
        >
          <p className="text-xs font-medium text-slate-500">
            © 2026 HPS Patch Management System
            <span className="mx-2 text-slate-300">•</span>
            Version 1.0.0
          </p>
        </motion.footer>
      </div>
    </main>
  );
}