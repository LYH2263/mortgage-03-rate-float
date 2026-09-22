<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const openId = ref(null)
const detail = ref(null)
const toggle = (h) => {
  if (openId.value === h.id) { openId.value = null; detail.value = null; return }
  openId.value = h.id
  try { detail.value = JSON.parse(h.result_json) } catch { detail.value = null }
}
onMounted(async () => { items.value = (await getJSON('/api/history')).items })
</script>
<template><div class="page"><h1>试算记录</h1>
<table>
  <tr><th>#</th><th>时间</th><th>月供</th><th>利息合计</th><th></th></tr>
  <template v-for="h in items" :key="h.id">
    <tr>
      <td>#{{ h.id }}</td><td>{{ h.created_at }}</td>
      <td>{{ JSON.parse(h.result_json).monthly_payment }}</td>
      <td>{{ JSON.parse(h.result_json).total_interest }}</td>
      <td><button @click="toggle(h)">{{ openId === h.id ? '收起' : '打开' }}</button></td>
    </tr>
    <tr v-if="openId === h.id && detail">
      <td colspan="5">
        <div v-if="detail.rate_float">
          <p v-for="sw in detail.rate_float.switches" :key="sw.period">
            第{{ sw.period }}期切换：利率 {{ sw.rate_before }}% → {{ sw.rate_after }}%，
            月供 {{ sw.payment_before }} → {{ sw.payment_after }}
          </p>
        </div>
        <p v-else>单一利率试算，无利率切换。</p>
      </td>
    </tr>
  </template>
</table>
</div></template>
