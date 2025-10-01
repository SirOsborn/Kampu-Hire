"""
Job posting manager:
- Stores HR-created job postings in SQLite
- Extracts requirements automatically
- Generates public application links
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import sqlite3
from dataclasses import dataclass
from datetime import datetime
import json
import secrets

from app.services.job_requirements import extract_job_requirements


@dataclass
class JobPosting:
    job_id: str
    title: str
    description: str
    requirements: Dict[str, Any]
    created_at: datetime
    token: str  # used in public links


class JobManager:
    def __init__(self, db_path: str = "candidate_data.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements_json TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        ''')
        # Minimal index
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title)')
        conn.commit()
        conn.close()

    def create_job(self, title: str, description: str) -> Dict[str, Any]:
        """Create a job and auto-extract requirements."""
        reqs = extract_job_requirements(title, description)
        job_id = self._generate_job_id()
        token = self._generate_token()
        posting = JobPosting(
            job_id=job_id,
            title=title,
            description=description,
            requirements=reqs,
            created_at=datetime.now(),
            token=token,
        )
        self._save_job(posting)
        return {
            'job_id': posting.job_id,
            'title': posting.title,
            'description': posting.description,
            'requirements': posting.requirements,
            'token': posting.token,
            'created_at': posting.created_at.isoformat()
        }

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT job_id, title, description, requirements_json, token, created_at FROM jobs WHERE job_id = ?', (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'job_id': row[0],
                'title': row[1],
                'description': row[2],
                'requirements': json.loads(row[3] or '{}'),
                'token': row[4],
                'created_at': row[5]
            }
        finally:
            conn.close()

    def get_job_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT job_id, title, description, requirements_json, token, created_at FROM jobs WHERE token = ?', (token,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'job_id': row[0],
                'title': row[1],
                'description': row[2],
                'requirements': json.loads(row[3] or '{}'),
                'token': row[4],
                'created_at': row[5]
            }
        finally:
            conn.close()

    def list_jobs(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT job_id, title, created_at FROM jobs ORDER BY created_at DESC')
            return [{'job_id': r[0], 'title': r[1], 'created_at': r[2]} for r in cursor.fetchall()]
        finally:
            conn.close()

    def _save_job(self, posting: JobPosting):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO jobs (job_id, title, description, requirements_json, token, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                posting.job_id,
                posting.title,
                posting.description,
                json.dumps(posting.requirements),
                posting.token,
                posting.created_at,
            ))
            conn.commit()
        finally:
            conn.close()

    def _generate_job_id(self) -> str:
        return f"JOB-{secrets.token_hex(3).upper()}"

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(12)


def create_job_manager() -> JobManager:
    return JobManager()
