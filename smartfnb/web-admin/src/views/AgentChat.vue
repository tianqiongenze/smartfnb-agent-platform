<template>
  <div style="max-width:900px;margin:0 auto">
    <el-card shadow="never" style="height:76vh;display:flex;flex-direction:column">
      <template #header>
        <el-space>
          🤖 智能体助手
          <el-select v-model="storeId" size="small" style="width:200px">
            <el-option v-for="s in storeList" :key="s.id" :label="`${s.id}-${s.name}`" :value="s.id" />
          </el-select>
          <el-date-picker v-model="date" type="date" size="small" value-format="YYYY-MM-DD" :clearable="false" />
        </el-space>
      </template>
      <div ref="box" style="flex:1;overflow-y:auto;padding:8px">
        <div v-for="(m, i) in msgs" :key="i" style="margin:8px 0">
          <div :style="{ textAlign: m.role === 'user' ? 'right' : 'left' }">
            <el-tag size="small" :type="m.role === 'user' ? 'primary' : 'success'" style="margin-right:6px">
              {{ m.role === 'user' ? '我' : '智能体' }}
            </el-tag>
            <span v-if="m.event && m.role === 'bot'" style="color:#909399;font-size:12px">
              [{{ m.event }}]</span>
          </div>
          <div :style="{
            display: 'inline-block', maxWidth: '80%', padding: '8px 12px', borderRadius: '8px',
            background: m.role === 'user' ? '#409EFF22' : '#95d4752c', whiteSpace: 'pre-wrap'
          }">{{ m.text }}</div>
        </div>
      </div>
      <el-space fill style="width:100%">
        <el-input v-model="q" placeholder="试试: 7号店今天牛肉用量差异多少?" @keyup.enter="send" :disabled="busy">
          <template #append><el-button @click="send" :loading="busy">发送</el-button></template>
        </el-input>
      </el-space>
    </el-card>
  </div>
</template>
<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { stores, agentChat } from '../api'

const q = ref(''); const msgs = ref([]); const busy = ref(false)
const storeId = ref(7); const storeList = ref([])
const date = ref(new Date(Date.now() - 86400000).toISOString().slice(0, 10))
const box = ref(null)

function scroll() { nextTick(() => box.value && (box.value.scrollTop = box.value.scrollHeight)) }

async function send() {
  const text = q.value.trim(); if (!text || busy.value) return
  q.value = ''; busy.value = true
  msgs.value.push({ role: 'user', text }); scroll()
  const bot = { role: 'bot', text: '' }; msgs.value.push(bot); scroll()
  try {
    await agentChat({ question: text, storeId: storeId.value, date: date.value }, ev => {
      if (ev.event === 'route') { bot.event = `路由→${ev.intent}` }
      else if (ev.event === 'progress') { bot.event = `工具调用×${ev.tools_used}` }
      else if (ev.event === 'answer') {
        bot.text = ev.answer
        bot.event = `置信度:${ev.confidence}`
      }
      else if (ev.event === 'error') { bot.text = '出错: ' + ev.message + '\n' + (ev.fallback || '') }
      scroll()
    })
  } catch (e) { bot.text = '网络错误: ' + e.message }
  busy.value = false; scroll()
}

onMounted(async () => {
  storeList.value = await stores()
  msgs.value.push({ role: 'bot', text: '您好! 我可以分析门店食材用量差异、浪费与预警。所有数字均来自MCP工具实时查询, 并通过溯源校验。' })
})
</script>
