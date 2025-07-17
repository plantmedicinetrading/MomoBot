import { createApp } from 'vue'
import App from './App.vue'

import { createNaiveUI } from './naive'

const app = createApp(App)

// Custom Naive setup (optional, reusable for theming and tree-shaking)
app.use(createNaiveUI())

app.mount('#app')