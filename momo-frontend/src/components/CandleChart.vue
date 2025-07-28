<template>
  <n-card :title="`Live Chart${props.symbol ? ' — ' + props.symbol : ''}`" style="height: 100%;">
    <div class="chart-controls">
      <n-button-group>
        <n-button 
          :type="currentTimeframe === '10s' ? 'primary' : 'default'"
          @click="switchTimeframe('10s')"
          size="small"
        >
          10s
        </n-button>
        <n-button 
          :type="currentTimeframe === '1m' ? 'primary' : 'default'"
          @click="switchTimeframe('1m')"
          size="small"
        >
          1m
        </n-button>
        <n-button 
          :type="currentTimeframe === '5m' ? 'primary' : 'default'"
          @click="switchTimeframe('5m')"
          size="small"
        >
          5m
        </n-button>
      </n-button-group>
      <n-button 
        type="info" 
        size="small" 
        @click="scrollToRealtime"
        :disabled="!chart"
      >
        Go to Realtime
      </n-button>
    </div>
    <div ref="chartContainer" style="height: 500px; width: 100%; position: relative;">
      <!-- Tooltip element -->
      <div ref="tooltip" class="chart-tooltip"></div>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { createChart } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { NCard, NButton, NButtonGroup } from 'naive-ui';
import { io, Socket } from 'socket.io-client';

const props = defineProps<{
  symbol: string,
  timeframe: '10s' | '1m' | '5m',
  breakoutLevels: (number|null)[], // [10s, 1m, 5m] levels
  tradeMarkers: Array<{ time: number, price: number, type: 'entry' | 'tp1' | 'tp2' | 'sl' }>,
  candles: Array<{
    time: number, // UNIX timestamp (seconds)
    open: number,
    high: number,
    low: number,
    close: number,
    volume?: number
  }>
}>();

const emit = defineEmits<{
  timeframeChanged: [timeframe: '10s' | '1m' | '5m']
}>();

const chartContainer = ref<HTMLDivElement | null>(null);
const tooltip = ref<HTMLDivElement | null>(null);
const currentTimeframe = ref<'10s' | '1m' | '5m'>(props.timeframe);
let chart: IChartApi | null = null;
let candleSeries: ISeriesApi<'Candlestick'> | null = null;
let breakoutLines: any[] = [];
let socket: Socket | null = null;

// Real-time update handling
let lastCandle: any = null;
let updateInterval: number | null = null;

function drawBreakoutLines() {
  // Remove all existing breakout lines
  breakoutLines.forEach(line => candleSeries?.removePriceLine(line));
  breakoutLines = [];
  
  if (!candleSeries) return;
  
  // Define colors for each timeframe
  const timeframeColors = {
    '10s': '#FF6B6B', // Red
    '1m': '#4ECDC4',  // Teal
    '5m': '#45B7D1'   // Blue
  };
  
  // Draw breakout lines for each timeframe
  const timeframes = ['10s', '1m', '5m'] as const;
  timeframes.forEach((tf, index) => {
    const level = props.breakoutLevels[index];
    if (level !== null && level !== undefined) {
      const line = candleSeries!.createPriceLine({
        price: level,
        color: timeframeColors[tf],
        lineWidth: 2,
        lineStyle: 2, // Dashed
        axisLabelVisible: true,
        title: `${tf} Breakout`
      });
      breakoutLines.push(line);
    }
  });
}

function drawTradeMarkers() {
  if (!candleSeries) return;
  candleSeries.setMarkers(
    props.tradeMarkers.map(marker => ({
      time: marker.time as UTCTimestamp,
      position: marker.type === 'entry' ? 'belowBar' : 'aboveBar',
      color: marker.type === 'entry' ? 'blue' :
             marker.type === 'tp1' ? 'green' :
             marker.type === 'tp2' ? 'lime' : 'red',
      shape: marker.type === 'entry' ? 'arrowUp' :
             marker.type === 'sl' ? 'arrowDown' : 'circle',
      text: marker.type.toUpperCase(),
      size: 2,
      price: marker.price
    }))
  );
}

function scrollToRealtime() {
  if (chart) {
    chart.timeScale().scrollToRealTime();
  }
}

function switchTimeframe(newTimeframe: '10s' | '1m' | '5m') {
  console.log(`🔄 Switching timeframe from ${currentTimeframe.value} to ${newTimeframe}`);
  currentTimeframe.value = newTimeframe;
  emit('timeframeChanged', newTimeframe);
  
  // Update chart time scale visibility
  if (chart) {
    chart.timeScale().applyOptions({
      secondsVisible: newTimeframe === '10s'
    });
  }
  
  // Clear current data and request new candle data for the selected timeframe
  if (candleSeries) {
    candleSeries.setData([]);
  }
  
  if (socket && props.symbol) {
    console.log(`📡 Requesting candles for ${props.symbol} (${newTimeframe})`);
    socket.emit('request_candles', {
      symbol: props.symbol,
      timeframe: newTimeframe
    });
  }
}

