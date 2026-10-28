<template>
  <div class="language-switcher">
    <button
      @click="nextLanguage"
      class="lang-button"
      :title="titles[locale]"
    >
      <span class="lang-icon"><Icon name="globe" :size="16" /></span>
      <span class="lang-text">{{ labels[locale] }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../i18n'
import Icon from './Icon.vue'

const { locale, setLocale } = useI18n()

const order = ['de', 'en', 'zh'] as const
const labels = { de: 'DE', en: 'EN', zh: '中文' } as const
const titles = {
  de: 'Sprache wechseln (aktuell Deutsch)',
  en: 'Switch language (currently English)',
  zh: '切换语言（当前中文）'
} as const

function nextLanguage() {
  const next = order[(order.indexOf(locale.value) + 1) % order.length]
  setLocale(next)
}
</script>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
}

.lang-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--border);
  color: var(--text-body);
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.lang-button:hover {
  background: var(--bg-hover);
  transform: translateY(-1px);
}

.lang-icon {
  display: flex;
  align-items: center;
}

.lang-text {
  font-weight: 600;
}
</style>
