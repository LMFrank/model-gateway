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
        <el-table-column label="运行参数" :min-width="uiTableTokens.providers.runtimeConfigMinWidth">
          <template #default="{ row }">
            <div class="runtime-summary">
              <el-tag v-for="item in summarizeRuntimeConfig(row)" :key="item" size="small" effect="plain">
                {{ item }}
              </el-tag>
              <span v-if="summarizeRuntimeConfig(row).length === 0" class="runtime-summary-empty">未配置</span>
            </div>
          </template>
        </el-table-column>
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
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="apiKeyPlaceholder"
          />
          <div v-if="isEdit && currentMaskedApiKey" class="mg-form-help">
            当前已配置密钥：{{ currentMaskedApiKey }}；留空表示不更新。
          </div>
        </el-form-item>

        <el-divider content-position="left">运行参数</el-divider>

        <template v-if="form.provider_type === 'api'">
          <el-form-item label="超时(s)">
            <el-input-number v-model="apiRuntimeForm.timeout_sec" :min="1" :max="3600" />
          </el-form-item>
          <el-form-item label="连接重试次数">
            <el-input-number v-model="apiRuntimeForm.connect_retries" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="重试退避(s)">
            <el-input-number v-model="apiRuntimeForm.retry_backoff_sec" :min="0" :max="60" :step="0.5" />
          </el-form-item>
          <el-form-item label="Chat Endpoint">
            <el-input v-model="apiRuntimeForm.chat_endpoint" placeholder="/chat/completions" />
          </el-form-item>
          <el-form-item label="上游模型名">
            <el-input v-model="apiRuntimeForm.upstream_model" placeholder="glm-5.1-fp8" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="超时(s)">
            <el-input-number v-model="cliRuntimeForm.timeout_sec" :min="1" :max="3600" />
          </el-form-item>
          <el-form-item label="命令">
            <el-input v-model="cliRuntimeForm.command" placeholder="kimi / codex" />
          </el-form-item>
          <el-form-item label="args(逐行)">
            <el-input
              v-model="cliArgsText"
              type="textarea"
              :rows="uiFormTokens.shortTextareaRows + 1"
              placeholder="exec&#10;--skip-git-repo-check"
            />
          </el-form-item>
          <el-form-item label="extra_args(逐行)">
            <el-input
              v-model="cliExtraArgsText"
              type="textarea"
              :rows="uiFormTokens.shortTextareaRows + 1"
              placeholder="--print&#10;--output-format"
            />
          </el-form-item>
          <el-form-item label="model_arg">
            <el-input v-model="cliRuntimeForm.model_arg" placeholder="--model" />
          </el-form-item>
          <el-form-item label="prompt_arg">
            <el-input v-model="cliRuntimeForm.prompt_arg" placeholder="--prompt / -p" />
          </el-form-item>
          <el-form-item label="stream_arg">
            <el-input v-model="cliRuntimeForm.stream_arg" placeholder="--stream" />
          </el-form-item>
          <el-form-item label="stdin_prompt_arg">
            <el-input v-model="cliRuntimeForm.stdin_prompt_arg" placeholder="-" />
          </el-form-item>
          <el-form-item label="response_file">
            <el-input v-model="cliRuntimeForm.response_file" placeholder="/tmp/codex_last_message.txt" />
          </el-form-item>
          <el-form-item label="上游模型名">
            <el-input v-model="cliRuntimeForm.upstream_model" placeholder="gpt-5.4 / kimi-k2.5" />
          </el-form-item>
          <el-form-item label="use_stdin_prompt">
            <el-switch v-model="cliRuntimeForm.use_stdin_prompt" />
          </el-form-item>
          <el-form-item label="force_stdin_prompt">
            <el-switch v-model="cliRuntimeForm.force_stdin_prompt" />
          </el-form-item>
        </template>

        <el-form-item label="高级扩展(JSON)">
          <el-input
            v-model="runtimeExtrasJson"
            type="textarea"
            :rows="uiFormTokens.providerConfigRows"
            placeholder='{"custom_header": "x-demo"}'
          />
          <div class="mg-form-help">
            仅填写未结构化支持的扩展键；已提供表单的字段请优先在上方配置。
          </div>
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
import type {
  ApiRuntimeConfig,
  CliRuntimeConfig,
  CreateProviderRequest,
  HealthStatus,
  JsonObject,
  Provider,
  ProviderRuntimeConfig,
} from '@/types'

const providersStore = useProvidersStore()

const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const checkingProviderId = ref<number | null>(null)
const currentMaskedApiKey = ref<string | null>(null)
const formRef = ref<FormInstance>()
const cliArgsText = ref('')
const cliExtraArgsText = ref('')

const buildDefaultForm = (): CreateProviderRequest => ({
  name: '',
  display_name: '',
  provider_type: 'api',
  base_url: '',
  api_key: '',
  runtime_config: {},
  runtime_config_extras: {},
  description: '',
  is_enabled: true,
})

const form = ref<CreateProviderRequest>(buildDefaultForm())

const runtimeExtrasJson = computed({
  get: () => JSON.stringify(form.value.runtime_config_extras || {}, null, 2),
  set: (raw: string) => {
    try {
      form.value.runtime_config_extras = JSON.parse(raw) as JsonObject
    } catch {
      // 忽略不完整 JSON，提交前会再次校验
    }
  },
})

