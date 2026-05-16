import { useState } from 'react'
import Sidebar from './Sidebar'

export default function AppShell({ children, topbar }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#FFFFFF' }}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Topbar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 16,
          padding: '16px 32px', borderBottom: '1px solid #E2D9CE',
          background: '#FFFFFF', flexShrink: 0,
        }}>
          {/* Toggle button */}
          <button
            onClick={() => setCollapsed(c => !c)}
            style={{
              width: 34, height: 34, borderRadius: 8, border: '1px solid #E2D9CE',
              background: '#FAF8F5', display: 'flex', alignItems: 'center',
              justifyContent: 'center', flexShrink: 0,
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="1" y="3" width="14" height="1.5" rx="0.75" fill="#8A7A6A" />
              <rect x="1" y="7.25" width="9" height="1.5" rx="0.75" fill="#8A7A6A" />
              <rect x="1" y="11.5" width="14" height="1.5" rx="0.75" fill="#8A7A6A" />
            </svg>
          </button>
          {topbar}
        </div>

        {/* Page content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  )
}
