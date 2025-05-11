'use client'

import React, { useState, useEffect } from 'react'
import { Check, X, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Contract, InvoiceData, ComparisonResult, PriceComparisonDetail } from '@/services/api'

interface ComparisonSectionProps {
  invoiceData: InvoiceData | null;
  contracts: Contract[];
  onContractsChange: (contracts: Contract[]) => void;
}

export function ComparisonSection({ invoiceData, contracts, onContractsChange }: ComparisonSectionProps) {
  const [selectedContract, setSelectedContract] = useState<string>('')
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [priceDetails, setPriceDetails] = useState<PriceComparisonDetail[]>([])

  // Reset comparison result when invoice data changes
  useEffect(() => {
    setComparisonResult(null)
    setPriceDetails([])
  }, [invoiceData])

  // Update selected contract when contracts change
  useEffect(() => {
    if (contracts.length > 0 && !selectedContract) {
      setSelectedContract(contracts[0].id)
    }
  }, [contracts, selectedContract])

  // Update price details when comparison result changes
  useEffect(() => {
    if (comparisonResult) {
      try {
        if (!comparisonResult.price_comparison_details) {
          console.warn("Missing price_comparison_details in comparison result");
          // Create a dummy entry to show something instead of nothing
          const dummyDetail: PriceComparisonDetail = {
            service_name: "No detailed price data available",
            contract_price: null,
            invoice_price: 0,
            match: false,
            note: "No items found in contract/invoice"
          };
          setPriceDetails([dummyDetail]);
        } else {
          setPriceDetails(comparisonResult.price_comparison_details);
          console.log("Price details updated:", comparisonResult.price_comparison_details.length, "items");
        }
      } catch (error) {
        console.error("Error processing price details:", error);
        // Set a fallback
        setPriceDetails([]);
      }
    }
  }, [comparisonResult]);

  const handleCompare = async () => {
    if (!selectedContract || !invoiceData) {
      toast.error('Please select a contract and upload an invoice')
      return
    }

    setIsLoading(true)
    try {
      const result = await api.invoices.compareInvoice(selectedContract, invoiceData)
      
      // Debug the full response
      console.log("Full comparison result:", JSON.stringify(result));
      
      // If no price_comparison_details or if we need to enhance the list with contract services
      if (!result.price_comparison_details || result.price_comparison_details.length < 3) {
        // Get the selected contract
        const contract = contracts.find(c => c.id === selectedContract);
        
        if (contract && contract.services && contract.services.length > 0) {
          console.log("Adding missing services from contract");
          
          // Create a comprehensive list including all contract services
          const enhancedDetails: PriceComparisonDetail[] = [];
          
          // First add any existing price comparison details
          if (result.price_comparison_details && result.price_comparison_details.length > 0) {
            enhancedDetails.push(...result.price_comparison_details);
          }
          
          // Then add any missing services from the contract
          contract.services.forEach(service => {
            // Check if this service is already in our enhanced list
            const existingIndex = enhancedDetails.findIndex(
              detail => detail.service_name.toLowerCase() === service.service_name.toLowerCase()
            );
            
            if (existingIndex === -1) {
              // Find if there's an invoice item that matches this service
              let invoicePrice = 0;
              let priceMatch = false;
              
              // Look in the issues for this service name
              if (result.issues && result.issues.length > 0) {
                const matchingIssue = result.issues.find(issue => 
                  issue.service_name && 
                  issue.service_name.toLowerCase() === service.service_name.toLowerCase()
                );
                
                if (matchingIssue && matchingIssue.invoice_value !== undefined) {
                  invoicePrice = Number(matchingIssue.invoice_value);
                  // Check if prices actually match within tolerance
                  priceMatch = Math.abs(service.unit_price - invoicePrice) < 0.01;
                }
              }
              
              // Look in the invoice data directly for matching services
              if (invoicePrice === 0 && result.invoice_data && result.invoice_data.items) {
                // Try to find a matching item in the invoice data
                const matchingItem = result.invoice_data.items.find(item => 
                  item.description && 
                  (item.description.toLowerCase() === service.service_name.toLowerCase() ||
                   item.description.toLowerCase().includes(service.service_name.toLowerCase()) ||
                   service.service_name.toLowerCase().includes(item.description.toLowerCase()))
                );
                
                if (matchingItem) {
                  // Use the unit_price if available, otherwise use total_price
                  invoicePrice = matchingItem.unit_price || matchingItem.total_price || 0;
                  priceMatch = Math.abs(service.unit_price - invoicePrice) < 0.01;
                  console.log(`Found direct match in invoice data: ${service.service_name} -> ${invoicePrice}`);
                }
              }
              
              // Add this service to our enhanced list
              enhancedDetails.push({
                service_name: service.service_name,
                contract_price: service.unit_price,
                invoice_price: invoicePrice,
                match: priceMatch,
                note: invoicePrice === 0 ? "Price not detected in invoice" : undefined
              });
            }
          });
          
          // Replace the price comparison details with our enhanced list
          if (enhancedDetails.length > 0) {
            result.price_comparison_details = enhancedDetails;
            console.log(`Enhanced price details to include ${enhancedDetails.length} items`);
          }
        }
      }
      
      setComparisonResult(result)
      
      // Check if we have price details
      if (result.price_comparison_details && result.price_comparison_details.length > 0) {
        console.log(`Received ${result.price_comparison_details.length} price details`);
      } else {
        console.warn("No price_comparison_details in API response");
      }
    } catch (error) {
      toast.error('Failed to compare documents')
      console.error('Error comparing documents:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Filter out false positives in issues and recalculate match status
  const filteredComparisonResult = React.useMemo(() => {
    if (!comparisonResult) return null;
    
    // Create a deep copy of the comparison result
    const result = {
      ...comparisonResult,
      issues: [...comparisonResult.issues],
      matches: { ...comparisonResult.matches }
    };
    
    // Filter out price mismatches where the prices actually match within tolerance
    const filteredIssues = result.issues.filter(issue => {
      if (issue.type === 'price_mismatch' && 
          issue.contract_value !== undefined && 
          issue.invoice_value !== undefined) {
        const contractValue = Number(issue.contract_value);
        const invoiceValue = Number(issue.invoice_value);
        
        // If they match within tolerance, don't show as an issue
        if (Math.abs(contractValue - invoiceValue) < 0.01) {
          return false;
        }
        
        // Keep "missing invoice price" issues
        if (invoiceValue === 0) {
          return true;
        }
        
        // Keep actual price mismatches
        return true;
      }
      // Keep all other types of issues
      return true;
    });
    
    // Add missing price issues if they don't exist already
    if (comparisonResult.price_comparison_details) {
      comparisonResult.price_comparison_details.forEach(detail => {
        const hasMissingPrice = detail.invoice_price === 0 && 
                              (detail.note === "Price not detected in invoice" || 
                               detail.note === "No items found in contract/invoice");
        
        if (hasMissingPrice) {
          // Check if this issue already exists
          const issueExists = filteredIssues.some(
            issue => issue.type === 'price_mismatch' && 
                    issue.service_name === detail.service_name && 
                    issue.invoice_value === 0
          );
          
          if (!issueExists && detail.contract_price !== null) {
            // Add a new issue for the missing price
            filteredIssues.push({
              type: 'price_mismatch',
              service_name: detail.service_name,
              contract_value: detail.contract_price,
              invoice_value: 0
            });
          }
        }
      });
    }
    
    result.issues = filteredIssues;
    
    // Recalculate matches status
    if (filteredIssues.length === 0) {
      result.matches.prices_match = true;
      
      // If no service_not_in_contract issues remain, set all_services_in_contract to true
      if (!filteredIssues.some(issue => issue.type === 'service_not_in_contract')) {
        result.matches.all_services_in_contract = true;
      }
    } else {
      // If we have price mismatch issues, prices don't match
      result.matches.prices_match = !filteredIssues.some(issue => issue.type === 'price_mismatch');
    }
    
    // Calculate overall match
    result.overall_match = Object.values(result.matches).every(Boolean);
    
    return result;
  }, [comparisonResult]);

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
                {filteredComparisonResult?.overall_match ? (
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
              {/* Price comparison table */}
              <div className="flex flex-col p-4 bg-white rounded-md">
                <span className="text-gray-900 font-medium mb-2">Price Comparison</span>
                {priceDetails.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm border border-gray-200 rounded-md">
                      <thead>
                        <tr className="bg-gray-100">
                          <th className="px-4 py-2 text-left font-semibold text-gray-700">Service</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700">Contract Price</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700">Invoice Price</th>
                          <th className="px-4 py-2 text-left font-semibold text-gray-700">Difference</th>
                          <th className="px-4 py-2 text-center font-semibold text-gray-700">Match</th>
                        </tr>
                      </thead>
                      <tbody>
                        {priceDetails.map((detail, idx) => {
                          const contractPrice = detail.contract_price !== null ? detail.contract_price : 0;
                          const invoicePrice = detail.invoice_price;
                          const difference = invoicePrice - contractPrice;
                          
                          // Handle missing price with a special message
                          const hasMissingPrice = invoicePrice === 0 && (detail.note === "Price not detected in invoice" || detail.note === "No items found in contract/invoice");
                          
                          // Use our own comparison with tolerance instead of backend's flag
                          // For missing prices, they should never match
                          const pricesMatch = hasMissingPrice ? false : Math.abs(difference) < 0.01;
                          
                          const formattedDiff = Math.abs(difference).toLocaleString('en-US', {
                            style: 'currency',
                            currency: 'USD',
                            minimumFractionDigits: 2
                          });
                          
                          // Determine row styling - highlight price mismatches in red, missing prices in yellow
                          const rowStyle = pricesMatch 
                            ? "border-b border-gray-200" 
                            : (hasMissingPrice ? "bg-yellow-50 border-b border-gray-200" : "bg-red-50 border-b border-gray-200");
                          
                          return (
                            <tr
                              key={idx}
                              className={rowStyle}
                            >
                              <td className="px-4 py-3 text-gray-900 font-medium">{detail.service_name}</td>
                              <td className="px-4 py-3 text-gray-900">
                                {detail.contract_price !== null 
                                  ? detail.contract_price.toLocaleString('en-US', {
                                      style: 'currency',
                                      currency: 'USD',
                                      minimumFractionDigits: 2
                                    }) 
                                  : <span className="text-gray-400 italic">N/A</span>}
                              </td>
                              <td className="px-4 py-3 text-gray-900">
                                {hasMissingPrice 
                                  ? <span className="text-amber-500 italic">Missing in invoice</span>
                                  : invoicePrice.toLocaleString('en-US', {
                                      style: 'currency',
                                      currency: 'USD',
                                      minimumFractionDigits: 2
                                    })}
                              </td>
                              <td className={`px-4 py-3 font-medium ${!pricesMatch ? (hasMissingPrice ? "text-amber-500" : (difference > 0 ? "text-red-600" : "text-blue-600")) : "text-gray-400"}`}>
                                {!pricesMatch ? (
                                  hasMissingPrice ? (
                                    <span className="text-amber-500">Price missing</span>
                                  ) : (
                                    <>
                                      {difference > 0 ? '+' : '-'} {formattedDiff}
                                      <span className="text-xs ml-1">
                                        ({Math.abs(difference) > 0 && contractPrice > 0 
                                          ? Math.round(Math.abs(difference) / contractPrice * 100) 
                                          : 100}%)
                                      </span>
                                    </>
                                  )
                                ) : (
                                  "—"
                                )}
                              </td>
                              <td className="px-4 py-3 text-center">
                                {renderMatchIcon(pricesMatch)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm">No price details to compare.</div>
                )}
              </div>

              <div className="flex items-center justify-between p-4 bg-white rounded-md">
                <span className="text-gray-900">All Services in Contract</span>
                {renderMatchIcon(filteredComparisonResult?.matches.all_services_in_contract ?? false)}
              </div>
            </div>

            {filteredComparisonResult && filteredComparisonResult.issues && filteredComparisonResult.issues.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium text-gray-900 mb-3">Issues</h4>
                <div className="space-y-2">
                  {filteredComparisonResult?.issues?.map((issue, index) => (
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