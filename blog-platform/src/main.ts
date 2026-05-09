import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import vant from 'vant'
import 'vant/lib/index.css'
import './style.css'
import { useUserStore } from './stores/user'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(vant)

const userStore = useUserStore()
userStore.initFromStorage()

app.mount('#app')
