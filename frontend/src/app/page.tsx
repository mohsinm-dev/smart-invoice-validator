'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { ComparisonSection } from '@/components/ComparisonSection'
import { ContractSection } from '@/components/ContractSection'
import InvoiceSection from '@/components/InvoiceSection'
import { Header } from '@/components/Header'
import { StatsOverview } from '@/components/StatsOverview'
import { InvoiceData, Contract } from '@/services/api'
import { api } from '@/services/api'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
}

export default function Home() {
  const [currentInvoiceData, setCurrentInvoiceData] = useState<InvoiceData | null>(null)
  const [contracts, setContracts] = useState<Contract[]>([])
  const [allInvoices, setAllInvoices] = useState<InvoiceData[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const fetchContracts = useCallback(async () => {
    try {
      const data = await api.contracts.getAll()
      setContracts(data)
    } catch (error) {
      console.error('Error fetching contracts:', error)
    }
  }, [])

  const fetchInvoices = useCallback(async () => {
    try {
      const data = await api.invoices.getAll()
      setAllInvoices(data)
    } catch (error) {
      console.error('Error fetching all invoices:', error)
    }
  }, [])

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([fetchContracts(), fetchInvoices()])
      setIsLoading(false)
    }
    loadData()
  }, [fetchContracts, fetchInvoices])

  const handleInvoiceProcessed = async (invoiceData: InvoiceData) => {
    setCurrentInvoiceData(invoiceData)
    await fetchInvoices()
  }

  const handleContractCreated = async () => {
    await fetchContracts()
  }

  const handleRefreshInvoices = async () => {
    await fetchInvoices()
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="loading-spinner w-12 h-12 mx-auto"></div>
          <p className="text-secondary-600 font-medium">Loading your workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <motion.main 
      className="min-h-screen"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <Header />
      
      <div className="container-custom section-padding">
        <motion.div variants={itemVariants} className="text-center mb-16">
          <h1 className="heading-xl bg-gradient-to-r from-secondary-900 via-primary-700 to-secondary-900 bg-clip-text text-transparent mb-6">
            Smart Invoice Validator
          </h1>
          <p className="text-body text-xl max-w-3xl mx-auto">
            Streamline your invoice validation process with AI-powered document analysis. 
            Compare invoices against contracts automatically and ensure accuracy with intelligent verification.
          </p>
        </motion.div>

        <motion.div variants={itemVariants} className="mb-12">
          <StatsOverview 
            contractsCount={contracts.length}
            invoicesCount={allInvoices.length}
            validatedCount={allInvoices.filter(inv => inv.is_valid).length}
          />
        </motion.div>
        
        <motion.div 
          variants={itemVariants}
          className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-12"
        >
          <div className="space-y-8">
            <ContractSection onContractCreated={handleContractCreated} />
          </div>
          <div className="space-y-8">
            <InvoiceSection 
              onInvoiceProcessed={handleInvoiceProcessed} 
              onRefreshInvoices={handleRefreshInvoices}
            />
          </div>
        </motion.div>
        
        <motion.div variants={itemVariants}>
          <ComparisonSection 
            allInvoices={allInvoices}
            contracts={contracts}
            onContractsChange={setContracts}
            onRefreshInvoices={handleRefreshInvoices}
          />
        </motion.div>
      </div>
    </motion.main>
  )
}