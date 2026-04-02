import client from './client'
import type { UsageSummary } from '@/types'

export interface UsageQuery {
  date_from?: string
  date_to?: string
}

export const usageApi = {
  async summary(params: UsageQuery = {}): Promise<UsageSummary> {
    const response = await client.get<UsageSummary>('/admin/usage/summary', { params })
    return response.data
  },
}
