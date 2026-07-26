import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const mainSource = await readFile(new URL('../src/main.ts', import.meta.url), 'utf8')

test('loads styles for imperative Element Plus feedback services', () => {
  assert.match(mainSource, /import ['"]element-plus\/theme-chalk\/el-message\.css['"]/)
  assert.match(mainSource, /import ['"]element-plus\/theme-chalk\/el-message-box\.css['"]/)
})
