<template>
  <div>
    <el-card shadow="never" style="margin-bottom:12px">
      <el-space wrap>
        <span>门店:</span>
        <el-select v-model="storeId" style="width:220px" @change="load">
          <el-option v-for="s in storeList" :key="s.id" :label="`${s.id}-${s.name}`" :value="s.id" />
        </el-select>
        <span>日期:</span>
        <el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD" :clearable="false" @change="load" />
        <el-button type="primary" @click="load" :loading="loading">查询</el-button>
        <el-tag v-if="report" type="danger" effect="dark">预警 {{ report.alertCount }} 条</el-tag>
        <el-button plain @click="$router.push('/agent')">🤖 问智能体</el-button>
      </el-space>
    </el-card>

    <el-row :gutter="12">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>理论 vs 实际用量差异 (Top |diff|)</template>
          <el-table :data="report?.lines || []" size="small" height="520" v-loading="loading">
            <el-table-column prop="ingName" label="食材" min-width="110" />
            <el-table-column prop="category" label="品类" width="80" />
            <el-table-column label="理论(kg)" width="95">
              <template #default="{ row }">{{ (row.theoGram / 1000).toFixed(1) }}</template>
            </el-table-column>
            <el-table-column label="实际(kg)" width="95">
              <template #default="{ row }">{{ (row.actualGram / 1000).toFixed(1) }}</template>
            </el-table-column>
            <el-table-column label="差异率" width="90">
              <template #default="{ row }">
                <el-tag :type="levelType(row.level)" effect="plain" v-if="row.level">{{ row.diffPct }}%</el-tag>
                <span v-else>{{ row.diffPct ?? '-' }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="级别" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.level === 'HIGH'" type="danger">HIGH</el-tag>
                <el-tag v-else-if="row.level === 'MEDIUM'" type="warning">MED</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>差异率分布 Top10</template>
          <div ref="chart" style="height:280px"></div>
        </el-card>
        <el-card shadow="never">
          <template #header>预警列表(可确认)</template>
          <el-table :data="alertList" size="small" height="200">
            <el-table-column prop="storeId" label="店" width="50" />
            <el-table-column prop="ingName" label="食材" min-width="90" />
            <el-table-column label="差异" width="80">
              <template #default="{ row }">{{ row.diffPct }}%</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-button v-if="row.status === 'OPEN'" size="small" type="danger" plain
                           @click="ack(row.id)">确认</el-button>
                <el-tag v-else size="small" type="info">已确认</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { stores, diffReport, alerts, ackAlert } from '../api'

const storeList = ref([]); const storeId = ref(7)
const date = ref(new Date(Date.now() - 86400000 * 3).toISOString().slice(0, 10))
const report = ref(null); const alertList = ref([]); const loading = ref(false)
const chart = ref(null)

function levelType(l) { return l === 'HIGH' ? 'danger' : 'warning' }

async function load() {
  loading.value = true
  try {
    report.value = await diffReport(storeId.value, date.value)
    alertList.value = await alerts(date.value)
    await nextTick(); draw()
  } catch (e) { ElMessage.error('查询失败: ' + e.message) } finally { loading.value = false }
}

function draw() {
  if (!chart.value || !report.value) return
  const c = echarts.init(chart.value)
  const top = [...(report.value.lines || [])].slice(0, 10)
  c.setOption({
    grid: { left: 110, right: 20, top: 10, bottom: 20 },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: top.map(l => l.ingName) },
    tooltip: {},
    series: [{
      type: 'bar',
      data: top.map(l => ({
        value: l.diffPct,
        itemStyle: { color: Math.abs(l.diffPct || 0) >= 30 ? '#F56C6C' : '#E6A23C' }
      }))
    }]
  })
}

async function ack(id) {
  await ackAlert(id); ElMessage.success('已确认'); load()
}

onMounted(async () => {
  storeList.value = await stores()
  load()
})
</script>
