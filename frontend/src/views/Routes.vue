<template>
  <section class="routes-page mg-page">
    <div class="page-header mg-page-header">
      <h1 class="mg-page-title">路由规则</h1>
    </div>

    <el-card class="table-card mg-table-card">
      <el-table :data="routesStore.items" v-loading="routesStore.loading" row-key="model_key">
        <el-table-column
          prop="model_key"
          label="Model Key"
          :min-width="uiTableTokens.routes.modelKeyMinWidth"
        />
        <el-table-column label="模型名称" :min-width="uiTableTokens.routes.modelNameMinWidth">
          <template #default="{ row }">
            {{ row.model?.display_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Provider" :min-width="uiTableTokens.routes.providerMinWidth">
          <template #default="{ row }">
            <el-tag size="small" :type="row.provider?.provider_type === 'cli' ? 'success' : 'primary'">
              {{ row.provider?.name || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" :width="uiTableTokens.routes.priorityWidth" />
        <el-table-column label="状态" :width="uiTableTokens.routes.statusWidth">
          <template #default="{ row }">
            <el-switch :model-value="row.is_enabled" @change="onStatusChange(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column
          prop="description"
          label="描述"
          :min-width="uiTableTokens.routes.descriptionMinWidth"
          show-overflow-tooltip
        />
      </el-table>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoutesStore } from '@/stores/routes'
import { extractErrorMessage } from '@/stores/helpers'
import { uiTableTokens } from '@/ui/designTokens'
import type { RouteRule } from '@/types'

const routesStore = useRoutesStore()

const handleStatusChange = async (row: RouteRule, nextValue: boolean) => {
  try {
    await routesStore.upsert({
      model_key: row.model_key,
      is_enabled: nextValue,
      priority: row.priority,
      description: row.description || undefined,
    })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '状态更新失败'))
  }
}

const onStatusChange = (row: RouteRule, value: string | number | boolean) => {
  void handleStatusChange(row, Boolean(value))
}

onMounted(async () => {
  try {
    await routesStore.fetchAll()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取路由规则失败'))
  }
})
</script>

<style scoped>
.page-header {
  margin-bottom: var(--mg-space-4);
}
</style>
