<template>
  <div class="dashboard-page">
    <h1>Model Gateway 概览</h1>
    
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ stats.providers }}</div>
            <div class="stat-label">Providers</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ stats.models }}</div>
            <div class="stat-label">模型</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ stats.routes }}</div>
            <div class="stat-label">路由规则</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ stats.healthyModels }}</div>
            <div class="stat-label">健康模型</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-card">
      <template #header>
        <span>快速导航</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6">
          <el-button type="primary" @click="$router.push('/providers')" style="width: 100%">
            Provider 管理
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button type="success" @click="$router.push('/models')" style="width: 100%">
            模型管理
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button type="warning" @click="$router.push('/routes')" style="width: 100%">
            路由规则
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button type="info" @click="$router.push('/usage')" style="width: 100%">
            使用量统计
          </el-button>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { providersApi } from '@/api/providers'
import { modelsApi } from '@/api/models'
import { routesApi } from '@/api/routes'

const stats = ref({
  providers: 0,
  models: 0,
  routes: 0,
  healthyModels: 0,
})

const fetchStats = async () => {
  try {
    const [providers, models, routes] = await Promise.all([
      providersApi.list(),
      modelsApi.list(),
      routesApi.list(),
    ])
    stats.value = {
      providers: providers.length,
      models: models.length,
      routes: routes.length,
      healthyModels: models.filter(m => m.health_status === 'healthy').length,
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.dashboard-page {
  padding: 20px;
}

.dashboard-page h1 {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #409EFF;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.recent-card {
  margin-top: 20px;
}
</style>
