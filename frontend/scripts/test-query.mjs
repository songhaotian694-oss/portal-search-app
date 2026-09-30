import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import vm from 'node:vm'
import ts from 'typescript'

function load(relative) {
  const url = new URL(relative, import.meta.url)
  const source = readFileSync(url, 'utf8')
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } }).outputText
  const exports = {}
  const context = { exports, require: createRequire(url), URLSearchParams, performance: { now: () => 0 } }
  vm.runInNewContext(code, context)
  return { exports, context }
}
const { exports: { parseQuery } } = load('../src/lib/query.ts')
const values = query => JSON.parse(JSON.stringify(parseQuery(query))).map(token => [token.facet, token.value])
assert.deepEqual(values('北京市或上海，排除本科'), [['city', '北京 / 上海'], ['degree', '排除本科']])
assert.deepEqual(values('2023至2025届计科硕士研究生'), [['year', '2023–2025'], ['major', '计算机'], ['degree', '硕士']])
assert.deepEqual(values('2024年毕业北京'), [['year', '2024'], ['city', '北京']])
assert.deepEqual(values('2020级 北京'), [['city', '北京']])
assert.deepEqual(values('“北京” 单位：财政局'), [])
assert.deepEqual(values('ＣＳ硕士'), [['major', '计算机'], ['degree', '硕士']])
assert.deepEqual(values('不在北京或上海工作的硕士'), [['city', '排除北京 / 排除上海'], ['degree', '硕士']])
assert.deepEqual(values('csirt'), [])
const { exports: { api }, context } = load('../src/services/api.ts')
const query = '2023至2025届 北京或上海 排除本科'
const exported = new URL(api.exportUrl(query, { major: '软件工程' }), 'http://localhost')
assert.equal(exported.searchParams.get('q'), query)
assert.equal(exported.searchParams.get('major'), '软件工程')
assert.equal(exported.searchParams.get('city'), null)
let searched
context.fetch = async path => { searched = new URL(path, 'http://localhost'); return { ok: true, json: async () => ({ results: [], summary: {} }) } }
await api.searchRecords(query, { major: '软件工程' })
searched.searchParams.delete('limit')
assert.equal(searched.searchParams.toString(), exported.searchParams.toString())
console.log('Chinese query preview and search/export consistency passed.')
