'use client'

import { useState, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Plus, X, Trash2, Edit2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Contract, Item as ApiItem } from '@/services/api'

interface ContractSectionProps {
  onContractCreated?: () => void;
}

export function ContractSection({ onContractCreated }: ContractSectionProps) {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [isManualMode, setIsManualMode] = useState(false)
  const [newContract, setNewContract] = useState<{
    supplier_name: string;
    items: ApiItem[];
  }>({
    supplier_name: '',
    items: []
  })
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [editingContract, setEditingContract] = useState<Contract | null>(null)

  // Load contracts on component mount
  useEffect(() => {
    fetchContracts()
  }, [])

  const fetchContracts = async () => {
    try {
      const data = await api.contracts.getAll()
      setContracts(data)
    } catch (error) {
      toast.error('Failed to load contracts')
      console.error('Error loading contracts:', error)
    }
  }

  const handleUpload = async (file: File) => {
    setIsLoading(true)
    setIsUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const data = await api.contracts.upload(formData)
      setContracts((prevContracts) => [...prevContracts, data])
      setNewContract({
        supplier_name: '',
        items: []
      })
      toast.success('Contract uploaded successfully')
      if (onContractCreated) {
        onContractCreated()
      }
    } catch (error) {
      toast.error('Failed to upload contract')
      console.error('Error uploading contract:', error)
    } finally {
      setIsLoading(false)
      setIsUploading(false)
    }
  }

  const handleFileDrop = async (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      await handleUpload(file)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleFileDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 1,
    multiple: false,
    disabled: isLoading || isUploading
  })

  const addItem = () => {
    setNewContract({
      ...newContract,
      items: [
        ...newContract.items,
        { description: '', quantity: 1, unit_price: 0, total_price: 0 }
      ]
    })
  }

  const removeItem = (index: number) => {
    setNewContract({
      ...newContract,
      items: newContract.items.filter((_, i) => i !== index)
    })
  }

  const handleItemChange = (index: number, field: keyof ApiItem, value: string | number) => {
    setNewContract(prev => {
      const updatedItems = [...prev.items]
      const itemToUpdate = { ...updatedItems[index] } as any;
      itemToUpdate[field] = typeof value === 'string' && (field === 'quantity' || field === 'unit_price' || field === 'total_price') ? parseFloat(value) || 0 : value;
      
      // Recalculate total_price if quantity or unit_price changes for this item
      if (field === 'quantity' || field === 'unit_price') {
        itemToUpdate.total_price = itemToUpdate.quantity * itemToUpdate.unit_price;
      }
      updatedItems[index] = itemToUpdate as ApiItem;
      return { ...prev, items: updatedItems };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    
    try {
      const data = await api.contracts.create(newContract)
      setContracts((prevContracts) => [...prevContracts, data])
      setNewContract({
        supplier_name: '',
        items: []
      })
      toast.success('Contract created successfully')
      if (onContractCreated) {
        onContractCreated()
      }
    } catch (error) {
      toast.error('Failed to create contract')
      console.error('Error creating contract:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this contract?')) {
      return;
    }

    try {
      await api.contracts.delete(id);
      setContracts(contracts.filter(contract => contract.id !== id));
      toast.success('Contract deleted successfully');
    } catch (error) {
      toast.error('Failed to delete contract');
      console.error('Error deleting contract:', error);
    }
  };

  const handleEdit = (contract: Contract) => {
    setEditingContract(contract);
    setNewContract({
      supplier_name: contract.supplier_name,
      items: contract.items
    });
    setIsManualMode(true);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingContract) return;

    setIsLoading(true);
    try {
      const updatedContract = await api.contracts.update(editingContract.id, newContract);
      setContracts(contracts.map(contract => 
        contract.id === editingContract.id ? updatedContract : contract
      ));
      setEditingContract(null);
      setNewContract({
        supplier_name: '',
        items: []
      });
      toast.success('Contract updated successfully');
    } catch (error) {
      toast.error('Failed to update contract');
      console.error('Error updating contract:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">Contracts</h2>
      
      <div className="flex items-center space-x-4 mb-6">
        <button
          onClick={() => { setIsManualMode(false); setEditingContract(null); setNewContract({ supplier_name: '', items: [] }); }}
          className={`px-4 py-2 rounded-md transition-colors ${
            !isManualMode
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Upload
        </button>
        <button
          onClick={() => { setIsManualMode(true); setEditingContract(null); setNewContract({ supplier_name: '', items: [] }); }}
          className={`px-4 py-2 rounded-md transition-colors ${
            isManualMode
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Manual Input
        </button>
      </div>

      {!isManualMode ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            (isLoading || isUploading) ? 'opacity-50 pointer-events-none' : ''
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
              : (isLoading || isUploading)
              ? 'Processing...'
              : 'Drag & drop a contract file, or click to select'}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Supported formats: PDF, JPEG, PNG
          </p>
        </div>
      ) : (
        <form onSubmit={editingContract ? handleUpdate : handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Supplier Name
            </label>
            <input
              type="text"
              value={newContract.supplier_name}
              onChange={(e) =>
                setNewContract({ ...newContract, supplier_name: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
              placeholder="Enter supplier name"
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Items
              </label>
              <button
                type="button"
                onClick={addItem}
                className="flex items-center text-sm text-indigo-600 hover:text-indigo-700"
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Item
              </button>
            </div>

            <div className="space-y-4">
              {newContract.items.map((item, index) => (
                <div key={index} className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                  <input
                    type="text"
                    value={item.description}
                    onChange={(e) => {
                      const updatedItems = [...newContract.items]
                      updatedItems[index].description = e.target.value
                      setNewContract({
                        ...newContract,
                        items: updatedItems
                      })
                    }}
                    placeholder="Item description"
                    className="md:col-span-6 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                    required
                  />
                  <input
                    type="number"
                    value={item.quantity === 0 ? '' : item.quantity}
                    onChange={(e) => {
                      const updatedItems = [...newContract.items]
                      updatedItems[index].quantity = parseFloat(e.target.value) || 0
                      setNewContract({ ...newContract, items: updatedItems })
                    }}
                    placeholder="Quantity"
                    className="md:col-span-2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                    required
                    step="0.01"
                  />
                  <input
                    type="number"
                    value={item.unit_price === 0 ? '' : item.unit_price}
                    onChange={(e) => {
                      const updatedItems = [...newContract.items]
                      updatedItems[index].unit_price = parseFloat(e.target.value) || 0
                      setNewContract({
                        ...newContract,
                        items: updatedItems
                      })
                    }}
                    placeholder="Unit price"
                    className="md:col-span-3 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent"
                    required
                    step="0.01"
                  />
                  <button
                    type="button"
                    onClick={() => removeItem(index)}
                    className="md:col-span-1 text-gray-400 hover:text-red-500 flex justify-center"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full bg-indigo-600 text-white py-2 px-4 rounded-md transition-colors ${
              isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-indigo-700'
            }`}
          >
            {isLoading ? 'Saving...' : editingContract ? 'Update Contract' : 'Create Contract'}
          </button>
        </form>
      )}

      {contracts.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Your Contracts
          </h3>
          <div className="space-y-4">
            {contracts.map((contract) => (
              <div
                key={contract.id}
                className="border border-gray-200 rounded-md p-4"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className="font-medium text-gray-900">
                      {contract.supplier_name}
                    </h4>
                    <p className="text-sm text-gray-500">
                      Created: {new Date(contract.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleEdit(contract)}
                      className="text-gray-400 hover:text-indigo-600"
                      title="Edit contract"
                    >
                      <Edit2 className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(contract.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Delete contract"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  {contract.items && contract.items.map((item, idx) => (
                    <div
                      key={idx}
                      className="grid grid-cols-12 gap-x-4 text-sm"
                    >
                      <span className="col-span-6 text-gray-700 truncate" title={item.description}>{item.description}</span>
                      <span className={`sm:col-span-2 text-gray-600 text-right sm:text-left`}>Qty: {item.quantity?.toFixed(2) || 'N/A'}</span>
                      <span className={`sm:col-span-2 text-gray-800 text-right sm:text-left ${item.unit_price < 0 ? 'text-red-600' : ''}`}>
                        @ ${item.unit_price !== undefined ? Math.abs(item.unit_price).toFixed(2) : 'N/A'}
                      </span>
                      <span className={`sm:col-span-3 text-gray-900 font-medium text-right ${item.total_price && item.total_price < 0 ? 'text-red-600' : ''}`}>
                        Total: ${item.total_price !== undefined ? Math.abs(item.total_price).toFixed(2) : (item.quantity * item.unit_price) ? (item.quantity * item.unit_price).toFixed(2) : 'N/A'}
                        {item.total_price && item.total_price < 0 ? ' (neg)' : ''}
                      </span>
                    </div>
                  ))}
                  {(!contract.items || contract.items.length === 0) && (
                     <p className="text-sm text-gray-500">No items listed for this contract.</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
} 