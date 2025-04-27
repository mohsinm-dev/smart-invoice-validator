import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'

interface ContractDetails {
  id: string
  name: string
  description: string
  created_at: string
  items: Array<{
    id: string
    name: string
    description: string
    quantity: number
    unit_price: number
  }>
  validations: Array<{
    id: string
    invoice_id: string
    status: string
    created_at: string
    results: {
      matches: boolean
      discrepancies: Array<{
        field: string
        expected: any
        actual: any
      }>
    }
  }>
}

const ContractDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [contract, setContract] = useState<ContractDetails | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchContractDetails = async () => {
      try {
        const response = await axios.get(
          `${import.meta.env.VITE_API_URL}/contracts/${id}`
        )
        setContract(response.data)
      } catch (err) {
        setError('Error fetching contract details. Please try again.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchContractDetails()
  }, [id])

  if (loading) {
    return <div className="text-center py-8">Loading contract details...</div>
  }

  if (error) {
    return (
      <div className="p-4 bg-red-100 text-red-700 rounded max-w-7xl mx-auto">
        {error}
      </div>
    )
  }

  if (!contract) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-100 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {contract.name}
          </h1>
          <p className="text-gray-600 mb-6">{contract.description}</p>
          <p className="text-sm text-gray-500 mb-8">
            Created: {new Date(contract.created_at).toLocaleDateString()}
          </p>

          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Contract Items
            </h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {contract.items.map((item) => (
                <div
                  key={item.id}
                  className="p-4 bg-gray-50 rounded-lg"
                >
                  <h3 className="font-medium text-gray-900">{item.name}</h3>
                  <p className="text-gray-600">{item.description}</p>
                  <p className="text-sm text-gray-500 mt-2">
                    Quantity: {item.quantity} | Unit Price: ${item.unit_price}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Validation History
            </h2>
            {contract.validations.length === 0 ? (
              <p className="text-gray-500">No validations yet.</p>
            ) : (
              <div className="space-y-4">
                {contract.validations.map((validation) => (
                  <div
                    key={validation.id}
                    className="p-4 border rounded-lg"
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-gray-500">
                        {new Date(validation.created_at).toLocaleString()}
                      </span>
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded ${
                          validation.status === 'valid'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {validation.status}
                      </span>
                    </div>
                    {validation.results.discrepancies.length > 0 && (
                      <div className="mt-4">
                        <h4 className="font-medium text-gray-900 mb-2">
                          Discrepancies Found:
                        </h4>
                        <ul className="space-y-2">
                          {validation.results.discrepancies.map(
                            (discrepancy, index) => (
                              <li
                                key={index}
                                className="text-sm text-gray-600"
                              >
                                <span className="font-medium">
                                  {discrepancy.field}:
                                </span>{' '}
                                Expected {discrepancy.expected}, got{' '}
                                {discrepancy.actual}
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ContractDetails 