<template>
  <n-message-provider>
    <div class="container">
      <nav class="main-nav">
        <router-link to="/" class="nav-link">Positions</router-link>
        <router-link to="/history" class="nav-link">Trade History</router-link>
      </nav>
      <div class="dashboard">
        <div class="sidebar">
          <TickerSelector @symbol-selected="onSymbolSelected" />
          <TodayPnLTable :data="pnlData" />
        </div>
        <div class="main-content">
          <router-view />
          <CandleChart
            :symbol="symbol"
            :timeframe="timeframe"
            :candles="candles"
            :breakoutLevels="breakoutLevels"
            :tradeMarkers="tradeMarkers"
            @timeframe-changed="onTimeframeChanged"
          />
        </div>
      </div>
    </div>
  </n-message-provider>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { io } from 'socket.io-client';
import CandleChart from './components/CandleChart.vue';
import TickerSelector from './components/TickerSelector.vue';
import TodayPnLTable from './components/TodayPnLTable.vue';
import { NMessageProvider } from 'naive-ui';
import axios from 'axios';

const symbol = ref('');
const timeframe = ref<'10s' | '1m' | '5m'>('10s');
const candles = ref<any[]>([]);
const breakoutLevels = ref<number[]>([]);
const tradeMarkers = ref<any[]>([]);
const pnlData = ref<any[]>([]);

let socket: any = null;

function subscribe() {
  if (socket && symbol.value) {
    socket.emit('select_ticker', symbol.value);
    socket.emit('set_entry_type', { symbol: symbol.value, entry_type: timeframe.value });
  }
}

function onSymbolSelected(newSymbol: string) {
  symbol.value = newSymbol;
  timeframe.value = '10s'; // Default to 10s chart when selecting a new ticker
  if (socket && newSymbol) {
    socket.emit('select_ticker', newSymbol);
    socket.emit('set_entry_type', { symbol: newSymbol, entry_type: 'none' });
  }
}

function onTimeframeChanged(newTimeframe: '10s' | '1m' | '5m') {
  timeframe.value = newTimeframe;
  // Don't change the active_entry_type when switching chart timeframes
  // The chart timeframe is just for display purposes
}

async function fetchPnLData() {
  try {
    const resp = await axios.get('http://localhost:5050/trade-history');
    const trades = resp.data;
    // Compute today's P&L summary (Eastern Time)
    const now = new Date();
    const ET_OFFSET = 4 * 60 * 60 * 1000; // 4 hours in ms (adjust for DST if needed)
    const etMidnight = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0) + ET_OFFSET);
    const startOfDay = etMidnight.getTime();
    const endOfDay = startOfDay + 24 * 60 * 60 * 1000;
    const todaysTrades = trades.filter((trade: any) => {
      const exitUTC = new Date(trade.exit_time);
      const exitET = exitUTC.getTime() - ET_OFFSET;
      return exitET >= startOfDay && exitET < endOfDay;
    });
    // Group by symbol
    const summary: Record<string, { ticker: string, trades: number, shares: number, realised: number, realisedDiffPerShare: number }> = {};
    for (const trade of todaysTrades) {
      const shares = Number(trade.shares) || 0;
      const pl = Number(trade.profit_loss) || 0;
      if (!summary[trade.symbol]) {
        summary[trade.symbol] = {
          ticker: trade.symbol,
          trades: 0,
          shares: 0,
          realised: 0,
          realisedDiffPerShare: 0
        };
      }
      summary[trade.symbol].trades += 1;
      summary[trade.symbol].shares += shares;
      summary[trade.symbol].realised += pl;
    }
    // Calculate realisedDiffPerShare
    for (const sym in summary) {
      const s = summary[sym];
      s.realisedDiffPerShare = s.shares ? s.realised / s.shares : 0;
    }
    pnlData.value = Object.values(summary);
  } catch (e) {
    pnlData.value = [];
  }
}

onMounted(() => {
  socket = io('http://localhost:5050');
  subscribe();

  fetchPnLData();

  socket.on('candle_update', (data: any) => {
    // Only handle single candle updates, not bulk updates
    if (!data.candles || !Array.isArray(data.candles)) {
      const idx = candles.value.findIndex(c => c.time === data.time);
      if (idx !== -1) {
        candles.value[idx] = data;
      } else {
        candles.value.push(data);
        if (candles.value.length > 500) candles.value.shift();
      }
    }
  });

  socket.on('breakout', (levels: number[]) => {
    breakoutLevels.value = levels;
  });

  socket.on('trade_marker', (marker: any) => {
    tradeMarkers.value.push(marker);
  });

  // Optionally, listen for trade close events to refresh PnL
  socket.on('trade_closed', () => {
    timeframe.value = '10s'; // Reset to 10s when trade closes
    if (symbol.value && socket) {
      socket.emit('set_entry_type', { symbol: symbol.value, entry_type: 'none' });
    }
    fetchPnLData();
  });
});

onBeforeUnmount(() => {
  socket?.disconnect();
});

watch([symbol, timeframe], fetchPnLData);
</script>

<style scoped>
.container {
  margin: auto;
  padding: 2rem;
  font-family: 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
.main-nav {
  display: flex;
  gap: 2rem;
  font-size: 1.1rem;
}
.nav-link {
  text-decoration: none;
  color: #333;
  font-weight: 500;
}
.nav-link.router-link-exact-active {
  color: #42b983;
  border-bottom: 2px solid #42b983;
}
.dashboard {
  display: flex;
  gap: 2rem;
}
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  min-width: 500px;
}
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}
</style>