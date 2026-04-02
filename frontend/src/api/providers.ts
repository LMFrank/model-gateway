import client from './client'
import type {
  ApiCreatedResponse,
  ApiItemResponse,
  ApiListResponse,
  CreateProviderRequest,
  Provider,
  ProviderHealthCheck,
  UpdateProviderRequest,
} from '@/types'

export type { CreateProviderRequest, Provider, UpdateProviderRequest } from '@/types'

export const providersApi = {
  async list(): Promise<Provider[]> {
    const response = await client.get<ApiListResponse<Provider>>('/api/providers')
    return response.data.items
  },

  async get(id: number): Promise<Provider> {
    const response = await client.get<Provider>(`/api/providers/${id}`)
    return response.data
  },

  async create(data: CreateProviderRequest): Promise<ApiCreatedResponse<Provider>> {
    const response = await client.post<ApiCreatedResponse<Provider>>('/api/providers', data)
    return response.data
  },

  async update(id: number, data: UpdateProviderRequest): Promise<ApiItemResponse<Provider>> {
    const response = await client.put<ApiItemResponse<Provider>>(`/api/providers/${id}`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await client.delete(`/api/providers/${id}`)
  },

  async healthCheck(id: number): Promise<ProviderHealthCheck> {
    const response = await client.post<ProviderHealthCheck>(`/api/health/check/provider/${id}`)
    return response.data
  },
}
