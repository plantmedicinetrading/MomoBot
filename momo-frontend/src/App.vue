<template>
  <div class="container">
    <h1>Momo Bot</h1>
    <TickerSelector />
  </div>
</template>

<script lang="ts">
import TickerSelector from './components/TickerSelector.vue'

export default {
  components: { TickerSelector }
}
</script>

<style scoped>
.container {
  max-width: 600px;
  margin: auto;
  padding: 2rem;
  font-family: 'Segoe UI', sans-serif;
}
</style>