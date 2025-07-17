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
      <th>Entry Type</th>
    </tr>
  </thead>
  <tbody v-if="livePrice">
    <tr :class="flashClass">
      <td><strong>{{ livePrice.ticker }}</strong></td>
      <td :class="colorClass('ask')">${{ livePrice.ask.toFixed(2) }}</td>
      <td :class="colorClass('bid')">${{ livePrice.bid.toFixed(2) }}</td>
      <td><strong>${{ spread.toFixed(2) }}</strong></td>
      <td><n-tag type="info">{{ formattedTime }}</n-tag></td>
      <td><n-select
  v-model:value="entryType"
  :options="entryTypes.map(type => ({ label: type, value: type }))"
  placeholder="Select Entry Type"
  class="entry-select"
/></td>
    </tr>
  </tbody>
</n-table>

<p v-if="entryType">📌 Entry Type: <strong>{{ entryType }}</strong></p>

  </n-card>
</template>

<script lang="ts">
import { ref, onMounted, computed, watch, reactive } from 'vue'
import { io, Socket } from 'socket.io-client'
import { NCard, NInput, NButton, NStatistic, NTag, NAlert, NTable, NSelect } from 'naive-ui'

let socket: Socket

export default {
  components: {
    NCard,
    NInput,
    NButton,
    NStatistic,
    NTag,
    NAlert,
    NTable,
    NSelect
  },
  setup() {
    const ticker = ref('')
    const currentTicker = ref<string | null>(null)
    const entryType = ref('')
    const entryTypes = [
      'None',
      '1-min pullback',
      '5-min pullback'
    ]


    const entryTypesMap = reactive<Record<string, string>>({})

      watch(entryType, (newValue) => {
        if (currentTicker.value) {
          entryTypesMap[currentTicker.value] = newValue
        }
      })
    const colorClass = (type: 'ask' | 'bid') => {
    if (!previous.value || !livePrice.value) return ''
    const prev = previous.value[type]
    const now = livePrice.value[type]
    return now > prev ? 'price-up' : now < prev ? 'price-down' : ''
  }

  const formattedTime = computed(() => {
    if (!livePrice.value?.timestamp) return ''
    return new Date(livePrice.value.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  })

  

    const livePrice = ref<{
      ticker: string
      ask: number
      ask_size: number
      bid: number
      bid_size: number
      timestamp: string
    } | null>(null)

    const previous = ref<{ ask: number; bid: number } | null>(null)

    const submitTicker = () => {
      if (!ticker.value) return
      socket.emit('select_ticker', ticker.value)
    }

    const spread = computed(() => {
      if (!livePrice.value) return 0
      return livePrice.value.ask - livePrice.value.bid
    })

    const askColor = computed(() => {
      if (!previous.value || !livePrice.value) return ''
      return livePrice.value.ask > previous.value.ask ? 'green' : 'red'
    })

    const bidColor = computed(() => {
      if (!previous.value || !livePrice.value) return ''
      return livePrice.value.bid > previous.value.bid ? 'green' : 'red'
    })

    const flashClass = ref('')


      // Trigger flash effect on price update
      watch(livePrice, () => {
        flashClass.value = 'flash'
        setTimeout(() => {
          flashClass.value = ''
        }, 300) // Flash lasts 300ms
      })

    onMounted(() => {
      socket = io('http://localhost:5050')
      ;(window as any).socket = socket

      socket.on('connect', () => {
        console.log('✅ Connected to socket server')
        socket.emit('get_selected_ticker')
      })

      socket.on('ticker_selected', (data: any) => {
        console.log('🎯 Ticker selected:', data)
        currentTicker.value = data.ticker
      })

      socket.on('price_update', (data: any) => {
        console.log('📥 Price update received:', data)

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
      askColor,
      bidColor,
      colorClass,
      formattedTime,
      flashClass,
      entryType,
      entryTypes,
      entryTypesMap
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

.quote-card {
  margin-top: 1rem;
  background-color: #fafafa;
}
</style>