function setupTooltip() {
  if (!chart || !tooltip.value || !candleSeries) return;
  
  // Subscribe to crosshair move events
  chart.subscribeCrosshairMove(param => {
    if (
      param.point === undefined ||
      !param.time ||
      param.point.x < 0 ||
      param.point.x > (chartContainer.value?.clientWidth || 0) ||
      param.point.y < 0 ||
      param.point.y > (chartContainer.value?.clientHeight || 0)
    ) {
      if (tooltip.value) {
        tooltip.value.style.display = 'none';
      }
    } else {
      const data = candleSeries ? param.seriesData.get(candleSeries) : null;
      if (data && tooltip.value && 'close' in data && 'open' in data && 'high' in data && 'low' in data) {
        const candleData = data as { open: number; high: number; low: number; close: number; volume?: number };
        const date = new Date((param.time as number) * 1000);
        const timeStr = date.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        });
        const dateStr = date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        });
        
        const isUp = candleData.close >= candleData.open;
        const color = isUp ? '#26a69a' : '#ef5350';
        
        tooltip.value.innerHTML = `
          <div style="color: ${color}; font-weight: 600; font-size: 14px;">
            ${props.symbol || 'Symbol'}
          </div>
          <div style="font-size: 20px; margin: 8px 0; color: ${color}; font-weight: 600;">
            $${candleData.close.toFixed(2)}
          </div>
          <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
            ${dateStr} ${timeStr}
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
            <div style="color: #666;">Open:</div>
            <div style="color: ${color}; font-weight: 500;">$${candleData.open.toFixed(2)}</div>
            <div style="color: #666;">High:</div>
            <div style="color: ${color}; font-weight: 500;">$${candleData.high.toFixed(2)}</div>
            <div style="color: #666;">Low:</div>
            <div style="color: ${color}; font-weight: 500;">$${candleData.low.toFixed(2)}</div>
            <div style="color: #666;">Close:</div>
            <div style="color: ${color}; font-weight: 500;">$${candleData.close.toFixed(2)}</div>
            <div style="color: #666;">Volume:</div>
            <div style="color: #666;">${(candleData.volume || 0).toLocaleString()}</div>
          </div>
        `;
        
        tooltip.value.style.display = 'block';
        
        // Position tooltip
        let left = param.point.x + 12;
        const containerWidth = chartContainer.value?.clientWidth || 0;
        const tooltipWidth = 200;
        
        // Ensure tooltip doesn't go off-screen
        if (left + tooltipWidth > containerWidth) {
          left = param.point.x - tooltipWidth - 12;
        }
        
        tooltip.value.style.left = left + 'px';
        tooltip.value.style.top = (param.point.y - 100) + 'px';
      }
    }
  });
}

function setupSocketConnection() {
  socket = io('http://localhost:5050');
  
  socket.on('connect', () => {
    console.log('✅ Chart connected to socket server');
    if (props.symbol && socket) {
      socket.emit('request_candles', {
        symbol: props.symbol,
        timeframe: currentTimeframe.value
      });
    }
  });

  // Watch for symbol changes and request candles
  watch(() => props.symbol, (newSymbol) => {
    if (newSymbol && socket) {
      console.log(`🔄 Symbol changed to ${newSymbol}, requesting ${currentTimeframe.value} candles`);
      // Clear existing data when switching symbols
      if (candleSeries) {
        candleSeries.setData([]);
      }
      socket.emit('request_candles', {
        symbol: newSymbol,
        timeframe: currentTimeframe.value
      });
    }
  });

  socket.on('candle_update', (data: any) => {
    console.log('📊 Chart received candle_update:', data);
    if (data.symbol === props.symbol && data.timeframe === currentTimeframe.value) {
      console.log('✅ Processing candle update for current timeframe');
      // Handle bulk candle updates (for historical data)
      if (data.candles && Array.isArray(data.candles)) {
        console.log(`📈 Setting ${data.candles.length} candles for ${data.timeframe}`);
        if (candleSeries) {
          candleSeries.setData(data.candles.map((c: any) => ({
            time: c.time as UTCTimestamp,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close
          })));
        }
      } else {
        // Handle single candle update
        updateCandle(data);
      }
    } else {
      console.log('❌ Ignoring candle update - symbol or timeframe mismatch');
    }
  });

  socket.on('price_update', (data: any) => {
    if (data.ticker === props.symbol) {
      // Update the current candle with real-time price data
      updateCurrentCandle(data);
    }
  });
}

