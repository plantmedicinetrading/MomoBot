<template>
  <n-card title="Today's P&L" class="pnl-card">
    <n-table bordered single-line size="small" class="pnl-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Trades</th>
          <th>Shares</th>
          <th>Realised</th>
          <th>Diff/Share</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in data" :key="row.ticker">
          <td><strong>{{ row.ticker }}</strong></td>
          <td>{{ row.trades }}</td>
          <td>{{ row.shares }}</td>
          <td :class="plClass(row.realised)">${{ Number(row.realised).toFixed(2) }}</td>
          <td :class="plClass(row.realisedDiffPerShare)">${{ Number(row.realisedDiffPerShare).toFixed(2) }}</td>
        </tr>
      </tbody>
      <tfoot>
        <tr class="totals-row">
          <td><strong>Totals</strong></td>
          <td></td>
          <td><strong>{{ totalShares }}</strong></td>
          <td :class="plClass(totalRealised)"><strong>${{ totalRealised.toFixed(2) }}</strong></td>
          <td :class="plClass(weightedAvgDiffPerShare)"><strong>${{ weightedAvgDiffPerShare.toFixed(2) }}</strong></td>
        </tr>
      </tfoot>
    </n-table>
  </n-card>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue'
import type { PropType } from 'vue'
import { NCard, NTable } from 'naive-ui'

interface PnLRow {
  ticker: string
  trades: number
  shares: number
  realised: number
  realisedDiffPerShare: number
}

export default defineComponent({
  name: 'TodayPnLTable',
  components: { NCard, NTable },
  props: {
    data: {
      type: Array as PropType<PnLRow[]>,
      required: true
    }
  },
  setup(props) {
    const totalShares = computed(() => props.data.reduce((sum, row) => sum + row.shares, 0))
    const totalRealised = computed(() => props.data.reduce((sum, row) => sum + row.realised, 0))
    const weightedAvgDiffPerShare = computed(() => {
      return totalShares.value ? totalRealised.value / totalShares.value : 0
    })
    const plClass = (val: number) => {
      if (val > 0) return 'pl-up'
      if (val < 0) return 'pl-down'
      return ''
    }
    return {
      totalShares,
      totalRealised,
      weightedAvgDiffPerShare,
      plClass
    }
  }
})
</script>

<style scoped>
.pnl-card {
  margin: 2rem auto 0 auto;
  max-width: 900px;
}
.pnl-table {
  margin-top: 1rem;
  background-color: #fafafa;
}
.pl-up {
  color: #2ecc40;
  font-weight: bold;
}
.pl-down {
  color: #e74c3c;
  font-weight: bold;
}
.totals-row {
  background: #f5f5f5;
}
@media (max-width: 900px) {
  .pnl-card {
    max-width: 100%;
  }
}
</style> 