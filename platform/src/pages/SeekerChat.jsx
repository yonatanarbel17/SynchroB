import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'

const MATCHES = [
  {
    id: 1, name: 'FraudShield AI', provider: 'Sentinel Labs', pct: 89, color: '#16A34A',
    desc: 'Native Node.js SDK, <50ms latency, $1,800/mo at your volume. Can be live in 3–4 weeks with the generated integration blueprint.',
  },
  {
    id: 2, name: 'RiskGuard Pro', provider: 'DataForge', pct: 74, color: '#D97706',
    desc: 'REST API, webhook support, $2,200/mo — slightly over budget but highly configurable.',
  },
  {
    id: 3, name: 'SecureLayer', provider: 'CipherTech', pct: 63, color: '#D97706',
    desc: 'ML-based anomaly detection, $1,600/mo, 6–8 week integration estimate.',
  },
]

function ShieldIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <path d="M10 2L3 5v5c0 4.4 3 8.1 7 9 4-.9 7-4.6 7-9V5L10 2Z" stroke="#7C5C3E" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

function BoltIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
      <path d="M11 2L3 12h7l-1 6 8-10h-7l1-6Z" stroke="#7C5C3E" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

function LayerIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
      <path d="M10 2L2 7l8 5 8-5-8-5Z" stroke="#7C5C3E" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M2 13l8 5 8-5" stroke="#7C5C3E" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function BotIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 26 26" fill="none">
      <rect x="3" y="7" width="20" height="14" rx="4" stroke="#7C5C3E" strokeWidth="1.8" />
      <circle cx="9" cy="14" r="2" fill="#7C5C3E" />
      <circle cx="17" cy="14" r="2" fill="#7C5C3E" />
      <path d="M9 7V5M17 7V5" stroke="#7C5C3E" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

const ICONS = [<ShieldIcon />, <BoltIcon />, <LayerIcon />]

export default function SeekerChat() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const userMsg = state?.query || 'We need a real-time fraud detection system for Node.js. Budget $2k/month, need it live within 6 weeks.'
  const [expanded, setExpanded] = useState(null)
  const [followUp, setFollowUp] = useState('')

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
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '32px 32px 0' }}>

          {/* User message */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 24 }}>
            <div style={{ background: '#7C5C3E', borderRadius: '16px 16px 4px 16px', padding: '12px 18px', maxWidth: 520 }}>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, color: '#fff', lineHeight: '22px', margin: 0 }}>{userMsg}</p>
            </div>
          </div>

          {/* AI response */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 32 }}>
            <div style={{ width: 34, height: 34, borderRadius: 10, background: '#FAF8F5', border: '1px solid #E2D9CE', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <BotIcon />
            </div>
            <div style={{ maxWidth: 720, width: '100%' }}>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 14, color: '#1A1410', lineHeight: '22px', marginBottom: 14 }}>
                I found <strong>{MATCHES.length} matches</strong> for your need. Click any result to see the full integration steps:
              </p>

              {MATCHES.map((m, i) => (
                <div key={m.id} style={{ marginBottom: 10 }}>
                  <button
                    onClick={() => setExpanded(expanded === m.id ? null : m.id)}
                    style={{
                      width: '100%', background: '#FAF8F5',
                      border: expanded === m.id ? '2px solid #7C5C3E' : '1px solid #E2D9CE',
                      borderRadius: expanded === m.id ? '14px 14px 0 0' : 14,
                      padding: '14px 18px', display: 'flex', alignItems: 'center',
                      gap: 12, cursor: 'pointer', transition: 'all 0.15s',
                    }}
                  >
                    <div style={{ width: 34, height: 34, background: '#F0EBE3', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      {ICONS[i]}
                    </div>
                    <div style={{ flex: 1, textAlign: 'left' }}>
                      <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 14, color: '#1A1410' }}>{m.name}</div>
                      <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#8A7A6A' }}>by {m.provider}</div>
                    </div>
                    <div style={{ background: m.color, borderRadius: 20, padding: '4px 12px', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 15, color: '#fff' }}>{m.pct}%</span>
                      <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>match</span>
                    </div>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ transform: expanded === m.id ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}>
                      <path d="M3 5L7 9L11 5" stroke="#8A7A6A" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>

                  {expanded === m.id && (
                    <div style={{ border: '2px solid #7C5C3E', borderTop: 'none', borderRadius: '0 0 14px 14px', padding: '20px 20px 16px', background: '#fff' }}>
                      <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#5A4A3A', lineHeight: '21px', marginBottom: 16 }}>{m.desc}</p>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button
                          onClick={() => navigate('/seeker/blueprint', { state: { match: m } })}
                          style={{ background: '#7C5C3E', color: '#fff', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 13, borderRadius: 8, padding: '9px 18px', cursor: 'pointer', border: 'none' }}
                        >
                          View Integration Steps
                        </button>
                        <button style={{ background: 'transparent', color: '#7C5C3E', fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: 13, borderRadius: 8, padding: '9px 18px', cursor: 'pointer', border: '1px solid #E2D9CE' }}>
                          Learn more
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Input bar */}
        <div style={{ padding: '16px 32px 24px', borderTop: '1px solid #E2D9CE', background: '#fff', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#FAF8F5', border: '1.5px solid #E2D9CE', borderRadius: 12, padding: '12px 16px' }}>
            <input
              value={followUp}
              onChange={e => setFollowUp(e.target.value)}
              placeholder="Ask a follow-up or describe another need..."
              style={{ flex: 1, fontFamily: "'Inter', sans-serif", fontSize: 14, color: '#1A1410', border: 'none', outline: 'none', background: 'transparent' }}
            />
            <button style={{ background: '#7C5C3E', borderRadius: 8, padding: '9px 16px', display: 'flex', alignItems: 'center', gap: 8, border: 'none', cursor: 'pointer', flexShrink: 0 }}>
              <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 13, color: '#fff' }}>Send</span>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 7h10M7 3l4 4-4 4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </button>
          </div>
        </div>

      </div>
    </AppShell>
  )
}
