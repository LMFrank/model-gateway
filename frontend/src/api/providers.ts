import client from './client'

export interface Provider {
  id: number
  name: string
  display_name: string
  provider_type: 'cli' | 'api'
  base_url: string | null
  api_key: string | null
  config: Record<string, any>
  description: string | null
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface CreateProviderRequest {
  name: string
  display_name: string
  provider_type: 'cli' | 'api'
  base_url?: string
  api_key?: string
  config?: Record<string, any>
  description?: string
  is_enabled?: boolean
}

export interface UpdateProviderRequest {
  display_name?: string
  provider_type?: 'cli' | 'api'
  base_url?: string
  api_key?: string
  config?: Record<string, any>
  description?: string
  is_enabled?: boolean
}

export const providersApi = {
  list: async (): Promise<Provider[]> => {
    const response = await client.get('/api/providers')
    return response.data.items
  },

  get: async (id: number): Promise<Provider> => {
    const response = await client.get(`/api/providers/${id}`)
    return response.data
  },

  create: async (data: CreateProviderRequest): Promise<{ id: number; item: Provider }> => {
    const response = await client.post('/api/providers', data)
    return response.data
  },

  update: async (id: number, data: UpdateProviderRequest): Promise<{ item: Provider }> => {
    const response = await client.put(`/api/providers/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/api/providers/${id}`)
  },

  healthCheck: async (id: number): Promise<{
    id: number
    provider_id: number
    provider_name: string
    status: string
    latency_ms: number
    check_result: Record<string, any>
    error_message: string | null
    checked_at: number
  }> => {
    const response = await client.post(`/api/health/check/provider/${id}`)
    return response.data
  },
}
