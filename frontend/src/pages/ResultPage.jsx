import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAnalysis, resendEmail, compareAnalysis } from '../services/api'

function ScoreBadge({ score, label }) {
  const color = score >= 8 ? '#4caf50' : score >= 6 ? '#ff9800' : '#f44336'
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        width: '60px', height: '60px', borderRadius: '50%',
        backgroundColor: color, color: 'white',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '20px', fontWeight: 'bold', margin: '0 auto 8px',
      }}>
        {score}
      </div>
      <div style={{ fontSize: '12px', color: '#666' }}>{label}</div>
    </div>
  )
}

function ResultPage() {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [resending, setResending] = useState(false)
  const [resendMessage, setResendMessage] = useState('')
  const [comparison, setComparison] = useState(null)

  useEffect(() => {
    loadAnalysis()
    // 분석 진행 중이면 폴링
    const interval = setInterval(() => {
      if (analysis && !['completed', 'failed'].includes(analysis.status)) {
        loadAnalysis()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [id, analysis?.status])

  const loadAnalysis = async () => {
    try {
      const response = await getAnalysis(id)
      setAnalysis(response.data)
      // 완료된 분석이면 비교 데이터 로드
      if (response.data.status === 'completed') {
        try {
          const cmp = await compareAnalysis(id)
          setComparison(cmp.data)
        } catch (_) { /* 비교 실패 무시 */ }
      }
    } catch (err) {
      setError('분석 결과를 불러올 수 없습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setResending(true)
    setResendMessage('')
    try {
      await resendEmail(id)
      setResendMessage('이메일이 발송되었습니다.')
      await loadAnalysis()
    } catch (err) {
      setResendMessage(err.response?.data?.detail || '이메일 발송에 실패했습니다.')
    } finally {
      setResending(false)
    }
  }

  if (loading) return <p>로딩중...</p>
  if (error) return <p style={{ color: '#f44336' }}>{error}</p>
  if (!analysis) return <p>데이터 없음</p>

  const { status, step, step_progress, results } = analysis
  const isInProgress = !['completed', 'failed'].includes(step)
  const summary = results?.summary || {}
  const scores = summary?.overall_scores || {}

  const STEPS = [
    { key: 'pending', label: '접수', icon: '1' },
    { key: 'discovering', label: '구조 파악', icon: '2' },
    { key: 'crawling', label: '크롤링', icon: '3' },
    { key: 'analyzing', label: 'AI 분석', icon: '4' },
    { key: 'completed', label: '완료', icon: '5' },
  ]

  const stepIndex = STEPS.findIndex(s => s.key === step)

  const getStepColor = (i) => {
    if (step === 'failed') return i <= stepIndex ? '#f44336' : '#e0e0e0'
    if (i < stepIndex) return '#4caf50'
    if (i === stepIndex) return isInProgress ? '#1976d2' : '#4caf50'
    return '#e0e0e0'
  }

  const getProgressDetail = () => {
    const steps = step_progress?.steps || {}
    if (step === 'discovering') {
      const d = steps.discovering || {}
      if (d.pages_found > 0) return `${d.pages_found}개 페이지 발견`
      return '홈페이지 구조 파악 중...'
    }
    if (step === 'crawling') {
      const c = steps.crawling || {}
      if (c.done > 0) return `${c.done}/${c.total || '?'} 페이지 수집`
      return '페이지 수집 중...'
    }
    if (step === 'analyzing') {
      const a = steps.analyzing || {}
      const done = a.done_categories?.length || 0
      const total = a.categories?.length || 0
      if (done > 0) return `${done}/${total} 카테고리 분석 완료`
      return '분석 시작 중...'
    }
    if (step === 'pending') return '분석 대기 중...'
    return ''
  }

  return (
    <div>
      <Link to="/history" style={{ fontSize: '14px', color: '#666' }}>
        &larr; 분석 이력으로
      </Link>

      <div style={{
        backgroundColor: 'white', padding: '24px', borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginTop: '16px',
      }}>
        <h1 style={{ marginBottom: '4px' }}>{analysis.company_name}</h1>
        <p style={{ color: '#666', marginBottom: '16px' }}>{analysis.url}</p>

        {/* 단계별 진행 인디케이터 */}
        {(isInProgress || step === 'completed') && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: '0', marginBottom: '24px', padding: '20px',
            backgroundColor: '#fafafa', borderRadius: '8px',
          }}>
            {STEPS.map((s, i) => (
              <div key={s.key} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: '50%',
                    backgroundColor: getStepColor(i),
                    color: 'white', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', fontSize: '14px', fontWeight: 'bold',
                    margin: '0 auto 6px',
                    transition: 'background-color 0.3s',
                  }}>
                    {i < stepIndex ? '\u2713' : s.icon}
                  </div>
                  <div style={{
                    fontSize: '12px', fontWeight: i === stepIndex ? 'bold' : 'normal',
                    color: i === stepIndex ? '#1976d2' : '#666',
                  }}>
                    {s.label}
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <div style={{
                    width: 48, height: 3, margin: '0 8px',
                    marginBottom: 20,
                    backgroundColor: i < stepIndex ? '#4caf50' : '#e0e0e0',
                    borderRadius: 2,
                    transition: 'background-color 0.3s',
                  }} />
                )}
              </div>
            ))}
          </div>
        )}

        {isInProgress && (
          <div style={{
            backgroundColor: '#e3f2fd', padding: '16px', borderRadius: '8px',
            textAlign: 'center', marginBottom: '24px',
          }}>
            <p style={{ fontSize: '16px', fontWeight: 'bold', color: '#1565c0' }}>
              {getProgressDetail()}
            </p>
            <p style={{ color: '#666', marginTop: '6px', fontSize: '13px' }}>
              브라우저를 닫아도 분석은 계속 진행됩니다.
            </p>
          </div>
        )}

        {status === 'failed' && (
          <div style={{
            backgroundColor: '#ffebee', padding: '16px', borderRadius: '8px',
            color: '#c62828',
          }}>
            분석에 실패했습니다: {analysis.error_message || '알 수 없는 오류'}
          </div>
        )}

        {status === 'completed' && (
          <>
            {/* 크롤링 통계 요약 */}
            {step_progress?.steps?.discovering?.pages_found > 0 && (
              <div style={{
                marginBottom: '24px', padding: '20px',
                backgroundColor: '#f5f5f5', borderRadius: '8px',
              }}>
                <h3 style={{ marginBottom: '12px', fontSize: '15px', color: '#333' }}>
                  크롤링 통계
                </h3>
                <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', marginBottom: '12px' }}>
                  <div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1976d2' }}>
                      {step_progress.steps.discovering.pages_found}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>발견 페이지</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#4caf50' }}>
                      {analysis.crawled_pages}
                    </div>
                    <div style={{ fontSize: '12px', color: '#666' }}>수집 페이지</div>
                  </div>
                  {step_progress.steps.crawling?.total_text_length > 0 && (
                    <div>
                      <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff9800' }}>
                        {(step_progress.steps.crawling.total_text_length / 1000).toFixed(0)}K
                      </div>
                      <div style={{ fontSize: '12px', color: '#666' }}>총 텍스트(자)</div>
                    </div>
                  )}
                </div>
                {/* 카테고리별 분포 */}
                {step_progress.steps.discovering.by_category && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {Object.entries(step_progress.steps.discovering.by_category).map(([cat, count]) => (
                      <span key={cat} style={{
                        padding: '4px 10px', borderRadius: '12px',
                        backgroundColor: '#e3f2fd', fontSize: '12px', color: '#1565c0',
                      }}>
                        {cat} {count}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 종합 점수 */}
            {scores.overall && (
              <div style={{
                display: 'flex', gap: '32px', justifyContent: 'center',
                padding: '24px', backgroundColor: '#fafafa', borderRadius: '8px',
                marginBottom: '24px',
              }}>
                <ScoreBadge score={scores.business} label="사업" />
                <ScoreBadge score={scores.digital} label="디지털" />
                <ScoreBadge score={scores.branding} label="브랜딩" />
                <ScoreBadge score={scores.overall} label="종합" />
              </div>
            )}

            {/* 이전 분석 대비 점수 변화 */}
            {comparison?.has_previous && comparison.score_diff && (
              <div style={{
                padding: '16px', backgroundColor: '#f3e5f5', borderRadius: '8px',
                marginBottom: '24px',
              }}>
                <h3 style={{ fontSize: '14px', color: '#7b1fa2', marginBottom: '12px' }}>
                  이전 분석 대비 ({new Date(comparison.previous_date).toLocaleDateString('ko-KR')})
                </h3>
                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                  {Object.entries(comparison.score_diff).map(([key, val]) => (
                    <div key={key} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
                        {key === 'business' ? '사업' : key === 'digital' ? '디지털' : key === 'branding' ? '브랜딩' : key === 'overall' ? '종합' : key}
                      </div>
                      <span style={{ fontSize: '18px', fontWeight: 'bold' }}>
                        {val.previous} → {val.current}
                      </span>
                      {val.diff !== 0 && (
                        <span style={{
                          marginLeft: '6px', fontSize: '14px', fontWeight: 'bold',
                          color: val.diff > 0 ? '#4caf50' : '#f44336',
                        }}>
                          {val.diff > 0 ? '+' : ''}{val.diff}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 한줄 요약 */}
            {summary.one_line_summary && (
              <p style={{
                fontSize: '18px', fontStyle: 'italic', color: '#555',
                textAlign: 'center', marginBottom: '32px',
              }}>
                "{summary.one_line_summary}"
              </p>
            )}

            {/* 강점 */}
            {summary.top_strengths?.length > 0 && (
              <div style={{ marginBottom: '32px' }}>
                <h2 style={{ color: '#4caf50', marginBottom: '16px' }}>주요 강점</h2>
                {summary.top_strengths.map((item, i) => (
                  <div key={i} style={{
                    padding: '16px', backgroundColor: '#f1f8e9',
                    borderRadius: '8px', marginBottom: '8px',
                    borderLeft: '4px solid #4caf50',
                  }}>
                    <strong>{item.rank}. {item.title}</strong>
                    <p style={{ marginTop: '4px', color: '#555' }}>{item.description}</p>
                  </div>
                ))}
              </div>
            )}

            {/* 개선점 */}
            {summary.top_improvements?.length > 0 && (
              <div style={{ marginBottom: '32px' }}>
                <h2 style={{ color: '#ff9800', marginBottom: '16px' }}>개선 필요 사항</h2>
                {summary.top_improvements.map((item, i) => (
                  <div key={i} style={{
                    padding: '16px', backgroundColor: '#fff8e1',
                    borderRadius: '8px', marginBottom: '8px',
                    borderLeft: '4px solid #ff9800',
                  }}>
                    <strong>{item.rank}. {item.title}</strong>
                    <p style={{ marginTop: '4px', color: '#555' }}>{item.description}</p>
                    {item.suggestion && (
                      <p style={{ marginTop: '8px', color: '#1976d2', fontSize: '14px' }}>
                        제안: {item.suggestion}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 사이트 정량 평가 */}
            {results?.site_metrics && (
              <div style={{ marginBottom: '32px' }}>
                <h2 style={{ color: '#0288d1', marginBottom: '16px' }}>사이트 정량 평가</h2>
                <div style={{
                  padding: '20px', backgroundColor: '#e1f5fe', borderRadius: '8px',
                }}>
                  <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '12px' }}>
                    {[
                      { key: 'https', label: 'HTTPS' },
                      { key: 'load_time_score', label: '로딩속도' },
                      { key: 'mobile_responsive', label: '모바일 반응형' },
                      { key: 'seo_meta_tags', label: 'SEO 메타태그' },
                      { key: 'multilingual', label: '다국어' },
                      { key: 'structured_data', label: '구조화 데이터' },
                    ].map(({ key, label }) => {
                      const val = results.site_metrics[key]
                      if (val === undefined) return null
                      const color = val >= 8 ? '#4caf50' : val >= 5 ? '#ff9800' : '#f44336'
                      return (
                        <div key={key} style={{ textAlign: 'center', minWidth: 70 }}>
                          <div style={{
                            fontSize: '20px', fontWeight: 'bold', color,
                          }}>{val}/10</div>
                          <div style={{ fontSize: '11px', color: '#666' }}>{label}</div>
                        </div>
                      )
                    })}
                  </div>
                  {results.site_metrics.code_measured_score && (
                    <div style={{ fontSize: '13px', color: '#555', borderTop: '1px solid #b3e5fc', paddingTop: '10px' }}>
                      코드 측정 종합: <strong>{results.site_metrics.code_measured_score}/10</strong>
                      {results.site_metrics.blended_digital_score && (
                        <span style={{ marginLeft: '16px' }}>
                          블렌딩 디지털 점수: <strong>{results.site_metrics.blended_digital_score}/10</strong>
                          <span style={{ color: '#999', marginLeft: '4px' }}>(코드 40% + LLM 60%)</span>
                        </span>
                      )}
                    </div>
                  )}
                  {results.site_metrics.load_time_ms && (
                    <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>
                      페이지 로딩: {results.site_metrics.load_time_ms}ms
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 종합 평가 */}
            {summary.overall_assessment && (
              <div style={{
                padding: '20px', backgroundColor: '#e8eaf6',
                borderRadius: '8px',
              }}>
                <h3 style={{ marginBottom: '8px' }}>종합 평가</h3>
                <p>{summary.overall_assessment}</p>
              </div>
            )}

            {/* 메타 정보 */}
            <div style={{
              marginTop: '32px', padding: '16px',
              backgroundColor: '#fafafa', borderRadius: '8px',
              fontSize: '14px', color: '#999',
            }}>
              크롤링: {analysis.crawled_pages}페이지 |
              토큰: {analysis.total_tokens?.toLocaleString()} |
              소요시간: {analysis.analysis_duration?.toFixed(1)}초 |
              분석일시: {analysis.completed_at && new Date(analysis.completed_at).toLocaleString('ko-KR')}
            </div>

            {/* 이메일 상태 */}
            {analysis.email && (
              <div style={{
                marginTop: '16px', padding: '16px',
                backgroundColor: '#fafafa', borderRadius: '8px',
                fontSize: '14px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <span style={{ color: '#666' }}>이메일: {analysis.email}</span>
                    {' — '}
                    {analysis.email_sent ? (
                      <span style={{ color: '#4caf50', fontWeight: 'bold' }}>
                        발송 완료
                        {analysis.email_sent_at && (
                          <span style={{ fontWeight: 'normal', color: '#999', marginLeft: '4px' }}>
                            ({new Date(analysis.email_sent_at).toLocaleString('ko-KR')})
                          </span>
                        )}
                      </span>
                    ) : analysis.email_error ? (
                      <span style={{ color: '#f44336', fontWeight: 'bold' }}>
                        발송 실패: {analysis.email_error}
                      </span>
                    ) : (
                      <span style={{ color: '#ff9800', fontWeight: 'bold' }}>대기중</span>
                    )}
                  </div>
                  <button
                    onClick={handleResend}
                    disabled={resending}
                    style={{
                      backgroundColor: resending ? '#999' : '#1976d2',
                      color: 'white',
                      border: 'none',
                      padding: '8px 16px',
                      borderRadius: '4px',
                      fontSize: '13px',
                      cursor: resending ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {resending ? '발송 중...' : '재발송'}
                  </button>
                </div>
                {resendMessage && (
                  <p style={{
                    marginTop: '8px', fontSize: '13px',
                    color: resendMessage.includes('실패') ? '#f44336' : '#4caf50',
                  }}>
                    {resendMessage}
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default ResultPage
