<template>
  <div class="usage-page">
    <div class="page-header">
      <h1>使用量统计</h1>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="fetchUsage"
      />
    </div>

    <el-row :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ usageData.total_calls || 0 }}</div>
            <div class="stat-label">总调用次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ usageData.failed_calls || 0 }}</div>
            <div class="stat-label">失败次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ formatRate(usageData.failure_rate) }}</div>
            <div class="stat-label">失败率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-item">
            <div class="stat-value">{{ usageData.total_tokens || 0 }}</div>
            <div class="stat-label">总 Token 数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="detail-card">
      <template #header>
        <span>按模型统计</span>
      </template>
      <el-table :data="usageData.by_model || []" style="width: 100%">
        <el-table-column prop="model_name" label="模型" />
        <el-table-column prop="call_count" label="调用次数" width="120" />
        <el-table-column prop="failed_calls" label="失败次数" width="120" />
        <el-table-column prop="failure_rate" label="失败率" width="120">
          <template #default="{ row }">
            {{ formatRate(row.failure_rate) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_tokens" label="Token 数" width="150" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '@/api/client'

const dateRange = ref<[Date, Date] | null>(null)
const usageData = ref<any>({})

const fetchUsage = async () => {
  try {
    const params: any = {}
    if (dateRange.value) {
      params.date_from = dateRange.value[0].toISOString().split('T')[0]
      params.date_to = dateRange.value[1].toISOString().split('T')[0]
    }
    const response = await client.get('/admin/usage/summary', { params })
    usageData.value = response.data
  } catch (error) {
    ElMessage.error('获取使用量统计失败')
  }
}

const formatRate = (rate: number) => {
  if (rate === undefined || rate === null) return '0%'
  return `${(rate * 100).toFixed(2)}%`
}

onMounted(() => {
  // Default to last 7 days
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 6)
  dateRange.value = [start, end]
  fetchUsage()
})
</script>

<style scoped>
.usage-page {
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

.summary-row {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.detail-card {
  margin-top: 20px;
}
</style>
