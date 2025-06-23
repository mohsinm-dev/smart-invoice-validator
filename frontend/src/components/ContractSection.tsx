'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { Upload, Plus, X, Trash2, Edit2, FileText, Calendar, DollarSign } from 'lucide-react'
import toast from 'react-hot-toast'
import { api, Contract, Item as ApiItemBase } from '@/services/api'

// Patch ApiItem type to include 'total'
export type ApiItem = ApiItemBase & { total: number };

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
        { description: '', quantity: 1, unit_price: 0, total: 0 }
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
      itemToUpdate[field] = typeof value === 'string' && (field === 'quantity' || field === 'unit_price' || field === 'total') ? parseFloat(value) || 0 : value;
      if (field === 'quantity' || field === 'unit_price') {
        itemToUpdate.total = itemToUpdate.quantity * itemToUpdate.unit_price;
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

  const totalValue = newContract.items.reduce((sum, item) => sum + (item.total || 0), 0);

  return (
    <motion.div 
      className="card-elevated"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-r from-primary-100 to-primary-200 rounded-xl">
            <FileText className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h2 className="heading-md text-secondary-900">Contracts</h2>
            <p className="text-sm text-secondary-600">Manage your contract documents</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2 bg-secondary-100 rounded-xl p-1">
          <button
            onClick={() => { setIsManualMode(false); setEditingContract(null); setNewContract({ supplier_name: '', items: [] }); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              !isManualMode
                ? 'bg-white text-primary-600 shadow-soft'
                : 'text-secondary-600 hover:text-secondary-900'
            }`}
          >
            Upload
          </button>
          <button
            onClick={() => { setIsManualMode(true); setEditingContract(null); setNewContract({ supplier_name: '', items: [] }); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              isManualMode
                ? 'bg-white text-primary-600 shadow-soft'
                : 'text-secondary-600 hover:text-secondary-900'
            }`}
          >
            Manual Input
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {!isManualMode ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ duration: 0.3 }}
          >
            <div
              {...getRootProps()}
              className={`dropzone ${isDragActive ? 'dropzone-active' : 'dropzone-inactive'} ${
                (isLoading || isUploading) ? 'opacity-50 pointer-events-none' : ''
              }`}
            >
              <input {...getInputProps()} />
              <div className="space-y-4">
                <div className="mx-auto w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-2xl flex items-center justify-center">
                  <Upload className="h-8 w-8 text-primary-600" />
                </div>
                <div className="text-center">
                  <p className="text-lg font-medium text-secondary-900 mb-2">
                    {isDragActive
                      ? 'Drop the file here'
                      : (isLoading || isUploading)
                      ? 'Processing...'
                      : 'Drag & drop a contract file'}
                  </p>
                  <p className="text-secondary-600">
                    or click to select • PDF, JPEG, PNG supported
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="manual"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <form onSubmit={editingContract ? handleUpdate : handleSubmit} className="space-y-6">
              <div>
                <label className="text-label">Supplier Name</label>
                <input
                  type="text"
                  value={newContract.supplier_name}
                  onChange={(e) =>
                    setNewContract({ ...newContract, supplier_name: e.target.value })
                  }
                  className="input-field"
                  placeholder="Enter supplier name"
                  required
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-4">
                  <label className="text-label mb-0">Contract Items</label>
                  <motion.button
                    type="button"
                    onClick={addItem}
                    className="btn btn-secondary text-sm"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Item
                  </motion.button>
                </div>

                <div className="space-y-4">
                  <AnimatePresence>
                    {newContract.items.map((item, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center p-4 bg-secondary-50 rounded-xl"
                      >
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
                          className="md:col-span-6 input-field"
                          required
                        />
                        <input
                          type="number"
                          value={item.quantity === 0 ? '' : item.quantity}
                          onChange={(e) => {
                            const updatedItems = [...newContract.items]
                            updatedItems[index].quantity = parseFloat(e.target.value) || 0
                            updatedItems[index].total = updatedItems[index].quantity * updatedItems[index].unit_price
                            setNewContract({ ...newContract, items: updatedItems })
                          }}
                          placeholder="Qty"
                          className="md:col-span-2 input-field"
                          required
                          step="0.01"
                        />
                        <input
                          type="number"
                          value={item.unit_price === 0 ? '' : item.unit_price}
                          onChange={(e) => {
                            const updatedItems = [...newContract.items]
                            updatedItems[index].unit_price = parseFloat(e.target.value) || 0
                            updatedItems[index].total = updatedItems[index].quantity * updatedItems[index].unit_price
                            setNewContract({
                              ...newContract,
                              items: updatedItems
                            })
                          }}
                          placeholder="Unit price"
                          className="md:col-span-3 input-field"
                          required
                          step="0.01"
                        />
                        <motion.button
                          type="button"
                          onClick={() => removeItem(index)}
                          className="md:col-span-1 p-2 text-secondary-400 hover:text-error-500 hover:bg-error-50 rounded-lg transition-colors"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                        >
                          <X className="h-5 w-5" />
                        </motion.button>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>

                {newContract.items.length > 0 && (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 p-4 bg-primary-50 rounded-xl border border-primary-200"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-primary-900">Total Contract Value</span>
                      <span className="text-xl font-bold text-primary-700">
                        ${totalValue.toFixed(2)}
                      </span>
                    </div>
                  </motion.div>
                )}
              </div>

              <motion.button
                type="submit"
                disabled={isLoading}
                className="btn btn-primary w-full"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="loading-spinner w-4 h-4"></div>
                    <span>Saving...</span>
                  </div>
                ) : (
                  editingContract ? 'Update Contract' : 'Create Contract'
                )}
              </motion.button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {contracts.length > 0 && (
        <motion.div 
          className="mt-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="heading-sm text-secondary-900 mb-6">
            Your Contracts ({contracts.length})
          </h3>
          <div className="space-y-4">
            {contracts.map((contract, index) => (
              <motion.div
                key={contract.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass rounded-2xl p-6 hover:shadow-medium transition-all duration-300"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h4 className="font-semibold text-secondary-900 text-lg mb-1">
                      {contract.supplier_name}
                    </h4>
                    <div className="flex items-center space-x-4 text-sm text-secondary-600">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>Created {new Date(contract.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <DollarSign className="h-4 w-4" />
                        <span>
                          ${contract.items?.reduce((sum, item) => sum + (item.total || 0), 0).toFixed(2) || '0.00'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    <motion.button
                      onClick={() => handleEdit(contract)}
                      className="p-2 text-secondary-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      title="Edit contract"
                    >
                      <Edit2 className="h-4 w-4" />
                    </motion.button>
                    <motion.button
                      onClick={() => handleDelete(contract.id)}
                      className="p-2 text-secondary-400 hover:text-error-600 hover:bg-error-50 rounded-lg transition-colors"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      title="Delete contract"
                    >
                      <Trash2 className="h-4 w-4" />
                    </motion.button>
                  </div>
                </div>
                
                {contract.items && contract.items.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-secondary-700 mb-3">
                      Contract Items ({contract.items.length})
                    </p>
                    <div className="grid gap-2">
                      {contract.items.slice(0, 3).map((item, idx) => (
                        <div
                          key={idx}
                          className="grid grid-cols-12 gap-x-4 text-sm py-2 px-3 bg-white/50 rounded-lg"
                        >
                          <span className="col-span-6 text-secondary-700 truncate font-medium" title={item.description}>
                            {item.description}
                          </span>
                          <span className="col-span-2 text-secondary-600 text-right">
                            {item.quantity?.toFixed(2) || 'N/A'}
                          </span>
                          <span className="col-span-2 text-secondary-800 text-right font-medium">
                            ${item.unit_price !== undefined ? Math.abs(item.unit_price).toFixed(2) : 'N/A'}
                          </span>
                          <span className="col-span-2 text-secondary-900 font-semibold text-right">
                            ${item.total !== undefined ? Math.abs(item.total).toFixed(2) : (item.quantity * item.unit_price) ? (item.quantity * item.unit_price).toFixed(2) : 'N/A'}
                          </span>
                        </div>
                      ))}
                      {contract.items.length > 3 && (
                        <p className="text-xs text-secondary-500 text-center py-2">
                          +{contract.items.length - 3} more items
                        </p>
                      )}
                    </div>
                  </div>
                )}
                
                {(!contract.items || contract.items.length === 0) && (
                  <p className="text-sm text-secondary-500 italic">No items listed for this contract.</p>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}