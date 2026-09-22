<script setup>
import { onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
const loans = ref([])
const loanId = ref(null)
const principal = ref(800000)
const annual_rate = ref(4.2)
const months = ref(360)
const out = ref(null)
onMounted(async () => { loans.value = (await getJSON('/api/loans')).items })
const pickLoan = () => {
  const l = loans.value.find(x => x.id === loanId.value)
  if (l) { principal.value = l.principal; annual_rate.value = l.annual_rate; months.value = l.months }
}
const run = async () => {
  out.value = await postJSON('/api/schedule', {
    principal: principal.value, annual_rate: annual_rate.value, months: months.value,
    loan_id: loanId.value, persist: true,
  })
}
</script>
<template><div class="page"><h1>等额本息试算</h1>
<label>贷款
  <select v-model.number="loanId" @change="pickLoan">
    <option :value="null">手工输入</option>
    <option v-for="l in loans" :key="l.id" :value="l.id">{{ l.name }}</option>
  </select>
</label>
<label>本金 <input v-model.number="principal" /></label>
<label>年利率% <input v-model.number="annual_rate" /></label>
<label>月数 <input v-model.number="months" /></label>
<button @click="run">计算</button>
<p v-if="out">月供 {{ out.monthly_payment }} · 利息合计 {{ out.total_interest }}</p>
<div v-if="out?.rate_float" class="float-box">
  <p v-for="sw in out.rate_float.switches" :key="sw.period">
    第{{ sw.period }}期切换：利率 {{ sw.rate_before }}% → {{ sw.rate_after }}%，
    月供 {{ sw.payment_before }} → {{ sw.payment_after }}，
    切换前利息 {{ sw.interest_before }} · 切换后利息 {{ sw.interest_after }}
  </p>
</div>
</div></template>

<style scoped>
.float-box { border: 1px dashed var(--accent); padding: 0.4rem 0.6rem; margin-top: 0.4rem; }
</style>
