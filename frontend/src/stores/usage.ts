import { defineStore } from 'pinia'
import { usageApi } from '@/api/usage'
import type { UsageSummary } from '@/types'

interface UsageState {
  summary: UsageSummary | null
  loading: boolean
}

export const useUsageStore = defineStore('usage', {
  state: (): UsageState => ({
    summary: null,
    loading: false,
  }),

  actions: {
    async fetchSummary(dateFrom?: string, dateTo?: string) {
      this.loading = true
      try {
        this.summary = await usageApi.summary({
          date_from: dateFrom,
          date_to: dateTo,
        })
      } finally {
        this.loading = false
      }
    },
  },
})
