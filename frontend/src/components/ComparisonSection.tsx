'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Check, X, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Contract, InvoiceData, ComparisonResult, PriceComparisonDetail, Item as ContractItemBase, InvoiceItem as InvoiceItemBase } from '@/services/api'

// Patch types to include 'total'
export type ContractItem = ContractItemBase & { total: number };
export type InvoiceItem = InvoiceItemBase & { total: number };

interface ComparisonSectionProps {
  allInvoices: InvoiceData[];
  contracts: Contract[];
  onContractsChange: (contracts: Contract[]) => void;
  onRefreshInvoices: () => Promise<void>;
}

export function ComparisonSection({ allInvoices = [], contracts, onContractsChange, onRefreshInvoices }: ComparisonSectionProps) {
  const [selectedContractId, setSelectedContractId] = useState<string>('')
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string>('')
  const [currentInvoiceData, setCurrentInvoiceData] = useState<InvoiceData | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [priceDetails, setPriceDetails] = useState<PriceComparisonDetail[]>([])

  console.log('ComparisonSection render. allInvoices:', allInvoices, 'selectedInvoiceId:', selectedInvoiceId, 'isLoading:', isLoading, 'contracts:', contracts, 'selectedContractId:', selectedContractId);

  // Effect to update currentInvoiceData when selectedInvoiceId or allInvoices changes
  useEffect(() => {
    console.log('[Effect currentInvoiceData] Triggered. selectedInvoiceId:', selectedInvoiceId, 'allInvoices count:', allInvoices.length);
    if (selectedInvoiceId) {
      const invoice = allInvoices.find(inv => inv.id === selectedInvoiceId);
      console.log('[Effect currentInvoiceData] Found invoice for currentInvoiceData:', invoice);
      setCurrentInvoiceData(invoice || null);
    } else {
      console.log('[Effect currentInvoiceData] Clearing currentInvoiceData because no selectedInvoiceId.');
      setCurrentInvoiceData(null);
    }
  }, [selectedInvoiceId, allInvoices]);

  // Reset comparison result when current invoice data changes
  useEffect(() => {
    console.log('[Effect resetComparison] Triggered. currentInvoiceData:', currentInvoiceData);
    setComparisonResult(null)
    setPriceDetails([])
  }, [currentInvoiceData])

  // Update selected contract when contracts change
  useEffect(() => {
    console.log('[Effect selectedContract] Triggered. contracts count:', contracts.length, 'selectedContractId:', selectedContractId);
    if (contracts.length > 0 && !selectedContractId) {
      console.log('[Effect selectedContract] Auto-selecting first contract:', contracts[0].id);
      setSelectedContractId(String(contracts[0].id))
    }
  }, [contracts, selectedContractId])

  // Auto-select first invoice if available and none is selected, or clear if invoices disappear
  useEffect(() => {
    console.log('[Effect autoSelectInvoice] Triggered. allInvoices count:', allInvoices.length, 'selectedInvoiceId:', selectedInvoiceId);
    if (allInvoices.length > 0 && !selectedInvoiceId) {
      console.log('[Effect autoSelectInvoice] Auto-selecting first invoice:', allInvoices[0].id);
      setSelectedInvoiceId(allInvoices[0].id);
    } else if (allInvoices.length === 0 && selectedInvoiceId) { 
      console.log('[Effect autoSelectInvoice] Invoices are empty, clearing selectedInvoiceId.');
      setSelectedInvoiceId('');
    }
  }, [allInvoices, selectedInvoiceId]);

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
    if (!selectedContractId || !currentInvoiceData) {
      toast.error('Please select a contract and an invoice')
      return
    }

    setIsLoading(true)
    try {
      // Fetch the full contract details
      const contract = await api.contracts.getById(selectedContractId);
      if (!contract) {
        toast.error('Could not fetch contract details.');
        setIsLoading(false);
        return;
      }

      // --- Start Frontend Comparison Logic ---
      const issues: ComparisonResult['issues'] = [];
      const priceComparisonDetails: PriceComparisonDetail[] = [];
      let overallMatch = true; // Assume match initially

      const matches: ComparisonResult['matches'] = {
        prices_match: true, // Will be updated based on item comparisons
        all_services_in_contract: true, // Will be updated
      };
      
      // 1. Compare Supplier Name
      // if (contract.supplier_name.toLowerCase() !== currentInvoiceData.supplier_name.toLowerCase()) {
      //   issues.push({
      //     type: 'supplier_mismatch',
      //     contract_value: contract.supplier_name,
      //     invoice_value: currentInvoiceData.supplier_name,
      //   });
      //   overallMatch = false;
      // }

      // 2. Compare Items/Services and Prices
      const contractItems = contract.items || []; // Assuming contract.items contains service details
      const invoiceItems = currentInvoiceData.items || [];

      let allInvoiceItemsFoundInContract = true;
      let allContractItemsFoundInInvoice = true;
      let pricesMatchOverall = true;

      // Normalize item descriptions for comparison
      const normalize = (str: string) => str.toLowerCase().trim();

      // Process contract items to populate priceComparisonDetails
      contractItems.forEach((cItem: ContractItem) => {
        const contractItemName = normalize(cItem.description);
        const matchingInvoiceItem = invoiceItems.find(
          (iItem: InvoiceItem) => normalize(iItem.description) === contractItemName
        );

              let invoicePrice = 0;
        let itemMatch = false;
        let note: string | undefined;

        if (matchingInvoiceItem) {
          invoicePrice = matchingInvoiceItem.unit_price || matchingInvoiceItem.total || 0;
          // Compare unit prices with a small tolerance for floating point issues
          itemMatch = Math.abs(cItem.unit_price - invoicePrice) < 0.01;
          if (!itemMatch) {
            pricesMatchOverall = false;
            note = `Price mismatch: Contract €${cItem.unit_price.toFixed(2)}, Invoice €${invoicePrice.toFixed(2)}`;
            issues.push({
              type: 'price_mismatch',
              service_name: cItem.description,
              contract_value: cItem.unit_price,
              invoice_value: invoicePrice,
            });
          }
        } else {
          allContractItemsFoundInInvoice = false;
          pricesMatchOverall = false; // Missing item means prices don't fully match
          note = "Service not found in invoice";
          issues.push({
            type: 'service_not_in_invoice', // Custom type
            service_name: cItem.description,
            contract_value: cItem.unit_price,
            invoice_value: 'N/A',
          });
        }
        
        priceComparisonDetails.push({
          service_name: cItem.description,
          contract_price: cItem.unit_price,
          invoice_price: invoicePrice,
          match: itemMatch,
          note: note,
        });
      });

      // Check for invoice items not in the contract
      invoiceItems.forEach((iItem: InvoiceItem) => {
        const invoiceItemName = normalize(iItem.description);
        const isInContract = contractItems.some(
          (cItem: ContractItem) => normalize(cItem.description) === invoiceItemName
        );
        if (!isInContract) {
          allInvoiceItemsFoundInContract = false;
          issues.push({
            type: 'service_not_in_contract',
            service_name: iItem.description,
            contract_value: 'N/A',
            invoice_value: iItem.unit_price || iItem.total || 0,
          });
           // Add to price comparison details as an extra item from invoice
           priceComparisonDetails.push({
            service_name: iItem.description,
            contract_price: null, // Not in contract
            invoice_price: iItem.unit_price || iItem.total || 0,
            match: false,
            note: "Service not found in contract",
              });
            }
          });
          
      matches.prices_match = pricesMatchOverall;
      matches.all_services_in_contract = allContractItemsFoundInInvoice; // If all contract services are in invoice.
                                                                     // Could also be interpreted as if all invoice services are in contract.
                                                                     // For now, let's stick to "all contract services are present and prices match"

      if (!pricesMatchOverall || !allContractItemsFoundInInvoice || !allInvoiceItemsFoundInContract || issues.length > 0) {
        overallMatch = false;
      }
      
      // 3. Compare Totals (optional, as item prices should dictate this)
      // We can add a check for currentInvoiceData.total vs sum of contract item totals if needed.
      // For now, focusing on item-level comparison.

      const result: ComparisonResult = {
        contract_id: selectedContractId,
        invoice_data: currentInvoiceData,
        matches: matches,
        issues: issues,
        overall_match: overallMatch,
        price_comparison_details: priceComparisonDetails,
      };
      // --- End Frontend Comparison Logic ---
      
      console.log("Frontend Comparison Result:", JSON.stringify(result, null, 2));
      setComparisonResult(result)
      
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
          value={selectedContractId}
          onChange={(e) => setSelectedContractId(e.target.value)}
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
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Select Invoice
        </label>
        <div className="flex items-center space-x-2">
          <select
            value={selectedInvoiceId}
            onChange={(e) => {
              console.log('Invoice dropdown onChange. New value:', e.target.value);
              setSelectedInvoiceId(e.target.value);
            }}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent disabled:bg-gray-100"
            disabled={allInvoices.length === 0 || isLoading}
          >
            <option value="">Choose an invoice...</option>
            {allInvoices.map((invoice) => (
              <option key={invoice.id} value={invoice.id}>
                ID: {invoice.id} - {invoice.supplier_name}
              </option>
            ))}
          </select>
        </div>
        {allInvoices.length === 0 && (
          <p className="mt-2 text-sm text-gray-500">
            No invoices available. Please process an invoice first.
          </p>
        )}
      </div>

      <div className="mb-6">
        <p className="text-sm text-gray-700 mb-3">
          {currentInvoiceData 
            ? `Invoice (ID: ${currentInvoiceData.id}) from ${currentInvoiceData.supplier_name} is ready for comparison` 
            : "Select an invoice to compare"}
        </p>
      </div>

      <button
        onClick={handleCompare}
        disabled={!selectedContractId || !currentInvoiceData || isLoading}
        className={`w-full bg-indigo-600 text-white py-2 px-4 rounded-md transition-colors ${
          (!selectedContractId || !currentInvoiceData || isLoading)
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
                          const hasMissingPrice = detail.invoice_price === 0 && detail.contract_price !== null && detail.note === "Service not found in invoice";
                          const isExtraInvoiceItem = detail.contract_price === null && detail.note === "Service not found in contract";
                          
                          // Use our own comparison with tolerance instead of backend's flag
                          // For missing prices, they should never match
                          let pricesMatch = false;
                          if (isExtraInvoiceItem) {
                            pricesMatch = false; // Cannot match if not in contract
                          } else if (hasMissingPrice) {
                            pricesMatch = false; // Cannot match if missing in invoice
                          } else {
                            pricesMatch = Math.abs(difference) < 0.01;
                          }
                          
                          const formattedDiff = Math.abs(difference).toLocaleString('en-US', {
                            style: 'currency',
                            currency: 'USD',
                            minimumFractionDigits: 2
                          });
                          
                          // Determine row styling - highlight price mismatches in red, missing prices in yellow
                          const rowStyle = pricesMatch 
                            ? "border-b border-gray-200" 
                            : (hasMissingPrice || isExtraInvoiceItem ? "bg-yellow-50 border-b border-gray-200" : "bg-red-50 border-b border-gray-200");
                          
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
                                  ? <span className="text-amber-500 italic">Not in invoice</span>
                                  : isExtraInvoiceItem 
                                    ? <span className="text-amber-500 italic">Not in contract (Invoice: {invoicePrice.toLocaleString('en-US', { style: 'currency', currency: 'USD' })})</span>
                                  : invoicePrice.toLocaleString('en-US', {
                                      style: 'currency',
                                      currency: 'USD',
                                      minimumFractionDigits: 2
                                    })}
                              </td>
                              <td className={`px-4 py-3 font-medium ${!pricesMatch ? (hasMissingPrice || isExtraInvoiceItem ? "text-amber-500" : (difference > 0 ? "text-red-600" : "text-blue-600")) : "text-gray-400"}`}>
                                {!pricesMatch ? (
                                  hasMissingPrice ? (
                                    <span className="text-amber-500">Not in invoice</span>
                                  ) : isExtraInvoiceItem ? (
                                    <span className="text-amber-500">Not in contract</span>
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
                {renderMatchIcon(comparisonResult.matches.all_services_in_contract)}
              </div>
            </div>

            {comparisonResult.issues && comparisonResult.issues.length > 0 && (
              <div className="mt-6">
                <h4 className="text-sm font-medium text-gray-900 mb-3">Issues</h4>
                <div className="space-y-2">
                  {comparisonResult.issues?.map((issue: ComparisonResult['issues'][0], index: number) => (
                    <div
                      key={index}
                      className="flex items-start space-x-3 text-sm text-gray-600 bg-white p-3 rounded-md"
                    >
                      <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
                      <div>
                        {issue.type === 'service_not_in_contract' && (
                          <p>
                            Service &quot;{issue.service_name}&quot; from invoice not found in contract. Invoice Price: ${typeof issue.invoice_value === 'number' ? issue.invoice_value.toFixed(2) : issue.invoice_value}
                          </p>
                        )}
                        {issue.type === 'price_mismatch' && (
                          <p>
                            Price mismatch for &quot;{issue.service_name}&quot;:
                            Contract: ${typeof issue.contract_value === 'number' ? issue.contract_value.toFixed(2) : issue.contract_value}, Invoice: $
                            {typeof issue.invoice_value === 'number' ? issue.invoice_value.toFixed(2) : issue.invoice_value}
                          </p>
                        )}
                        {issue.type === 'supplier_mismatch' && (
                          <p>
                            Supplier name mismatch: Contract: &quot;
                            {issue.contract_value}&quot;, Invoice: &quot;
                            {issue.invoice_value}&quot;
                          </p>
                        )}
                        {issue.type === 'service_not_in_invoice' && (
                          <p>
                            Service &quot;{issue.service_name}&quot; from contract not found in invoice. Contract Price: ${typeof issue.contract_value === 'number' ? issue.contract_value.toFixed(2) : issue.contract_value}
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