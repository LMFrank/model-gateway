<template>
  <section class="usage-page mg-page">
    <div class="page-header mg-page-header">
      <h1 class="mg-page-title">使用量统计</h1>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        unlink-panels
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="refreshUsage"
      />
    </div>

    <el-row :gutter="uiLayoutTokens.gridGutter" class="summary-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="summary-card">
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ summary.total_calls }}</div>
            <div class="mg-stat-label">总调用次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="summary-card">
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ summary.failed_calls }}</div>
            <div class="mg-stat-label">失败次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="summary-card">
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ formatRate(summary.failure_rate) }}</div>
            <div class="mg-stat-label">失败率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card class="summary-card">
          <div class="mg-stat-item">
            <div class="stat-value mg-stat-value">{{ summary.total_tokens }}</div>
            <div class="mg-stat-label">总 Token 数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="uiLayoutTokens.gridGutter">
      <el-col :xs="24" :lg="14">
        <el-card class="detail-card" v-loading="usageStore.loading">
          <template #header>按模型统计</template>
          <el-table :data="summary.by_model" row-key="model_name">
            <el-table-column
              prop="model_name"
              label="模型"
              :min-width="uiTableTokens.usage.modelNameMinWidth"
            />
            <el-table-column prop="call_count" label="调用次数" :width="uiTableTokens.usage.metricWidth" />
            <el-table-column
              prop="failed_calls"
              label="失败次数"
              :width="uiTableTokens.usage.metricWidth"
            />
            <el-table-column label="失败率" :width="uiTableTokens.usage.metricWidth">
              <template #default="{ row }">
                {{ formatRate(row.failure_rate) }}
              </template>
            </el-table-column>
            <el-table-column prop="total_tokens" label="Token 数" :width="uiTableTokens.usage.tokenWidth" />
            <el-table-column
              prop="p95_latency_ms"
              label="P95 延迟(ms)"
              :width="uiTableTokens.usage.latencyWidth"
            />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card class="detail-card" v-loading="usageStore.loading">
          <template #header>按 Provider 统计</template>
          <el-table :data="summary.by_provider" row-key="provider_name">
            <el-table-column
              prop="provider_name"
              label="Provider"
              :min-width="uiTableTokens.usage.providerMinWidth"
            />
            <el-table-column
              prop="call_count"
              label="调用"
              :width="uiTableTokens.usage.compactMetricWidth"
            />
            <el-table-column
              prop="failed_calls"
              label="失败"
              :width="uiTableTokens.usage.compactMetricWidth"
            />
            <el-table-column label="失败率" :width="uiTableTokens.usage.compactRateWidth">
              <template #default="{ row }">
                {{ formatRate(row.failure_rate) }}
              </template>
            </el-table-column>
            <el-table-column prop="p95_latency_ms" label="P95" :width="uiTableTokens.usage.compactMetricWidth" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useUsageStore } from '@/stores/usage'
import { extractErrorMessage } from '@/stores/helpers'
import { uiLayoutTokens, uiTableTokens } from '@/ui/designTokens'
import type { UsageSummary } from '@/types'

const usageStore = useUsageStore()
const dateRange = ref<[Date, Date] | null>(null)

const emptySummary: UsageSummary = {
  date_from: '',
  date_to: '',
  total_calls: 0,
  failed_calls: 0,
  failure_rate: 0,
  total_tokens: 0,
  p95_latency_ms: null,
  by_model: [],
  by_provider: [],
}

const summary = computed<UsageSummary>(() => usageStore.summary || emptySummary)

const formatRate = (rate: number): string => `${(rate * 100).toFixed(2)}%`

const refreshUsage = async () => {
  try {
    const dateFrom = dateRange.value?.[0]?.toISOString().split('T')[0]
    const dateTo = dateRange.value?.[1]?.toISOString().split('T')[0]
    await usageStore.fetchSummary(dateFrom, dateTo)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取使用量统计失败'))
  }
}

onMounted(async () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 6)
  dateRange.value = [start, end]
  await refreshUsage()
})
</script>

<style scoped>
.summary-row {
  margin-bottom: 0;
}

.summary-card {
  margin-bottom: var(--mg-space-3);
}

.stat-value {
  font-size: var(--mg-font-size-stat-md);
}

.detail-card {
  margin-bottom: var(--mg-space-3);
}
</style>
