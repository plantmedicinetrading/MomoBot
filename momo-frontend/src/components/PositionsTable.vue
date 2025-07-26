<template>
  <div class="positions-layout">
    
    <div class="positions-col table-col">
      <n-card title="Open Positions" class="positions-card">
        <n-table bordered single-line size="small" class="positions-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Shares</th>
              <th>Current Price</th>
              <th>Bid</th>
              <th>Ask</th>
              <th>Entry Price</th>
              <th>Unrealized P/L</th>
              <th>Diff/Share</th>
              <th>Stop Loss</th>
              <th>TP1</th>
              <th>TP2</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pos in positions" :key="pos.symbol">
              <td><strong>{{ pos.symbol }}</strong></td>
              <td>{{ pos.size ?? '-' }}</td>
              <td>
                <span v-if="pos.last_price !== undefined">${{ Number(pos.last_price).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="pos.bid !== undefined">${{ Number(pos.bid).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="pos.ask !== undefined">${{ Number(pos.ask).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="pos.entry_price !== undefined">${{ Number(pos.entry_price).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td :class="plClass(pos)">
                <span v-if="pos.unrealized !== undefined">
                  ${{ pos.unrealized.toFixed(2) }} ({{ ((pos.unrealized / ((pos.size ?? 0) * (pos.entry_price ?? 0))) * 100).toFixed(2) }}%)
                </span>
                <span v-else>-</span>
              </td>
              <td :class="diffClass(pos)">
                <span v-if="pos.diff_per_share !== undefined">
                  ${{ pos.diff_per_share.toFixed(2) }}
                </span>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="pos.stop !== undefined">${{ Number(pos.stop).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="pos.tp1 !== undefined">${{ Number(pos.tp1).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <span v-if="pos.tp2 !== undefined">${{ Number(pos.tp2).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <n-button type="error" size="small" @click="closePosition(pos.symbol)">
                  Close Position
                </n-button>
              </td>
            </tr>
            <tr v-if="positions.length === 0">
              <td colspan="10" style="text-align: center;">No open positions</td>
            </tr>
          </tbody>
        </n-table>
      </n-card>
    </div>
  </div>
</template>

<script lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NCard, NTable, NButton, useMessage } from 'naive-ui'
import TodayPnLTable from './TodayPnLTable.vue'

interface Position {
  symbol: string
  size?: number
  entry_price?: number
  ask?: number
  bid?: number
  last_price?: number
  tp1?: number
  tp2?: number
  stop?: number
  unrealized?: number
  diff_per_share?: number
}

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
  profit_loss: number
}

export default {
  name: 'PositionsTable',
  components: { NCard, NTable, NButton, TodayPnLTable },
  setup() {
    const positions = ref<Position[]>([])
    const message = useMessage()
    const tradeHistory = ref<any[]>([])

    // Fetch open positions from backend
    const fetchPositions = async () => {
      try {
        const res = await fetch('http://localhost:5050/positions')
        const data = await res.json()
        positions.value = data.map((pos: any) => {
          return {
            ...pos
          }
        })
      } catch (e) {
        positions.value = []
      }
    }

    // Fetch trade history for PnL summary
    const fetchTradeHistory = async () => {
      try {
        const res = await fetch('http://localhost:5050/trade-history')
        const trades = await res.json()
        tradeHistory.value = trades
      } catch (e) {
        tradeHistory.value = []
      }
    }

    // Listen for price_update events to update ask in real time
    onMounted(() => {
      fetchPositions()
      fetchTradeHistory()
      setInterval(fetchPositions, 5000)
      setInterval(fetchTradeHistory, 60000)
      // SocketIO price update
      if ((window as any).socket) {
        (window as any).socket.on('price_update', (data: any) => {
          const idx = positions.value.findIndex(p => p.symbol === data.ticker)
          if (idx !== -1) {
            positions.value[idx].ask = data.ask
          }
        })
      }
    })

    function getEasternDayBounds(date = new Date()) {
      // Get the current date in ET
      const options = { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' };
      const etDateString = date.toLocaleDateString('en-US', options as Intl.DateTimeFormatOptions);
      const [month, day, year] = etDateString.split('/');
      const start = new Date(`${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T00:00:00-05:00`);
      const end = new Date(start.getTime() + 24 * 60 * 60 * 1000);
      return [start.getTime(), end.getTime()];
    }

    const todayPnLSummary = computed(() => {
      const now = new Date();
      // Get ET midnight for today (assume UTC-4 for July)
      const ET_OFFSET = 4 * 60 * 60 * 1000; // 4 hours in ms
      const etMidnight = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0) + ET_OFFSET);
      const startOfDay = etMidnight.getTime();
      const endOfDay = startOfDay + 24 * 60 * 60 * 1000;
      // Filter trades for today (convert UTC to ET by subtracting 4 hours)
      const todaysTrades = tradeHistory.value.filter(trade => {
        const exitUTC = new Date(trade.exit_time);
        const exitET = exitUTC.getTime() - ET_OFFSET;
        return exitET >= startOfDay && exitET < endOfDay;
      });
      console.log('TODAYS TRADES:', todaysTrades);
      // Group by symbol
      const summary: Record<string, { ticker: string, trades: number, shares: number, realised: number, realisedDiffPerShare: number }> = {}
      for (const trade of todaysTrades) {
        const shares = Number(trade.shares) || 0
        const pl = Number(trade.profit_loss) || 0
        if (!summary[trade.symbol]) {
          summary[trade.symbol] = {
            ticker: trade.symbol,
            trades: 0,
            shares: 0,
            realised: 0,
            realisedDiffPerShare: 0
          }
        }
        summary[trade.symbol].trades += 1
        summary[trade.symbol].shares += shares
        summary[trade.symbol].realised += pl
      }
      // Calculate realisedDiffPerShare
      for (const sym in summary) {
        const s = summary[sym]
        s.realisedDiffPerShare = s.shares ? s.realised / s.shares : 0
      }
      return Object.values(summary)
    })

    // Color coding for P/L
    const plClass = (pos: Position) => {
      if (pos.unrealized === undefined) return ''
      return pos.unrealized > 0 ? 'pl-up' : pos.unrealized < 0 ? 'pl-down' : ''
    }
    const diffClass = (pos: Position) => {
      if (pos.diff_per_share === undefined) return ''
      return pos.diff_per_share > 0 ? 'pl-up' : pos.diff_per_share < 0 ? 'pl-down' : ''
    }

    // Close position handler
    const closePosition = async (symbol: string) => {
      try {
        const res = await fetch('http://localhost:5050/close-position', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol })
        })
        const data = await res.json()
        if (res.ok) {
          message.success(`Closed position for ${symbol}`)
          await fetchPositions() // Refresh open positions after close
        } else {
          message.error(data.error || 'Failed to close position')
        }
      } catch (e) {
        message.error('Failed to close position')
      }
    }

    return {
      positions,
      message,
      todayPnLSummary,
      plClass,
      diffClass,
      closePosition
    }
  }
}
</script>

<style scoped>
.positions-layout {
  display: flex;
  flex-direction: row;
  gap: 2rem;
  align-items: flex-start;
}
.positions-col {
  flex: 1 1 0;
  min-width: 0;
}
.ticker-col {
  max-width: 400px;
}
.table-col {
  flex: 2 1 0;
}
@media (max-width: 900px) {
  .positions-layout {
    flex-direction: column;
  }
  .ticker-col, .table-col {
    max-width: 100%;
  }
}
.positions-card {
  margin: 0;
}
.positions-table {
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
</style> 