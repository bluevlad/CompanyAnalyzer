import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getAnalyses } from '../services/api'

const STEP_LABELS = {
  pending: { text: '대기중', color: '#ff9800' },
  discovering: { text: '구조파악중', color: '#00bcd4' },
  crawling: { text: '크롤링중', color: '#2196f3' },
  statistics: { text: '통계생성', color: '#673ab7' },
  analyzing: { text: '분석중', color: '#9c27b0' },
  completed: { text: '완료', color: '#4caf50' },
  failed: { text: '실패', color: '#f44336' },
}

function HistoryPage() {
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAnalyses()
  }, [])

  const loadAnalyses = async () => {
    try {
      const response = await getAnalyses()
      setAnalyses(response.data)
    } catch (err) {
      console.error('분석 이력 조회 실패:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <p>로딩중...</p>

  return (
    <div>
      <h1 style={{ marginBottom: '24px' }}>분석 이력</h1>

      {analyses.length === 0 ? (
        <div style={{
          backgroundColor: 'white',
          padding: '48px',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#666',
        }}>
          <p>아직 분석 이력이 없습니다.</p>
          <Link to="/analyze" style={{ display: 'inline-block', marginTop: '16px' }}>
            분석하러 가기
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {analyses.map((analysis) => {
            const status = STEP_LABELS[analysis.step || analysis.status] || { text: analysis.status, color: '#999' }
            return (
              <Link
                key={analysis.id}
                to={`/result/${analysis.id}`}
                style={{
                  backgroundColor: 'white',
                  padding: '20px',
                  borderRadius: '8px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  textDecoration: 'none',
                  color: 'inherit',
                }}
              >
                <div>
                  <strong style={{ fontSize: '16px' }}>{analysis.company_name}</strong>
                  <div style={{ color: '#666', fontSize: '14px', marginTop: '4px' }}>
                    {analysis.url}
                  </div>
                  <div style={{ color: '#999', fontSize: '12px', marginTop: '4px' }}>
                    {new Date(analysis.created_at).toLocaleString('ko-KR')}
                    {analysis.crawled_pages > 0 && ` | ${analysis.crawled_pages}페이지 수집`}
                  </div>
                </div>
                <span style={{
                  backgroundColor: status.color,
                  color: 'white',
                  padding: '4px 12px',
                  borderRadius: '12px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                }}>
                  {status.text}
                </span>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default HistoryPage
