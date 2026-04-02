export interface UsageGroupItem {
  call_count: number
  failed_calls: number
  failure_rate: number
  total_tokens: number
  p95_latency_ms: number | null
}

export interface UsageByModelItem extends UsageGroupItem {
  model_name: string
}

export interface UsageByProviderItem extends UsageGroupItem {
  provider_name: string
}

export interface UsageSummary {
  date_from: string
  date_to: string
  total_calls: number
  failed_calls: number
  failure_rate: number
  total_tokens: number
  p95_latency_ms: number | null
  by_model: UsageByModelItem[]
  by_provider: UsageByProviderItem[]
}
