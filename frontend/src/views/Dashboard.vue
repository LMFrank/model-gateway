<template>
  <section class="dashboard-page mg-page">
    <h1 class="mg-page-title">Model Gateway 概览</h1>

    <el-row :gutter="uiLayoutTokens.gridGutter" class="stats-row">
      <el-col :xs="12" :md="6">
        <el-card>
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ stats.providers }}</div>
            <div class="mg-stat-label">Providers</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card>
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ stats.models }}</div>
            <div class="mg-stat-label">模型</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card>
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ stats.routes }}</div>
            <div class="mg-stat-label">路由规则</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card>
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ stats.healthyModels }}</div>
            <div class="mg-stat-label">健康模型</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="quick-card">
      <template #header>快速导航</template>
      <el-row :gutter="uiLayoutTokens.gridGutter">
        <el-col :xs="12" :md="6">
          <el-button class="full-width" type="primary" @click="go('/providers')">Provider 管理</el-button>
        </el-col>
        <el-col :xs="12" :md="6">
          <el-button class="full-width" type="success" @click="go('/models')">模型管理</el-button>
        </el-col>
        <el-col :xs="12" :md="6">
          <el-button class="full-width" type="warning" @click="go('/routes')">路由规则</el-button>
        </el-col>
        <el-col :xs="12" :md="6">
          <el-button class="full-width" type="info" @click="go('/usage')">使用量统计</el-button>
        </el-col>
      </el-row>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useModelsStore } from '@/stores/models'
import { useProvidersStore } from '@/stores/providers'
import { useRoutesStore } from '@/stores/routes'
import { extractErrorMessage } from '@/stores/helpers'
import { uiLayoutTokens } from '@/ui/designTokens'

const router = useRouter()
const providersStore = useProvidersStore()
const modelsStore = useModelsStore()
const routesStore = useRoutesStore()

const stats = computed(() => ({
  providers: providersStore.items.length,
  models: modelsStore.items.length,
  routes: routesStore.items.length,
  healthyModels: modelsStore.items.filter((item) => item.health_status === 'healthy').length,
}))

const go = (path: string) => {
  void router.push(path)
}

onMounted(async () => {
  try {
    await Promise.all([providersStore.fetchAll(), modelsStore.fetchAll(), routesStore.fetchAll()])
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取概览数据失败'))
  }
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 0;
}

.stat-value {
  font-size: var(--mg-font-size-stat-lg);
}

.quick-card {
  margin-top: 0;
}

.full-width {
  width: 100%;
}
</style>
