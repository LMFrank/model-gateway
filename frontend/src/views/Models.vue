<template>
  <div class="models-page">
    <div class="page-header">
      <h1>模型管理</h1>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>新增模型
      </el-button>
    </div>

    <el-table :data="models" v-loading="loading" style="width: 100%">
      <el-table-column prop="model_key" label="Model Key" width="180" />
      <el-table-column prop="display_name" label="显示名称" width="180" />
      <el-table-column prop="upstream_model" label="上游模型" width="180" />
      <el-table-column prop="provider.name" label="Provider" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.provider?.name || '-' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="health_status" label="健康状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getHealthType(row.health_status)">
            {{ getHealthLabel(row.health_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="100">
        <template #default="{ row }">
          <el-switch v-model="row.is_active" @change="handleStatusChange(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button type="success" size="small" @click="handleTest(row)" :loading="row._testing">
            测试
          </el-button>
          <el-button type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑模型' : '新增模型'" width="600px">
      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
        <el-form-item label="Model Key" prop="model_key" v-if="!isEdit">
          <el-input v-model="form.model_key" placeholder="唯一标识符，如 qwen3.5-plus" />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item label="上游模型" prop="upstream_model">
          <el-input v-model="form.upstream_model" placeholder="上游 Provider 使用的模型名" />
        </el-form-item>
        <el-form-item label="Provider" prop="provider_id">
          <el-select v-model="form.provider_id" placeholder="选择 Provider" style="width: 100%">
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="p.display_name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="默认参数(JSON)">
          <el-input v-model="paramsJson" type="textarea" :rows="4" placeholder='{"temperature": 0.7}' />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { modelsApi, type Model, type CreateModelRequest } from '@/api/models'
import { providersApi, type Provider } from '@/api/providers'

const models = ref<Model[]>([])
const providers = ref<Provider[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const form = ref<CreateModelRequest>({
  provider_id: 0,
  model_key: '',
  display_name: '',
  upstream_model: '',
  default_params: {},
  description: '',
  notes: '',
  is_active: true,
})

const paramsJson = computed({
  get: () => JSON.stringify(form.value.default_params || {}, null, 2),
  set: (val: string) => {
    try {
      form.value.default_params = JSON.parse(val)
    } catch {}
  },
})

const rules = {
  model_key: [{ required: true, message: '请输入 Model Key', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  upstream_model: [{ required: true, message: '请输入上游模型', trigger: 'blur' }],
  provider_id: [{ required: true, message: '请选择 Provider', trigger: 'change' }],
}

const getHealthType = (status: string) => {
  const map: Record<string, any> = { healthy: 'success', unhealthy: 'danger', unknown: 'info' }
  return map[status] || 'info'
}

const getHealthLabel = (status: string) => {
  const map: Record<string, string> = { healthy: '健康', unhealthy: '异常', unknown: '未知' }
  return map[status] || status
}

const fetchData = async () => {
  loading.value = true
  try {
    const [modelsData, providersData] = await Promise.all([
      modelsApi.list(),
      providersApi.list(),
    ])
    models.value = modelsData
    providers.value = providersData
  } catch (error) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  form.value = {
    provider_id: 0,
    model_key: '',
    display_name: '',
    upstream_model: '',
    default_params: {},
    description: '',
    notes: '',
    is_active: true,
  }
  dialogVisible.value = true
}

const showEditDialog = (row: Model) => {
  isEdit.value = true
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
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        const row = models.value.find(m => m.model_key === form.value.model_key)
        if (row) {
          await modelsApi.update(row.id, form.value)
          ElMessage.success('更新成功')
        }
      } else {
        await modelsApi.create(form.value)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      await fetchData()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleStatusChange = async (row: Model) => {
  try {
    await modelsApi.update(row.id, { is_active: row.is_active })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error('状态更新失败')
    row.is_active = !row.is_active
  }
}

const handleDelete = async (row: Model) => {
  try {
    await ElMessageBox.confirm(`确定要删除模型 "${row.display_name}" 吗？`, '确认删除', { type: 'warning' })
    await modelsApi.delete(row.id)
    ElMessage.success('删除成功')
    await fetchData()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleTest = async (row: Model & { _testing?: boolean }) => {
  row._testing = true
  try {
    const result = await modelsApi.test(row.model_key)
    const content = result.choices?.[0]?.message?.content || '无响应内容'
    ElMessage.success(`测试成功: ${content.slice(0, 50)}${content.length > 50 ? '...' : ''}`)
    await fetchData()
  } catch (error: any) {
    const detail = error.response?.data?.detail || error.message
    ElMessage.error(`测试失败: ${detail}`)
  } finally {
    row._testing = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.models-page {
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
