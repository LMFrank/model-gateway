import client from './client'

export interface ModelInfo {
  id: number
  display_name: string
  upstream_model: string
  is_active: boolean
}

export interface RouteProviderInfo {
  id: number
  name: string
  provider_type: string
}

export interface RouteRule {
  model_key: string
  is_enabled: boolean
  priority: number
  description: string | null
  created_at: string
  updated_at: string
  model: ModelInfo | null
  provider: RouteProviderInfo | null
}

export interface CreateRouteRequest {
  model_key: string
  is_enabled?: boolean
  priority?: number
  description?: string
}

export const routesApi = {
  list: async (): Promise<RouteRule[]> => {
    const response = await client.get('/api/routes')
    return response.data.items
  },

  create: async (data: CreateRouteRequest): Promise<{ items: RouteRule[] }> => {
    const response = await client.post('/api/routes', { rules: [data] })
    return response.data
  },

  update: async (data: CreateRouteRequest): Promise<{ items: RouteRule[] }> => {
    const response = await client.post('/api/routes', { rules: [data] })
    return response.data
  },

  delete: async (modelKey: string): Promise<void> => {
    await client.delete(`/api/routes/${modelKey}`)
  },
}
