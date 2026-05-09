<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTemplateStore } from '../stores/template'
import type { Template } from '../stores/template'
import { useUserStore } from '../stores/user'
import { showSuccessToast } from 'vant'

const router = useRouter()
const templateStore = useTemplateStore()
const userStore = useUserStore()

const selectedId = ref(userStore.userInfo?.template_id || 1)

const templateColors: Record<string, { primary: string; bg: string; gradient: string }> = {
  fresh: { primary: '#4CAF50', bg: '#F5F9F6', gradient: 'linear-gradient(135deg, #4CAF50 0%, #81C784 100%)' },
  minimal: { primary: '#333333', bg: '#FAFAFA', gradient: 'linear-gradient(135deg, #333333 0%, #666666 100%)' },
  business: { primary: '#1976D2', bg: '#F0F4F8', gradient: 'linear-gradient(135deg, #1976D2 0%, #64B5F6 100%)' },
  creative: { primary: '#9C27B0', bg: '#FDF5FF', gradient: 'linear-gradient(135deg, #9C27B0 0%, #CE93D8 100%)' },
  warm: { primary: '#FF7043', bg: '#FFF8F5', gradient: 'linear-gradient(135deg, #FF7043 0%, #FFAB91 100%)' }
}

const getTemplateStyle = (style: string) => templateColors[style] || templateColors.fresh

const selectTemplate = (template: Template) => { selectedId.value = template.id }
const confirmTemplate = () => {
  const template = templateStore.templateList.find(t => t.id === selectedId.value)
  if (template) { templateStore.setCurrentTemplate(template); if (userStore.userInfo) userStore.userInfo.template_id = selectedId.value; showSuccessToast('模板应用成功'); router.push('/home') }
}
const goBack = () => router.back()
</script>

<template>
  <div class="template-container">
    <div class="template-header">
      <van-icon name="arrow-left" class="back-btn" @click="goBack" />
      <h1 class="header-title">选择模板</h1>
      <div class="placeholder"></div>
    </div>
    <div class="template-grid">
      <div v-for="template in templateStore.templateList" :key="template.id" class="template-card" :class="{ selected: selectedId === template.id }" @click="selectTemplate(template)">
        <div class="card-preview" :style="{ background: getTemplateStyle(template.style).bg }">
          <div class="preview-header" :style="{ background: getTemplateStyle(template.style).gradient }"><span class="preview-title">{{ template.name }}</span></div>
          <div class="preview-content">
            <div class="preview-block" :style="{ background: getTemplateStyle(template.style).primary + '20' }"></div>
            <div class="preview-block" :style="{ background: getTemplateStyle(template.style).primary + '15' }"></div>
            <div class="preview-block" :style="{ background: getTemplateStyle(template.style).primary + '10' }"></div>
          </div>
        </div>
        <div class="card-footer">
          <span class="template-name">{{ template.name }}</span>
          <van-icon v-if="selectedId === template.id" name="success" class="check-icon" :style="{ color: getTemplateStyle(template.style).primary }" />
        </div>
      </div>
    </div>
    <div class="template-action">
      <van-button type="primary" size="large" round block @click="confirmTemplate">应用模板</van-button>
    </div>
  </div>
</template>

<style scoped>
.template-container { min-height: 100vh; background: #f5f9f6; }
.template-header { position: sticky; top: 0; height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; background: white; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); z-index: 100; }
.back-btn { font-size: 22px; color: #333; cursor: pointer; }
.header-title { margin: 0; font-size: 18px; font-weight: 600; color: #1a1a1a; }
.placeholder { width: 22px; }
.template-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; padding: 16px; }
.template-card { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04); cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.template-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1); }
.template-card.selected { border-color: #4CAF50; }
.card-preview { height: 160px; padding: 8px; }
.preview-header { height: 32px; border-radius: 8px; display: flex; align-items: center; padding: 0 8px; }
.preview-title { font-size: 12px; color: white; font-weight: 500; }
.preview-content { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.preview-block { height: 24px; border-radius: 4px; }
.card-footer { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-top: 1px solid #f0f0f0; }
.template-name { font-size: 14px; font-weight: 500; color: #1a1a1a; }
.check-icon { font-size: 18px; font-weight: bold; }
.template-action { position: fixed; bottom: 0; left: 0; right: 0; padding: 16px; background: white; box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.04); }
.template-action :deep(.van-button) { height: 48px; font-size: 16px; font-weight: 500; background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%); border: none; }
@media (min-width: 768px) { .template-grid { max-width: 800px; margin: 0 auto; grid-template-columns: repeat(3, 1fr); } }
</style>