const apiRuntimeForm = computed<ApiRuntimeConfig>(() => (form.value.runtime_config || {}) as ApiRuntimeConfig)
const cliRuntimeForm = computed<CliRuntimeConfig>(() => (form.value.runtime_config || {}) as CliRuntimeConfig)

const apiKeyPlaceholder = computed(() =>
  isEdit.value ? '留空表示不更新现有 API Key' : 'API Key',
)

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

const compactObject = <T extends Record<string, unknown>>(value: T): T => {
  const output = Object.fromEntries(
    Object.entries(value).filter(([, item]) => {
      if (item === '' || item === null || item === undefined) return false
      if (Array.isArray(item) && item.length === 0) return false
      return true
    }),
  )
  return output as T
}

const parseLineList = (raw: string): string[] =>
  raw
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)

const formatLineList = (items: unknown): string =>
  Array.isArray(items) ? items.map((item) => String(item)).join('\n') : ''

const summarizeRuntimeConfig = (provider: Provider): string[] => {
  const config = provider.runtime_config || {}
  const summary: string[] = []
  if (typeof config.timeout_sec === 'number') summary.push(`timeout=${config.timeout_sec}s`)
  if (typeof config.connect_retries === 'number') summary.push(`retries=${config.connect_retries}`)
  if (typeof config.upstream_model === 'string' && config.upstream_model) summary.push(`model=${config.upstream_model}`)
  if (typeof config.command === 'string' && config.command) summary.push(`cmd=${config.command}`)
  return summary.slice(0, 3)
}

const syncCliTextFields = () => {
  cliArgsText.value = formatLineList(cliRuntimeForm.value.args)
  cliExtraArgsText.value = formatLineList(cliRuntimeForm.value.extra_args)
}

const resetForm = () => {
  form.value = buildDefaultForm()
  currentMaskedApiKey.value = null
  cliArgsText.value = ''
  cliExtraArgsText.value = ''
}

const openCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  resetForm()
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
    api_key: '',
    runtime_config: { ...(row.runtime_config || {}) },
    runtime_config_extras: { ...(row.runtime_config_extras || {}) },
    description: row.description || '',
    is_enabled: row.is_enabled,
  }
  currentMaskedApiKey.value = row.masked_api_key || (row.has_api_key ? '已配置' : null)
  syncCliTextFields()
  dialogVisible.value = true
}

const validateRuntimeConfig = (runtimeConfig: ProviderRuntimeConfig) => {
  if (typeof runtimeConfig.timeout_sec === 'number' && runtimeConfig.timeout_sec <= 0) {
    throw new Error('timeout_sec 必须大于 0')
  }
  if (typeof runtimeConfig.connect_retries === 'number' && runtimeConfig.connect_retries < 0) {
    throw new Error('connect_retries 不能小于 0')
  }
  if (
    typeof runtimeConfig.retry_backoff_sec === 'number' &&
    runtimeConfig.retry_backoff_sec < 0
  ) {
    throw new Error('retry_backoff_sec 不能小于 0')
  }
  if (
    typeof runtimeConfig.chat_endpoint === 'string' &&
    runtimeConfig.chat_endpoint &&
    !runtimeConfig.chat_endpoint.startsWith('/')
  ) {
    throw new Error('chat_endpoint 必须以 / 开头')
  }
}

const buildRuntimeConfigForSubmit = (): ProviderRuntimeConfig => {
  if (form.value.provider_type === 'api') {
    return compactObject({
      timeout_sec: apiRuntimeForm.value.timeout_sec,
      connect_retries: apiRuntimeForm.value.connect_retries,
      retry_backoff_sec: apiRuntimeForm.value.retry_backoff_sec,
      chat_endpoint: apiRuntimeForm.value.chat_endpoint,
      upstream_model: apiRuntimeForm.value.upstream_model,
    }) as ProviderRuntimeConfig
  }

  return compactObject({
    timeout_sec: cliRuntimeForm.value.timeout_sec,
    command: cliRuntimeForm.value.command,
    args: parseLineList(cliArgsText.value),
    extra_args: parseLineList(cliExtraArgsText.value),
    model_arg: cliRuntimeForm.value.model_arg,
    prompt_arg: cliRuntimeForm.value.prompt_arg,
    stream_arg: cliRuntimeForm.value.stream_arg,
    stdin_prompt_arg: cliRuntimeForm.value.stdin_prompt_arg,
    response_file: cliRuntimeForm.value.response_file,
    upstream_model: cliRuntimeForm.value.upstream_model,
    use_stdin_prompt: cliRuntimeForm.value.use_stdin_prompt,
    force_stdin_prompt: cliRuntimeForm.value.force_stdin_prompt,
  }) as ProviderRuntimeConfig
}

const buildSubmitPayload = (): CreateProviderRequest => {
  let runtimeConfigExtras: JsonObject = {}
  try {
    runtimeConfigExtras = JSON.parse(runtimeExtrasJson.value || '{}') as JsonObject
  } catch {
    throw new Error('高级扩展 JSON 格式无效')
  }

  const runtimeConfig = buildRuntimeConfigForSubmit()
  validateRuntimeConfig(runtimeConfig)

  return {
    ...form.value,
    runtime_config: runtimeConfig,
    runtime_config_extras: runtimeConfigExtras,
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  try {
    const payload = buildSubmitPayload()
    if (isEdit.value && editingId.value !== null) {
      await providersStore.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await providersStore.create(payload)
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

.runtime-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--mg-space-1);
}

.runtime-summary-empty {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.mg-form-help {
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
}
</style>