function updateCandle(candleData: any) {
  if (!candleSeries) return;
  
  const candle = {
    time: candleData.time as UTCTimestamp,
    open: candleData.open,
    high: candleData.high,
    low: candleData.low,
    close: candleData.close
  };

  // Check if this candle already exists
  const existingCandle = props.candles.find(c => c.time === candleData.time);
  if (existingCandle) {
    // Update existing candle
    candleSeries.update(candle);
  } else {
    // Add new candle
    candleSeries.update(candle);
  }
}

function updateCurrentCandle(priceData: any) {
  if (!candleSeries || !priceData) return;
  
  const currentPrice = (priceData.ask + priceData.bid) / 2;
  const currentTime = Math.floor(Date.now() / 1000);
  
  // Get the current candle period based on timeframe
  let periodSeconds = 60; // 1m default
  if (currentTimeframe.value === '10s') periodSeconds = 10;
  else if (currentTimeframe.value === '5m') periodSeconds = 300;
  
  const candleStartTime = Math.floor(currentTime / periodSeconds) * periodSeconds;
  
  if (!lastCandle || lastCandle.time !== candleStartTime) {
    // Start a new candle
    lastCandle = {
      time: candleStartTime as UTCTimestamp,
      open: currentPrice,
      high: currentPrice,
      low: currentPrice,
      close: currentPrice
    };
    candleSeries.update(lastCandle);
  } else {
    // Update the current candle
    lastCandle.high = Math.max(lastCandle.high, currentPrice);
    lastCandle.low = Math.min(lastCandle.low, currentPrice);
    lastCandle.close = currentPrice;
    candleSeries.update(lastCandle);
  }
}

onMounted(async () => {
  if (!chartContainer.value) return;
  
  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 400,
    layout: { 
      background: { color: '#fff' }, 
      textColor: '#333' 
    },
    grid: { 
      vertLines: { color: '#eee' }, 
      horzLines: { color: '#eee' } 
    },
    timeScale: { 
      timeVisible: true, 
      secondsVisible: currentTimeframe.value === '10s',
      rightOffset: 12,
      barSpacing: 3,
      fixLeftEdge: true,
      lockVisibleTimeRangeOnResize: true,
      rightBarStaysOnScroll: true,
      borderVisible: false,
      visible: true,
      tickMarkFormatter: (time: number) => {
        const date = new Date(time * 1000);
        if (currentTimeframe.value === '10s') {
          return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit' 
          });
        } else {
          return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
          });
        }
      }
    },
    crosshair: {
      mode: 1,
      vertLine: {
        labelVisible: false,
      },
      horzLine: {
        labelVisible: false,
      }
    },
    rightPriceScale: {
      borderColor: '#ddd',
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: true
    },
    handleScale: {
      axisPressedMouseMove: true,
      mouseWheel: true,
      pinch: true
    }
  });

  candleSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
  });

  // Set initial data
  if (props.candles.length > 0) {
    candleSeries.setData(props.candles.map(c => ({
      time: c.time as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close
    })));
  }

  drawBreakoutLines();
  drawTradeMarkers();
  
  // Setup tooltip
  setupTooltip();
  
  // Setup socket connection for real-time updates
  setupSocketConnection();
  
  // Fit content and scroll to realtime
  await nextTick();
  chart.timeScale().fitContent();
  chart.timeScale().scrollToRealTime();
});

onBeforeUnmount(() => {
  if (updateInterval) {
    clearInterval(updateInterval);
  }
  socket?.disconnect();
  chart?.remove();
});

watch(() => props.candles, (newCandles) => {
  if (candleSeries) {
    candleSeries.setData(newCandles.map(c => ({
      time: c.time as UTCTimestamp,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close
    })));
  }
}, { deep: true });

watch(() => props.breakoutLevels, drawBreakoutLines, { deep: true });
watch(() => props.tradeMarkers, drawTradeMarkers, { deep: true });

watch(() => props.timeframe, (newTimeframe) => {
  currentTimeframe.value = newTimeframe;
  if (chart) {
    chart.timeScale().applyOptions({
      secondsVisible: newTimeframe === '10s'
    });
  }
  // Request candles for the new timeframe
  if (socket && props.symbol) {
    socket.emit('request_candles', {
      symbol: props.symbol,
      timeframe: newTimeframe
    });
  }
});

// Handle window resize
window.addEventListener('resize', () => {
  if (chart && chartContainer.value) {
    chart.applyOptions({ 
      width: chartContainer.value.clientWidth 
    });
  }
});
</script>

<style scoped>
.chart-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.chart-tooltip {
  position: absolute;
  display: none;
  padding: 12px;
  box-sizing: border-box;
  font-size: 12px;
  text-align: left;
  z-index: 1000;
  pointer-events: none;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-width: 200px;
  max-width: 250px;
}
</style> 