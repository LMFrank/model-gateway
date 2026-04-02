import { defineStore } from 'pinia'
import { modelsApi } from '@/api/models'
import type { CreateModelRequest, Model, ModelHealthCheck, UpdateModelRequest } from '@/types'

interface ModelsState {
  items: Model[]
  loading: boolean
  submitting: boolean
}

export const useModelsStore = defineStore('models', {
  state: (): ModelsState => ({
    items: [],
    loading: false,
    submitting: false,
  }),

  actions: {
    async fetchAll(providerId?: number) {
      this.loading = true
      try {
        this.items = await modelsApi.list(providerId)
      } finally {
        this.loading = false
      }
    },

    async create(payload: CreateModelRequest) {
      this.submitting = true
      try {
        await modelsApi.create(payload)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async update(id: number, payload: UpdateModelRequest) {
      this.submitting = true
      try {
        await modelsApi.update(id, payload)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async remove(id: number) {
      this.submitting = true
      try {
        await modelsApi.delete(id)
        await this.fetchAll()
      } finally {
        this.submitting = false
      }
    },

    async toggleActive(row: Model) {
      await this.update(row.id, { is_active: !row.is_active })
    },

    async checkHealth(id: number): Promise<ModelHealthCheck> {
      return modelsApi.healthCheck(id)
    },
  },
})
