'use client'

import { useState, useEffect } from 'react'
import { ComparisonSection } from '@/components/ComparisonSection'
import { ContractSection } from '@/components/ContractSection'
import InvoiceSection from '@/components/InvoiceSection'
import { InvoiceData, Contract } from '@/services/api'
import { api } from '@/services/api'

export default function Home() {
  const [currentInvoiceData, setCurrentInvoiceData] = useState<InvoiceData | null>(null)
  const [contracts, setContracts] = useState<Contract[]>([])

  useEffect(() => {
    fetchContracts()
  }, [])

  const fetchContracts = async () => {
    try {
      const data = await api.contracts.getAll()
      setContracts(data)
    } catch (error) {
      console.error('Error fetching contracts:', error)
    }
  }

  const handleInvoiceProcessed = (invoiceData: InvoiceData) => {
    setCurrentInvoiceData(invoiceData)
  }

  const handleContractCreated = () => {
    fetchContracts() // Refresh contracts list when a new contract is created
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <h1 className="text-4xl font-bold text-gray-900 text-center mb-12">
          Smart Invoice Validator
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <ContractSection onContractCreated={handleContractCreated} />
          <InvoiceSection onInvoiceProcessed={handleInvoiceProcessed} />
        </div>
        
        <ComparisonSection 
          invoiceData={currentInvoiceData} 
          contracts={contracts}
          onContractsChange={setContracts}
        />
      </div>
    </main>
  )
}
