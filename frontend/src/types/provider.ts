import type { JsonObject } from './common'

export type ProviderType = 'cli' | 'api'

export interface Provider {
  id: number
  name: string
  display_name: string
  provider_type: ProviderType
  base_url: string | null
  api_key: string | null
  masked_api_key: string | null
  has_api_key: boolean
  config: JsonObject
  description: string | null
  is_enabled: boolean
  created_at: string | null
  updated_at: string | null
}

export interface ProviderInfo {
  id: number
  name: string
  display_name: string
}

export interface CreateProviderRequest {
  name: string
  display_name: string
  provider_type: ProviderType
  base_url?: string
  api_key?: string
  config?: JsonObject
  description?: string
  is_enabled?: boolean
}

export interface UpdateProviderRequest {
  display_name?: string
  provider_type?: ProviderType
  base_url?: string
  api_key?: string
  config?: JsonObject
  description?: string
  is_enabled?: boolean
}
