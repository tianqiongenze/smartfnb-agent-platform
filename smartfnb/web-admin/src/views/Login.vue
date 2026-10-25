<template>
  <div style="display:flex;justify-content:center;align-items:center;height:80vh">
    <el-card style="width:380px">
      <h2 style="text-align:center">智慧餐链 · 登录</h2>
      <el-form @submit.prevent>
        <el-form-item><el-input v-model="u" placeholder="用户名 admin/buyer/store7" /></el-form-item>
        <el-form-item><el-input v-model="p" type="password" placeholder="密码" show-password /></el-form-item>
        <el-button type="primary" style="width:100%" :loading="loading" @click="go">登 录</el-button>
      </el-form>
    </el-card>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api'
const u = ref('admin'); const p = ref('admin123'); const loading = ref(false)
const router = useRouter()
async function go() {
  loading.value = true
  try {
    const d = await login(u.value, p.value)
    ElMessage.success(`欢迎, ${d.user}`)
    router.push('/dashboard')
  } catch (e) { ElMessage.error('登录失败: ' + (e.response?.data?.detail || e.message)) }
  finally { loading.value = false }
}
</script>
