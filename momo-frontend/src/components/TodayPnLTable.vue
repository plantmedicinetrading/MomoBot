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
          <td class="totals-label"><strong>Totals</strong></td>
          <td class="totals-trades">{{ totalTrades }}</td>
          <td class="totals-shares"><strong>{{ totalShares }}</strong></td>
          <td :class="['totals-realised', plClass(totalRealised)]">
            <strong>${{ totalRealised.toFixed(2) }}</strong>
          </td>
          <td :class="['totals-diff', plClass(weightedAvgDiffPerShare)]">
            <strong>${{ weightedAvgDiffPerShare.toFixed(2) }}</strong>
          </td>
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
    const totalTrades = computed(() => props.data.reduce((sum, row) => sum + row.trades, 0))
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
      totalTrades,
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
  margin: 0 auto 0 auto;
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

/* Subtle totals styling */
.totals-row {
  background: #f8f9fa;
  border-top: 2px solid #e9ecef;
  font-weight: 600;
}

.totals-label {
  font-weight: 700;
  color: #495057;
  text-align: center;
  background: #e9ecef;
  border-right: 1px solid #dee2e6;
}

.totals-trades {
  text-align: center;
  background: #f8f9fa;
}

.totals-shares {
  text-align: center;
  background: #f8f9fa;
}

.totals-realised {
  text-align: center;
  font-size: 1.1em;
  background: #f1f3f4;
  border-left: 1px solid #dee2e6;
}

.totals-diff {
  text-align: center;
  font-size: 1.1em;
  background: #f1f3f4;
  border-left: 1px solid #dee2e6;
}

/* Subtle hover effect */
.totals-row:hover {
  background: #e9ecef;
  transition: background-color 0.2s ease;
}

/* Responsive adjustments */
@media (max-width: 900px) {
  .pnl-card {
    max-width: 100%;
  }
}

@media (max-width: 600px) {
  .totals-realised,
  .totals-diff {
    font-size: 1em;
  }
}
</style> 