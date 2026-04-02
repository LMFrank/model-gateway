import client from './client'
import type { ApiListResponse, RouteRule, UpsertRouteRequest } from '@/types'

export type { RouteRule, UpsertRouteRequest } from '@/types'

interface UpsertRoutesPayload {
  rules: UpsertRouteRequest[]
}

export const routesApi = {
  async list(): Promise<RouteRule[]> {
    const response = await client.get<ApiListResponse<RouteRule>>('/api/routes')
    return response.data.items
  },

  async create(data: UpsertRouteRequest): Promise<ApiListResponse<RouteRule>> {
    const payload: UpsertRoutesPayload = { rules: [data] }
    const response = await client.post<ApiListResponse<RouteRule>>('/api/routes', payload)
    return response.data
  },

  async update(data: UpsertRouteRequest): Promise<ApiListResponse<RouteRule>> {
    const payload: UpsertRoutesPayload = { rules: [data] }
    const response = await client.post<ApiListResponse<RouteRule>>('/api/routes', payload)
    return response.data
  },

  async delete(modelKey: string): Promise<void> {
    await client.delete(`/api/routes/${modelKey}`)
  },
}
