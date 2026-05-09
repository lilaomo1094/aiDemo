<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { showToast, showSuccessToast } from 'vant'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref('password')
const loading = ref(false)

const loginForm = ref({
  phone: '',
  code: '',
  username: 'admin',
  password: '888888'
})

const sendCode = () => {
  if (!loginForm.value.phone) { showToast('请输入手机号'); return }
  showSuccessToast('验证码已发送')
}

const handleLogin = async () => {
  loading.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    const username = loginForm.value.username
    const password = loginForm.value.password
    if (username !== 'admin' || password !== '888888') {
      showToast('请使用 admin/888888 登录')
      loading.value = false
      return
    }
    userStore.setToken('mock-token-' + Date.now())
    userStore.setUserInfo({
      id: 1, username: 'admin', phone: '13800138000',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user',
      nickname: '博客作者', bio: '这个人很懒，什么都没写~', template_id: 1, wechat_openid: ''
    })
    showSuccessToast('登录成功')
    router.push('/profile')
  } catch (error) { showToast('登录失败') }
  finally { loading.value = false }
}

const handleWechatLogin = () => { showToast('微信扫码登录功能开发中') }
</script>

<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo"><span class="logo-icon">📝</span></div>
        <h1 class="title">博客平台</h1>
        <p class="subtitle">登录后开始您的创作之旅</p>
      </div>
      <van-tabs v-model:active="activeTab" class="login-tabs">
        <van-tab title="账号密码" name="password">
          <van-form @submit="handleLogin" class="login-form">
            <van-cell-group inset>
              <van-field v-model="loginForm.username" name="username" placeholder="请输入用户名" left-icon="user-o" :rules="[{ required: true, message: '请输入用户名' }]" />
              <van-field v-model="loginForm.password" type="password" name="password" placeholder="请输入密码" left-icon="lock" :rules="[{ required: true, message: '请输入密码' }]" />
            </van-cell-group>
            <div class="submit-btn">
              <van-button type="primary" size="large" round :loading="loading" loading-text="登录中..." native-type="submit">登 录</van-button>
            </div>
          </van-form>
        </van-tab>
        <van-tab title="手机验证码" name="phone">
          <van-form @submit="handleLogin" class="login-form">
            <van-cell-group inset>
              <van-field v-model="loginForm.phone" name="phone" placeholder="请输入手机号" left-icon="phone" :rules="[{ required: true, message: '请输入手机号' }]">
                <template #button><van-button size="small" type="primary" round @click="sendCode" class="send-code-btn">发送验证码</van-button></template>
              </van-field>
              <van-field v-model="loginForm.code" name="code" placeholder="请输入验证码" left-icon="chat-o" :rules="[{ required: true, message: '请输入验证码' }]" />
            </van-cell-group>
            <div class="submit-btn">
              <van-button type="primary" size="large" round :loading="loading" loading-text="登录中..." native-type="submit">登 录</van-button>
            </div>
          </van-form>
        </van-tab>
        <van-tab title="微信扫码" name="wechat">
          <div class="wechat-login">
            <div class="qrcode-placeholder"><span class="qrcode-icon">📱</span><p>扫码功能开发中</p></div>
            <van-button type="primary" size="large" round block @click="handleWechatLogin" class="wechat-btn"><span class="wechat-icon">💬</span>微信扫码登录</van-button>
          </div>
        </van-tab>
      </van-tabs>
      <div class="login-footer"><span>还没有账号？</span><a href="#" class="register-link">立即注册</a></div>
    </div>
  </div>
</template>

<style scoped>
.login-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #e8f5e9 0%, #f5f9f6 50%, #e3f2fd 100%); padding: 20px; }
.login-card { width: 100%; max-width: 420px; background: white; border-radius: 24px; box-shadow: 0 8px 40px rgba(0, 0, 0, 0.08); padding: 40px 32px; animation: slideUp 0.5s ease-out; }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
.login-header { text-align: center; margin-bottom: 32px; }
.logo { width: 72px; height: 72px; margin: 0 auto 16px; background: linear-gradient(135deg, #4CAF50 0%, #81C784 100%); border-radius: 20px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3); }
.logo-icon { font-size: 36px; }
.title { font-size: 24px; font-weight: 600; color: #1a1a1a; margin: 0 0 8px; }
.subtitle { font-size: 14px; color: #999; margin: 0; }
.login-tabs :deep(.van-tabs__line) { background: #4CAF50; }
.login-form { margin-top: 24px; }
.submit-btn { margin-top: 32px; padding: 0 16px; }
.submit-btn :deep(.van-button) { height: 48px; font-size: 16px; font-weight: 500; background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%); border: none; box-shadow: 0 4px 16px rgba(76, 175, 80, 0.3); }
.send-code-btn { height: 32px; font-size: 12px; }
.wechat-login { padding: 32px 16px; text-align: center; }
.qrcode-placeholder { padding: 40px; background: #f5f5f5; border-radius: 16px; margin-bottom: 24px; }
.qrcode-icon { font-size: 48px; display: block; margin-bottom: 12px; }
.qrcode-placeholder p { color: #999; margin: 0; font-size: 14px; }
.wechat-btn { background: #07C160 !important; border: none !important; }
.wechat-icon { font-size: 18px; margin-right: 8px; }
.login-footer { text-align: center; margin-top: 24px; font-size: 14px; color: #999; }
.register-link { color: #4CAF50; text-decoration: none; margin-left: 4px; font-weight: 500; }
</style>
