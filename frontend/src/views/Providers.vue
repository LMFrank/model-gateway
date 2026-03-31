<template>
  <div class="providers-page">
    <div class="page-header">
      <h1>Provider 管理</h1>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon>新增 Provider
      </el-button>
    </div>

    <el-table :data="providers" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="名称" width="150" />
      <el-table-column prop="display_name" label="显示名称" width="180" />
      <el-table-column prop="provider_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.provider_type === 'cli' ? 'success' : 'primary'">
            {{ row.provider_type === 'cli' ? 'CLI' : 'API' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="base_url" label="Base URL" show-overflow-tooltip />
      <el-table-column prop="is_enabled" label="状态" width="100">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_enabled"
            @change="handleStatusChange(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button type="success" size="small" @click="handleHealthCheck(row)" :loading="row._checking">
            健康检查
          </el-button>
          <el-button type="primary" size="small" @click="showEditDialog(row)">
            编辑
          </el-button>
          <el-button type="danger" size="small" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑 Provider' : '新增 Provider'"
      width="600px"
    >
      <el-form :model="form" label-width="120px" :rules="rules" ref="formRef">
        <el-form-item label="名称" prop="name" v-if="!isEdit">
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
        <el-form-item label="Base URL" v-if="form.provider_type === 'api'">
          <el-input v-model="form.base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="API Key" v-if="form.provider_type === 'api'">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="API Key"
          />
        </el-form-item>
        <el-form-item label="配置(JSON)">
          <el-input
            v-model="configJson"
            type="textarea"
            :rows="5"
            placeholder='{"timeout_sec": 120, "upstream_model": "model-name"}'
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="Provider 描述"
          />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { providersApi, type Provider, type CreateProviderRequest } from '@/api/providers'

const providers = ref<Provider[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref()

const form = ref<CreateProviderRequest>({
  name: '',
  display_name: '',
  provider_type: 'api',
  base_url: '',
  api_key: '',
  config: {},
  description: '',
  is_enabled: true,
})

const configJson = computed({
  get: () => JSON.stringify(form.value.config || {}, null, 2),
  set: (val: string) => {
    try {
      form.value.config = JSON.parse(val)
    } catch {
      // Invalid JSON, ignore
    }
  },
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  provider_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
}

const fetchProviders = async () => {
  loading.value = true
  try {
    providers.value = await providersApi.list()
  } catch (error) {
    ElMessage.error('获取 Provider 列表失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  form.value = {
    name: '',
    display_name: '',
    provider_type: 'api',
    base_url: '',
    api_key: '',
    config: {},
    description: '',
    is_enabled: true,
  }
  dialogVisible.value = true
}

const showEditDialog = (row: Provider) => {
  isEdit.value = true
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
  
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (isEdit.value) {
        const row = providers.value.find(p => p.name === form.value.name)
        if (row) {
          await providersApi.update(row.id, form.value)
          ElMessage.success('更新成功')
        }
      } else {
        await providersApi.create(form.value)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      await fetchProviders()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleStatusChange = async (row: Provider) => {
  try {
    await providersApi.update(row.id, { is_enabled: row.is_enabled })
    ElMessage.success('状态更新成功')
  } catch (error) {
    ElMessage.error('状态更新失败')
    row.is_enabled = !row.is_enabled
  }
}

const handleDelete = async (row: Provider) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 Provider "${row.display_name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    await providersApi.delete(row.id)
    ElMessage.success('删除成功')
    await fetchProviders()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleHealthCheck = async (row: Provider & { _checking?: boolean }) => {
  row._checking = true
  try {
    const result = await providersApi.healthCheck(row.id)
    if (result.status === 'healthy') {
      ElMessage.success(`${row.display_name} 健康检查通过 (${result.latency_ms}ms)`)
    } else {
      ElMessage.warning(`${row.display_name} 健康检查异常: ${result.error_message || result.status}`)
    }
  } catch (error: any) {
    ElMessage.error(`健康检查失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    row._checking = false
  }
}

onMounted(fetchProviders)
</script>

<style scoped>
.providers-page {
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
