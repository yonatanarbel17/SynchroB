import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'

const chips = ['Fraud detection', 'Payments SDK', 'Document extraction', 'Voice authentication', 'AI / LLM integration']

export default function SeekerStart() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  function handleSubmit() {
    if (query.trim()) navigate('/seeker/chat', { state: { query } })
    else navigate('/seeker/chat')
  }

  return (
    <AppShell topbar={
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flex: 1 }}>
        <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 16, color: '#1A1410' }}>John</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#FAF8F5', border: '1px solid #E2D9CE', borderRadius: 8, padding: '7px 14px' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22C55E' }} />
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#8A7A6A', fontWeight: 500 }}>AI Model Active</span>
        </div>
      </div>
    }>
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 40, padding: '40px 80px' }}>
        {/* Icon + headline */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, textAlign: 'center' }}>
          <div style={{ width: 60, height: 60, borderRadius: 16, background: '#FAF8F5', border: '1px solid #E2D9CE', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none"><circle cx="12" cy="12" r="7.5" stroke="#7C5C3E" strokeWidth="2" /><path d="M18 18L24 24" stroke="#7C5C3E" strokeWidth="2.2" strokeLinecap="round" /></svg>
          </div>
          <div>
            <h1 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 32, letterSpacing: '-0.03em', color: '#1A1410', marginBottom: 8 }}>What do you need built?</h1>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 16, lineHeight: '26px', color: '#8A7A6A', maxWidth: 440 }}>Describe it — our AI will find the best existing technology and show you exactly how to integrate it.</p>
          </div>
        </div>

        {/* Search bar */}
        <div style={{ width: '100%', maxWidth: 680 }}>
          <div style={{ display: 'flex', alignItems: 'center', background: '#FFFFFF', border: '2px solid #E2D9CE', borderRadius: 14, overflow: 'hidden', boxShadow: '0 2px 12px rgba(124,92,62,0.07)', marginBottom: 12 }}>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder='e.g. "I need a real-time fraud detection system for Node.js under $2k/month"'
              style={{ flex: 1, padding: '18px 20px', fontFamily: "'Inter', sans-serif", fontSize: 15, color: '#1A1410', border: 'none', outline: 'none', background: 'transparent' }}
            />
            <button
              onClick={handleSubmit}
              style={{ background: '#7C5C3E', padding: '12px 22px', display: 'flex', alignItems: 'center', gap: 8, margin: 6, borderRadius: 10, cursor: 'pointer', border: 'none', flexShrink: 0 }}
            >
              <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 14, color: '#fff' }}>Find Match</span>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 8h10M8 4l4 4-4 4" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          </div>

          {/* Chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {chips.map(chip => (
              <button
                key={chip}
                onClick={() => { setQuery(chip); navigate('/seeker/chat', { state: { query: chip } }) }}
                style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#7C5C3E', background: '#FAF8F5', border: '1px solid #E2D9CE', borderRadius: 20, padding: '7px 16px', cursor: 'pointer', whiteSpace: 'nowrap' }}
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
