<template>
  <el-container class="app-shell">
    <el-aside class="shell-sidebar desktop-only">
      <div class="brand-block">
        <h1>Model Gateway</h1>
        <p>Admin Console</p>
      </div>
      <el-menu class="shell-menu" :default-active="route.path" router>
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <el-icon><component :is="iconMap[item.icon]" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-drawer
      v-model="mobileNavOpen"
      class="mobile-nav-drawer"
      direction="ltr"
      :show-close="false"
      :with-header="false"
      :size="uiLayoutTokens.drawerSize"
    >
      <div class="brand-block">
        <h1>Model Gateway</h1>
        <p>Admin Console</p>
      </div>
      <el-menu class="shell-menu" :default-active="route.path" @select="handleMobileSelect">
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <el-icon><component :is="iconMap[item.icon]" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <el-container class="shell-main-container">
      <el-header class="shell-header">
        <div class="header-left">
          <el-button class="mobile-nav-trigger mobile-only" text @click="mobileNavOpen = true">
            <el-icon><Menu /></el-icon>
          </el-button>
          <h2>{{ currentTitle }}</h2>
        </div>
        <div class="header-right">
          <span class="version-chip">v0.1.5</span>
        </div>
      </el-header>
      <el-main class="shell-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Collection,
  Menu,
  Monitor,
  SetUp,
  Share,
  TrendCharts,
} from '@element-plus/icons-vue'
import { navigationRoutes, type NavIconKey } from '@/router'
import { uiLayoutTokens } from '@/ui/designTokens'

interface NavItem {
  path: string
  title: string
  icon: NavIconKey
}

const route = useRoute()
const router = useRouter()
const mobileNavOpen = ref(false)

const iconMap: Record<NavIconKey, Component> = {
  Monitor,
  SetUp,
  Collection,
  Share,
  TrendCharts,
}

const navItems = computed<NavItem[]>(() =>
  navigationRoutes.map((item) => ({
    path: item.path,
    title: item.meta.title,
    icon: item.meta.icon || 'Monitor',
  })),
)

const currentTitle = computed(() => {
  const active = navItems.value.find((item) => item.path === route.path)
  return active?.title || 'Model Gateway'
})

const handleMobileSelect = async (path: string) => {
  await router.push(path)
  mobileNavOpen.value = false
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--mg-color-bg-canvas);
}

.shell-sidebar {
  width: var(--mg-layout-sidebar-width);
  background: var(--mg-gradient-sidebar);
  border-right: 1px solid var(--mg-color-sidebar-border);
}

.shell-main-container {
  min-width: 0;
}

.brand-block {
  min-height: var(--mg-layout-brand-height);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--mg-space-1);
  color: var(--mg-color-text-on-dark);
  border-bottom: 1px solid var(--mg-color-sidebar-border);
  padding: var(--mg-space-3) var(--mg-space-2);
}

.brand-block h1 {
  margin: 0;
  font-size: var(--mg-font-size-lg);
  line-height: var(--mg-line-height-tight);
  font-family: var(--mg-font-family-display);
  letter-spacing: var(--mg-letter-spacing-brand);
}

.brand-block p {
  margin: 0;
  opacity: 0.7;
  font-size: var(--mg-font-size-xs);
  font-family: var(--mg-font-family-body);
  letter-spacing: var(--mg-letter-spacing-caption);
  text-transform: uppercase;
}

.shell-menu {
  background: transparent;
  border-right: none;
}

.shell-header {
  height: var(--mg-layout-header-height);
  background: var(--mg-color-bg-panel);
  border-bottom: 1px solid var(--mg-color-border-soft);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--mg-space-5);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--mg-space-2);
}

.header-left h2 {
  margin: 0;
  font-family: var(--mg-font-family-display);
  font-size: var(--mg-font-size-lg);
  font-weight: 600;
  color: var(--mg-color-text-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.mobile-nav-trigger {
  padding: var(--mg-space-1);
  color: var(--mg-color-text-secondary);
}

.version-chip {
  color: var(--mg-color-text-secondary);
  font-size: var(--mg-font-size-sm);
  font-family: var(--mg-font-family-mono);
  border: 1px solid var(--mg-color-border-soft);
  padding: var(--mg-space-1) var(--mg-space-2);
  border-radius: var(--mg-radius-pill);
  background: var(--mg-color-bg-elevated);
}

.shell-main {
  background: var(--mg-color-bg-canvas);
  padding: var(--mg-space-5);
  overflow-y: auto;
}

:deep(.shell-menu .el-menu-item) {
  color: var(--mg-color-text-on-dark-muted);
  margin: var(--mg-space-1) var(--mg-space-2);
  border-radius: var(--mg-radius-md);
}

:deep(.shell-menu .el-menu-item:hover) {
  color: var(--mg-color-text-on-dark);
  background: var(--mg-color-sidebar-hover);
}

:deep(.shell-menu .el-menu-item.is-active) {
  color: var(--mg-color-accent-strong);
  background: var(--mg-color-sidebar-active);
}

:deep(.shell-menu .el-icon) {
  color: currentColor;
}

:deep(.mobile-nav-drawer .el-drawer) {
  background: var(--mg-gradient-sidebar);
}

.desktop-only {
  display: block;
}

.mobile-only {
  display: none;
}

@media (max-width: 960px) {
  .desktop-only {
    display: none;
  }

  .mobile-only {
    display: inline-flex;
  }

  .shell-header {
    padding: 0 var(--mg-space-3);
  }

  .shell-main {
    padding: var(--mg-space-3);
  }
}
</style>
