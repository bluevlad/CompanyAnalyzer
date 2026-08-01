import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import GatewayLanding from './pages/gateway-landing/GatewayLanding'
import AnalyzePage from './pages/AnalyzePage'
import HistoryPage from './pages/HistoryPage'
import ResultPage from './pages/ResultPage'
import LoginPage from './pages/LoginPage'
import RequireAuth from './components/RequireAuth'
import { getUser, logout, isAuthenticated } from './services/auth'

function Header() {
  const navigate = useNavigate()
  const user = getUser()
  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }
  return (
    <header
      style={{
        backgroundColor: '#1976d2',
        color: 'white',
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 24,
      }}
    >
      <Link to="/" style={{ color: 'white', fontSize: 20, fontWeight: 'bold', textDecoration: 'none' }}>
        CompanyAnalyzer
      </Link>
      <nav style={{ display: 'flex', gap: 16, flex: 1 }}>
        <Link to="/" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>
          홈
        </Link>
        <Link to="/analyze" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>
          분석하기
        </Link>
        <Link to="/history" style={{ color: 'rgba(255,255,255,0.9)', textDecoration: 'none' }}>
          분석 이력
        </Link>
      </nav>
      {user && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 13, opacity: 0.9 }}>{user.name || user.email}</span>
          <button
            onClick={handleLogout}
            style={{
              background: 'rgba(255,255,255,0.15)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.3)',
              padding: '6px 12px',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 12,
            }}
          >
            로그아웃
          </button>
        </div>
      )}
    </header>
  )
}

function ProtectedLayout({ children }) {
  return (
    <div style={{ minHeight: '100vh' }}>
      <Header />
      <main style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>{children}</main>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<GatewayLanding />} />
        <Route
          path="/analyze"
          element={
            <RequireAuth>
              <ProtectedLayout>
                <AnalyzePage />
              </ProtectedLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/history"
          element={
            <RequireAuth>
              <ProtectedLayout>
                <HistoryPage />
              </ProtectedLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/result/:id"
          element={
            <RequireAuth>
              <ProtectedLayout>
                <ResultPage />
              </ProtectedLayout>
            </RequireAuth>
          }
        />
      </Routes>
    </Router>
  )
}

export default App
