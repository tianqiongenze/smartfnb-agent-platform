<template>
  <div>
    <el-card shadow="never" style="margin-bottom:12px">
      <el-space wrap>
        <el-button-group>
          <el-button type="primary" plain @click="tab='po'">📋 采购建议审批</el-button>
          <el-button type="primary" plain @click="tab='quality'">🛡️ 数据质量门禁</el-button>
          <el-button type="primary" plain @click="tab='forecast'">📈 需求预测</el-button>
        </el-button-group>
      </el-space>
    </el-card>

    <!-- 采购建议(人在环) -->
    <el-card v-if="tab==='po'" shadow="never">
      <template #header>
        <el-space>AI采购建议单（DRAFT待审批 · 人在环）
          <el-radio-group v-model="poStatus" size="small" @change="loadPo">
            <el-radio-button value="DRAFT">待审批</el-radio-button>
            <el-radio-button value="APPROVED">已批准</el-radio-button>
            <el-radio-button value="REJECTED">已驳回</el-radio-button>
          </el-radio-group>
        </el-space>
      </template>
      <el-table :data="poList" size="small" v-loading="loading" height="480">
        <el-table-column prop="id" label="单号" width="190" />
        <el-table-column prop="storeId" label="店" width="55" />
        <el-table-column prop="ingName" label="食材" min-width="90" />
        <el-table-column label="数量" width="100">
          <template #default="{ row }">{{ row.suggestQty }}{{ row.unitCode }}</template>
        </el-table-column>
        <el-table-column prop="supName" label="供应商" min-width="120" />
        <el-table-column prop="estPrice" label="参考价" width="80" />
        <el-table-column prop="reason" label="理由" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <template v-if="poStatus==='DRAFT'">
              <el-button size="small" type="success" @click="decide(row.id,'approve')">批准</el-button>
              <el-button size="small" type="danger" plain @click="decide(row.id,'reject')">驳回</el-button>
            </template>
            <el-tag v-else size="small" :type="poStatus==='APPROVED' ? 'success':'info'">{{ poStatus }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 质量门禁 -->
    <el-card v-if="tab==='quality'" shadow="never">
      <template #header>每日06:00 五规则门禁（GB/T 36073 数据质量）</template>
      <el-table :data="quality" size="small" v-loading="loading">
        <el-table-column prop="ruleName" label="规则" width="160" />
        <el-table-column label="结论" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status==='PASS' ? 'success':'danger'" effect="dark">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metric" label="指标值" width="110" />
        <el-table-column prop="detail" label="说明" min-width="380" />
      </el-table>
    </el-card>

    <!-- 需求预测 -->
    <el-card v-if="tab==='forecast'" shadow="never">
      <template #header>
        <el-space>
          需求预测（World Model置信区间 + MAPE置信度）
          <el-select v-model="fcStore" size="small" style="width:160px">
            <el-option v-for="s in stores" :key="s.id" :label="`${s.id}-${s.name}`" :value="s.id" />
          </el-select>
          <el-select v-model="fcIng" size="small" style="width:140px" filterable>
            <el-option v-for="i in ings" :key="i.id" :label="i.name" :value="i.name" />
          </el-select>
          <el-button type="primary" size="small" @click="loadForecast" :loading="loading">预测</el-button>
        </el-space>
      </template>
      <div ref="fcChart" style="height:420px"></div>
    </el-card>
  </div>
</template>
<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { http } from '../api'

const tab = ref('po')
const loading = ref(false)
const poList = ref([]); const poStatus = ref('DRAFT')
const quality = ref([])
const stores = ref([]); const ings = ref([])
const fcStore = ref(7); const fcIng = ref('鲈鱼')
const fcChart = ref(null)

async function loadPo() {
  loading.value = true
  try {
    const { data } = await http.post('/graphql', {
      query: `query($st:String!){ suggestions: _ }`.replace('suggestions: _', 'suggestionsX') // 占位
    }).catch(() => ({ data: {} }))
    // REST直连(经portal代理更简): 用GraphQL聚合前先走inventory REST
    const r = await http.get(`/api/proc/suggestions?status=${poStatus.value}`)
    poList.value = r.data
  } catch (e) { ElMessage.error('加载失败: ' + e.message) } finally { loading.value = false }
}

async function decide(id, act) {
  await http.post(`/api/proc/suggestions/${id}/${act}`)
  ElMessage.success(`已${act === 'approve' ? '批准' : '驳回'} #${id}`)
  loadPo()
}

async function loadQuality() {
  loading.value = true
  try {
    const { data } = await http.post('/graphql', { query: '{quality{ruleName status metric detail}}' })
    quality.value = data.data.quality
  } finally { loading.value = false }
}

async function loadForecast() {
  loading.value = true
  try {
    const [ci, fc] = await Promise.all([
      http.get(`/api/wm/forecast-ci?storeId=${fcStore.value}&ingName=${encodeURIComponent(fcIng.value)}&days=7`),
      http.get(`/api/fc/forecast?storeId=${fcStore.value}&ingName=${encodeURIComponent(fcIng.value)}&days=7`)
    ])
    await nextTick()
    const c = echarts.init(fcChart.value)
    const days = ci.data.days.map(d => d.date.slice(5))
    c.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['p10', 'p50(中位)', 'p90'] },
      grid: { left: 60, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: days },
      yAxis: { type: 'value', name: 'kg' },
      series: [
        { name: 'p10', type: 'line', data: ci.data.days.map(d => d.p10Kg), lineStyle: { opacity: 0.4 }, symbol: 'none' },
        { name: 'p50(中位)', type: 'line', data: ci.data.days.map(d => d.p50Kg), lineStyle: { width: 3 } },
        { name: 'p90', type: 'line', data: ci.data.days.map(d => d.p90Kg), lineStyle: { opacity: 0.4 }, symbol: 'none',
          areaStyle: { color: '#409EFF22' } }
      ]
    })
    if (fc.data.days?.length) {
      ElMessage.info(`点预测置信度: ${fc.data.days[0].confidence} (回测MAPE ${fc.data.days[0].mape}%)`)
    }
  } catch (e) { ElMessage.error('预测失败: ' + e.message) } finally { loading.value = false }
}

onMounted(async () => {
  loadPo(); loadQuality()
  const { data } = await http.post('/graphql', { query: '{stores{id,name} ingredients{id name}}' })
  stores.value = data.data.stores; ings.value = data.data.ingredients
})
</script>
