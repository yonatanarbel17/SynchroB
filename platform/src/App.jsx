import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Onboarding from './pages/Onboarding'
import SeekerStart from './pages/SeekerStart'
import SeekerChat from './pages/SeekerChat'
import SeekerBlueprint from './pages/SeekerBlueprint'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Onboarding />} />
        <Route path="/seeker" element={<SeekerStart />} />
        <Route path="/seeker/chat" element={<SeekerChat />} />
        <Route path="/seeker/blueprint" element={<SeekerBlueprint />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}
