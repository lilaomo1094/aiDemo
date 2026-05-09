import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Template {
  id: number
  name: string
  style: string
  config_json: Record<string, any>
  preview_url: string
}

export const templates: Template[] = [
  { id: 1, name: '清新自然', style: 'fresh', config_json: { primaryColor: '#4CAF50', backgroundColor: '#F5F9F6' }, preview_url: '' },
  { id: 2, name: '简约现代', style: 'minimal', config_json: { primaryColor: '#333333', backgroundColor: '#FAFAFA' }, preview_url: '' },
  { id: 3, name: '商务专业', style: 'business', config_json: { primaryColor: '#1976D2', backgroundColor: '#F0F4F8' }, preview_url: '' },
  { id: 4, name: '创意艺术', style: 'creative', config_json: { primaryColor: '#9C27B0', backgroundColor: '#FDF5FF' }, preview_url: '' },
  { id: 5, name: '温馨暖色', style: 'warm', config_json: { primaryColor: '#FF7043', backgroundColor: '#FFF8F5' }, preview_url: '' }
]

export const useTemplateStore = defineStore('template', () => {
  const templateList = ref<Template[]>(templates)
  const currentTemplate = ref<Template | null>(null)

  const setCurrentTemplate = (template: Template) => {
    currentTemplate.value = template
  }

  return { templateList, currentTemplate, setCurrentTemplate }
})
