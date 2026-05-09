<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { showSuccessToast } from 'vant'

const router = useRouter()
const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo)
const isEditing = ref(false)
const editingBio = ref('')

const startEditBio = () => { editingBio.value = userInfo.value?.bio || ''; isEditing.value = true }
const saveBio = () => { if (userInfo.value) { userInfo.value.bio = editingBio.value; showSuccessToast('保存成功') } isEditing.value = false }
const cancelEdit = () => { isEditing.value = false }
const goToBlog = () => router.push('/home')
const goToTemplate = () => router.push('/template')
const handleLogout = () => { userStore.logout(); showSuccessToast('已退出登录'); router.push('/login') }
</script>

<template>
  <div class="profile-container">
    <div class="profile-header">
      <van-icon name="arrow-left" class="back-btn" @click="router.back()" />
      <span class="header-title">个人中心</span>
    </div>
    <div class="profile-cover"></div>
    <div class="profile-content">
      <div class="avatar-section">
        <van-image round width="100" height="100" :src="userInfo?.avatar || 'https://api.dicebear.com/7.x/avataaars/svg?seed=user'" class="avatar" />
        <h2 class="nickname">{{ userInfo?.nickname || '未登录' }}</h2>
        <p class="username">@{{ userInfo?.username || 'guest' }}</p>
      </div>
      <div class="bio-section">
        <div class="bio-header"><span class="bio-label">个人简介</span><van-icon v-if="!isEditing" name="edit" class="edit-icon" @click="startEditBio" /></div>
        <div v-if="!isEditing" class="bio-content">{{ userInfo?.bio || '这个人很懒，什么都没写~' }}</div>
        <div v-else class="bio-edit">
          <van-field v-model="editingBio" type="textarea" placeholder="介绍一下自己吧~" rows="3" maxlength="200" show-word-limit" class="bio-field" />
          <div class="edit-actions"><van-button size="small" round @click="cancelEdit">取消</van-button><van-button size="small" type="primary" round @click="saveBio">保存</van-button></div>
        </div>
      </div>
      <div class="menu-section">
        <van-cell-group>
          <van-cell title="我的博客" icon="edit" is-link @click="goToBlog" />
          <van-cell title="模板选择" icon="brush" is-link @click="goToTemplate" />
          <van-cell title="设置" icon="setting-o" is-link />
        </van-cell-group>
      </div>
      <div class="logout-section">
        <van-button type="danger" round block @click="handleLogout"><van-icon name="poweroff" class="logout-icon" />退出登录</van-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-container { min-height: 100vh; background: #f5f9f6; }
.profile-header { position: fixed; top: 0; left: 0; right: 0; height: 46px; display: flex; align-items: center; padding: 0 16px; background: transparent; z-index: 100; }
.back-btn { font-size: 20px; color: #333; cursor: pointer; }
.header-title { position: absolute; left: 50%; transform: translateX(-50%); font-size: 16px; font-weight: 500; color: #333; }
.profile-cover { height: 180px; background: linear-gradient(135deg, #4CAF50 0%, #81C784 50%, #A5D6A7 100%); border-radius: 0 0 40px 40px; }
.profile-content { margin-top: -60px; padding: 0 16px; }
.avatar-section { text-align: center; margin-bottom: 24px; }
.avatar { border: 4px solid white; box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3); }
.nickname { margin: 12px 0 4px; font-size: 22px; font-weight: 600; color: #1a1a1a; }
.username { margin: 0; font-size: 14px; color: #999; }
.bio-section { background: white; border-radius: 16px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04); }
.bio-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.bio-label { font-size: 14px; font-weight: 500; color: #666; }
.edit-icon { font-size: 16px; color: #4CAF50; cursor: pointer; }
.bio-content { font-size: 14px; color: #333; line-height: 1.6; }
.bio-edit { margin-top: 8px; }
.bio-field { background: #f5f5f5; border-radius: 8px; }
.edit-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 12px; }
.menu-section { margin-bottom: 16px; }
.menu-section :deep(.van-cell) { border-radius: 12px; margin-bottom: 8px; }
.menu-section :deep(.van-cell__left-icon) { color: #4CAF50; }
.logout-section { padding: 16px; }
.logout-section :deep(.van-button) { height: 48px; font-size: 16px; }
.logout-icon { margin-right: 8px; }
</style>
