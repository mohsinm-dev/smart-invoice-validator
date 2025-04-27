'use client'

import { useState } from 'react'
import { ComparisonSection } from '@/components/ComparisonSection'
import { ContractSection } from '@/components/ContractSection'
import InvoiceSection from '@/components/InvoiceSection'
import { InvoiceData } from '@/services/api'

export default function Home() {
  const [currentInvoiceData, setCurrentInvoiceData] = useState<InvoiceData | null>(null)

  const handleInvoiceProcessed = (invoiceData: InvoiceData) => {
    setCurrentInvoiceData(invoiceData)
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <h1 className="text-4xl font-bold text-gray-900 text-center mb-12">
          Smart Invoice Validator
        </h1>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <ContractSection />
          <InvoiceSection onInvoiceProcessed={handleInvoiceProcessed} />
        </div>
        
        <ComparisonSection invoiceData={currentInvoiceData} />
      </div>
    </main>
  )
}
