<template>
  <section class="providers-page mg-page">
    <div class="page-header mg-page-header">
      <h1 class="mg-page-title">Provider 管理</h1>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新增 Provider
      </el-button>
    </div>

    <el-card class="table-card mg-table-card">
      <el-table :data="providersStore.items" v-loading="providersStore.loading" row-key="id">
        <el-table-column prop="name" label="名称" :min-width="uiTableTokens.providers.nameMinWidth" />
        <el-table-column
          prop="display_name"
          label="显示名称"
          :min-width="uiTableTokens.providers.displayNameMinWidth"
        />
        <el-table-column prop="provider_type" label="类型" :width="uiTableTokens.providers.typeWidth">
          <template #default="{ row }">
            <el-tag :type="row.provider_type === 'cli' ? 'success' : 'primary'" effect="light">
              {{ row.provider_type === 'cli' ? 'CLI' : 'API' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="base_url"
          label="Base URL"
          :min-width="uiTableTokens.providers.baseUrlMinWidth"
          show-overflow-tooltip
        />
        <el-table-column label="状态" :width="uiTableTokens.providers.statusWidth">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_enabled"
              :loading="providersStore.submitting"
              @change="onStatusChange(row, $event)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" :width="uiTableTokens.providers.actionsWidth">
          <template #default="{ row }">
            <div class="action-group">
              <el-button
                type="success"
                size="small"
                :loading="checkingProviderId === row.id"
                @click="handleHealthCheck(row)"
              >
                健康检查
              </el-button>
              <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 Provider' : '新增 Provider'"
      :width="uiLayoutTokens.dialogWidth"
    >
      <el-form
        ref="formRef"
        :model="form"
        :label-width="uiLayoutTokens.formLabelWidth"
        :rules="rules"
      >
        <el-form-item v-if="!isEdit" label="名称" prop="name">
          <el-input v-model="form.name" placeholder="唯一标识符，如 qwen_api" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称，如 Qwen API" />
        </el-form-item>
        <el-form-item label="类型" prop="provider_type">
          <el-radio-group v-model="form.provider_type">
            <el-radio label="api">API</el-radio>
            <el-radio label="cli">CLI</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.provider_type === 'api'" label="Base URL">
          <el-input v-model="form.base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item v-if="form.provider_type === 'api'" label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="API Key" />
        </el-form-item>
        <el-form-item label="配置(JSON)">
          <el-input
            v-model="configJson"
            type="textarea"
            :rows="uiFormTokens.providerConfigRows"
            placeholder='{"timeout_sec": 120, "upstream_model": "model-name"}'
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="uiFormTokens.shortTextareaRows"
            placeholder="Provider 描述"
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="providersStore.submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useProvidersStore } from '@/stores/providers'
import { extractErrorMessage } from '@/stores/helpers'
import { uiFormTokens, uiLayoutTokens, uiTableTokens } from '@/ui/designTokens'
import type { CreateProviderRequest, HealthStatus, Provider } from '@/types'

const providersStore = useProvidersStore()

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const checkingProviderId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const buildDefaultForm = (): CreateProviderRequest => ({
  name: '',
  display_name: '',
  provider_type: 'api',
  base_url: '',
  api_key: '',
  config: {},
  description: '',
  is_enabled: true,
})

const form = ref<CreateProviderRequest>(buildDefaultForm())

const configJson = computed({
  get: () => JSON.stringify(form.value.config || {}, null, 2),
  set: (raw: string) => {
    try {
      form.value.config = JSON.parse(raw)
    } catch {
      // 忽略不完整 JSON，提交前会再次校验
    }
  },
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  provider_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

const getHealthLabel = (status: HealthStatus) => {
  if (status === 'healthy') return '健康'
  if (status === 'unhealthy') return '异常'
  return '未知'
}

const openCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  form.value = buildDefaultForm()
  dialogVisible.value = true
}

const openEditDialog = (row: Provider) => {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    name: row.name,
    display_name: row.display_name,
    provider_type: row.provider_type,
    base_url: row.base_url || '',
    api_key: row.api_key || '',
    config: row.config || {},
    description: row.description || '',
    is_enabled: row.is_enabled,
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  try {
    if (isEdit.value && editingId.value !== null) {
      await providersStore.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await providersStore.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, isEdit.value ? '更新失败' : '创建失败'))
  }
}

const handleStatusChange = async (row: Provider, nextValue: boolean) => {
  try {
    await providersStore.update(row.id, { is_enabled: nextValue })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '状态更新失败'))
  }
}

const onStatusChange = (row: Provider, value: string | number | boolean) => {
  void handleStatusChange(row, Boolean(value))
}

const handleDelete = async (row: Provider) => {
  try {
    await ElMessageBox.confirm(`确定要删除 Provider "${row.display_name}" 吗？`, '确认删除', {
      type: 'warning',
    })
    await providersStore.remove(row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(extractErrorMessage(error, '删除失败'))
    }
  }
}

const handleHealthCheck = async (row: Provider) => {
  checkingProviderId.value = row.id
  const checkingTip = ElMessage({
    type: 'info',
    message: `${row.display_name} 健康检查进行中，请稍候...`,
    duration: 0,
  })
  try {
    const result = await providersStore.checkHealth(row.id)
    if (result.status === 'healthy') {
      ElMessage.success(`${row.display_name} 健康检查通过 (${result.latency_ms}ms)`)
      return
    }
    const healthLabel = getHealthLabel(result.status)
    const reason = result.error_message?.trim() || `返回状态：${healthLabel}`
    ElMessage.warning(`${row.display_name} 健康检查未通过（${healthLabel}）：${reason}`)
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '健康检查失败'))
  } finally {
    checkingTip.close()
    checkingProviderId.value = null
  }
}

onMounted(async () => {
  try {
    await providersStore.fetchAll()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取 Provider 列表失败'))
  }
})
</script>

<style scoped>
.action-group {
  display: inline-flex;
  align-items: center;
  gap: var(--mg-space-1);
}
</style>
