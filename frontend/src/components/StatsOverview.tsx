'use client'

import { motion } from 'framer-motion'
import { FileText, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'

interface StatsOverviewProps {
  contractsCount: number
  invoicesCount: number
  validatedCount: number
}

export function StatsOverview({ contractsCount, invoicesCount, validatedCount }: StatsOverviewProps) {
  const stats = [
    {
      label: 'Total Contracts',
      value: contractsCount,
      icon: FileText,
      color: 'primary',
      change: '+12%',
    },
    {
      label: 'Invoices Processed',
      value: invoicesCount,
      icon: TrendingUp,
      color: 'accent',
      change: '+8%',
    },
    {
      label: 'Validated',
      value: validatedCount,
      icon: CheckCircle,
      color: 'success',
      change: '+15%',
    },
    {
      label: 'Pending Review',
      value: invoicesCount - validatedCount,
      icon: AlertCircle,
      color: 'warning',
      change: '-5%',
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: [0.25, 0.46, 0.45, 0.94],
      },
    },
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"
    >
      {stats.map((stat, index) => {
        const Icon = stat.icon
        return (
          <motion.div
            key={stat.label}
            variants={itemVariants}
            whileHover={{ scale: 1.02, y: -2 }}
            className="card-elevated group cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-secondary-600 mb-1">
                  {stat.label}
                </p>
                <p className="text-3xl font-display font-bold text-secondary-900 mb-2">
                  {stat.value}
                </p>
                <div className="flex items-center space-x-1">
                  <span className={`text-xs font-medium ${
                    stat.change.startsWith('+') ? 'text-success-600' : 'text-error-600'
                  }`}>
                    {stat.change}
                  </span>
                  <span className="text-xs text-secondary-500">vs last month</span>
                </div>
              </div>
              <div className={`p-3 rounded-2xl bg-gradient-to-br ${
                stat.color === 'primary' ? 'from-primary-100 to-primary-200' :
                stat.color === 'accent' ? 'from-accent-100 to-accent-200' :
                stat.color === 'success' ? 'from-success-100 to-success-200' :
                'from-warning-100 to-warning-200'
              } group-hover:scale-110 transition-transform duration-200`}>
                <Icon className={`h-6 w-6 ${
                  stat.color === 'primary' ? 'text-primary-600' :
                  stat.color === 'accent' ? 'text-accent-600' :
                  stat.color === 'success' ? 'text-success-600' :
                  'text-warning-600'
                }`} />
              </div>
            </div>
          </motion.div>
        )
      })}
    </motion.div>
  )
}