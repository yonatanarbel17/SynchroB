import { useNavigate, useLocation } from 'react-router-dom'
import LogoIcon from './LogoIcon'

const nav = [
  {
    label: 'Dashboard', path: '/seeker',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="1" y="1" width="6" height="6" rx="1.5" fill="currentColor" /><rect x="9" y="1" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.4" /><rect x="1" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.4" /><rect x="9" y="9" width="6" height="6" rx="1.5" fill="currentColor" opacity="0.4" /></svg>
  },
  {
    label: 'My Needs', path: '/seeker/needs',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
  },
  {
    label: 'Matches', path: '/seeker/chat',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="5" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" /><circle cx="11" cy="8" r="3" stroke="currentColor" strokeWidth="1.5" /></svg>
  },
  {
    label: 'Blueprints', path: '/seeker/blueprint',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" /><path d="M5 8h6M5 5.5h3M5 10.5h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" /></svg>
  },
  {
    label: 'Marketplace', path: '/seeker/marketplace',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 5h12l-1.5 7H3.5L2 5Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /><path d="M5 5V3.5A1.5 1.5 0 0 1 6.5 2h3A1.5 1.5 0 0 1 11 3.5V5" stroke="currentColor" strokeWidth="1.5" /></svg>
  },
  {
    label: 'Settings', path: '/seeker/settings',
    icon: <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" /><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.22 3.22l1.42 1.42M11.36 11.36l1.42 1.42M3.22 12.78l1.42-1.42M11.36 4.64l1.42-1.42" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" /></svg>
  },
]

export default function Sidebar({ collapsed, onToggle }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()

  return (
    <aside style={{
      width: collapsed ? 0 : 240,
      minWidth: collapsed ? 0 : 240,
      height: '100vh',
      background: '#FAF8F5',
      borderRight: '1px solid #E2D9CE',
      display: 'flex',
      flexDirection: 'column',
      padding: collapsed ? 0 : '28px 16px',
      overflow: 'hidden',
      transition: 'width 0.25s ease, min-width 0.25s ease, padding 0.25s ease',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '0 8px', marginBottom: 32 }}>
        <LogoIcon size={26} />
        <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 15, letterSpacing: '0.04em', color: '#1A1410', whiteSpace: 'nowrap' }}>SYNCHRO B</span>
      </div>

      {/* Nav */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
        {nav.map(item => {
          const active = pathname === item.path || (item.path !== '/seeker' && pathname.startsWith(item.path))
          return (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', borderRadius: 8,
                background: active ? '#F0EBE3' : 'transparent',
                color: active ? '#7C5C3E' : '#8A7A6A',
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: active ? 600 : 500,
                fontSize: 14, textAlign: 'left', whiteSpace: 'nowrap',
                transition: 'background 0.15s',
              }}
            >
              {item.icon}
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* User */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '16px 12px 10px', borderTop: '1px solid #E2D9CE' }}>
        <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#7C5C3E', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 13, color: '#fff', flexShrink: 0 }}>AC</div>
        <div>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 13, color: '#1A1410' }}>Acme Corp</div>
          <div style={{ fontSize: 11, color: '#8A7A6A' }}>Seeker</div>
        </div>
      </div>
    </aside>
  )
}
