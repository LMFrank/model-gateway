import { defineStore } from 'pinia'
import { providersApi } from '@/api/providers'
import type { CreateProviderRequest, Provider, ProviderHealthCheck, UpdateProviderRequest } from '@/types'

interface ProvidersState {
  items: Provider[]
  loading: boolean
  submitting: boolean
}

export const useProvidersStore = defineStore('providers', {
  state: (): ProvidersState => ({
    items: [],
    loading: false,
    submitting: false,
  }),

  actions: {
    async fetchAll() {
      this.loading = true
      try {
        this.items = await providersApi.list()
      } finally {
        this.loading = false
      }
    },

    async create(payload: CreateProviderRequest) {
      this.submitting = true
      try {
        await providersApi.create(payload)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async update(id: number, payload: UpdateProviderRequest) {
      this.submitting = true
      try {
        await providersApi.update(id, payload)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async remove(id: number) {
      this.submitting = true
      try {
        await providersApi.delete(id)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async toggleEnabled(row: Provider) {
      const next = !row.is_enabled
      await this.update(row.id, { is_enabled: next })
    },

    async checkHealth(id: number): Promise<ProviderHealthCheck> {
      return providersApi.healthCheck(id)
    },
  },
})
