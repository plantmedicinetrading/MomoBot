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

    <n-table bordered single-line size="small" class="quote-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Ask</th>
          <th>Bid</th>
          <th>Spread</th>
          <th>Updated</th>
          <th>Entry</th>
        </tr>
      </thead>
      <tbody v-if="livePrice">
        <tr :class="flashClass">
          <td><strong>{{ livePrice.ticker }}</strong></td>
          <td :class="colorClass('ask')">${{ livePrice.ask.toFixed(2) }}</td>
          <td :class="colorClass('bid')">${{ livePrice.bid.toFixed(2) }}</td>
          <td><strong>${{ spread.toFixed(2) }}</strong></td>
          <td><n-tag type="info">{{ formattedTime }}</n-tag></td>
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
          <td colspan="6" style="text-align: center;">
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
  setup() {
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

    // 🔁 Emit entry type to backend when changed
    watch(entryType, (newValue) => {
      if (currentTicker.value && newValue !== 'None') {
        const mapped = newValue === '10 Sec PB' ? '10s' :
                       newValue === '1 Min PB' ? '1m' :
                       newValue === '5 Min PB' ? '5m' : ''
        if (mapped) {
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
      })

      socket.on('ticker_selected', (data: any) => {
        console.log('🎯 Ticker selected:', data)
        currentTicker.value = data.ticker
        previous.value = null
        livePrice.value = null
        entryType.value = 'None'
      })

      socket.on('price_update', (data: any) => {
        if (data.ticker === currentTicker.value) {
          previous.value = livePrice.value
            ? { ask: livePrice.value.ask, bid: livePrice.value.bid }
            : { ask: data.ask, bid: data.bid }
          livePrice.value = data
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
  margin: 2rem auto;
}

.mt-2 {
  margin-top: 0.5rem;
}

.mt-3 {
  margin-top: 1rem;
}

.quote-table {
  margin-top: 1rem;
  background-color: #fafafa;
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