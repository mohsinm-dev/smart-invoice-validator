import { FileText } from 'lucide-react'

export function Navbar() {
  return (
    <nav className="bg-white shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="h-6 w-6 text-indigo-600" />
            <span className="text-xl font-semibold text-gray-900">
              Smart Invoice Validator
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <a
              href="https://github.com/yourusername/smart-invoice-validator"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </div>
    </nav>
  )
} 