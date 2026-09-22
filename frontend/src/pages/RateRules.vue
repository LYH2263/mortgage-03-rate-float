<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON, putJSON } from '../api'

const loans = ref([])
const loanId = ref(null)
const events = ref([])
const error = ref('')
const form = ref({ effective_period: 13, new_annual_rate: 4.5, note: '' })
const editingId = ref(null)
const editForm = ref({ effective_period: null, new_annual_rate: null, note: '' })

const loan = computed(() => loans.value.find(l => l.id === loanId.value))

const showError = (e) => {
  try { error.value = JSON.parse(e.message).detail || e.message } catch { error.value = e.message }
}
const loadEvents = async () => {
  error.value = ''
  events.value = loanId.value ? (await getJSON(`/api/loans/${loanId.value}/rate-floats`)).items : []
}
const pickLoan = async () => { editingId.value = null; await loadEvents() }
onMounted(async () => {
  loans.value = (await getJSON('/api/loans')).items
  if (loans.value.length) { loanId.value = loans.value[0].id; await loadEvents() }
})
const create = async () => {
  error.value = ''
  try {
    await postJSON(`/api/loans/${loanId.value}/rate-floats`, { ...form.value })
    await loadEvents()
  } catch (e) { showError(e) }
}
const startEdit = (ev) => {
  editingId.value = ev.id
  editForm.value = { effective_period: ev.effective_period, new_annual_rate: ev.new_annual_rate, note: ev.note }
}
const saveEdit = async (id) => {
  error.value = ''
  try {
    await putJSON(`/api/rate-floats/${id}`, { ...editForm.value })
    editingId.value = null
    await loadEvents()
  } catch (e) { showError(e) }
}
const disable = async (id) => {
  error.value = ''
  try { await postJSON(`/api/rate-floats/${id}/disable`, {}); await loadEvents() } catch (e) { showError(e) }
}
</script>

<template><div class="page"><h1>利率浮动事件</h1>
<p>默认等额本息：月利率 = 年利率 / 12 / 100。启用事件自生效期起按余额与新年利率重算剩余月供。</p>
<label>贷款
  <select v-model.number="loanId" @change="pickLoan">
    <option v-for="l in loans" :key="l.id" :value="l.id">{{ l.name }}（{{ l.principal }}元 · {{ l.months }}期 · {{ l.annual_rate }}%）</option>
  </select>
</label>
<p v-if="error" class="err">{{ error }}</p>

<h2>新增事件</h2>
<div v-if="loan">
  <label>生效期 <input type="number" v-model.number="form.effective_period" :max="loan.months" /></label>
  <label>新年利率% <input type="number" step="0.01" v-model.number="form.new_annual_rate" /></label>
  <label>备注 <input v-model="form.note" /></label>
  <button @click="create">创建</button>
</div>

<h2>事件列表</h2>
<table>
  <tr><th>#</th><th>生效期</th><th>新年利率%</th><th>状态</th><th>备注</th><th>操作</th></tr>
  <tr v-for="ev in events" :key="ev.id">
    <template v-if="editingId === ev.id">
      <td>#{{ ev.id }}</td>
      <td><input type="number" v-model.number="editForm.effective_period" /></td>
      <td><input type="number" step="0.01" v-model.number="editForm.new_annual_rate" /></td>
      <td>{{ ev.enabled ? '启用' : '停用' }}</td>
      <td><input v-model="editForm.note" /></td>
      <td><button @click="saveEdit(ev.id)">保存</button> <button @click="editingId = null">取消</button></td>
    </template>
    <template v-else>
      <td>#{{ ev.id }}</td>
      <td>第{{ ev.effective_period }}期</td>
      <td>{{ ev.new_annual_rate }}</td>
      <td>{{ ev.enabled ? '启用' : '停用' }}</td>
      <td>{{ ev.note }}</td>
      <td>
        <button @click="startEdit(ev)">编辑</button>
        <button v-if="ev.enabled" @click="disable(ev.id)">停用</button>
      </td>
    </template>
  </tr>
  <tr v-if="!events.length"><td colspan="6">该贷款暂无浮动事件</td></tr>
</table>
</div></template>

<style scoped>
.err { color: #a33; }
h2 { font-size: 1rem; margin: 0.8rem 0 0.3rem; }
label { margin-right: 0.6rem; }
</style>
