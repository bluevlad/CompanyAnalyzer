import { useState, useEffect, useCallback } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { isAuthenticated, getUser } from '../../services/auth'
import './GatewayLanding.css'

const FEATURES = [
  {
    icon: '🏢',
    name: '기업 분석',
    desc: 'URL 입력 → 구조 파악 → 크롤링 → AI 분석 → 리포트 생성',
    level: 'member',
    to: '/analyze',
  },
  {
    icon: '📊',
    name: '분석 대시보드',
    desc: '진행 중/완료된 분석 현황과 이력 비교 뷰',
    level: 'member',
    to: '/history',
  },
  {
    icon: '📰',
    name: '모니터링',
    desc: '키워드 뉴스 수집과 일/주/월간 AI 브리핑 자동 발송',
    level: 'member',
    to: '/history',
  },
  {
    icon: '🔍',
    name: '기업 검색',
    desc: '수집된 뉴스·분석 데이터에서 의미 기반 통합 검색',
    level: 'member',
    to: '/history',
  },
  {
    icon: '📋',
    name: '리포트',
    desc: 'PDF/HTML 리포트 내보내기와 이메일 자동 발송',
    level: 'member',
    to: '/history',
  },
  {
    icon: '🔌',
    name: 'API Docs',
    desc: 'Swagger UI 기반 OpenAPI 명세 (FastAPI 자동 생성)',
    level: 'public',
    to: '/api/docs',
    external: true,
  },
]

const TECH_STACK = [
  { name: 'React 18', dot: '#61dafb' },
  { name: 'Vite', dot: '#646cff' },
  { name: 'FastAPI', dot: '#009688' },
  { name: 'Python 3.11+', dot: '#3776ab' },
  { name: 'PostgreSQL', dot: '#336791' },
  { name: 'Crawler · BeautifulSoup', dot: '#10b981' },
  { name: 'Google OAuth · JWT', dot: '#eab308' },
  { name: 'Docker', dot: '#2496ed' },
]

const CONNECTED_SERVICES = [
  { name: 'NewsLetterPlatform', role: '브리핑 발송 연동', href: 'https://newsletter.unmong.com', dot: '#ec4899' },
  { name: 'AllergyInsight', role: '동일 인프라 운영', href: 'https://allergyinsight.unmong.com', dot: '#f43f5e' },
  { name: 'EduFit', role: '동일 인프라 운영', href: 'https://edufit.unmong.com', dot: '#22c55e' },
  { name: 'InfraWatcher', role: '컨테이너 모니터링', href: 'https://infrawatcher.unmong.com', dot: '#06b6d4' },
  { name: 'LogAnalyzer', role: '로그 분석', href: 'https://loganalyzer.unmong.com', dot: '#f97316' },
  { name: 'QA-Agent', role: '품질 자동 테스트', href: 'https://qaagent.unmong.com', dot: '#8b5cf6' },
]

function accessFor(level, { authed, isAdmin }) {
  if (level === 'public') return 'granted'
  if (level === 'member') return authed ? 'granted' : 'member-locked'
  if (level === 'admin') return isAdmin ? 'granted' : 'admin-locked'
  return 'member-locked'
}

function tagInfo(state, level) {
  if (state === 'granted' && level === 'public') return { label: '🌐 공개', variant: 'public' }
  if (state === 'granted') return { label: '✓ 사용 가능', variant: 'granted' }
  if (state === 'member-locked') return { label: '🔒 회원전용', variant: 'member-locked' }
  if (state === 'admin-locked') return { label: '🔐 관리자 전용', variant: 'admin-locked' }
  return { label: '', variant: '' }
}

function lockedToastFor(state) {
  if (state === 'member-locked') {
    return { icon: '🔒', message: '회원전용 서비스입니다', actionLabel: '로그인', actionTo: '/login' }
  }
  if (state === 'admin-locked') {
    return { icon: '🔐', message: '관리자 전용입니다', actionLabel: '관리자 로그인', actionTo: '/login' }
  }
  return null
}

function FeatureCard({ feature, accessState, onLocked }) {
  const locked = accessState !== 'granted'
  const { label, variant } = tagInfo(accessState, feature.level)

  const handleClick = (e) => {
    if (locked) {
      e.preventDefault()
      onLocked(accessState)
    }
  }

  const inner = (
    <>
      {locked && <span className="sl-feature-lock" aria-hidden="true">🔒</span>}
      <span className="sl-feature-icon" aria-hidden="true">{feature.icon}</span>
      <div className="sl-feature-name">{feature.name}</div>
      <div className="sl-feature-desc">{feature.desc}</div>
      <span className={`sl-feature-tag sl-feature-tag--${variant}`}>{label}</span>
    </>
  )

  const commonProps = {
    className: 'sl-feature',
    'data-locked': locked ? 'true' : 'false',
    onClick: handleClick,
  }

  if (feature.external) {
    return (
      <a {...commonProps} href={feature.to} target="_blank" rel="noopener noreferrer">
        {inner}
      </a>
    )
  }
  if (locked) {
    return (
      <a {...commonProps} href={feature.to}>
        {inner}
      </a>
    )
  }
  return (
    <Link {...commonProps} to={feature.to}>
      {inner}
    </Link>
  )
}

