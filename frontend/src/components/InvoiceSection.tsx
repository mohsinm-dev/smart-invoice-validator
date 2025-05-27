'use client'

import React, { useState, useEffect } from 'react'
import { useDropzone, DropzoneOptions } from 'react-dropzone'
import { Upload, Trash2 } from 'lucide-react'
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
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">Invoices</h2>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isLoading ? 'opacity-50 pointer-events-none' : ''
        } ${
          isDragActive
            ? 'border-indigo-600 bg-indigo-50'
            : 'border-gray-300 hover:border-indigo-600 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-600">
          {isDragActive
            ? 'Drop the file here'
            : isLoading
            ? 'Processing...'
            : 'Drag & drop an invoice file, or click to select'}
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Supported formats: PDF, JPEG, PNG
        </p>
      </div>

      {processedInvoice && (
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Processed Invoice
          </h3>
          <div className="border border-gray-200 rounded-md p-4">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h4 className="font-medium text-gray-900">
                  {processedInvoice.supplier_name}
                </h4>
                <p className="text-sm text-gray-600">
                  Invoice ID: {processedInvoice.id}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">
                  Processed: {new Date(processedInvoice.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="border-t border-gray-200 pt-4">
              <div className="space-y-2">
                {processedInvoice.items.map((item, index) => (
                  <div
                    key={index}
                    className="flex justify-between text-sm"
                  >
                    <div className="flex-1">
                      <p className="text-gray-900">{item.description}</p>
                      <p className="text-gray-600">
                        {item.quantity} x ${formatCurrency(item.unit_price)}
                      </p>
                    </div>
                    <p className="text-gray-900">
                      ${formatCurrency(item.total)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {invoices.length > 0 && !processedInvoice && (
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Saved Invoices
          </h3>
          <div className="space-y-4">
            {invoices.map((invoice) => (
              <div
                key={invoice.id}
                className="border border-gray-200 rounded-md p-4 flex justify-between items-center"
              >
                <div className="flex-1">
                  <p className="font-medium">{invoice.supplier_name} - ID: {invoice.id}</p>
                    <p className="text-sm text-gray-600">
                    Processed: {new Date(invoice.created_at).toLocaleDateString()}
                    </p>
                  </div>
                <button
                  onClick={() => handleDeleteInvoice(invoice.id)}
                  disabled={isDeleting === invoice.id || isLoading}
                  className="p-2 text-red-500 hover:text-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Delete this invoice"
                >
                  {isDeleting === invoice.id ? (
                    <span className="text-sm italic">Deleting...</span>
                  ) : (
                    <Trash2 size={18} />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default InvoiceSection 