import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'

interface Contract {
  id: string
  name: string
  description: string
  created_at: string
}

const Contracts = () => {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchContracts = async () => {
      try {
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/v1/contracts`)
        setContracts(response.data)
      } catch (err) {
        setError('Error fetching contracts. Please try again.')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchContracts()
  }, [])

  return (
    <div className="min-h-screen bg-gray-100 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-900">Contracts</h1>
            <Link
              to="/upload"
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            >
              Upload New Contract
            </Link>
          </div>

          {loading ? (
            <div className="text-center py-8">Loading contracts...</div>
          ) : error ? (
            <div className="p-4 bg-red-100 text-red-700 rounded">{error}</div>
          ) : contracts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No contracts found. Upload a contract to get started.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {contracts.map((contract) => (
                <Link
                  key={contract.id}
                  to={`/contracts/${contract.id}`}
                  className="block p-6 bg-white border rounded-lg shadow hover:bg-gray-50"
                >
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {contract.name}
                  </h2>
                  <p className="text-gray-600 mb-4">{contract.description}</p>
                  <p className="text-sm text-gray-500">
                    Created: {new Date(contract.created_at).toLocaleDateString()}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Contracts 