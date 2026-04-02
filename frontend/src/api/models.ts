import client from './client'
import type {
  ApiCreatedResponse,
  ApiItemResponse,
  ApiListResponse,
  CreateModelRequest,
  Model,
  ModelHealthCheck,
  UpdateModelRequest,
} from '@/types'

export type { CreateModelRequest, Model, UpdateModelRequest } from '@/types'

export const modelsApi = {
  async list(providerId?: number): Promise<Model[]> {
    const params = providerId ? { provider_id: providerId } : {}
    const response = await client.get<ApiListResponse<Model>>('/api/models', { params })
    return response.data.items
  },

  async get(id: number): Promise<Model> {
    const response = await client.get<Model>(`/api/models/${id}`)
    return response.data
  },

  async create(data: CreateModelRequest): Promise<ApiCreatedResponse<Model>> {
    const response = await client.post<ApiCreatedResponse<Model>>('/api/models', data)
    return response.data
  },

  async update(id: number, data: UpdateModelRequest): Promise<ApiItemResponse<Model>> {
    const response = await client.put<ApiItemResponse<Model>>(`/api/models/${id}`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await client.delete(`/api/models/${id}`)
  },

  async healthCheck(id: number): Promise<ModelHealthCheck> {
    const response = await client.post<ModelHealthCheck>(`/api/health/check/model/${id}`)
    return response.data
  },

  async test(modelKey: string, message = 'Hello'): Promise<unknown> {
    const response = await client.post('/v1/chat/completions', {
      model: modelKey,
      messages: [{ role: 'user', content: message }],
      max_tokens: 50,
    })
    return response.data
  },
}
