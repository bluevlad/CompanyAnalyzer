"""이메일 발송 서비스 - 분석 결과를 뉴스레터 형식으로 발송"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.SMTP_HOST)

    async def send_analysis_report(
        self,
        to_email: str,
        company_name: str,
        analysis_data: dict,
    ) -> dict:
        """분석 결과를 이메일로 발송합니다."""
        if not self.is_configured:
            return {"success": False, "error": "SMTP not configured"}

        try:
            summary = analysis_data.get("results", {}).get("summary", {})
            scores = summary.get("overall_scores", {})

            template_data = {
                "company_name": company_name,
                "scores": scores,
                "top_strengths": summary.get("top_strengths", []),
                "top_improvements": summary.get("top_improvements", []),
                "overall_assessment": summary.get("overall_assessment", ""),
                "one_line_summary": summary.get("one_line_summary", ""),
                "crawled_pages": analysis_data.get("crawled_pages", 0),
                "total_tokens": analysis_data.get("total_tokens", 0),
                "analysis_duration": analysis_data.get("analysis_duration"),
                "completed_at": analysis_data.get("completed_at", ""),
                "result_url": f"{self.settings.FRONTEND_URL}/result/{analysis_data.get('id', '')}",
            }

            # HTML 렌더링
            template = self.jinja_env.get_template("newsletter.html")
            html_content = template.render(**template_data)

            # 플레인 텍스트 버전
            plain_text = self._build_plain_text(template_data)

            # MIME 메시지 구성
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[CompanyAnalyzer] {company_name} 분석 결과"
            msg["From"] = f"{self.settings.SMTP_FROM_NAME} <{self.settings.SMTP_FROM_EMAIL}>"
            msg["To"] = to_email

            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 발송
            await aiosmtplib.send(
                msg,
                hostname=self.settings.SMTP_HOST,
                port=self.settings.SMTP_PORT,
                username=self.settings.SMTP_USER or None,
                password=self.settings.SMTP_PASSWORD or None,
                use_tls=self.settings.SMTP_USE_TLS,
            )

            logger.info(f"Email sent to {to_email} for {company_name}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Email send failed for {to_email}: {e}")
            return {"success": False, "error": str(e)}

    def _build_plain_text(self, data: dict) -> str:
        """플레인 텍스트 버전 생성"""
        scores = data.get("scores", {})
        lines = [
            f"CompanyAnalyzer - {data['company_name']} 분석 결과",
            "=" * 50,
            "",
        ]

        if data.get("one_line_summary"):
            lines.append(f'"{data["one_line_summary"]}"')
            lines.append("")

        if scores:
            lines.append("[종합 점수]")
            if scores.get("business"):
                lines.append(f"  사업: {scores['business']}/10")
            if scores.get("digital"):
                lines.append(f"  디지털: {scores['digital']}/10")
            if scores.get("branding"):
                lines.append(f"  브랜딩: {scores['branding']}/10")
            if scores.get("overall"):
                lines.append(f"  종합: {scores['overall']}/10")
            lines.append("")

        if data.get("top_strengths"):
            lines.append("[주요 강점]")
            for item in data["top_strengths"]:
                lines.append(f"  {item.get('rank', '-')}. {item.get('title', '')}")
                if item.get("description"):
                    lines.append(f"     {item['description']}")
            lines.append("")

        if data.get("top_improvements"):
            lines.append("[개선 필요 사항]")
            for item in data["top_improvements"]:
                lines.append(f"  {item.get('rank', '-')}. {item.get('title', '')}")
                if item.get("description"):
                    lines.append(f"     {item['description']}")
                if item.get("suggestion"):
                    lines.append(f"     > 제안: {item['suggestion']}")
            lines.append("")

        if data.get("overall_assessment"):
            lines.append("[종합 평가]")
            lines.append(data["overall_assessment"])
            lines.append("")

        lines.append("-" * 50)
        lines.append(f"자세한 결과 보기: {data.get('result_url', '')}")

        return "\n".join(lines)
