<template>
  <div class="routes-page">
    <div class="page-header">
      <h1>路由规则</h1>
    </div>

    <el-table :data="routes" v-loading="loading" style="width: 100%">
      <el-table-column prop="model_key" label="Model Key" width="180" />
      <el-table-column prop="model.display_name" label="模型名称" width="180" />
      <el-table-column prop="provider.name" label="Provider" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="row.provider?.provider_type === 'cli' ? 'success' : 'primary'">
            {{ row.provider?.name || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="priority" label="优先级" width="100" />
      <el-table-column prop="is_enabled" label="状态" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.is_enabled" @change="handleStatusChange(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { routesApi, type RouteRule } from '@/api/routes'

const routes = ref<RouteRule[]>([])
const loading = ref(false)

const fetchRoutes = async () => {
  loading.value = true
  try {
    routes.value = await routesApi.list()
  } catch (error) {
    ElMessage.error('获取路由规则失败')
  } finally {
    loading.value = false
  }
}

const handleStatusChange = async (row: RouteRule) => {
  try {
    await routesApi.update({
      model_key: row.model_key,
      is_enabled: row.is_enabled,
      priority: row.priority,
      description: row.description || undefined,
    })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error('状态更新失败')
    row.is_enabled = !row.is_enabled
  }
}

onMounted(fetchRoutes)
</script>

<style scoped>
.routes-page {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h1 {
  margin: 0;
  font-size: 24px;
}
</style>
