import { computed } from 'vue'

// Ergaenzt um Deutsch (fenfa-portal). Ersetzt die Datei aus dem Fenfa-Quellcode.
function detectLanguage(): 'zh' | 'en' | 'de' {
  const lang = navigator.language.toLowerCase()
  if (lang.startsWith('zh')) return 'zh'
  if (lang.startsWith('de')) return 'de'
  return 'en'
}

const translations = {
  zh: {
    loading: '加载中...',
    error: {
      title: '页面暂时不可用',
      loadFailed: '加载产品信息失败'
    },
    hero: {
      productCenter: '多平台分发中心',
      legacyPage: '兼容分发页',
      subtitle: '同一页面展示全部可用平台版本，按你的设备优先推荐最合适的下载项。',
      recommended: '推荐'
    },
    actions: {
      install: '安装',
      installing: '正在安装...',
      download: '下载',
      bindDevice: '绑定设备',
      scan: '扫码访问',
      unavailable: '暂不可用'
    },
    variant: {
      identifier: '标识',
      version: '版本',
      build: '构建',
      minOS: '最低系统',
      updatedAt: '更新时间',
      allVersions: '可用版本',
      iosHint: 'iOS 首次安装前需要先绑定当前设备 UDID。'
    },
    time: {
      justNow: '刚刚',
      minutesAgo: '分钟前',
      hoursAgo: '小时前',
      daysAgo: '天前',
      weeksAgo: '周前',
      monthsAgo: '个月前'
    }
  },
  en: {
    loading: 'Loading...',
    error: {
      title: 'This page is temporarily unavailable',
      loadFailed: 'Failed to load product information'
    },
    hero: {
      productCenter: 'Multi-platform Distribution',
      legacyPage: 'Compatibility Page',
      subtitle: 'All platform builds live on one page, with a recommendation based on the current device.',
      recommended: 'Recommended'
    },
    actions: {
      install: 'Install',
      installing: 'Installing...',
      download: 'Download',
      bindDevice: 'Bind Device',
      scan: 'Scan QR Code',
      unavailable: 'Unavailable'
    },
    variant: {
      identifier: 'Identifier',
      version: 'Version',
      build: 'Build',
      minOS: 'Minimum OS',
      updatedAt: 'Updated',
      allVersions: 'Available Versions',
      iosHint: 'On iOS, the device must be registered before the first install.'
    },
    time: {
      justNow: 'Just now',
      minutesAgo: 'min ago',
      hoursAgo: 'h ago',
      daysAgo: 'd ago',
      weeksAgo: 'w ago',
      monthsAgo: 'mo ago'
    }
  },
  de: {
    loading: 'Wird geladen …',
    error: {
      title: 'Diese Seite ist vorübergehend nicht verfügbar',
      loadFailed: 'Produktinformationen konnten nicht geladen werden'
    },
    hero: {
      productCenter: 'Verteilung für alle Plattformen',
      legacyPage: 'Kompatibilitätsseite',
      subtitle: 'Alle Plattform-Builds auf einer Seite, mit einer Empfehlung passend zum aktuellen Gerät.',
      recommended: 'Empfohlen'
    },
    actions: {
      install: 'Installieren',
      installing: 'Wird installiert …',
      download: 'Herunterladen',
      bindDevice: 'Gerät verbinden',
      scan: 'QR-Code scannen',
      unavailable: 'Nicht verfügbar'
    },
    variant: {
      identifier: 'Kennung',
      version: 'Version',
      build: 'Build',
      minOS: 'Mindest-OS',
      updatedAt: 'Aktualisiert',
      allVersions: 'Verfügbare Versionen',
      iosHint: 'Unter iOS muss das Gerät vor der ersten Installation registriert werden.'
    },
    time: {
      justNow: 'Gerade eben',
      minutesAgo: 'Min. her',
      hoursAgo: 'Std. her',
      daysAgo: 'Tg. her',
      weeksAgo: 'Wo. her',
      monthsAgo: 'Mon. her'
    }
  }
}

export type Language = 'zh' | 'en' | 'de'

let currentLanguage: Language = detectLanguage()

export function useI18n() {
  const t = computed(() => translations[currentLanguage])

  const setLanguage = (lang: Language) => {
    currentLanguage = lang
  }

  const getLanguage = () => currentLanguage

  return { t, setLanguage, getLanguage }
}
