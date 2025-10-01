"""
CSV-based Job Management System for HR Portal
Stores jobs and applications in CSV files for easy data analysis
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import hashlib

class SimpleJobManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # CSV file paths
        self.jobs_csv = self.data_dir / "jobs.csv"
        self.applications_csv = self.data_dir / "applications.csv"
        
        # Initialize CSV files if they don't exist
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Initialize CSV files with headers if they don't exist"""
        # Jobs CSV headers
        if not self.jobs_csv.exists():
            with open(self.jobs_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'job_id', 'title', 'description', 'requirements', 'company', 'hr_contact',
                    'department', 'employment_type', 'work_location', 'location', 'experience_level',
                    'salary_range', 'benefits', 'required_skills', 'preferred_skills', 'technologies',
                    'education_level', 'language_requirements', 'urgency', 'positions_available',
                    'application_deadline', 'start_date', 'application_requirements', 'evaluation_weights',
                    'evaluation_criteria', 'company_size', 'company_description', 'website',
                    'status', 'created_at', 'application_count'
                ])
        
        # Applications CSV headers
        if not self.applications_csv.exists():
            with open(self.applications_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'application_id', 'job_id', 'candidate_id', 'candidate_name', 'candidate_email',
                    'candidate_phone', 'candidate_summary', 'resume_filename', 'resume_text',
                    'submitted_at', 'overall_score', 'recommendation', 'skills_found', 'experience_match',
                    'education_match', 'culture_fit', 'ai_reasoning', 'key_strengths', 'improvement_areas'
                ])
    
    def _generate_job_id(self) -> str:
        """Generate unique job ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"JOB_{timestamp}"
    
    def _generate_candidate_id(self, candidate_name: str, email: str) -> str:
        """Generate anonymous candidate ID"""
        data = f"{candidate_name}_{email}_{datetime.now().isoformat()}"
        hash_obj = hashlib.md5(data.encode())
        return f"CAND_{hash_obj.hexdigest()[:8].upper()}"
    
    def create_job(self, **job_data) -> Dict[str, Any]:
        """Create a new job posting and save to CSV"""
        job_id = self._generate_job_id()
        created_at = datetime.now().isoformat()
        
        job = {
            'job_id': job_id,
            'title': job_data.get('title', ''),
            'description': job_data.get('description', ''),
            'requirements': job_data.get('requirements', ''),
            'company': job_data.get('company', ''),
            'hr_contact': job_data.get('hr_contact', ''),
            'department': job_data.get('department', ''),
            'employment_type': job_data.get('employment_type', 'full-time'),
            'work_location': job_data.get('work_location', 'remote'),
            'location': job_data.get('location', ''),
            'experience_level': job_data.get('experience_level', 'mid'),
            'salary_range': job_data.get('salary_range', ''),
            'benefits': job_data.get('benefits', ''),
            'required_skills': job_data.get('required_skills', ''),
            'preferred_skills': job_data.get('preferred_skills', ''),
            'technologies': job_data.get('technologies', ''),
            'education_level': job_data.get('education_level', ''),
            'language_requirements': job_data.get('language_requirements', ''),
            'urgency': job_data.get('urgency', 'medium'),
            'positions_available': job_data.get('positions_available', 1),
            'application_deadline': job_data.get('application_deadline', ''),
            'start_date': job_data.get('start_date', ''),
            'application_requirements': str(job_data.get('application_requirements', [])),
            'evaluation_weights': str(job_data.get('evaluation_weights', {})),
            'evaluation_criteria': job_data.get('evaluation_criteria', ''),
            'company_size': job_data.get('company_size', ''),
            'company_description': job_data.get('company_description', ''),
            'website': job_data.get('website', ''),
            'status': 'active',
            'created_at': created_at,
            'application_count': 0
        }
        
        # Append to CSV
        with open(self.jobs_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([job[key] for key in job.keys()])
        
        return job
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from CSV"""
        jobs = []
        if self.jobs_csv.exists():
            with open(self.jobs_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Update application count
                    app_count = self._count_applications(row['job_id'])
                    row['application_count'] = app_count
                    jobs.append(row)
        return jobs
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get specific job by ID"""
        jobs = self.list_jobs()
        for job in jobs:
            if job['job_id'] == job_id:
                return job
        return None
    
    def _count_applications(self, job_id: str) -> int:
        """Count applications for a job"""
        count = 0
        if self.applications_csv.exists():
            with open(self.applications_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['job_id'] == job_id:
                        count += 1
        return count
    
    def submit_application(self, job_id: str, candidate_name: str, candidate_email: str,
                          candidate_phone: str, candidate_summary: str, resume_filename: str,
                          resume_text: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Submit job application and save to CSV"""
        application_id = f"APP_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        candidate_id = self._generate_candidate_id(candidate_name, candidate_email)
        submitted_at = datetime.now().isoformat()
        
        application = {
            'application_id': application_id,
            'job_id': job_id,
            'candidate_id': candidate_id,
            'candidate_name': candidate_name,
            'candidate_email': candidate_email,
            'candidate_phone': candidate_phone,
            'candidate_summary': candidate_summary,
            'resume_filename': resume_filename,
            'resume_text': resume_text.replace('\n', ' ').replace('\r', ' '),  # Clean for CSV but preserve full content
            'submitted_at': submitted_at,
            'overall_score': evaluation.get('overall_score', 0),
            'recommendation': evaluation.get('recommendation', 'unknown'),
            'skills_found': str(evaluation.get('skills_found', [])),
            'experience_match': evaluation.get('experience_match', 0),
            'education_match': evaluation.get('education_match', 0),
            'culture_fit': evaluation.get('culture_fit', 0),
            'ai_reasoning': evaluation.get('reasoning', '').replace('\n', ' '),
            'key_strengths': str(evaluation.get('key_strengths', [])),
            'improvement_areas': str(evaluation.get('improvement_areas', []))
        }
        
        # Append to CSV
        with open(self.applications_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([application[key] for key in application.keys()])
        
        return {
            'application_id': application_id,
            'candidate_id': candidate_id,
            'evaluation': evaluation
        }
    
    def get_job_applications(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all applications for a specific job"""
        applications = []
        if self.applications_csv.exists():
            with open(self.applications_csv, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['job_id'] == job_id:
                        # Convert string representations back to proper format
                        application = dict(row)
                        try:
                            # Handle both JSON and Python list string formats
                            def safe_parse_list(value):
                                if not value or value == '[]':
                                    return []
                                try:
                                    # Try JSON first
                                    return json.loads(value)
                                except:
                                    # Fall back to eval for Python list strings like "['item1', 'item2']"
                                    try:
                                        return eval(value) if isinstance(eval(value), list) else []
                                    except:
                                        return []
                            
                            application['evaluation'] = {
                                'overall_score': float(row['overall_score']) if row['overall_score'] else 0,
                                'recommendation': row['recommendation'],
                                'skills_found': safe_parse_list(row['skills_found']),
                                'experience_match': float(row['experience_match']) if row['experience_match'] else 0,
                                'education_match': float(row['education_match']) if row['education_match'] else 0,
                                'culture_fit': float(row['culture_fit']) if row['culture_fit'] else 0,
                                'reasoning': row['ai_reasoning'],
                                'key_strengths': safe_parse_list(row['key_strengths']),
                                'improvement_areas': safe_parse_list(row['improvement_areas'])
                            }
                        except:
                            application['evaluation'] = {
                                'overall_score': 0,
                                'recommendation': 'unknown',
                                'skills_found': [],
                                'experience_match': 0,
                                'education_match': 0,
                                'culture_fit': 0,
                                'reasoning': '',
                                'key_strengths': [],
                                'improvement_areas': []
                            }
                        applications.append(application)
        return applications
    
    def get_application_stats(self, job_id: str) -> Dict[str, Any]:
        """Get application statistics for a job"""
        applications = self.get_job_applications(job_id)
        total = len(applications)
        
        if total == 0:
            return {
                'total_applications': 0,
                'hire_recommended': 0,
                'interview_recommended': 0,
                'reject_recommended': 0,
                'average_score': 0
            }
        
        hire_count = len([app for app in applications if app['recommendation'] == 'hire'])
        interview_count = len([app for app in applications if app['recommendation'] == 'interview'])
        reject_count = len([app for app in applications if app['recommendation'] == 'reject'])
        
        scores = [float(app['overall_score']) for app in applications if app['overall_score']]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'total_applications': total,
            'hire_recommended': hire_count,
            'interview_recommended': interview_count,
            'reject_recommended': reject_count,
            'average_score': avg_score
        }

# Global instance
_job_manager = None

def get_job_manager() -> SimpleJobManager:
    """Get singleton job manager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = SimpleJobManager()
    return _job_manager