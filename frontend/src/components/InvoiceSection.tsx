'use client'

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone, DropzoneOptions } from 'react-dropzone'
import { Upload, Trash2, Receipt, Calendar, DollarSign, FileText, CheckCircle, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, InvoiceData } from '@/services/api'

// Add InvoiceItem type override to include 'total'
export interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
}

interface InvoiceSectionProps {
  onInvoiceProcessed?: (invoiceData: InvoiceData) => void;
  onRefreshInvoices?: () => Promise<void>;
}

const InvoiceSection: React.FC<InvoiceSectionProps> = ({ onInvoiceProcessed, onRefreshInvoices }) => {
  const [invoices, setInvoices] = useState<InvoiceData[]>([])
  const [processedInvoice, setProcessedInvoice] = useState<InvoiceData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState<string | null>(null);

  useEffect(() => {
    fetchInvoices()
  }, [])

  const fetchInvoices = async () => {
    setIsLoading(true)
    try {
      const data = await api.invoices.getAll()
      setInvoices(data)
    } catch (error) {
      console.error('Error fetching invoices:', error)
      toast.error('Could not load saved invoices.')
    } finally {
      setIsLoading(false)
    }
  }

  const onDrop = async (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      await processInvoice(file)
    }
  }

  const processInvoice = async (file: File) => {
    setIsLoading(true)
    try {
      const invoiceData = await api.invoices.processInvoice(file)
      setProcessedInvoice(invoiceData)
      
      if (onInvoiceProcessed) {
        onInvoiceProcessed(invoiceData)
      }
      await fetchInvoices()
      
      toast.success('Invoice processed successfully')
    } catch (error) {
      toast.error('Failed to process invoice')
      console.error('Error processing invoice:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteInvoice = async (invoiceId: string) => {
    setIsDeleting(invoiceId)
    try {
      await api.invoices.deleteById(invoiceId)
      toast.success('Invoice deleted successfully!')
      await fetchInvoices()
      if (onRefreshInvoices) {
        await onRefreshInvoices()
      }
    } catch (error) {
      console.error('Error deleting invoice:', error)
      toast.error('Failed to delete invoice.')
    } finally {
      setIsDeleting(null)
    }
  }

  const dropzoneOptions: DropzoneOptions = {
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 1,
    multiple: false,
    disabled: isLoading
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone(dropzoneOptions)

  const formatCurrency = (value: number) => {
    return value.toFixed(2)
  }

  return (
    <motion.div 
      className="card-elevated"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94], delay: 0.1 }}
    >
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-r from-accent-100 to-accent-200 rounded-xl">
            <Receipt className="h-6 w-6 text-accent-600" />
          </div>
          <div>
            <h2 className="heading-md text-secondary-900">Invoices</h2>
            <p className="text-sm text-secondary-600">Process and validate invoice documents</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="status-badge status-info">
            <FileText className="h-3 w-3 mr-1" />
            {invoices.length} processed
          </div>
        </div>
      </div>

      <motion.div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'dropzone-active' : 'dropzone-inactive'} ${
          isLoading ? 'opacity-50 pointer-events-none' : ''
        }`}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        <input {...getInputProps()} />
        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-accent-100 to-accent-200 rounded-2xl flex items-center justify-center">
            {isLoading ? (
              <div className="loading-spinner w-8 h-8"></div>
            ) : (
              <Upload className="h-8 w-8 text-accent-600" />
            )}
          </div>
          <div className="text-center">
            <p className="text-lg font-medium text-secondary-900 mb-2">
              {isDragActive
                ? 'Drop the invoice here'
                : isLoading
                ? 'Processing invoice...'
                : 'Drag & drop an invoice file'}
            </p>
            <p className="text-secondary-600">
              or click to select • PDF, JPEG, PNG supported
            </p>
          </div>
        </div>
      </motion.div>

      <AnimatePresence>
        {processedInvoice && (
          <motion.div 
            className="mt-8"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="heading-sm text-secondary-900">Latest Processed Invoice</h3>
              <div className="status-badge status-success">
                <CheckCircle className="h-3 w-3 mr-1" />
                Processed
              </div>
            </div>
            
            <div className="glass rounded-2xl p-6">
              <div className="flex justify-between items-start mb-6">
                <div className="flex-1">
                  <h4 className="font-semibold text-secondary-900 text-lg mb-1">
                    {processedInvoice.supplier_name}
                  </h4>
                  <div className="flex items-center space-x-4 text-sm text-secondary-600">
                    <div className="flex items-center space-x-1">
                      <FileText className="h-4 w-4" />
                      <span>ID: {processedInvoice.id}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Calendar className="h-4 w-4" />
                      <span>Processed: {new Date(processedInvoice.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-secondary-900">
                    ${processedInvoice.total?.toFixed(2) || '0.00'}
                  </p>
                  <p className="text-sm text-secondary-600">Total Amount</p>
                </div>
              </div>
              
              <div className="border-t border-secondary-200 pt-6">
                <h5 className="font-medium text-secondary-900 mb-4">Line Items</h5>
                <div className="space-y-3">
                  {processedInvoice.items.map((item, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex justify-between items-center py-3 px-4 bg-white/50 rounded-xl"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-secondary-900">{item.description}</p>
                        <p className="text-sm text-secondary-600">
                          {item.quantity} × ${formatCurrency(item.unit_price)}
                        </p>
                      </div>
                      <p className="font-semibold text-secondary-900">
                        ${formatCurrency(item.total)}
                      </p>
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {invoices.length > 0 && !processedInvoice && (
        <motion.div 
          className="mt-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <h3 className="heading-sm text-secondary-900 mb-6">
            Saved Invoices ({invoices.length})
          </h3>
          <div className="space-y-4">
            {invoices.map((invoice, index) => (
              <motion.div
                key={invoice.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass rounded-2xl p-4 flex justify-between items-center hover:shadow-medium transition-all duration-300"
              >
                <div className="flex items-center space-x-4">
                  <div className="p-2 bg-gradient-to-r from-primary-100 to-primary-200 rounded-xl">
                    <Receipt className="h-5 w-5 text-primary-600" />
                  </div>
                  <div>
                    <p className="font-medium text-secondary-900">
                      {invoice.supplier_name}
                    </p>
                    <div className="flex items-center space-x-3 text-sm text-secondary-600">
                      <span>ID: {invoice.id}</span>
                      <div className="flex items-center space-x-1">
                        <Clock className="h-3 w-3" />
                        <span>Processed: {new Date(invoice.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <p className="font-semibold text-secondary-900">
                      ${invoice.total?.toFixed(2) || '0.00'}
                    </p>
                    <p className="text-xs text-secondary-600">Total</p>
                  </div>
                  <motion.button
                    onClick={() => handleDeleteInvoice(invoice.id)}
                    disabled={isDeleting === invoice.id || isLoading}
                    className="p-2 text-secondary-400 hover:text-error-600 hover:bg-error-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    title="Delete this invoice"
                  >
                    {isDeleting === invoice.id ? (
                      <div className="loading-spinner w-4 h-4"></div>
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </motion.button>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}

export default InvoiceSection