<template>
  <el-container class="app-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>Model Gateway</h2>
      </div>
      <el-menu
        :default-active="$route.path"
        class="el-menu-vertical"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">
          <el-icon><Monitor /></el-icon>
          <span>概览</span>
        </el-menu-item>
        <el-menu-item index="/providers">
          <el-icon><SetUp /></el-icon>
          <span>Provider 管理</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Collection /></el-icon>
          <span>模型管理</span>
        </el-menu-item>
        <el-menu-item index="/routes">
          <el-icon><Share /></el-icon>
          <span>路由规则</span>
        </el-menu-item>
        <el-menu-item index="/usage">
          <el-icon><TrendCharts /></el-icon>
          <span>使用量统计</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-right">
          <span class="version">v0.1.0</span>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { Monitor, SetUp, Collection, Share, TrendCharts } from '@element-plus/icons-vue'
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid #1f2d3d;
}

.logo h2 {
  margin: 0;
  font-size: 18px;
}

.el-menu-vertical {
  border-right: none;
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.header-right {
  display: flex;
  align-items: center;
}

.version {
  color: #909399;
  font-size: 14px;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
