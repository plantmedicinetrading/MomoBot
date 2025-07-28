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
                <div v-if="pos.stop !== undefined && pos.last_price !== undefined" class="level-indicator">
                  <span class="level-price">${{ Number(pos.stop).toFixed(2) }}</span>
                  <span :class="levelDiffClass(pos.stop, pos.last_price)" class="level-diff">
                    {{ getLevelDiff(pos.stop, pos.last_price) }}
                  </span>
                </div>
                <span v-else-if="pos.stop !== undefined">${{ Number(pos.stop).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <div v-if="pos.tp1 !== undefined && pos.last_price !== undefined" class="level-indicator">
                  <span class="level-price">${{ Number(pos.tp1).toFixed(2) }}</span>
                  <span :class="levelDiffClass(pos.tp1, pos.last_price)" class="level-diff">
                    {{ getLevelDiff(pos.tp1, pos.last_price) }}
                  </span>
                </div>
                <span v-else-if="pos.tp1 !== undefined">${{ Number(pos.tp1).toFixed(2) }}</span>
                <span v-else>-</span>
              </td>
              <td>
                <div v-if="pos.tp2 !== undefined && pos.last_price !== undefined" class="level-indicator">
                  <span class="level-price">${{ Number(pos.tp2).toFixed(2) }}</span>
                  <span :class="levelDiffClass(pos.tp2, pos.last_price)" class="level-diff">
                    {{ getLevelDiff(pos.tp2, pos.last_price) }}
                  </span>
                </div>
                <span v-else-if="pos.tp2 !== undefined">${{ Number(pos.tp2).toFixed(2) }}</span>
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
import { io, Socket } from 'socket.io-client'
import TodayPnLTable from './TodayPnLTable.vue'

interface Position {
  symbol: string
  size?: number
  entry_price?: number
  last_price?: number
  tp1?: number
  tp2?: number
  stop?: number
  unrealized?: number
  diff_per_share?: number
}

export default {
  name: 'PositionsTable',
  components: { NCard, NTable, NButton, TodayPnLTable },
  setup() {
    const positions = ref<Position[]>([])
    const message = useMessage()
    const tradeHistory = ref<any[]>([])
    let socket: Socket | null = null

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

    // Setup socket connection for real-time updates
    const setupSocketConnection = () => {
      socket = io('http://localhost:5050')
      
      socket.on('connect', () => {
        console.log('✅ PositionsTable connected to socket server')
      })

      // Listen for price updates to update current price in real-time
      socket.on('price_update', (data: any) => {
        const idx = positions.value.findIndex(p => p.symbol === data.ticker)
        if (idx !== -1) {
          // Update the current price with the mid price from bid/ask
          const midPrice = (data.ask + data.bid) / 2
          positions.value[idx].last_price = midPrice
          
          // Recalculate unrealized P/L and diff per share
          const position = positions.value[idx]
          if (position.size && position.entry_price) {
            const diffPerShare = midPrice - position.entry_price
            position.diff_per_share = diffPerShare
            position.unrealized = diffPerShare * position.size
          }
        }
      })
    }

    // Calculate difference from a level to current price
    const getLevelDiff = (level: number, currentPrice: number) => {
      const diff = currentPrice - level
      const sign = diff >= 0 ? '+' : ''
      return `${sign}$${diff.toFixed(2)}`
    }

    // Get CSS class for level difference
    const levelDiffClass = (level: number, currentPrice: number) => {
      const diff = currentPrice - level
      if (Math.abs(diff) < 0.01) return 'level-at-target' // Within 1 cent
      return diff > 0 ? 'level-above' : 'level-below'
    }

    onMounted(() => {
      fetchPositions()
      fetchTradeHistory()
      setupSocketConnection()
      
      // Poll for position updates every 5 seconds as backup
      setInterval(fetchPositions, 5000)
      setInterval(fetchTradeHistory, 60000)
    })

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
      closePosition,
      getLevelDiff,
      levelDiffClass
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

/* Level indicator styles */
.level-indicator {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.level-price {
  font-weight: 500;
  font-size: 0.9em;
}

.level-diff {
  font-size: 0.8em;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  text-align: center;
  min-width: 60px;
  display: inline-block;
}

.level-above {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.level-below {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.level-at-target {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
  font-weight: bold;
}

/* Hover effects for better UX */
.level-indicator:hover .level-diff {
  transform: scale(1.05);
  transition: transform 0.1s ease;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
  .level-indicator {
    flex-direction: row;
    align-items: center;
    gap: 4px;
  }
  
  .level-diff {
    min-width: 50px;
    font-size: 0.75em;
  }
}
</style> 