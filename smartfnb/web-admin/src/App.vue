<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="background:#1f2d3d">
      <div style="color:#fff;padding:18px 16px;font-weight:700;font-size:16px">🍽️ 智慧餐链</div>
      <el-menu router :default-active="$route.path" background-color="#1f2d3d" text-color="#bfcbd9"
               active-text-color="#409EFF" style="border-right:none">
        <el-menu-item index="/dashboard">📊 用量差异看板</el-menu-item>
        <el-menu-item index="/agent">🤖 智能体助手</el-menu-item>
        <el-menu-item index="/ops">🧭 运营决策</el-menu-item>
      </el-menu>
      <div style="position:absolute;bottom:12px;color:#5a6d82;font-size:12px;padding:0 16px">
        Phase-0 · {{ user || '未登录' }}
      </div>
    </el-aside>
    <el-main><router-view /></el-main>
  </el-container>
</template>
<script setup>
import { ref } from 'vue'
const user = ref(localStorage.getItem('user') || '')
</script>
