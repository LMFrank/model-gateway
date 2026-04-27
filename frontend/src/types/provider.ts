export type ProviderType = 'cli' | 'api'

export interface ApiRuntimeConfig {
  [key: string]: unknown
  timeout_sec?: number
  connect_retries?: number
  retry_backoff_sec?: number
  chat_endpoint?: string
  upstream_model?: string
}

export interface CliRuntimeConfig {
  [key: string]: unknown
  timeout_sec?: number
  command?: string
  args?: string[]
  extra_args?: string[]
  model_arg?: string
  prompt_arg?: string
  stream_arg?: string
  stdin_prompt_arg?: string
  response_file?: string
  upstream_model?: string
  use_stdin_prompt?: boolean
  force_stdin_prompt?: boolean
}

export type ProviderRuntimeConfig = ApiRuntimeConfig | CliRuntimeConfig

export interface Provider {
  id: number
  name: string
  display_name: string
  provider_type: ProviderType
  base_url: string | null
  api_key: string | null
  masked_api_key: string | null
  has_api_key: boolean
  config: Record<string, unknown>
  runtime_config: ProviderRuntimeConfig
  runtime_config_extras: Record<string, unknown>
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
  config?: Record<string, unknown>
  runtime_config?: ProviderRuntimeConfig
  runtime_config_extras?: Record<string, unknown>
  description?: string
  is_enabled?: boolean
}

export interface UpdateProviderRequest {
  display_name?: string
  provider_type?: ProviderType
  base_url?: string
  api_key?: string
  config?: Record<string, unknown>
  runtime_config?: ProviderRuntimeConfig
  runtime_config_extras?: Record<string, unknown>
  description?: string
  is_enabled?: boolean
}
