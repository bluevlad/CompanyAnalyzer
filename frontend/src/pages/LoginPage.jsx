import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { verifyGoogleCredential, fetchGoogleClientId } from '../services/auth'

export default function LoginPage() {
  const [error, setError] = useState('')
  const [googleReady, setGoogleReady] = useState(false)
  const googleBtnRef = useRef(null)
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from || '/'

  // ─── Google Identity Services 초기화 ────────────────────────────────
  useEffect(() => {
    let cancelled = false

    async function init() {
      const clientId = await fetchGoogleClientId()
      if (cancelled) return
      if (!clientId) return // GOOGLE_CLIENT_ID 미설정 — 버튼 숨김
      // GSI 스크립트가 로드될 때까지 폴링 (index.html에 <script async>로 삽입됨)
      const start = Date.now()
      while (!window.google?.accounts?.id) {
        if (Date.now() - start > 5000) return
        await new Promise((r) => setTimeout(r, 100))
        if (cancelled) return
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCredential,
        auto_select: false,
        cancel_on_tap_outside: true,
      })

      if (googleBtnRef.current) {
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
          logo_alignment: 'left',
          width: 340,
        })
        setGoogleReady(true)
      }
    }

    init()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleGoogleCredential(response) {
    setError('')
    try {
      await verifyGoogleCredential(response.credential)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err?.response?.data?.detail || 'Google 로그인에 실패했습니다.')
    }
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.card}>
        <div style={styles.brand}>
          <div style={styles.logo}>CA</div>
          <div>
            <div style={styles.title}>CompanyAnalyzer</div>
            <div style={styles.subtitle}>관리자 로그인</div>
          </div>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        <div ref={googleBtnRef} style={{ ...styles.googleSlot, marginTop: 24 }} />
        {!googleReady && (
          <div style={styles.gsiHint}>
            Google 로그인 버튼을 불러오는 중...
          </div>
        )}

        <div style={styles.hint}>
          등록된 Google 계정으로 접속할 수 있습니다.
        </div>
      </div>
    </div>
  )
}

const styles = {
  wrap: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%)',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 420,
    background: '#fff',
    borderRadius: 14,
    boxShadow: '0 20px 50px rgba(15,23,42,.25)',
    padding: 32,
  },
  brand: { display: 'flex', alignItems: 'center', gap: 14 },
  logo: {
    width: 48,
    height: 48,
    borderRadius: 12,
    background: 'linear-gradient(135deg,#1e3a8a,#2563eb)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: 18,
  },
  title: { fontSize: 18, fontWeight: 700, color: '#0f172a' },
  subtitle: { fontSize: 12, color: '#64748b' },
  googleSlot: { display: 'flex', justifyContent: 'center', minHeight: 44 },
  gsiHint: { textAlign: 'center', fontSize: 11, color: '#94a3b8', marginTop: 6 },
  error: {
    marginTop: 12,
    padding: '8px 12px',
    background: '#fef2f2',
    color: '#b91c1c',
    fontSize: 12,
    borderRadius: 6,
    border: '1px solid #fecaca',
  },
  hint: { marginTop: 18, fontSize: 11, color: '#94a3b8', textAlign: 'center' },
}
