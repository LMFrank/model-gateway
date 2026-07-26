import type { ProviderType } from './provider'

export interface RouteModelInfo {
  id: number
  display_name: string
  upstream_model: string
  is_active: boolean
}

export interface RouteProviderInfo {
  id: number
  name: string
  provider_type: ProviderType
}

export interface RouteRule {
  model_key: string
  is_enabled: boolean
  priority: number
  description: string | null
  fallback_provider: string | null
  fallback_model_key: string | null
  created_at: string | null
  updated_at: string | null
  model: RouteModelInfo | null
  provider: RouteProviderInfo | null
}

export interface UpsertRouteRequest {
  model_key: string
  is_enabled?: boolean
  priority?: number
  description?: string
  fallback_provider?: string | null
  fallback_model_key?: string | null
}
