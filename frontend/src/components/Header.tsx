'use client'

import { motion } from 'framer-motion'
import { FileText, Sparkles } from 'lucide-react'

export function Header() {
  return (
    <motion.header 
      className="glass border-b border-white/20 sticky top-0 z-50"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div className="container-custom">
        <div className="flex items-center justify-between py-4">
          <motion.div 
            className="flex items-center space-x-3"
            whileHover={{ scale: 1.02 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
          >
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl blur opacity-20"></div>
              <div className="relative bg-gradient-to-r from-primary-600 to-primary-700 p-2 rounded-xl">
                <FileText className="h-6 w-6 text-white" />
              </div>
            </div>
            <div>
              <h1 className="text-xl font-display font-bold text-secondary-900">
                Smart Invoice Validator
              </h1>
              <p className="text-xs text-secondary-500 font-medium">
                AI-Powered Document Analysis
              </p>
            </div>
          </motion.div>
          
          <div className="flex items-center space-x-4">
            <motion.div 
              className="hidden sm:flex items-center space-x-2 px-3 py-1.5 bg-gradient-to-r from-accent-100 to-primary-100 rounded-full"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <Sparkles className="h-4 w-4 text-accent-600" />
              <span className="text-sm font-medium text-accent-700">
                Powered by AI
              </span>
            </motion.div>
            
            <motion.a
              href="https://github.com/yourusername/smart-invoice-validator"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-ghost text-sm"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              GitHub
            </motion.a>
          </div>
        </div>
      </div>
    </motion.header>
  )
}