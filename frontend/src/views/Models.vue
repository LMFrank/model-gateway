<template>
  <section class="models-page mg-page">
    <div class="page-header mg-page-header">
      <h1 class="mg-page-title">模型管理</h1>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        新增模型
      </el-button>
    </div>

    <el-card class="table-card mg-table-card">
      <el-table :data="modelsStore.items" v-loading="modelsStore.loading" row-key="id">
        <el-table-column
          prop="model_key"
          label="Model Key"
          :min-width="uiTableTokens.models.modelKeyMinWidth"
        />
        <el-table-column
          prop="display_name"
          label="显示名称"
          :min-width="uiTableTokens.models.displayNameMinWidth"
        />
        <el-table-column
          prop="upstream_model"
          label="上游模型"
          :min-width="uiTableTokens.models.upstreamModelMinWidth"
        />
        <el-table-column label="Provider" :min-width="uiTableTokens.models.providerMinWidth">
          <template #default="{ row }">
            <el-tag size="small">{{ row.provider?.name || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="健康状态" :width="uiTableTokens.models.healthWidth">
          <template #default="{ row }">
            <el-tag :type="getHealthTagType(row.health_status)" effect="light">
              {{ getHealthLabel(row.health_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" :width="uiTableTokens.models.statusWidth">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" @change="onStatusChange(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" :width="uiTableTokens.models.actionsWidth">
          <template #default="{ row }">
            <div class="action-group">
              <el-button
                type="success"
                size="small"
                :loading="checkingModelId === row.id"
                @click="handleTest(row)"
              >
                测试
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
      :title="isEdit ? '编辑模型' : '新增模型'"
      :width="uiLayoutTokens.dialogWidth"
    >
      <el-form
        ref="formRef"
        :model="form"
        :label-width="uiLayoutTokens.formLabelWidth"
        :rules="rules"
      >
        <el-form-item v-if="!isEdit" label="Model Key" prop="model_key">
          <el-input v-model="form.model_key" placeholder="唯一标识符，如 qwen3-max" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="上游模型" prop="upstream_model">
          <el-input v-model="form.upstream_model" placeholder="上游 Provider 使用的模型名" />
        </el-form-item>
        <el-form-item label="Provider" prop="provider_id">
          <el-select v-model="form.provider_id" placeholder="选择 Provider" class="full-width">
            <el-option
              v-for="provider in providersStore.items"
              :key="provider.id"
              :label="provider.display_name"
              :value="provider.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="默认参数(JSON)">
          <el-input
            v-model="paramsJson"
            type="textarea"
            :rows="uiFormTokens.modelParamsRows"
            placeholder='{"temperature": 0.7}'
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="uiFormTokens.shortTextareaRows" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="uiFormTokens.shortTextareaRows" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="modelsStore.submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useModelsStore } from '@/stores/models'
import { useProvidersStore } from '@/stores/providers'
import { extractErrorMessage } from '@/stores/helpers'
import { uiFormTokens, uiLayoutTokens, uiTableTokens } from '@/ui/designTokens'
import type { CreateModelRequest, HealthStatus, Model } from '@/types'

const modelsStore = useModelsStore()
const providersStore = useProvidersStore()

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const checkingModelId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const buildDefaultForm = (): CreateModelRequest => ({
  provider_id: 0,
  model_key: '',
  display_name: '',
  upstream_model: '',
  default_params: {},
  description: '',
  notes: '',
  is_active: true,
})

const form = ref<CreateModelRequest>(buildDefaultForm())

const paramsJson = computed({
  get: () => JSON.stringify(form.value.default_params || {}, null, 2),
  set: (raw: string) => {
    try {
      form.value.default_params = JSON.parse(raw)
    } catch {
      // 忽略不完整 JSON，提交前会校验必填字段
    }
  },
})

const rules: FormRules = {
  model_key: [{ required: true, message: '请输入 Model Key', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  upstream_model: [{ required: true, message: '请输入上游模型', trigger: 'blur' }],
  provider_id: [{ required: true, message: '请选择 Provider', trigger: 'change' }],
}

const getHealthTagType = (status: HealthStatus) => {
  if (status === 'healthy') return 'success'
  if (status === 'unhealthy') return 'danger'
  return 'info'
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

const openEditDialog = (row: Model) => {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    provider_id: row.provider?.id || 0,
    model_key: row.model_key,
    display_name: row.display_name,
    upstream_model: row.upstream_model,
    default_params: row.default_params || {},
    description: row.description || '',
    notes: row.notes || '',
    is_active: row.is_active,
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
      await modelsStore.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await modelsStore.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, isEdit.value ? '更新失败' : '创建失败'))
  }
}

const handleStatusChange = async (row: Model, nextValue: boolean) => {
  try {
    await modelsStore.update(row.id, { is_active: nextValue })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '状态更新失败'))
  }
}

const onStatusChange = (row: Model, value: string | number | boolean) => {
  void handleStatusChange(row, Boolean(value))
}

const handleDelete = async (row: Model) => {
  try {
    await ElMessageBox.confirm(`确定要删除模型 "${row.display_name}" 吗？`, '确认删除', {
      type: 'warning',
    })
    await modelsStore.remove(row.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(extractErrorMessage(error, '删除失败'))
    }
  }
}

const handleTest = async (row: Model) => {
  checkingModelId.value = row.id
  try {
    const result = await modelsStore.checkHealth(row.id)
    if (result.status === 'healthy') {
      ElMessage.success(`测试成功：${row.display_name} 状态已更新为健康`)
    } else if (result.status === 'unhealthy') {
      ElMessage.error(`测试失败：${result.error_message || '请求异常'}`)
    } else {
      ElMessage.warning(`测试完成：当前状态为 ${getHealthLabel(result.status)}`)
    }
    await modelsStore.fetchAll()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '测试失败'))
  } finally {
    checkingModelId.value = null
  }
}

onMounted(async () => {
  try {
    await Promise.all([providersStore.fetchAll(), modelsStore.fetchAll()])
  } catch (error) {
    ElMessage.error(extractErrorMessage(error, '获取数据失败'))
  }
})
</script>

<style scoped>
.action-group {
  display: inline-flex;
  align-items: center;
  gap: var(--mg-space-1);
}

.full-width {
  width: 100%;
}
</style>
