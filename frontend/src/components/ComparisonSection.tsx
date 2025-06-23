'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, AlertTriangle, BarChart3, TrendingUp, TrendingDown, Minus } from 'lucide-react'
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
      return <Check className="h-5 w-5 text-success-500" />
    }
    return <X className="h-5 w-5 text-error-500" />
  }

  const getPriceChangeIcon = (difference: number) => {
    if (Math.abs(difference) < 0.01) return <Minus className="h-4 w-4 text-secondary-400" />
    if (difference > 0) return <TrendingUp className="h-4 w-4 text-error-500" />
    return <TrendingDown className="h-4 w-4 text-success-500" />
  }

  return (
    <motion.div 
      className="card-elevated"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.2 }}
    >
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-r from-success-100 to-success-200 rounded-xl">
            <BarChart3 className="h-6 w-6 text-success-600" />
          </div>
          <div>
            <h2 className="heading-md text-secondary-900">Document Comparison</h2>
            <p className="text-sm text-secondary-600">Compare invoices against contracts</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div>
          <label className="text-label">Select Contract</label>
          <select
            value={selectedContractId}
            onChange={(e) => setSelectedContractId(e.target.value)}
            className="input-field"
          >
            <option value="">Choose a contract...</option>
            {contracts.map((contract) => (
              <option key={contract.id} value={contract.id}>
                {contract.supplier_name} (ID: {contract.id})
              </option>
            ))}
          </select>
          {contracts.length === 0 && (
            <p className="mt-2 text-sm text-secondary-500">
              No contracts available. Please upload a contract first.
            </p>
          )}
        </div>

        <div>
          <label className="text-label">Select Invoice</label>
          <select
            value={selectedInvoiceId}
            onChange={(e) => {
              console.log('Invoice dropdown onChange. New value:', e.target.value);
              setSelectedInvoiceId(e.target.value);
            }}
            className="input-field"
            disabled={allInvoices.length === 0 || isLoading}
          >
            <option value="">Choose an invoice...</option>
            {allInvoices.map((invoice) => (
              <option key={invoice.id} value={invoice.id}>
                ID: {invoice.id} - {invoice.supplier_name}
              </option>
            ))}
          </select>
          {allInvoices.length === 0 && (
            <p className="mt-2 text-sm text-secondary-500">
              No invoices available. Please process an invoice first.
            </p>
          )}
        </div>
      </div>

      {currentInvoiceData && (
        <motion.div 
          className="glass rounded-2xl p-4 mb-6"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <p className="text-sm text-secondary-700">
            <span className="font-medium">Ready for comparison:</span> Invoice (ID: {currentInvoiceData.id}) from {currentInvoiceData.supplier_name}
          </p>
        </motion.div>
      )}

      <motion.button
        onClick={handleCompare}
        disabled={!selectedContractId || !currentInvoiceData || isLoading}
        className="btn btn-primary w-full mb-8"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {isLoading ? (
          <div className="flex items-center space-x-2">
            <div className="loading-spinner w-4 h-4"></div>
            <span>Comparing documents...</span>
          </div>
        ) : (
          'Compare Documents'
        )}
      </motion.button>

      <AnimatePresence>
        {comparisonResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="space-y-6"
          >
            {/* Overall Status */}
            <div className="glass rounded-2xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="heading-sm text-secondary-900">Comparison Results</h3>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                >
                  {comparisonResult.overall_match ? (
                    <div className="status-badge status-success">
                      <Check className="h-4 w-4 mr-1" />
                      Perfect Match
                    </div>
                  ) : (
                    <div className="status-badge status-error">
                      <X className="h-4 w-4 mr-1" />
                      Issues Found
                    </div>
                  )}
                </motion.div>
              </div>

              {/* Match Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <motion.div 
                  className={`p-4 rounded-xl border-2 ${
                    comparisonResult.matches.prices_match 
                      ? 'bg-success-50 border-success-200' 
                      : 'bg-error-50 border-error-200'
                  }`}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-secondary-900">Price Validation</p>
                      <p className="text-sm text-secondary-600">
                        {comparisonResult.matches.prices_match ? 'All prices match' : 'Price discrepancies found'}
                      </p>
                    </div>
                    {renderMatchIcon(comparisonResult.matches.prices_match)}
                  </div>
                </motion.div>

                <motion.div 
                  className={`p-4 rounded-xl border-2 ${
                    comparisonResult.matches.all_services_in_contract 
                      ? 'bg-success-50 border-success-200' 
                      : 'bg-error-50 border-error-200'
                  }`}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-secondary-900">Service Coverage</p>
                      <p className="text-sm text-secondary-600">
                        {comparisonResult.matches.all_services_in_contract ? 'All services covered' : 'Missing services detected'}
                      </p>
                    </div>
                    {renderMatchIcon(comparisonResult.matches.all_services_in_contract)}
                  </div>
                </motion.div>
              </div>

              {/* Price Comparison Table */}
              {priceDetails.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <h4 className="font-semibold text-secondary-900 mb-4">Detailed Price Analysis</h4>
                  <div className="overflow-x-auto">
                    <div className="min-w-full bg-white rounded-xl border border-secondary-200 overflow-hidden">
                      <div className="bg-secondary-50 px-6 py-3 border-b border-secondary-200">
                        <div className="grid grid-cols-12 gap-4 text-sm font-medium text-secondary-700">
                          <div className="col-span-4">Service</div>
                          <div className="col-span-2 text-right">Contract Price</div>
                          <div className="col-span-2 text-right">Invoice Price</div>
                          <div className="col-span-3 text-right">Difference</div>
                          <div className="col-span-1 text-center">Status</div>
                        </div>
                      </div>
                      <div className="divide-y divide-secondary-100">
                        {priceDetails.map((detail, idx) => {
                          const contractPrice = detail.contract_price !== null ? detail.contract_price : 0;
                          const invoicePrice = detail.invoice_price;
                          const difference = invoicePrice - contractPrice;
                          
                          const hasMissingPrice = detail.invoice_price === 0 && detail.contract_price !== null && detail.note === "Service not found in invoice";
                          const isExtraInvoiceItem = detail.contract_price === null && detail.note === "Service not found in contract";
                          
                          let pricesMatch = false;
                          if (isExtraInvoiceItem) {
                            pricesMatch = false;
                          } else if (hasMissingPrice) {
                            pricesMatch = false;
                          } else {
                            pricesMatch = Math.abs(difference) < 0.01;
                          }
                          
                          return (
                            <motion.div
                              key={idx}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: 0.6 + idx * 0.1 }}
                              className={`px-6 py-4 hover:bg-secondary-25 transition-colors ${
                                !pricesMatch ? 'bg-error-25' : ''
                              }`}
                            >
                              <div className="grid grid-cols-12 gap-4 items-center text-sm">
                                <div className="col-span-4">
                                  <p className="font-medium text-secondary-900 truncate" title={detail.service_name}>
                                    {detail.service_name}
                                  </p>
                                </div>
                                <div className="col-span-2 text-right">
                                  {detail.contract_price !== null ? (
                                    <span className="font-medium text-secondary-900">
                                      ${detail.contract_price.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="text-secondary-400 italic">N/A</span>
                                  )}
                                </div>
                                <div className="col-span-2 text-right">
                                  {hasMissingPrice ? (
                                    <span className="text-warning-600 italic text-xs">Not in invoice</span>
                                  ) : isExtraInvoiceItem ? (
                                    <span className="font-medium text-secondary-900">
                                      ${invoicePrice.toFixed(2)}
                                    </span>
                                  ) : (
                                    <span className="font-medium text-secondary-900">
                                      ${invoicePrice.toFixed(2)}
                                    </span>
                                  )}
                                </div>
                                <div className="col-span-3 text-right">
                                  <div className="flex items-center justify-end space-x-2">
                                    {getPriceChangeIcon(difference)}
                                    <div>
                                      {!pricesMatch ? (
                                        hasMissingPrice ? (
                                          <span className="text-warning-600 text-xs">Missing</span>
                                        ) : isExtraInvoiceItem ? (
                                          <span className="text-warning-600 text-xs">Extra</span>
                                        ) : (
                                          <div className="text-right">
                                            <div className={`font-medium ${difference > 0 ? 'text-error-600' : 'text-success-600'}`}>
                                              {difference > 0 ? '+' : ''}${Math.abs(difference).toFixed(2)}
                                            </div>
                                            {contractPrice > 0 && (
                                              <div className="text-xs text-secondary-500">
                                                ({Math.round(Math.abs(difference) / contractPrice * 100)}%)
                                              </div>
                                            )}
                                          </div>
                                        )
                                      ) : (
                                        <span className="text-secondary-400">—</span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="col-span-1 text-center">
                                  {renderMatchIcon(pricesMatch)}
                                </div>
                              </div>
                            </motion.div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* Issues Section */}
              {comparisonResult.issues && comparisonResult.issues.length > 0 && (
                <motion.div 
                  className="mt-6"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                >
                  <h4 className="font-semibold text-secondary-900 mb-4 flex items-center">
                    <AlertTriangle className="h-5 w-5 text-warning-500 mr-2" />
                    Issues Detected ({comparisonResult.issues.length})
                  </h4>
                  <div className="space-y-3">
                    {comparisonResult.issues?.map((issue: ComparisonResult['issues'][0], index: number) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.8 + index * 0.1 }}
                        className="flex items-start space-x-3 p-4 bg-warning-50 border border-warning-200 rounded-xl"
                      >
                        <AlertTriangle className="h-5 w-5 text-warning-500 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                          {issue.type === 'service_not_in_contract' && (
                            <div>
                              <p className="font-medium text-warning-900">Service not in contract</p>
                              <p className="text-sm text-warning-700">
                                "{issue.service_name}" from invoice (${typeof issue.invoice_value === 'number' ? issue.invoice_value.toFixed(2) : issue.invoice_value}) 
                                is not covered by the contract
                              </p>
                            </div>
                          )}
                          {issue.type === 'price_mismatch' && (
                            <div>
                              <p className="font-medium text-warning-900">Price mismatch detected</p>
                              <p className="text-sm text-warning-700">
                                "{issue.service_name}": Contract price ${typeof issue.contract_value === 'number' ? issue.contract_value.toFixed(2) : issue.contract_value} 
                                vs Invoice price ${typeof issue.invoice_value === 'number' ? issue.invoice_value.toFixed(2) : issue.invoice_value}
                              </p>
                            </div>
                          )}
                          {issue.type === 'supplier_mismatch' && (
                            <div>
                              <p className="font-medium text-warning-900">Supplier name mismatch</p>
                              <p className="text-sm text-warning-700">
                                Contract: "{issue.contract_value}" vs Invoice: "{issue.invoice_value}"
                              </p>
                            </div>
                          )}
                          {issue.type === 'service_not_in_invoice' && (
                            <div>
                              <p className="font-medium text-warning-900">Missing service in invoice</p>
                              <p className="text-sm text-warning-700">
                                "{issue.service_name}" from contract (${typeof issue.contract_value === 'number' ? issue.contract_value.toFixed(2) : issue.contract_value}) 
                                is not found in the invoice
                              </p>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}