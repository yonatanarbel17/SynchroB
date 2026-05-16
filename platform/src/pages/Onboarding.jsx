import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import LogoIcon from '../components/LogoIcon'

function SearchIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <circle cx="12" cy="12" r="7.5" stroke="#7C5C3E" strokeWidth="2" />
      <path d="M18 18L24 24" stroke="#7C5C3E" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

function GridIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <rect x="3" y="3" width="9" height="9" rx="2" stroke="#7C5C3E" strokeWidth="1.8" />
      <rect x="16" y="3" width="9" height="9" rx="2" stroke="#7C5C3E" strokeWidth="1.8" />
      <rect x="3" y="16" width="9" height="9" rx="2" stroke="#7C5C3E" strokeWidth="1.8" />
      <rect x="16" y="16" width="9" height="9" rx="2" stroke="#7C5C3E" strokeWidth="1.8" />
    </svg>
  )
}

function Card({ icon, title, description, onClick }) {
  const [hovered, setHovered] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 24,
        width: 340, background: hovered ? '#F0EBE3' : '#FAF8F5',
        border: `1.5px solid ${hovered ? '#7C5C3E' : '#E2D9CE'}`,
        borderRadius: 20, padding: '40px 36px 36px',
        cursor: 'pointer', textAlign: 'left',
        transition: 'all 0.2s ease',
      }}
    >
      <div style={{ width: 52, height: 52, borderRadius: 14, background: '#F0EBE3', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {icon}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 24, letterSpacing: '-0.02em', color: '#1A1410' }}>{title}</div>
        <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 15, lineHeight: '24px', color: '#8A7A6A' }}>{description}</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#7C5C3E', borderRadius: 10, padding: '13px 22px', color: '#fff', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 15 }}>
        Get started
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </div>
    </button>
  )
}

export default function Onboarding() {
  const navigate = useNavigate()
  return (
    <div style={{ minHeight: '100vh', background: '#FFFFFF', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 48, padding: 40 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <LogoIcon size={32} />
        <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 20, letterSpacing: '0.04em', color: '#1A1410' }}>SYNCHRO B</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, textAlign: 'center' }}>
        <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 48, lineHeight: '52px', letterSpacing: '-0.03em', color: '#1A1410', margin: 0 }}>Who are you here as?</h1>
        <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 17, lineHeight: '26px', color: '#8A7A6A', maxWidth: 420, margin: 0 }}>Tell us your role so we can tailor the experience to your needs.</p>
      </div>

      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
        <Card
          icon={<SearchIcon />}
          title="I'm a Seeker"
          description="My company needs specific technology. I want AI to find and integrate the right solution — without building from scratch."
          onClick={() => navigate('/seeker')}
        />
        <Card
          icon={<GridIcon />}
          title="I'm a Provider"
          description="I have technology modules ready to license. I want to reach companies that need exactly what I've built — and close deals faster."
          onClick={() => navigate('/seeker')}
        />
      </div>

      <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#8A7A6A', margin: 0 }}>
        Already have an account?{' '}
        <span style={{ fontWeight: 500, color: '#7C5C3E', textDecoration: 'underline', cursor: 'pointer' }}>Sign in</span>
      </p>
    </div>
  )
}
