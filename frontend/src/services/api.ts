// API URL handling - direct API URL for debugging
const API_URL = 'http://localhost:8000';
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

export interface PriceComparisonDetail {
  service_name: string;
  contract_price: number | null;
  invoice_price: number;
  match: boolean;
  note?: string;
}

export interface ComparisonResult {
  contract_id: string;
  invoice_data: InvoiceData;
  matches: {
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
  price_comparison_details: PriceComparisonDetail[];
}

// Helper function to handle errors
const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const errorText = await response.text();
    console.error('API Error:', response.status, errorText);
    throw new Error(`API request failed with status ${response.status}: ${errorText}`);
  }
  return response.json();
};

// Debug function
const debugFetch = async (url: string, options?: RequestInit) => {
  console.log(`Fetching ${url}`, options);
  try {
    const response = await fetch(url, options);
    console.log(`Response for ${url}:`, response.status);
    return response;
  } catch (error) {
    console.error(`Fetch error for ${url}:`, error);
    throw error;
  }
};

// API services
export const api = {
  // Contract endpoints
  contracts: {
    getAll: async (): Promise<Contract[]> => {
      try {
        const response = await debugFetch(`${API_V1}/contracts`);
        return handleResponse(response);
      } catch (error) {
        console.error('Error in getAll:', error);
        throw new Error('Failed to fetch contracts');
      }
    },
    
    getById: async (id: string): Promise<Contract> => {
      try {
        const response = await debugFetch(`${API_V1}/contracts/${id}`);
        return handleResponse(response);
      } catch (error) {
        console.error('Error in getById:', error);
        throw new Error('Failed to fetch contract');
      }
    },
    
    create: async (contractData: ContractCreate): Promise<Contract> => {
      try {
        const response = await debugFetch(`${API_V1}/contracts`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(contractData),
        });
        return handleResponse(response);
      } catch (error) {
        console.error('Error in create:', error);
        throw new Error('Failed to create contract');
      }
    },
    
    upload: async (formData: FormData): Promise<Contract> => {
      try {
        const response = await debugFetch(`${API_V1}/contracts/upload`, {
          method: 'POST',
          body: formData,
        });
        return handleResponse(response);
      } catch (error) {
        console.error('Error in upload:', error);
        throw new Error('Failed to upload contract');
      }
    },
    
    delete: async (id: string): Promise<void> => {
      try {
        const response = await debugFetch(`${API_V1}/contracts/${id}`, {
          method: 'DELETE',
        });
        return handleResponse(response);
      } catch (error) {
        console.error('Error in delete:', error);
        throw new Error('Failed to delete contract');
      }
    },
    
    update: async (id: string, contractData: ContractCreate): Promise<Contract> => {
      try {
        const response = await debugFetch(`${API_V1}/contracts/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(contractData),
        });
        return handleResponse(response);
      } catch (error) {
        console.error('Error in update:', error);
        throw new Error('Failed to update contract');
      }
    }
  },
  
  // Invoice endpoints
  invoices: {
    getAll: async (): Promise<any[]> => {
      try {
        // Try direct API first for debugging
        const directUrl = `${API_URL}${API_V1}/invoices/`;
        console.log("Trying direct API URL:", directUrl);
        const directResponse = await debugFetch(directUrl);
        
        if (directResponse.ok) {
          return await directResponse.json();
        }
        
        // Fall back to relative URL if direct fails
        console.log("Direct API failed, trying relative URL");
        const response = await debugFetch(`${API_V1}/invoices/`);
        return handleResponse(response);
      } catch (error) {
        console.error('Error in getAll invoices:', error);
        throw new Error('Failed to fetch invoices');
      }
    },
    
    getById: async (id: string): Promise<any> => {
      try {
        const response = await debugFetch(`${API_V1}/invoices/${id}`);
        return handleResponse(response);
      } catch (error) {
        console.error('Error in getById invoice:', error);
        throw new Error('Failed to fetch invoice');
      }
    },
    
    processInvoice: async (file: File): Promise<InvoiceData> => {
      try {
        // Read the file as base64
        const fileContent = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            // Extract the base64 content (remove data:application/pdf;base64, prefix)
            const base64String = reader.result as string;
            const base64Content = base64String.split(',')[1];
            resolve(base64Content);
          };
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });
        
        // Get file type from the file extension
        const fileType = file.name.split('.').pop()?.toLowerCase() || '';
        
        // Send request with base64 encoded content
        const response = await debugFetch(`${API_V1}/invoices/process`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file_content: fileContent,
            file_type: fileType
          }),
        });
        
        return handleResponse(response);
      } catch (error) {
        console.error('Error in processInvoice:', error);
        throw new Error('Failed to process invoice');
      }
    },
    
    compareInvoice: async (contractId: string, invoiceData: InvoiceData): Promise<ComparisonResult> => {
      try {
        const response = await debugFetch(`${API_V1}/invoices/compare`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            contract_id: contractId,
            invoice_data: invoiceData,
          }),
        });
        
        return handleResponse(response);
      } catch (error) {
        console.error('Error in compareInvoice:', error);
        throw new Error('Failed to compare invoice');
      }
    }
  }
}; 