import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getAnalyses, getActiveAnalyses } from '../services/api'

const CARDS = [
  {
    icon: '\uD83C\uDFE2',
    title: '기업 분석',
    desc: 'URL 입력 \u2192 구조 파악 \u2192 크롤링 \u2192 AI 분석 \u2192 리포트 생성',
    link: '/analyze',
    btnText: '새 분석 시작',
    color: '#1976d2',
  },
  {
    icon: '\uD83D\uDCCA',
    title: '분석 대시보드',
    desc: '진행 중/완료된 분석 현황, 이력 비교 뷰',
    link: '/history',
    btnText: '대시보드 열기',
    color: '#4caf50',
  },
  {
    icon: '\uD83D\uDCF0',
    title: '모니터링',
    desc: '키워드 뉴스 수집, 일/주/월간 AI 브리핑 자동 발송',
    link: '/history',
    btnText: '모니터링 설정',
    color: '#ff9800',
  },
  {
    icon: '\uD83D\uDD0D',
    title: '기업 검색',
    desc: '수집된 뉴스/분석 데이터에서 의미 기반 통합 검색',
    link: '/history',
    btnText: '검색하기',
    color: '#9c27b0',
  },
  {
    icon: '\uD83D\uDCCB',
    title: '리포트',
    desc: 'PDF/HTML 리포트 내보내기, 이메일 자동 발송',
    link: '/history',
    btnText: '리포트 관리',
    color: '#00bcd4',
  },
  {
    icon: '\uD83D\uDD0C',
    title: 'API 문서',
    desc: 'RESTful API (FastAPI Swagger)',
    link: '/api/docs',
    btnText: 'API Docs',
    color: '#607d8b',
    external: true,
  },
]

function GatewayPage() {
  const [stats, setStats] = useState({ total: 0, active: 0 })

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const [analysesRes, activeRes] = await Promise.all([
        getAnalyses(0, 100),
        getActiveAnalyses(),
      ])
      setStats({
        total: analysesRes.data.filter(a => a.status === 'completed').length,
        active: activeRes.data.length,
      })
    } catch (_) {}
  }

  return (
    <div>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '28px', marginBottom: '8px' }}>CompanyAnalyzer</h1>
        <p style={{ color: '#666', fontSize: '16px' }}>
          Company Intelligence & Monitoring
        </p>
        <div style={{ display: 'flex', gap: '24px', justifyContent: 'center', marginTop: '16px' }}>
          <div style={{
            padding: '8px 20px', backgroundColor: '#e8f5e9', borderRadius: '20px',
            fontSize: '14px', color: '#2e7d32',
          }}>
            {stats.total}건 분석 완료
          </div>
          {stats.active > 0 && (
            <div style={{
              padding: '8px 20px', backgroundColor: '#e3f2fd', borderRadius: '20px',
              fontSize: '14px', color: '#1565c0',
            }}>
              {stats.active}건 진행 중
            </div>
          )}
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '20px',
      }}>
        {CARDS.map((card) => (
          <div key={card.title} style={{
            backgroundColor: 'white',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            borderTop: `4px solid ${card.color}`,
            transition: 'box-shadow 0.2s',
          }}>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>
              {card.icon}
            </div>
            <h3 style={{ marginBottom: '8px', fontSize: '18px' }}>{card.title}</h3>
            <p style={{ color: '#666', fontSize: '14px', flex: 1, lineHeight: '1.5' }}>
              {card.desc}
            </p>
            {card.external ? (
              <a
                href={card.link}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-block', marginTop: '16px', padding: '10px 20px',
                  backgroundColor: card.color, color: 'white', borderRadius: '6px',
                  textDecoration: 'none', textAlign: 'center', fontSize: '14px',
                  fontWeight: 'bold',
                }}
              >
                {card.btnText}
              </a>
            ) : (
              <Link
                to={card.link}
                style={{
                  display: 'inline-block', marginTop: '16px', padding: '10px 20px',
                  backgroundColor: card.color, color: 'white', borderRadius: '6px',
                  textDecoration: 'none', textAlign: 'center', fontSize: '14px',
                  fontWeight: 'bold',
                }}
              >
                {card.btnText}
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default GatewayPage
