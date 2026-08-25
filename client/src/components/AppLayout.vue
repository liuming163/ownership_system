<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="layout-aside">
      <div class="logo">权属管理系统</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/companies">
          <el-icon><OfficeBuilding /></el-icon>
          <span>代理主体</span>
        </el-menu-item>
        <el-menu-item index="/agents">
          <el-icon><User /></el-icon>
          <span>被代理人</span>
        </el-menu-item>
        <el-menu-item index="/works">
          <el-icon><Document /></el-icon>
          <span>作品管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <span>{{ userStore.username }}</span>
        <el-button type="text" @click="handleLogout">退出登录</el-button>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { OfficeBuilding, User, Document } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import { checkExpiringAuth } from '../api/agent'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)

async function handleLogout() {
  await userStore.logout()
  router.push('/login')
}

// 登录后检查授权委托书到期提醒
onMounted(() => {
  setTimeout(async () => {
    // 检查当前用户本次登录是否已提醒过
    const notified = sessionStorage.getItem(`auth_expiry_notified_${userStore.uid}`)
    if (notified) return

    try {
      const { data } = await checkExpiringAuth()
      const { expired, expiring_soon } = data

      if (expired.length === 0 && expiring_soon.length === 0) {
        // 没有需要提醒的，标记为已提醒
        sessionStorage.setItem(`auth_expiry_notified_${userStore.uid}`, 'true')
        return
      }

      // 构建提醒内容
      let message = ''

      if (expired.length > 0) {
        message += '<div style="margin-bottom: 12px;"><strong>【已过期】</strong></div>'
        expired.forEach(item => {
          message += `<div style="margin-bottom: 8px;">• ${item.agent_name}（代理主体：${item.company_name}）已过期 <span style="color: #F56C6C; font-weight: bold;">${item.days}</span> 天</div>`
        })
      }

      if (expiring_soon.length > 0) {
        if (message) message += '<div style="margin-top: 16px;"></div>'
        message += '<div style="margin-bottom: 12px;"><strong>【即将过期】</strong></div>'
        expiring_soon.forEach(item => {
          message += `<div style="margin-bottom: 8px;">• ${item.agent_name}（代理主体：${item.company_name}）将于 <span style="color: #E6A23C; font-weight: bold;">${item.days}</span> 天后到期</div>`
        })
      }

      // 显示弹窗
      await ElMessageBox.confirm(message, '授权委托书到期提醒', {
        confirmButtonText: '前往被代理人管理页面',
        cancelButtonText: '我知道了',
        dangerouslyUseHTMLString: true,
        type: 'warning',
        distinguishCancelAndClose: true,
      }).then(() => {
        // 点击确认按钮，跳转到被代理人管理页面
        router.push('/agents')
      }).catch(() => {
        // 点击取消或关闭，不做处理
      })

      // 标记为已提醒
      sessionStorage.setItem(`auth_expiry_notified_${userStore.uid}`, 'true')
    } catch (error) {
      console.error('检查授权到期失败:', error)
    }
  }, 1000)
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}
.layout-aside {
  background-color: #304156;
  overflow: hidden;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid #3d4d5e;
}
.layout-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  border-bottom: 1px solid #eee;
  background: #fff;
}
.layout-main {
  background: #f5f7fa;
}
</style>
