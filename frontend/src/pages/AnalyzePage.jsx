import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { analyzeCompany, getActiveAnalyses } from '../services/api'

const STEP_LABELS = {
  pending: '대기중',
  discovering: '구조 파악중',
  crawling: '크롤링중',
  statistics: '통계 생성중',
  analyzing: '분석중',
}

function AnalyzePage() {
  const [url, setUrl] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeAnalyses, setActiveAnalyses] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    loadActiveAnalyses()
  }, [])

  const loadActiveAnalyses = async () => {
    try {
      const response = await getActiveAnalyses()
      setActiveAnalyses(response.data)
    } catch (err) {
      // 조회 실패 시 무시 (배너만 안 보임)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError('')

    try {
      const response = await analyzeCompany(
        url.trim(),
        companyName.trim() || undefined,
        email.trim() || undefined,
      )
      navigate(`/result/${response.data.id}`)
    } catch (err) {
      if (err.response?.status === 409) {
        const detail = err.response.data.detail
        setError(
          `${detail.company_name} 기업의 분석이 이미 진행 중입니다 (${STEP_LABELS[detail.status] || detail.status}). ` +
          `진행 중인 분석을 확인해주세요.`
        )
        // 진행 중 분석 목록 갱신
        loadActiveAnalyses()
      } else {
        setError(err.response?.data?.detail || '분석 요청에 실패했습니다.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: '8px' }}>기업 홈페이지 분석</h1>
      <p style={{ color: '#666', marginBottom: '32px' }}>
        기업 홈페이지 URL을 입력하면 AI가 강점과 개선점을 분석합니다.
      </p>

      {/* 진행 중인 분석 안내 배너 */}
      {activeAnalyses.length > 0 && (
        <div style={{
          backgroundColor: '#e3f2fd',
          border: '1px solid #90caf9',
          borderRadius: '8px',
          padding: '16px 20px',
          marginBottom: '24px',
        }}>
          <div style={{ fontWeight: 'bold', color: '#1565c0', marginBottom: '8px' }}>
            분석 진행 중인 기업이 있습니다
          </div>
          {activeAnalyses.map((a) => (
            <div key={a.id} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: 'white',
              padding: '10px 14px',
              borderRadius: '6px',
              marginTop: '8px',
            }}>
              <div>
                <strong>{a.company_name}</strong>
                <span style={{ color: '#666', fontSize: '13px', marginLeft: '8px' }}>
                  {STEP_LABELS[a.step || a.status] || a.status}
                  {a.crawled_pages > 0 && ` (${a.crawled_pages}페이지 수집)`}
                </span>
              </div>
              <Link
                to={`/result/${a.id}`}
                style={{
                  backgroundColor: '#1976d2',
                  color: 'white',
                  padding: '6px 14px',
                  borderRadius: '4px',
                  textDecoration: 'none',
                  fontSize: '13px',
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                }}
              >
                분석 현황 보기
              </Link>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{
        backgroundColor: 'white',
        padding: '32px',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}>
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            홈페이지 URL *
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.example.com"
            required
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px',
            }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            기업명 (선택)
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="기업명을 입력하세요"
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px',
            }}
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            이메일 (선택)
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="example@email.com"
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '16px',
            }}
          />
          <p style={{ margin: '6px 0 0', color: '#999', fontSize: '13px' }}>
            입력 시 분석 완료 후 결과를 이메일로 발송합니다.
          </p>
        </div>

        {error && (
          <div style={{
            backgroundColor: '#ffebee',
            color: '#c62828',
            padding: '12px',
            borderRadius: '4px',
            marginBottom: '16px',
          }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            backgroundColor: loading ? '#999' : '#1976d2',
            color: 'white',
            border: 'none',
            padding: '14px 32px',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: loading ? 'not-allowed' : 'pointer',
            width: '100%',
          }}
        >
          {loading ? '분석 요청 중...' : '분석 시작'}
        </button>
      </form>
    </div>
  )
}

export default AnalyzePage
