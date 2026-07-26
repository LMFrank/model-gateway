import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const providerTypeSource = await readFile(
  new URL('../src/types/provider.ts', import.meta.url),
  'utf8',
)
const providersViewSource = await readFile(
  new URL('../src/views/Providers.vue', import.meta.url),
  'utf8',
)
const routeTypeSource = await readFile(
  new URL('../src/types/route.ts', import.meta.url),
  'utf8',
)
const routesViewSource = await readFile(
  new URL('../src/views/Routes.vue', import.meta.url),
  'utf8',
)

test('exposes force_temperature as a structured API provider setting', () => {
  assert.match(providerTypeSource, /force_temperature\?: number/)
  assert.match(
    providersViewSource,
    /v-model="apiRuntimeForm\.force_temperature"/,
  )
  assert.match(
    providersViewSource,
    /force_temperature: apiRuntimeForm\.value\.force_temperature/,
  )
})

test('shows the explicit fallback provider and model target', () => {
  assert.match(routeTypeSource, /fallback_provider: string \| null/)
  assert.match(routeTypeSource, /fallback_model_key: string \| null/)
  assert.match(routesViewSource, /row\.fallback_provider/)
  assert.match(routesViewSource, /row\.fallback_model_key/)
})
