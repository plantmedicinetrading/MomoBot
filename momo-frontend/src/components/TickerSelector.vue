<template>
  <n-card title="Stock Ticker" class="momo-card">
    <n-input
      v-model:value="ticker" 
      placeholder="Enter Ticker (e.g. SBET)"
      @keyup.enter="submitTicker"
      clearable
    />
    <n-button type="primary" class="mt-2" @click="submitTicker">Send</n-button>

    <n-alert v-if="currentTicker" type="success" class="mt-3">
      Selected: <strong>{{ currentTicker }}</strong>
    </n-alert>

    <n-table bordered single-line size="small" class="quote-table-vertical">
      <tbody v-if="livePrice">
        <tr>
          <th>Ticker</th>
          <td><strong>{{ livePrice.ticker }}</strong></td>
        </tr>
        <tr>
          <th>Ask</th>
          <td :class="colorClass('ask')">${{ livePrice.ask.toFixed(2) }}</td>
        </tr>
        <tr>
          <th>Bid</th>
          <td :class="colorClass('bid')">${{ livePrice.bid.toFixed(2) }}</td>
        </tr>
        <tr>
          <th>Spread</th>
          <td><strong>${{ spread.toFixed(2) }}</strong></td>
        </tr>
        <tr>
          <th>Updated</th>
          <td><n-tag type="info">{{ formattedTime }}</n-tag></td>
        </tr>
        <tr>
          <th>Entry</th>
          <td>
            <n-select
              v-model:value="entryType"
              :options="entryTypes.map(type => ({ label: type, value: type }))"
              placeholder="Select Entry Type"
              class="entry-select"
            />
          </td>
        </tr>
      </tbody>
      <tbody v-else>
        <tr>
          <td colspan="2" style="text-align: center;">
            ⏳ Waiting for price update...
          </td>
        </tr>
      </tbody>
    </n-table>

    <p v-if="entryType">📌 Entry Type: <strong>{{ entryType }}</strong></p>
  </n-card>
</template>

<script lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { io, Socket } from 'socket.io-client'
import {
  NCard, NInput, NButton, NTag, NAlert, NTable, NSelect
} from 'naive-ui'

let socket: Socket

export default {
  components: {
    NCard,
    NInput,
    NButton,
    NTag,
    NAlert,
    NTable,
    NSelect
  },
  setup(_props, { emit }) {
    const ticker = ref('')
    const currentTicker = ref<string | null>(null)
    const entryType = ref('')
    const entryTypes = ['None', '10 Sec PB', '1 Min PB', '5 Min PB']

    const livePrice = ref<{
      ticker: string
      ask: number
      ask_size: number
      bid: number
      bid_size: number
      timestamp: string
    } | null>(null)

    const previous = ref<{ ask: number; bid: number } | null>(null)
    const flashClass = ref('')

    const submitTicker = () => {
      if (!ticker.value) return
      socket.emit('select_ticker', ticker.value)
      emit('symbol-selected', ticker.value)
    }

    const colorClass = (type: 'ask' | 'bid') => {
      if (!previous.value || !livePrice.value) return ''
      const prev = previous.value[type]
      const now = livePrice.value[type]
      return now > prev ? 'price-up' : now < prev ? 'price-down' : ''
    }

    const formattedTime = computed(() => {
      if (!livePrice.value?.timestamp) return ''
      return new Date(livePrice.value.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    })

    const spread = computed(() => {
      if (!livePrice.value) return 0
      return livePrice.value.ask - livePrice.value.bid
    })

    // 🔁 Flash on price update
    watch(livePrice, () => {
      flashClass.value = 'flash'
      setTimeout(() => { flashClass.value = '' }, 300)
    })

    // 🔁 Emit entry type to backend when changed (only if not initial load)
    let initialEntryTypeSet = false
    watch(entryType, (newValue) => {
      if (!initialEntryTypeSet) {
        initialEntryTypeSet = true
        return
      }
      if (currentTicker.value) {
        let mapped = ''
        if (newValue === '10 Sec PB') mapped = '10s'
        else if (newValue === '1 Min PB') mapped = '1m'
        else if (newValue === '5 Min PB') mapped = '5m'
        else if (newValue === 'None') mapped = 'none'
        if (mapped !== '') {
          socket.emit('set_entry_type', {
            symbol: currentTicker.value,
            entry_type: mapped
          })
        }
      }
    })

    onMounted(() => {
      socket = io('http://localhost:5050')
      ;(window as any).socket = socket

      socket.on('connect', () => {
        console.log('✅ Connected to socket server')
        // Request the current selected ticker from backend
        socket.emit('get_selected_ticker')
      })

      socket.on('ticker_selected', (data: any) => {
        console.log('🎯 Ticker selected:', data)
        if (data.ticker) {
          currentTicker.value = data.ticker
          previous.value = null
          livePrice.value = null
          // Don't reset entryType here; let backend send entry_type_set if needed
        } else {
          currentTicker.value = null
          entryType.value = 'None'
        }
      })

      socket.on('price_update', (data: any) => {
        if (data.ticker === currentTicker.value) {
          previous.value = livePrice.value
            ? { ask: livePrice.value.ask, bid: livePrice.value.bid }
            : { ask: data.ask, bid: data.bid }
          livePrice.value = data
        }
      })

      // Listen for backend-driven entry type changes
      socket.on('entry_type_set', (data: any) => {
        if (data.symbol === currentTicker.value) {
          // Map backend value to dropdown label
          let label = 'None'
          if (data.entry_type === '10s') label = '10 Sec PB'
          else if (data.entry_type === '1m') label = '1 Min PB'
          else if (data.entry_type === '5m') label = '5 Min PB'
          entryType.value = label
        }
      })
    })

    return {
      ticker,
      submitTicker,
      currentTicker,
      livePrice,
      spread,
      colorClass,
      formattedTime,
      flashClass,
      entryType,
      entryTypes
    }
  }
}
</script>

<style scoped>
.momo-card {
  max-width: 500px;
  /* margin: 2rem auto; */
  margin: 0 auto;
}
.mt-2 {
  margin-top: 0.5rem;
}
.mt-3 {
  margin-top: 1rem;
}
.quote-table-vertical {
  margin-top: 1rem;
  background-color: #fafafa;
  width: 100%;
}
.quote-table-vertical th {
  text-align: left;
  width: 40%;
  font-weight: 600;
  background: #f5f5f5;
}
.quote-table-vertical td {
  text-align: left;
  width: 60%;
}
.price-up {
  background-color: #d6f5d6;
}
.price-down {
  background-color: #fbdcdc;
}
.flash {
  animation: flashFade 0.3s;
}
@keyframes flashFade {
  0% { background-color: #fffae6; }
  100% { background-color: transparent; }
}
</style>