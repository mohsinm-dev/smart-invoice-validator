// API URL handling - we're using Next.js rewrites, so use relative URLs
const API_V1 = '/api/v1';

// Types
export interface Service {
  service_name: string;
  unit_price: number;
}

export interface ContractCreate {
  supplier_name: string;
  services: Service[];
}

export interface Contract {
  id: string;
  supplier_name: string;
  services: Service[];
  created_at: string;
  updated_at?: string;
}

export interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
  total_price?: number;
}

export interface InvoiceData {
  invoice_number: string;
  supplier_name: string;
  issue_date: string;
  due_date?: string;
  items: InvoiceItem[];
  subtotal?: number;
  tax?: number;
  total: number;
  raw_text?: string;
}

export interface ComparisonResult {
  contract_id: string;
  invoice_data: InvoiceData;
  matches: {
    supplier_name: boolean;
    prices_match: boolean;
    all_services_in_contract: boolean;
  };
  issues: Array<{
    type: string;
    service_name?: string;
    contract_value?: number | string;
    invoice_value?: number | string;
  }>;
  overall_match: boolean;
}

// API services
export const api = {
  // Contract endpoints
  contracts: {
    getAll: async (): Promise<Contract[]> => {
      const response = await fetch(`${API_V1}/contracts/`);
      if (!response.ok) {
        throw new Error('Failed to fetch contracts');
      }
      return response.json();
    },
    
    getById: async (id: string): Promise<Contract> => {
      const response = await fetch(`${API_V1}/contracts/${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch contract');
      }
      return response.json();
    },
    
    create: async (contractData: ContractCreate): Promise<Contract> => {
      const response = await fetch(`${API_V1}/contracts/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(contractData),
      });
      
      if (!response.ok) {
        throw new Error('Failed to create contract');
      }
      
      return response.json();
    }
  },
  
  // Invoice endpoints
  invoices: {
    getAll: async (): Promise<any[]> => {
      const response = await fetch(`${API_V1}/invoices/`);
      if (!response.ok) {
        throw new Error('Failed to fetch invoices');
      }
      return response.json();
    },
    
    getById: async (id: string): Promise<any> => {
      const response = await fetch(`${API_V1}/invoices/${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch invoice');
      }
      return response.json();
    },
    
    processInvoice: async (file: File): Promise<InvoiceData> => {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_V1}/invoices/process`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Failed to process invoice');
      }
      
      return response.json();
    },
    
    compareInvoice: async (contractId: string, invoiceData: InvoiceData): Promise<ComparisonResult> => {
      const response = await fetch(`${API_V1}/invoices/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contract_id: contractId,
          invoice_data: invoiceData,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to compare invoice');
      }
      
      return response.json();
    }
  }
}; 