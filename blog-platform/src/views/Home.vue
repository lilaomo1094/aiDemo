<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useTemplateStore } from '../stores/template'

interface Blog { id: number; title: string; cover: string; summary: string; created_at: string }

const router = useRouter()
const userStore = useUserStore()
const templateStore = useTemplateStore()

const blogs = ref<Blog[]>([])
const loading = ref(false)
const refreshing = ref(false)

const currentTemplate = computed(() => templateStore.currentTemplate || templateStore.templateList[0])
const templateStyles = computed(() => {
  const config = currentTemplate.value?.config_json || {}
  return { primaryColor: config.primaryColor || '#4CAF50', backgroundColor: config.backgroundColor || '#F5F9F6' }
})

const mockBlogs: Blog[] = [
  { id: 1, title: '探索 Vue 3 的 Composition API', cover: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=400', summary: 'Vue 3 引入的 Composition API 为我们提供了一种更灵活、更可复用的代码组织方式...', created_at: '2024-01-15' },
  { id: 2, title: 'TypeScript 入门指南', cover: 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=400', summary: 'TypeScript 是 JavaScript 的超集，它为 JS 带来了类型系统...', created_at: '2024-01-12' },
  { id: 3, title: 'CSS Grid 布局完全指南', cover: 'https://images.unsplash.com/photo-1507721999472-8d4421c4af2?w=400', summary: 'CSS Grid 是一个强大的二维布局系统...', created_at: '2024-01-10' },
  { id: 4, title: 'Node.js 性能优化实践', cover: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400', summary: '本文分享了一些在生产环境中实践的 Node.js 性能优化技巧...', created_at: '2024-01-08' },
  { id: 5, title: '响应式设计最佳实践', cover: 'https://images.unsplash.com/photo-1517134191118-9d595e4c8c2b?w=400', summary: '现代 Web 开发中，响应式设计已经成为标配...', created_at: '2024-01-05' },
  { id: 6, title: '前端工程化探索', cover: 'https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=400', summary: '随着项目规模的增长，前端工程化的重要性日益凸显...', created_at: '2024-01-03' }
]

const loadBlogs = () => { loading.value = true; setTimeout(() => { blogs.value = mockBlogs; loading.value = false }, 500) }
const onRefresh = () => { setTimeout(() => { refreshing.value = false; loadBlogs() }, 1000) }
const goToProfile = () => router.push('/profile')

onMounted(() => { loadBlogs() })
</script>

<template>
  <div class="home-container" :style="{ backgroundColor: templateStyles.backgroundColor }">
    <div class="home-header" :style="{ backgroundColor: templateStyles.primaryColor }">
      <van-icon name="arrow-left" class="back-btn" @click="goToProfile" />
      <h1 class="blog-title">{{ userStore.userInfo?.nickname || '我的博客' }}</h1>
      <van-icon name="user-circle-o" class="user-btn" @click="goToProfile" />
    </div>
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <div class="waterfall-container">
        <div class="waterfall-column" v-for="(column, colIndex) in [[0,1,2], [3,4,5]]" :key="colIndex">
          <div v-for="blog in column.map(i => blogs[i]).filter(Boolean)" :key="blog.id" class="blog-card">
            <div class="card-cover"><img :src="blog.cover" :alt="blog.title" /></div>
            <div class="card-content">
              <h3 class="card-title">{{ blog.title }}</h3>
              <p class="card-summary">{{ blog.summary }}</p>
              <span class="card-date">{{ blog.created_at }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="loading" class="loading"><van-loading type="spinner" /></div>
    </van-pull-refresh>
  </div>
</template>

<style scoped>
.home-container { min-height: 100vh; padding-bottom: 20px; }
.home-header { position: sticky; top: 0; height: 56px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; z-index: 100; }
.back-btn, .user-btn { font-size: 22px; color: white; cursor: pointer; }
.blog-title { margin: 0; font-size: 18px; font-weight: 600; color: white; }
.waterfall-container { display: flex; gap: 12px; padding: 16px; }
.waterfall-column { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.blog-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06); transition: transform 0.3s; }
.blog-card:hover { transform: translateY(-4px); }
.card-cover { width: 100%; height: 150px; overflow: hidden; }
.card-cover img { width: 100%; height: 100%; object-fit: cover; }
.card-content { padding: 12px; }
.card-title { margin: 0 0 8px; font-size: 15px; font-weight: 600; color: #1a1a1a; }
.card-summary { margin: 0 0 8px; font-size: 13px; color: #666; }
.card-date { font-size: 12px; color: #999; }
.loading { display: flex; justify-content: center; padding: 20px; }
@media (min-width: 768px) { .waterfall-container { max-width: 900px; margin: 0 auto; gap: 16px; } .card-cover { height: 180px; } }
</style>