function Toast({ toast, onClose }) {
  if (!toast) return null
  return (
    <div className="sl-toast" role="status" aria-live="polite">
      <span className="sl-toast-icon" aria-hidden="true">{toast.icon}</span>
      <span className="sl-toast-msg">{toast.message}</span>
      <Link className="sl-toast-action" to={toast.actionTo} onClick={onClose}>
        {toast.actionLabel} →
      </Link>
      <button type="button" className="sl-toast-close" onClick={onClose} aria-label="닫기">×</button>
    </div>
  )
}

const GatewayLanding = () => {
  const [toast, setToast] = useState(null)
  const authed = isAuthenticated()
  const user = getUser()
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  useEffect(() => {
    if (!toast) return undefined
    const timer = setTimeout(() => setToast(null), 4500)
    return () => clearTimeout(timer)
  }, [toast])

  const handleLocked = useCallback((accessState) => {
    const next = lockedToastFor(accessState)
    if (next) setToast(next)
  }, [])

  if (authed) {
    return <Navigate to="/history" replace />
  }

  const authState = { authed, isAdmin }

  return (
    <div className="gateway-landing-root">
      <div className="sl-container">
        <section className="sl-hero">
          <h1>CompanyAnalyzer</h1>
          <p className="tagline">Company Intelligence &amp; Monitoring</p>
          <p className="desc">
            기업 홈페이지 자동 크롤링과 AI 분석으로 구조·동향·리스크를 정리하고, 키워드 뉴스 수집·일/주/월간 브리핑까지 한 흐름으로 제공하는 기업 인텔리전스 플랫폼
          </p>
        </section>

        <section className="sl-section">
          <div className="sl-section-title">Features</div>
          <div className="sl-features">
            {FEATURES.map((feature) => (
              <FeatureCard
                key={feature.name}
                feature={feature}
                accessState={accessFor(feature.level, authState)}
                onLocked={handleLocked}
              />
            ))}
          </div>
        </section>

        <section className="sl-section sl-arch">
          <div className="sl-section-title">Architecture</div>
          <div className="sl-arch-diagram">
            <div className="sl-arch-node">
              <div className="sl-arch-node-label">Frontend</div>
              <div className="sl-arch-node-tech">React + Vite<br /><span className="sl-arch-node-tech-sub">Gateway</span></div>
            </div>
            <div className="sl-arch-arrow">→</div>
            <div className="sl-arch-node highlight">
              <div className="sl-arch-node-label">Backend</div>
              <div className="sl-arch-node-tech">FastAPI<br /><span className="sl-arch-node-tech-sub">+ 크롤러</span></div>
            </div>
            <div className="sl-arch-arrow">→</div>
            <div className="sl-arch-node">
              <div className="sl-arch-node-label">Data Layer</div>
              <div className="sl-arch-node-tech">PostgreSQL<br /><span className="sl-arch-node-tech-sub">분석·이력</span></div>
            </div>
            <div className="sl-arch-arrow">←</div>
            <div className="sl-arch-node">
              <div className="sl-arch-node-label">AI Engine</div>
              <div className="sl-arch-node-tech">LLM<br /><span className="sl-arch-node-tech-sub">요약·브리핑</span></div>
            </div>
          </div>
        </section>

        <section className="sl-section sl-flow">
          <div className="sl-section-title">Service Flow</div>
          <div className="sl-flow-steps">
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">1</div>
              <div className="sl-flow-step-label">URL 입력</div>
              <div className="sl-flow-step-desc">대상 기업 등록</div>
            </div>
            <div className="sl-flow-arrow">→</div>
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">2</div>
              <div className="sl-flow-step-label">크롤링</div>
              <div className="sl-flow-step-desc">홈페이지·뉴스 수집</div>
            </div>
            <div className="sl-flow-arrow">→</div>
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">3</div>
              <div className="sl-flow-step-label">AI 분석</div>
              <div className="sl-flow-step-desc">구조·요약·리스크</div>
            </div>
            <div className="sl-flow-arrow">→</div>
            <div className="sl-flow-step">
              <div className="sl-flow-step-num">4</div>
              <div className="sl-flow-step-label">리포트/브리핑</div>
              <div className="sl-flow-step-desc">PDF · 이메일 발송</div>
            </div>
          </div>
        </section>

        <section className="sl-section sl-tech">
          <div className="sl-section-title">Tech Stack</div>
          <div className="sl-tech-list">
            {TECH_STACK.map((tech) => (
              <span className="sl-tech-badge" key={tech.name}>
                <span className="sl-tech-dot" style={{ background: tech.dot }} />
                {tech.name}
              </span>
            ))}
          </div>
        </section>

        <section className="sl-section sl-connected">
          <div className="sl-section-title">Connected Services</div>
          <div className="sl-connected-grid">
            {CONNECTED_SERVICES.map((svc) => (
              <a
                key={svc.name}
                href={svc.href}
                target="_blank"
                rel="noopener noreferrer"
                className="sl-connected-card"
              >
                <span className="sl-connected-dot" style={{ background: svc.dot }} />
                <div className="sl-connected-info">
                  <div className="sl-connected-name">{svc.name}</div>
                  <div className="sl-connected-role">{svc.role}</div>
                </div>
                <span className="sl-connected-arrow">→</span>
              </a>
            ))}
          </div>
        </section>
      </div>

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  )
}

export default GatewayLanding
