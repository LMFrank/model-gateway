import { defineStore } from 'pinia'
import { routesApi } from '@/api/routes'
import type { RouteRule, UpsertRouteRequest } from '@/types'

interface RoutesState {
  items: RouteRule[]
  loading: boolean
  submitting: boolean
}

export const useRoutesStore = defineStore('routes', {
  state: (): RoutesState => ({
    items: [],
    loading: false,
    submitting: false,
  }),

  actions: {
    async fetchAll() {
      this.loading = true
      try {
        this.items = await routesApi.list()
      } finally {
        this.loading = false
      }
    },

    async upsert(payload: UpsertRouteRequest) {
      this.submitting = true
      try {
        await routesApi.update(payload)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async remove(modelKey: string) {
      this.submitting = true
      try {
        await routesApi.delete(modelKey)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },
  },
})
