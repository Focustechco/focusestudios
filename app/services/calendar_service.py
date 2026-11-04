from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.scheduled_post import ScheduledPost
from app.models.post_draft import PostDraft
from app.models.media_asset import MediaAsset
from app.models.approval import Approval
from app.models.account import Account
from app.models.audit_event import AuditEvent
from app.core.timezone import (
    combine_date_slot,
    to_fortaleza,
    to_utc,
    get_current_time_fortaleza,
    get_current_time_utc,
    format_fortaleza
)


class CalendarService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calcula as métricas de operação, estoque, cobertura e déficit."""
        now_fortaleza = get_current_time_fortaleza()
        today = now_fortaleza.date()

        # 1. Total de vídeos no estoque disponíveis (ativos sem publicação)
        published_asset_ids = self.db.query(MediaAsset.id).join(
            PostDraft, PostDraft.media_asset_id == MediaAsset.id
        ).join(
            ScheduledPost, ScheduledPost.post_draft_id == PostDraft.id
        ).filter(ScheduledPost.status == "PUBLISHED").subquery()

        available_stock_count = self.db.query(MediaAsset).filter(
            ~MediaAsset.id.in_(published_asset_ids.select())
        ).count()

        # 2. Dias de cobertura (Estoque / Meta diária)
        coverage_days = round(available_stock_count / max(settings.DAILY_POST_TARGET, 1), 1)

        # 3. Publicações de hoje (Programadas vs Publicadas)
        start_of_day_utc = to_utc(datetime.combine(today, datetime.min.time()))
        end_of_day_utc = to_utc(datetime.combine(today, datetime.max.time()))

        today_scheduled = self.db.query(ScheduledPost).filter(
            ScheduledPost.scheduled_time_utc >= start_of_day_utc,
            ScheduledPost.scheduled_time_utc <= end_of_day_utc,
            ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING", "PUBLISHED"])
        ).count()

        today_published = self.db.query(ScheduledPost).filter(
            ScheduledPost.scheduled_time_utc >= start_of_day_utc,
            ScheduledPost.scheduled_time_utc <= end_of_day_utc,
            ScheduledPost.status == "PUBLISHED"
        ).count()

        # 4. Déficit diário
        daily_deficit = max(0, settings.DAILY_POST_TARGET - today_scheduled)

        # 5. Falhas pendentes de ação
        failed_count = self.db.query(ScheduledPost).filter(
            ScheduledPost.status.in_(["FAILED", "UNKNOWN", "NEEDS_REVIEW"])
        ).count()

        # 6. Modo e Bloqueios
        account = self.db.query(Account).filter_by(is_active=True).first()
        is_blocked = (
            settings.OPERATION_MODE == "DIRECT_POST" and
            (not account or not account.is_eligible or account.is_token_expired())
        )

        return {
            "operation_mode": settings.OPERATION_MODE,
            "daily_target": settings.DAILY_POST_TARGET,
            "today_scheduled": today_scheduled,
            "today_published": today_published,
            "daily_deficit": daily_deficit,
            "available_stock": available_stock_count,
            "coverage_days": coverage_days,
            "failed_count": failed_count,
            "is_blocked": is_blocked,
            "timezone": settings.TIMEZONE
        }

    def schedule_approved_drafts(self, days_ahead: int = 1) -> Dict[str, Any]:
        """
        Organiza o calendário interno com a meta de 10 publicações por dia.
        Usa os slots padrão em America/Fortaleza.
        Garante que apenas rascunhos aprovados com consentimento ativo sejam agendados.
        Nunca repete vídeos já agendados ou publicados.
        """
        now_fortaleza = get_current_time_fortaleza()
        today = now_fortaleza.date()
        scheduled_count = 0
        slots = settings.POST_SLOTS

        # Busca rascunhos aprovados que ainda não estão agendados
        scheduled_draft_ids = self.db.query(ScheduledPost.post_draft_id).filter(
            ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING", "PUBLISHED"])
        ).subquery()

        approved_drafts = self.db.query(PostDraft).join(
            Approval, Approval.post_draft_id == PostDraft.id
        ).filter(
            Approval.is_active == True,
            PostDraft.status == "APPROVED",
            ~PostDraft.id.in_(scheduled_draft_ids.select())
        ).all()

        if not approved_drafts:
            return {"scheduled": 0, "message": "Nenhum rascunho aprovado com consentimento ativo disponível."}

        draft_idx = 0
        account = self.db.query(Account).filter_by(is_active=True).first()

        for day_offset in range(min(days_ahead, settings.MAX_CALENDAR_DAYS)):
            target_date = today + timedelta(days=day_offset)

            for slot in slots:
                if draft_idx >= len(approved_drafts):
                    break

                slot_time_utc = combine_date_slot(target_date, slot)

                # Não agendar no passado
                if slot_time_utc <= get_current_time_utc():
                    continue

                # Verificar se o slot já está ocupado
                existing_slot = self.db.query(ScheduledPost).filter(
                    ScheduledPost.scheduled_time_utc == slot_time_utc,
                    ScheduledPost.status.in_(["SCHEDULED", "UPLOADING", "PROCESSING"])
                ).first()

                if existing_slot:
                    continue

                draft = approved_drafts[draft_idx]

                scheduled_post = ScheduledPost(
                    post_draft_id=draft.id,
                    account_id=account.id if account else draft.account_id,
                    scheduled_time_utc=slot_time_utc,
                    status="SCHEDULED",
                    priority=0
                )
                self.db.add(scheduled_post)
                draft.status = "SCHEDULED"
                scheduled_count += 1
                draft_idx += 1

        self.db.commit()
        return {"scheduled": scheduled_count, "remaining_unassigned": len(approved_drafts) - draft_idx}

    def list_calendar_events(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Retorna os eventos do calendário no período informado convertidos para Fortaleza."""
        start_utc = to_utc(datetime.combine(start_date, datetime.min.time()))
        end_utc = to_utc(datetime.combine(end_date, datetime.max.time()))

        posts = self.db.query(ScheduledPost).filter(
            ScheduledPost.scheduled_time_utc >= start_utc,
            ScheduledPost.scheduled_time_utc <= end_utc
        ).order_by(ScheduledPost.scheduled_time_utc.asc()).all()

        events = []
        for post in posts:
            local_dt = to_fortaleza(post.scheduled_time_utc)
            events.append({
                "id": post.id,
                "draft_id": post.post_draft_id,
                "asset_id": post.post_draft.media_asset_id if post.post_draft else None,
                "title": post.post_draft.title if post.post_draft else "Sem título",
                "caption": post.post_draft.caption if post.post_draft else "",
                "status": post.status,
                "time_fortaleza": local_dt.strftime("%H:%M"),
                "date_fortaleza": local_dt.strftime("%Y-%m-%d"),
                "full_formatted": local_dt.strftime("%d/%m/%Y %H:%M"),
                "privacy": post.post_draft.privacy_level if post.post_draft else "SELF_ONLY"
            })
        return events

    def get_monthly_calendar_data(self, year: int, month: int) -> Dict[str, Any]:
        """
        Gera a estrutura completa para exibição em forma de grade de calendário mensal.
        Inclui dias da semana (Dom a Sáb), semanas completas alinhadas e eventos por dia.
        """
        import calendar

        MESES_PT = [
            "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]

        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1

        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1

        now_fortaleza = get_current_time_fortaleza()
        today = now_fortaleza.date()

        # Inicia a semana no Domingo (firstweekday=6)
        cal = calendar.Calendar(firstweekday=6)
        month_days = cal.monthdatescalendar(year, month)

        grid_start = month_days[0][0]
        grid_end = month_days[-1][-1]

        # Busca eventos para toda a grade (inclusive dias de transição do mês)
        events = self.list_calendar_events(grid_start, grid_end)

        events_by_date: Dict[str, List[Dict[str, Any]]] = {}
        for ev in events:
            d_str = ev["date_fortaleza"]
            if d_str not in events_by_date:
                events_by_date[d_str] = []
            events_by_date[d_str].append(ev)

        weeks_data = []
        for week in month_days:
            week_days = []
            for day_date in week:
                d_str = day_date.strftime("%Y-%m-%d")
                day_events = events_by_date.get(d_str, [])
                is_current_month = (day_date.month == month)
                is_today = (day_date == today)
                is_past = (day_date < today)

                target = settings.DAILY_POST_TARGET
                count = len(day_events)
                scheduled_count = sum(1 for e in day_events if e["status"] in ["SCHEDULED", "UPLOADING", "PROCESSING"])
                published_count = sum(1 for e in day_events if e["status"] == "PUBLISHED")

                week_days.append({
                    "date": day_date,
                    "date_str": d_str,
                    "day_num": day_date.day,
                    "is_current_month": is_current_month,
                    "is_today": is_today,
                    "is_past": is_past,
                    "events": day_events,
                    "total_events": count,
                    "scheduled_count": scheduled_count,
                    "published_count": published_count,
                    "daily_target": target,
                    "target_reached": (count >= target),
                    "coverage_pct": min(100, int((count / max(target, 1)) * 100))
                })
            weeks_data.append(week_days)

        month_prefix = f"{year}-{month:02d}"
        total_month_posts = sum(len(evs) for d, evs in events_by_date.items() if d.startswith(month_prefix))

        return {
            "year": year,
            "month": month,
            "month_name": MESES_PT[month] if 1 <= month <= 12 else f"Mês {month}",
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "today_str": today.strftime("%Y-%m-%d"),
            "weeks": weeks_data,
            "weekday_names": ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"],
            "total_month_posts": total_month_posts
        }
