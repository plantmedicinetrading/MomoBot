// naive.ts
import {
    create,
    NButton,
    NInput,
    NCard,
    NTag,
    NGrid,
    NGridItem,
    NStatistic,
    NText,
    NDivider,
    NSpin
  } from 'naive-ui'
  
  export const createNaiveUI = () =>
    create({
      components: [
        NButton,
        NInput,
        NCard,
        NTag,
        NGrid,
        NGridItem,
        NStatistic,
        NText,
        NDivider,
        NSpin
      ]
    })