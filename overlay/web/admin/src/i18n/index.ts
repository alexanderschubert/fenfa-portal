import { ref, computed } from 'vue'
import zh from './zh'
import en from './en'
import de from './de'

// Ergaenzt um Deutsch (fenfa-portal). Ersetzt die Datei aus dem Fenfa-Quellcode.
type Locale = 'zh' | 'en' | 'de'
type Messages = typeof zh

const messages: Record<Locale, Messages> = {
  zh,
  en,
  de
}

const LOCALE_KEY = 'fenfa_admin_locale'
const LOCALES: Locale[] = ['de', 'en', 'zh']

// Gespeicherte Sprache, sonst Deutsch
let savedLocale: Locale | null = null
try {
  const stored = localStorage.getItem(LOCALE_KEY) as Locale | null
  if (stored && LOCALES.includes(stored)) savedLocale = stored
} catch (e) {
  // localStorage nicht verfuegbar
}
const currentLocale = ref<Locale>(savedLocale || 'de')

export function useI18n() {
  const locale = computed(() => currentLocale.value)

  const t = computed(() => messages[currentLocale.value])

  function setLocale(newLocale: Locale) {
    currentLocale.value = newLocale
    try {
      localStorage.setItem(LOCALE_KEY, newLocale)
    } catch (e) {
      console.warn('Failed to save locale:', e)
    }
  }

  return {
    locale,
    t,
    setLocale
  }
}
