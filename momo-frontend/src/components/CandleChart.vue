<template>
  <n-card :title="`Live Chart${props.symbol ? ' — ' + props.symbol : ''}`" style="height: 100%;">
    <div ref="chartContainer" style="height: 500px; width: 100%;"></div>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { createChart } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts';
import { NCard } from 'naive-ui';

const props = defineProps<{
  symbol: string,
  timeframe: '10s' | '1m' | '5m',
  breakoutLevels: number[], // e.g. [breakout1, breakout2]
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

const chartContainer = ref<HTMLDivElement | null>(null);
let chart: IChartApi | null = null;
let candleSeries: ISeriesApi<'Candlestick'> | null = null;
let breakoutLines: any[] = [];

function drawBreakoutLines() {
  breakoutLines.forEach(line => candleSeries?.removePriceLine(line));
  breakoutLines = [];
  if (!candleSeries) return;
  props.breakoutLevels.forEach(level => {
    const line = candleSeries!.createPriceLine({
      price: level,
      color: 'orange',
      lineWidth: 2,
      lineStyle: 2,
      axisLabelVisible: true,
      title: 'Breakout'
    });
    breakoutLines.push(line);
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

onMounted(() => {
  if (!chartContainer.value) return;
  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 400,
    layout: { background: { color: '#fff' }, textColor: '#333' },
    grid: { vertLines: { color: '#eee' }, horzLines: { color: '#eee' } },
    timeScale: { timeVisible: true, secondsVisible: props.timeframe === '10s' }
  });
  candleSeries = chart.addCandlestickSeries();
  candleSeries.setData(props.candles.map(c => ({
    time: c.time as UTCTimestamp,
    open: c.open,
    high: c.high,
    low: c.low,
    close: c.close
  })));
  drawBreakoutLines();
  drawTradeMarkers();
});

onBeforeUnmount(() => {
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
</script> 