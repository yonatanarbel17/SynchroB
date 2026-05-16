export default function LogoIcon({ size = 26 }) {
  return (
    <svg width={size} height={size * 1.15} viewBox="0 0 38 42" fill="none">
      <circle cx="27" cy="5" r="2.5" fill="#1A1410" />
      <circle cx="11" cy="37" r="2.5" fill="#1A1410" />
      <path d="M27 5 L8 5 Q5 5 5 8 L5 17 Q5 20 8 20 L30 20 Q33 20 33 23 L33 34 Q33 37 30 37 L11 37" stroke="#1A1410" strokeWidth="2" fill="none" strokeLinecap="round" />
      <path d="M27 9 L10 9 Q8 9 8 11 L8 17 Q8 20 10 20" stroke="#1A1410" strokeWidth="2" fill="none" strokeLinecap="round" />
      <path d="M28 22 Q30 22 30 24 L30 31 Q30 33 28 33 L11 33" stroke="#1A1410" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  )
}
