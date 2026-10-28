// Setzt das Projektlogo in die Admin-Oberflaeche von Fenfa (Anmeldung und Seitenmenue).
// Bricht den Build ab, wenn eine Stelle im Fenfa-Quellcode nicht mehr passt.
import { readFileSync, writeFileSync } from 'node:fs'

function patch(file, from, to) {
  const text = readFileSync(file, 'utf8')
  if (text.split(from).length !== 2) {
    console.error(`Anpassung passt nicht mehr: ${file}`)
    process.exit(1)
  }
  writeFileSync(file, text.replace(from, () => to))
}

const logo = (size, radius, extra = '') =>
  `<img :src="'/portal/logo'" alt="" style="width:${size}px;height:${size}px;border-radius:${radius}px;flex:none;${extra}" />`

patch(
  'web/admin/src/components/Sidebar.vue',
  '<div class="sidebar-header">',
  `<div class="sidebar-header" style="display:flex;align-items:center;gap:12px">${logo(40, 10)}<div style="min-width:0">`
)
patch(
  'web/admin/src/components/Sidebar.vue',
  '<p v-if="!collapsed" class="sidebar-subtitle">{{ t.sidebar.subtitle }}</p>',
  '<p v-if="!collapsed" class="sidebar-subtitle">{{ t.sidebar.subtitle }}</p></div>'
)
patch(
  'web/admin/src/pages/LoginPage.vue',
  '<div class="header-top">',
  `${logo(64, 15, 'display:block;margin:0 0 16px;')}<div class="header-top">`
)
