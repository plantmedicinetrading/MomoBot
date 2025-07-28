import { createRouter, createWebHistory } from 'vue-router'
import PositionsTable from './components/PositionsTable.vue'

import TradeHistory from './components/TradeHistory.vue'

const routes = [
  {
    path: '/',
    name: 'Positions',
    components: {
      default: PositionsTable,
      // Optionally, you can add TickerSelector as a named view or include it in PositionsTable
    }
  },
  {
    path: '/history',
    name: 'TradeHistory',
    component: TradeHistory
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router 