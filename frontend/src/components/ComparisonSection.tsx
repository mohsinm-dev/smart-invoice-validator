'use client'

import React, { useState, useEffect } from 'react'
import { Check, X, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Contract, InvoiceData, ComparisonResult } from '@/services/api'

interface ComparisonSectionProps {
  invoiceData: InvoiceData | null;
  contracts: Contract[];
  onContractsChange: (contracts: Contract[]) => void;
}

export function ComparisonSection({ invoiceData, contracts, onContractsChange }: ComparisonSectionProps) {
  const [selectedContract, setSelectedContract] = useState<string>('')
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Reset comparison result when invoice data changes
  useEffect(() => {
    setComparisonResult(null)
  }, [invoiceData])

  // Update selected contract when contracts change
  useEffect(() => {
    if (contracts.length > 0 && !selectedContract) {
      setSelectedContract(contracts[0].id)
    }
  }, [contracts, selectedContract])

  const handleCompare = async () => {
    if (!selectedContract || !invoiceData) {
      toast.error('Please select a contract and upload an invoice')
      return
    }

    setIsLoading(true)
    try {
      const result = await api.invoices.compareInvoice(selectedContract, invoiceData)
      setComparisonResult(result)
    } catch (error) {
      toast.error('Failed to compare documents')
      console.error('Error comparing documents:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const renderMatchIcon = (isMatch: boolean) => {
    if (isMatch) {
      return <Check className="h-5 w-5 text-green-500" />
    }
    return <X className="h-5 w-5 text-red-500" />
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">
        Document Comparison
      </h2>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Contract
        </label>
        <select
          value={selectedContract}
          onChange={(e) => setSelectedContract(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
        >
          <option value="">Choose a contract...</option>
          {contracts.map((contract) => (
            <option key={contract.id} value={contract.id}>
              {contract.supplier_name} (ID: {contract.id})
            </option>
          ))}
        </select>
        {contracts.length === 0 && (
          <p className="mt-2 text-sm text-gray-500">
            No contracts available. Please upload a contract first.
          </p>
        )}
      </div>

      <div className="mb-6">
        <p className="text-sm text-gray-700 mb-3">
          {invoiceData 
            ? `Invoice #${invoiceData.invoice_number} from ${invoiceData.supplier_name} is ready for comparison` 
            : "Upload an invoice from the Invoices section to compare"}
        </p>
      </div>

      <button
        onClick={handleCompare}
        disabled={!selectedContract || !invoiceData || isLoading}
        className={`w-full bg-indigo-600 text-white py-2 px-4 rounded-md transition-colors ${
          (!selectedContract || !invoiceData || isLoading)
            ? 'opacity-50 cursor-not-allowed'
            : 'hover:bg-indigo-700'
        }`}
      >
        {isLoading ? 'Comparing...' : 'Compare Documents'}
      </button>

      {comparisonResult && (
        <div className="mt-8">
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Comparison Results
              </h3>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">Overall Match:</span>
                {comparisonResult.overall_match ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Match
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    Mismatch
                  </span>
                )}
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-white rounded-md">
                <span className="text-gray-900">Supplier Name Match</span>
                {renderMatchIcon(comparisonResult.matches.supplier_name)}
              </div>

              <div className="flex items-center justify-between p-4 bg-white rounded-md">
                <span className="text-gray-900">Prices Match</span>
                {renderMatchIcon(comparisonResult.matches.prices_match)}
              </div>

              <div className="flex items-center justify-between p-4 bg-white rounded-md">
                <span className="text-gray-900">All Services in Contract</span>
                {renderMatchIcon(comparisonResult.matches.all_services_in_contract)}
              </div>
            </div>

            {comparisonResult.issues.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium text-gray-900 mb-3">Issues</h4>
                <div className="space-y-2">
                  {comparisonResult.issues.map((issue, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-3 text-sm text-gray-600 bg-white p-3 rounded-md"
                    >
                      <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
                      <div>
                        {issue.type === 'service_not_in_contract' && (
                          <p>
                            Service &quot;{issue.service_name}&quot; not found in contract
                          </p>
                        )}
                        {issue.type === 'price_mismatch' && (
                          <p>
                            Price mismatch for &quot;{issue.service_name}&quot;:
                            Contract: ${issue.contract_value}, Invoice: $
                            {issue.invoice_value}
                          </p>
                        )}
                        {issue.type === 'supplier_mismatch' && (
                          <p>
                            Supplier name mismatch: Contract: &quot;
                            {issue.contract_value}&quot;, Invoice: &quot;
                            {issue.invoice_value}&quot;
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
} 