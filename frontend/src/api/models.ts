import client from './client'

export interface ProviderInfo {
  id: number
  name: string
  display_name: string
}

export interface Model {
  id: number
  model_key: string
  display_name: string
  upstream_model: string
  default_params: Record<string, any>
  description: string | null
  notes: string | null
  is_active: boolean
  health_status: 'unknown' | 'healthy' | 'unhealthy'
  last_health_check: string | null
  created_at: string
  updated_at: string
  provider: ProviderInfo | null
}

export interface CreateModelRequest {
  provider_id: number
  model_key: string
  display_name: string
  upstream_model: string
  default_params?: Record<string, any>
  description?: string
  notes?: string
  is_active?: boolean
}

export interface UpdateModelRequest {
  provider_id?: number
  display_name?: string
  upstream_model?: string
  default_params?: Record<string, any>
  description?: string
  notes?: string
  is_active?: boolean
  health_status?: 'unknown' | 'healthy' | 'unhealthy'
}

export const modelsApi = {
  list: async (providerId?: number): Promise<Model[]> => {
    const params = providerId ? { provider_id: providerId } : {}
    const response = await client.get('/api/models', { params })
    return response.data.items
  },

  get: async (id: number): Promise<Model> => {
    const response = await client.get(`/api/models/${id}`)
    return response.data
  },

  create: async (data: CreateModelRequest): Promise<{ id: number; item: Model }> => {
    const response = await client.post('/api/models', data)
    return response.data
  },

  update: async (id: number, data: UpdateModelRequest): Promise<{ item: Model }> => {
    const response = await client.put(`/api/models/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await client.delete(`/api/models/${id}`)
  },

  healthCheck: async (id: number): Promise<{
    id: number
    model_id: number
    model_key: string
    provider_name: string
    status: string
    latency_ms: number
    check_result: Record<string, any>
    error_message: string | null
    checked_at: number
  }> => {
    const response = await client.post(`/api/health/check/model/${id}`)
    return response.data
  },

  test: async (modelKey: string, message: string = 'Hello'): Promise<any> => {
    const response = await client.post('/v1/chat/completions', {
      model: modelKey,
      messages: [{ role: 'user', content: message }],
      max_tokens: 50,
    })
    return response.data
  },
}
