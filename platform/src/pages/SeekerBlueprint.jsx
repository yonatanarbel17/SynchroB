import { useLocation, useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'

const STEPS = [
  {
    num: 1, title: 'Install the SDK', time: '30 min', difficulty: 'Easy',
    body: 'Run ', code: 'npm install fraudshield-sdk', body2: ' in your Node.js project. Requires Node 16+. Add your API key to your environment variables.',
  },
  {
    num: 2, title: 'Wrap your payment endpoints', time: '2 hrs', difficulty: 'Medium',
    body: 'Initialize FraudShield in your Express middleware. Call ', code: 'fraudshield.evaluate(req)', body2: ' before processing any transaction. Returns a risk score 0–100 in under 50ms.',
  },
  {
    num: 3, title: 'Set risk thresholds & alerts', time: '1 hr', difficulty: 'Easy',
    body: 'Configure block/flag/allow thresholds in the dashboard. Set up webhooks to receive real-time alerts when suspicious activity is detected.', code: '', body2: '',
  },
  {
    num: 4, title: 'Test in sandbox & go live', time: '1 week', difficulty: 'Easy',
    body: 'Use the sandbox environment with test card numbers to validate your integration. Switch to production keys when ready. Full go-live estimated at 3–4 weeks.', code: '', body2: '',
  },
]

function ShieldIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
      <path d="M10 2L3 5v5c0 4.4 3 8.1 7 9 4-.9 7-4.6 7-9V5L10 2Z" stroke="#7C5C3E" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  )
}

export default function SeekerBlueprint() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const match = state?.match || { name: 'FraudShield AI', provider: 'Sentinel Labs', pct: 89, color: '#16A34A' }

  return (
    <AppShell topbar={
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
        <button
          onClick={() => navigate('/seeker/chat')}
          style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#8A7A6A', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9 3L5 7L9 11" stroke="#8A7A6A" strokeWidth="1.6" strokeLinecap="round" /></svg>
          Back
        </button>
        <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 16, color: '#1A1410' }}>Integration Blueprint</span>
      </div>
    }>
      <div style={{ padding: '32px 40px', maxWidth: 820 }}>

        {/* Match header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32, padding: '20px 24px', background: '#FAF8F5', border: '1px solid #E2D9CE', borderRadius: 14 }}>
          <div style={{ width: 44, height: 44, background: '#F0EBE3', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShieldIcon />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 18, color: '#1A1410' }}>{match.name}</div>
            <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#8A7A6A' }}>by {match.provider}</div>
          </div>
          <div style={{ background: match.color, borderRadius: 20, padding: '5px 16px' }}>
            <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 16, color: '#fff' }}>{match.pct}% match</span>
          </div>
        </div>

        {/* Steps */}
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {STEPS.map((step, i) => (
            <div key={step.num} style={{ display: 'flex', gap: 20 }}>
              {/* Number + connector line */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#7C5C3E', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 14, color: '#fff' }}>
                  {step.num}
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{ width: 2, flex: 1, minHeight: 32, background: '#E2D9CE', marginTop: 4 }} />
                )}
              </div>

              {/* Content */}
              <div style={{ paddingBottom: 28, flex: 1 }}>
                <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 15, color: '#1A1410', marginBottom: 6 }}>{step.title}</div>
                <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 13, lineHeight: '21px', color: '#5A4A3A', marginBottom: 6 }}>
                  {step.body}
                  {step.code && (
                    <code style={{ fontFamily: 'monospace', background: '#F0EBE3', padding: '2px 7px', borderRadius: 4, fontSize: 12 }}>
                      {step.code}
                    </code>
                  )}
                  {step.body2}
                </p>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, color: '#8A7A6A' }}>
                  Est. {step.time} &middot; Difficulty: {step.difficulty}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* CTA row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingTop: 24, borderTop: '1px solid #E2D9CE', marginTop: 8, flexWrap: 'wrap' }}>
          <button style={{ background: '#7C5C3E', color: '#fff', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: 14, borderRadius: 8, padding: '11px 22px', cursor: 'pointer', border: 'none' }}>
            Start Integration
          </button>
          <button style={{ background: 'transparent', color: '#7C5C3E', fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: 14, borderRadius: 8, padding: '11px 22px', cursor: 'pointer', border: '1px solid #E2D9CE' }}>
            Download Blueprint PDF
          </button>
          <span style={{ marginLeft: 'auto', fontFamily: "'Inter', sans-serif", fontSize: 13, color: '#8A7A6A' }}>
            Total est. time: <strong style={{ color: '#1A1410' }}>3–4 weeks</strong>
          </span>
        </div>

      </div>
    </AppShell>
  )
}
