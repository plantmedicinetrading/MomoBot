import { createApp } from 'vue'
import App from './App.vue'

import { createNaiveUI } from './naive'
import router from './router'

const app = createApp(App)

// Custom Naive setup (optional, reusable for theming and tree-shaking)
app.use(createNaiveUI())
app.use(router)

app.mount('#app')