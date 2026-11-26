"""
Сервис лидов: capture, согласия, статусы, автоудаление и выгрузка.

Смысл таблицы — видеть воронку «email -> оплата», которой раньше не было:
запись о клиенте создавалась только по факту платежа.

Порядок действий важен юридически (ФЗ-152): согласие на обработку ПДн должно
быть получено ДО начала самой обработки. Поэтому лид создаётся не проверкой
сеанса (GET /session/check — его могут слать сканеры и боты), а явным POST
с уже отмеченными согласиями.
"""
import csv
import io
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.database import (
    Lead,
    RETENTION_NEW_DAYS,
    RETENTION_PAID_DAYS,
)

# Текущая редакция политики/оферты. Фиксируется в лиде: через год нужно
# доказать, на какой именно текст человек согласился, а не «галочка была».
CONSENT_VERSION = "1.0"

# Поля для CSV-экспорта (полный набор).
EXPORT_FIELDS = [
    "email", "status", "created_at", "paid_at", "amount", "pays",
    "payment_id", "source",
    "consent_pd", "consent_offer", "consent_version", "consent_at",
    "consent_ip", "delete_after",
]


def _as_naive(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite хранит наивные datetime — приводим входящие значения к тому же виду."""
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _parse_date(value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    """
    Разбор границы диапазона. Принимает 'YYYY-MM-DD' или ISO datetime.
    Для правой границы дата трактуется как конец суток, иначе записи этого
    дня в диапазон не попадут.
    """
    if not value:
        return None
    try:
        if len(value) == 10:
            d = date.fromisoformat(value)
            base = datetime(d.year, d.month, d.day)
            return base + timedelta(days=1) - timedelta(seconds=1) if end_of_day else base
        return _as_naive(datetime.fromisoformat(value))
    except ValueError:
        return None


class LeadService:

    # ---------- запись ----------

    def capture(
        self,
        db: Session,
        email: str,
        consent_pd: bool,
        consent_offer: bool,
        ip: str = "",
        user_agent: str = "",
        source: str = "",
    ) -> Lead:
        """
        Зафиксировать лида с его согласиями.

        Email уникален: повторный захват обновляет существующую запись,
        а не создаёт дубликат. Согласия перезаписываются только когда их
        действительно дали — снятие галочки задним числом не допускается.
        """
        email = (email or "").strip().lower()
        lead = db.query(Lead).filter(Lead.email == email).first()

        now = datetime.now()
        granted = bool(consent_pd and consent_offer)

        if lead is None:
            lead = Lead(
                email=email,
                status="new",
                created_at=now,
                pays=0,
                source=source or "",
                delete_after=now + timedelta(days=RETENTION_NEW_DAYS),
            )
            db.add(lead)

        if source:
            lead.source = source

        if granted:
            lead.consent_pd = True
            lead.consent_offer = True
            lead.consent_version = CONSENT_VERSION
            lead.consent_at = now
            lead.consent_ip = ip or ""
            lead.consent_user_agent = (user_agent or "")[:512]

        # Оплаченный лид не должен откатиться к new по повторному захвату.
        if lead.status == "new" and lead.paid_at is not None:
            lead.status = "paid"

        db.commit()
        db.refresh(lead)
        return lead

    def mark_paid(
        self,
        db: Session,
        email: str,
        payment_id: Optional[str] = None,
        amount: Optional[int] = None,
    ) -> Optional[Lead]:
        """
        Пометить лид оплаченным. Вызывается из webhook и /payment/status.

        Лид создаётся и если его вдруг не было (например, клиент пришёл в
        обход формы с согласиями) — иначе оплата осталась бы не видна в
        воронке. Но в этом случае согласия будут False, и это честно:
        отсутствие согласия видно как факт.
        """
        email = (email or "").strip().lower()
        if not email:
            return None

        now = datetime.now()
        lead = db.query(Lead).filter(Lead.email == email).first()

        if lead is None:
            lead = Lead(email=email, created_at=now, pays=0, source="")
            db.add(lead)

        # Идемпотентность: ЮKassa повторяет webhook, пока не получит 200, а
        # фронт параллельно опрашивает /payment/status. Оба пути ведут сюда,
        # поэтому по одному и тому же платежу счётчик оплат не наращиваем —
        # иначе pays показывал бы 2-3 при единственной оплате.
        is_same_payment = bool(payment_id) and lead.payment_id == payment_id

        lead.status = "paid"
        lead.paid_at = now
        if payment_id:
            lead.payment_id = payment_id
        if amount is not None:
            lead.amount = amount
        if not is_same_payment:
            lead.pays = (lead.pays or 0) + 1
        # С момента оплаты срок хранения считаем по более длинному основанию.
        lead.delete_after = now + timedelta(days=RETENTION_PAID_DAYS)

        db.commit()
        db.refresh(lead)
        return lead

    def mark_expired(self, db: Session, email: str) -> None:
        """
        Сеанс истёк: статус меняется на expired, но ПДн остаются до срока
        delete_after — удаление по сроку отдельное и не привязано к статусу.
        """
        email = (email or "").strip().lower()
        lead = db.query(Lead).filter(Lead.email == email).first()
        if lead and lead.status == "paid":
            lead.status = "expired"
            db.commit()

    # ---------- автоудаление ----------

    def purge_expired(self, db: Session) -> int:
        """
        Удалить лиды с истёкшим delete_after (ФЗ-152: ПДн не хранятся вечно).

        Дёшево и без планировщика: вызывается при открытии списка лидов и
        при старте приложения. Срок уже проставлен при создании/оплате.
        """
        cutoff = datetime.now()
        deleted = db.query(Lead).filter(
            Lead.delete_after.isnot(None),
            Lead.delete_after < cutoff,
        ).delete(synchronize_session=False)
        if deleted:
            db.commit()
        return deleted

    # ---------- чтение ----------

    def _filtered_query(
        self,
        db: Session,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
    ):
        """
        Общий фильтр для списка и экспорта — иначе превью и файл могут
        разойтись по составу записей.
        Диапазон применяется к created_at: это точка входа в воронку.
        """
        q = db.query(Lead)
        conditions = []

        if status and status != "all":
            conditions.append(Lead.status == status)

        dt_from = _parse_date(date_from, end_of_day=False)
        if dt_from:
            conditions.append(Lead.created_at >= dt_from)

        dt_to = _parse_date(date_to, end_of_day=True)
        if dt_to:
            conditions.append(Lead.created_at <= dt_to)

        if search:
            conditions.append(Lead.email.ilike(f"%{search.strip().lower()}%"))

        if conditions:
            q = q.filter(and_(*conditions))
        return q

    def list_leads(
        self,
        db: Session,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Список лидов + общее число подходящих записей (для пагинации)."""
        q = self._filtered_query(db, status, date_from, date_to, search)
        total = q.count()
        rows = (
            q.order_by(Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [r.to_dict() for r in rows], total

    def funnel(self, db: Session) -> Dict[str, Any]:
        """
        Счётчики воронки. Ради них таблица и заведена: список сам по себе
        бесполезен, важна конверсия email -> оплата.

        Важно: выручку и конверсию считаем по paid_at, а не по текущему
        статусу. Когда сеанс истекает, mark_expired переводит статус в
        expired, и подсчёт по статусу обнулял бы деньги за уже оплаченные
        заказы: клиент заплатил, а в отчёте выручка 0.
        """
        total = db.query(Lead).count()
        # Активные сеансы (статус paid) — отдельная плитка.
        paid = db.query(Lead).filter(Lead.status == "paid").count()
        new = db.query(Lead).filter(Lead.status == "new").count()
        expired = db.query(Lead).filter(Lead.status == "expired").count()
        # Все, кто когда-либо оплатил, независимо от того, истёк ли сеанс.
        paid_total = db.query(Lead).filter(Lead.paid_at.isnot(None)).count()
        revenue = db.query(Lead).filter(Lead.paid_at.isnot(None)).with_entities(
            Lead.amount
        ).all()
        revenue_sum = sum((r[0] or 0) for r in revenue)
        consented = db.query(Lead).filter(
            Lead.consent_pd.is_(True), Lead.consent_offer.is_(True)
        ).count()

        return {
            "total": total,
            "new": new,
            "paid": paid,
            "paid_total": paid_total,
            "expired": expired,
            "revenue": revenue_sum,
            "consented": consented,
            "conversion_pct": round(paid_total / total * 100, 1) if total else 0.0,
        }

    def export_csv(
        self,
        db: Session,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search: Optional[str] = None,
    ) -> str:
        """
        CSV со всеми полями выбранных записей.

        BOM обязателен: Excel без него определяет кириллицу как ANSI и
        открывает файл кракозябрами.
        """
        rows, _ = self.list_leads(
            db, status, date_from, date_to, search, limit=100000, offset=0
        )

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, lineterminator="\r\n")
        writer.writerow({f: _header(f) for f in EXPORT_FIELDS})
        for row in rows:
            writer.writerow({f: _cell(row.get(f)) for f in EXPORT_FIELDS})

        return "\ufeff" + buf.getvalue()


def _header(field: str) -> str:
    headers = {
        "email": "Email",
        "status": "Статус",
        "created_at": "Дата захвата",
        "paid_at": "Дата оплаты",
        "amount": "Сумма, руб",
        "pays": "Оплат всего",
        "payment_id": "ID платежа",
        "source": "Источник",
        "consent_pd": "Согласие ПДн",
        "consent_offer": "Согласие оферта",
        "consent_version": "Версия политики",
        "consent_at": "Дата согласия",
        "consent_ip": "IP согласия",
        "delete_after": "Удалить после",
    }
    return headers.get(field, field)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, str) and "T" in value:
        # ISO-datetime приводим к читаемому виду для Excel
        try:
            return datetime.fromisoformat(value).strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return value
    return str(value)


lead_service = LeadService()
