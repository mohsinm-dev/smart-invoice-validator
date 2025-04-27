import { useState } from 'react'
import axios from 'axios'

const Upload = () => {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verificationResult, setVerificationResult] = useState<any>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setError(null)
      setVerificationResult(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      // First verify the document
      const verifyResponse = await axios.post('http://localhost:8000/api/v1/documents/verify-document', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setVerificationResult(verifyResponse.data)

      // If verification is successful, proceed with comparison
      if (verifyResponse.data.verification.is_purchase_order) {
        // Here you would typically show a contract selection UI
        // and then call the compare endpoint with the selected contract_id
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center sm:py-12">
      <div className="relative py-3 sm:max-w-xl sm:mx-auto">
        <div className="relative px-4 py-10 bg-white shadow-lg sm:rounded-3xl sm:p-20">
          <div className="max-w-md mx-auto">
            <div className="divide-y divide-gray-200">
              <div className="py-8 text-base leading-6 space-y-4 text-gray-700 sm:text-lg sm:leading-7">
                <h1 className="text-3xl font-bold text-center text-gray-900 mb-8">
                  Upload Document
                </h1>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Document File
                    </label>
                    <input
                      type="file"
                      accept=".pdf,.doc,.docx"
                      onChange={handleFileChange}
                      className="mt-1 block w-full text-sm text-gray-500
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-full file:border-0
                        file:text-sm file:font-semibold
                        file:bg-blue-50 file:text-blue-700
                        hover:file:bg-blue-100"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={!file || loading}
                    className="w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
                  >
                    {loading ? 'Processing...' : 'Upload and Verify'}
                  </button>
                </form>

                {error && (
                  <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
                    {error}
                  </div>
                )}

                {verificationResult && (
                  <div className="mt-4 p-4 bg-gray-100 rounded">
                    <h3 className="font-bold mb-2">Verification Result:</h3>
                    <p>Is Purchase Order: {verificationResult.verification.is_purchase_order ? 'Yes' : 'No'}</p>
                    <p>Confidence: {verificationResult.verification.confidence}</p>
                    <p>Reason: {verificationResult.verification.reason}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Upload 