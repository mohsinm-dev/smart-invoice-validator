'use client'

import React, { useState, useEffect } from 'react'
import { useDropzone, DropzoneOptions } from 'react-dropzone'
import { Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, InvoiceData } from '@/services/api'

interface InvoiceSectionProps {
  onInvoiceProcessed?: (invoiceData: InvoiceData) => void;
}

const InvoiceSection: React.FC<InvoiceSectionProps> = ({ onInvoiceProcessed }) => {
  const [invoices, setInvoices] = useState<any[]>([])
  const [processedInvoice, setProcessedInvoice] = useState<InvoiceData | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    fetchInvoices()
  }, [])

  const fetchInvoices = async () => {
    try {
      const data = await api.invoices.getAll()
      setInvoices(data)
    } catch (error) {
      console.error('Error fetching invoices:', error)
      // Don't show error toast since this isn't critical for the user
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
      
      // Notify parent component if callback is provided
      if (onInvoiceProcessed) {
        onInvoiceProcessed(invoiceData)
      }
      
      toast.success('Invoice processed successfully')
    } catch (error) {
      toast.error('Failed to process invoice')
      console.error('Error processing invoice:', error)
    } finally {
      setIsLoading(false)
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
                  Invoice #{processedInvoice.invoice_number}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">
                  Issue Date: {new Date(processedInvoice.issue_date).toLocaleDateString()}
                </p>
                {processedInvoice.due_date && (
                  <p className="text-sm text-gray-600">
                    Due Date: {new Date(processedInvoice.due_date).toLocaleDateString()}
                  </p>
                )}
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
                      ${formatCurrency(item.total_price || (item.quantity * item.unit_price))}
                    </p>
                  </div>
                ))}
              </div>

              <div className="border-t border-gray-200 mt-4 pt-4">
                {processedInvoice.subtotal && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Subtotal</span>
                    <span className="text-gray-900">
                      ${formatCurrency(processedInvoice.subtotal)}
                    </span>
                  </div>
                )}
                {processedInvoice.tax && (
                  <div className="flex justify-between text-sm mt-2">
                    <span className="text-gray-600">Tax</span>
                    <span className="text-gray-900">
                      ${formatCurrency(processedInvoice.tax)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between font-medium mt-2">
                  <span className="text-gray-900">Total</span>
                  <span className="text-gray-900">
                    ${formatCurrency(processedInvoice.total)}
                  </span>
                </div>
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
                className="border border-gray-200 rounded-md p-4"
              >
                <div className="flex justify-between">
                  <div>
                    <p className="font-medium">Invoice #{invoice.id}</p>
                    <p className="text-sm text-gray-600">
                      Created: {new Date(invoice.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    {invoice.is_valid ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Valid
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        Invalid
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default InvoiceSection 