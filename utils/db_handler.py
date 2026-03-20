from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


class TaskReport(Base):
    __tablename__ = "task_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    thread_id: Mapped[str] = mapped_column(String(100), index=True)
    task_description: Mapped[str] = mapped_column(Text)
    analysis_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    analysis_report: Mapped[str] = mapped_column(Text, default="")
    extracted_data_json: Mapped[list[dict[str, Any]]] = mapped_column(
        SQLITE_JSON, default=list
    )
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ScrapedIntelligence(Base):
    __tablename__ = "intelligence_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(100), index=True)
    thread_id: Mapped[str] = mapped_column(String(100), index=True)
    source_url: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(50), default="general")
    raw_content: Mapped[str] = mapped_column(Text, default="")
    structured_data: Mapped[dict[str, Any]] = mapped_column(SQLITE_JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class DBHandler:
    """
    Business DB handler (separate from LangGraph checkpointer DB).

    Stores final intelligence outputs and task-level report snapshots.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path) if db_path else settings.reports_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def upsert_task_report(
        self,
        *,
        task_id: str,
        thread_id: str,
        task_description: str,
        analysis_type: str,
        status: str,
        analysis_report: str,
        extracted_data: list[dict[str, Any]],
        error_count: int,
    ) -> None:
        with self.SessionLocal() as session:
            stmt = select(TaskReport).where(TaskReport.task_id == task_id)
            report = session.execute(stmt).scalar_one_or_none()
            if report is None:
                report = TaskReport(
                    task_id=task_id,
                    thread_id=thread_id,
                    task_description=task_description,
                    analysis_type=analysis_type,
                )
                session.add(report)

            report.thread_id = thread_id
            report.task_description = task_description
            report.analysis_type = analysis_type
            report.status = status
            report.analysis_report = analysis_report
            report.extracted_data_json = extracted_data
            report.error_count = error_count
            report.updated_at = datetime.utcnow()
            session.commit()

    def save_intelligence(
        self,
        *,
        task_id: str,
        thread_id: str,
        source_url: str,
        category: str,
        raw_content: str,
        structured_data: dict[str, Any],
        summary: str,
    ) -> int:
        with self.SessionLocal() as session:
            row = ScrapedIntelligence(
                task_id=task_id,
                thread_id=thread_id,
                source_url=source_url,
                category=category,
                raw_content=raw_content,
                structured_data=structured_data,
                summary=summary,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def get_task_report(self, task_id: str) -> TaskReport | None:
        with self.SessionLocal() as session:
            stmt = select(TaskReport).where(TaskReport.task_id == task_id)
            return session.execute(stmt).scalar_one_or_none()

    def get_reports_by_task(self, task_id: str) -> list[ScrapedIntelligence]:
        with self.SessionLocal() as session:
            stmt = (
                select(ScrapedIntelligence)
                .where(ScrapedIntelligence.task_id == task_id)
                .order_by(ScrapedIntelligence.created_at.desc())
            )
            return list(session.execute(stmt).scalars().all())


_DB_SINGLETON: DBHandler | None = None


def get_db_handler() -> DBHandler:
    global _DB_SINGLETON
    if _DB_SINGLETON is None:
        _DB_SINGLETON = DBHandler()
    return _DB_SINGLETON


# Backward compatibility alias.
ReportDBHandler = DBHandler

