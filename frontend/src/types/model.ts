import type { JsonObject } from './common'
import type { ProviderInfo } from './provider'

export type HealthStatus = 'unknown' | 'healthy' | 'unhealthy'

export interface Model {
  id: number
  model_key: string
  display_name: string
  upstream_model: string
  default_params: JsonObject
  description: string | null
  notes: string | null
  is_active: boolean
  health_status: HealthStatus
  last_health_check: string | null
  created_at: string | null
  updated_at: string | null
  provider: ProviderInfo | null
}

export interface CreateModelRequest {
  provider_id: number
  model_key: string
  display_name: string
  upstream_model: string
  default_params?: JsonObject
  description?: string
  notes?: string
  is_active?: boolean
}

export interface UpdateModelRequest {
  provider_id?: number
  display_name?: string
  upstream_model?: string
  default_params?: JsonObject
  description?: string
  notes?: string
  is_active?: boolean
  health_status?: HealthStatus
}
