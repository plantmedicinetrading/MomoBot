<template>
  <n-card title="Trade History" class="history-card">
    <div class="filters-row">
      <n-date-picker v-model:value="dateRange" type="daterange" clearable placeholder="Date Range" style="max-width: 250px;" />
      <n-select v-model:value="entryTypeFilter" :options="entryTypeOptions" clearable placeholder="Entry Type" style="max-width: 180px;" />
      <n-button type="primary" @click="exportTraderVue" style="margin-left: auto;">Export for TraderVue</n-button>
    </div>
    <n-table bordered single-line size="small" class="history-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Shares</th>
          <th>Entry Price</th>
          <th>Exit Price</th>
          <th>Entry Time</th>
          <th>Exit Time</th>
          <th>Entry Type</th>
          <th>P/L</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="trade in filteredTrades" :key="trade.id">
          <td>{{ trade.symbol }}</td>
          <td>{{ trade.shares }}</td>
          <td>${{ Number(trade.entry_price).toFixed(2) }}</td>
          <td>${{ Number(trade.exit_price).toFixed(2) }}</td>
          <td>{{ toEasternTimeString(trade.entry_time) }}</td>
          <td>{{ toEasternTimeString(trade.exit_time) }}</td>
          <td>{{ trade.entry_type || '-' }}</td>
          <td :class="trade.pl >= 0 ? 'pl-up' : 'pl-down'">
            ${{ Number(trade.pl).toFixed(2) }}
          </td>
          <td>
            <n-button type="error" size="small" @click="deleteTrade(trade.id)">Delete</n-button>
          </td>
        </tr>
        <tr v-if="filteredTrades.length === 0">
          <td colspan="8" style="text-align: center;">No trades yet</td>
        </tr>
      </tbody>
    </n-table>
  </n-card>
</template>

<script lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NCard, NTable, NButton, NDatePicker, NSelect, useMessage } from 'naive-ui'

interface Trade {
  id: string
  symbol: string
  shares: number
  entry_price: number
  exit_price: number
  entry_time: string
  exit_time: string
  entry_type?: string
  pl: number
}

function toEasternTimeString(isoString: string) {
  const date = new Date(isoString)
  return date.toLocaleString('en-US', { timeZone: 'America/New_York' })
}

function toEasternMidnightTimestamp(date: Date) {
  const options = { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' } as const;
  const etDateString = date.toLocaleDateString('en-US', options);
  const [month, day, year] = etDateString.split('/');
  return new Date(`${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T00:00:00-05:00`).getTime();
}

export default {
  name: 'TradeHistory',
  components: { NCard, NTable, NButton, NDatePicker, NSelect },
  setup() {
    const trades = ref<Trade[]>([])
    const dateRange = ref<[number, number] | null>(null)
    const entryTypeFilter = ref<string | null>(null)
    const message = useMessage()

    const entryTypeOptions = [
      { label: '10s', value: '10s' },
      { label: '1m', value: '1m' },
      { label: '5m', value: '5m' }
    ]

    const fetchExecutions = async () => {
      try {
        const res = await fetch('http://localhost:5050/trade-history')
        const tradeRows = await res.json()
        trades.value = tradeRows.map((row: any) => ({
          id: row.id,
          symbol: row.symbol,
          shares: row.shares,
          entry_price: row.entry_price,
          exit_price: row.exit_price,
          entry_time: row.entry_time,
          exit_time: row.exit_time,
          entry_type: row.entry_type,
          pl: row.profit_loss
        }))
      } catch (e) {
        trades.value = []
      }
    }

    const filteredTrades = computed(() => {
      return trades.value.filter(trade => {
        // Date filter
        let dateOk = true
        if (dateRange.value && dateRange.value.length === 2) {
          // Convert picker values to ET day boundaries
          const startET = toEasternMidnightTimestamp(new Date(dateRange.value[0]))
          const endET = toEasternMidnightTimestamp(new Date(dateRange.value[1])) + 24 * 60 * 60 * 1000
          const entryET = new Date(new Date(trade.entry_time).toLocaleString('en-US', { timeZone: 'America/New_York' })).getTime();
          dateOk = entryET >= startET && entryET < endET
        }
        // Entry type filter
        let entryTypeOk = true
        if (entryTypeFilter.value) {
          entryTypeOk = trade.entry_type === entryTypeFilter.value
        }
        return dateOk && entryTypeOk
      })
    })

    const exportTraderVue = () => {
      window.open('http://localhost:5050/tradervue-export', '_blank')
      message.success('Export started!')
    }

    async function deleteTrade(tradeId: string) {
      try {
        await fetch(`http://localhost:5050/trade-history/${tradeId}`, { method: 'DELETE' });
        await fetchExecutions();
        message.success('Trade deleted!');
      } catch (e) {
        message.error('Failed to delete trade');
      }
    }

    onMounted(fetchExecutions)
    return { trades, filteredTrades, dateRange, entryTypeFilter, entryTypeOptions, exportTraderVue, toEasternTimeString, deleteTrade }
  }
}
</script>

<style scoped>
.history-card {
  margin: 2rem auto;
}
.history-table {
  margin-top: 1rem;
  background-color: #fafafa;
}
.filters-row {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1.5rem;
}
.pl-up {
  color: #2ecc40;
  font-weight: bold;
}
.pl-down {
  color: #e74c3c;
  font-weight: bold;
}
</style> 