from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import json
from datetime import datetime, timedelta
from app.services.simple_job_manager import get_job_manager
from app.services.explainable_ai_evaluator import evaluate_candidate_simple

router = APIRouter()
job_manager = get_job_manager()

@router.get('/', response_class=HTMLResponse)
async def hr_portal():
    """Comprehensive HR Portal Dashboard"""
    jobs = job_manager.list_jobs()
    
    # Calculate dashboard statistics
    total_jobs = len(jobs)
    active_jobs = len([j for j in jobs if j.get('status', 'active') == 'active'])
    total_applications = sum(len(job_manager.get_job_applications(job['job_id'])) for job in jobs)
    
    # Get recent applications (last 7 days)
    recent_apps = 0
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    for job in jobs:
        apps = job_manager.get_job_applications(job['job_id'])
        recent_apps += len([app for app in apps if app.get('submitted_at', '') > week_ago])
    
    # Build job cards HTML
    job_cards_html = ""
    for job in jobs:
        app_count = len(job_manager.get_job_applications(job['job_id']))
        status = job.get('status', 'active')
        status_color = {'active': '#28a745', 'paused': '#ffc107', 'closed': '#dc3545'}.get(status, '#6c757d')
        created_date = job.get('created_at', '')[:10]
        urgency = job.get('urgency', 'medium')
        urgency_icon = {'high': '🔥', 'medium': '⏰', 'low': '📅'}.get(urgency, '⏰')
        
        job_cards_html += f"""
        <div class="job-card" data-status="{status}">
            <div class="job-header">
                <div class="job-title-section">
                    <h3 class="job-title">{job['title']}</h3>
                    <div class="job-meta">
                        <span class="badge" style="background: {status_color}; color: white;">{status.title()}</span>
                        <span class="urgency">{urgency_icon} {urgency.title()}</span>
                        <span class="date">📅 {created_date}</span>
                    </div>
                </div>
                <div class="job-actions">
                    <button class="btn-icon" onclick="editJob('{job['job_id']}')" title="Edit Job">
                        ✏️
                    </button>
                    <button class="btn-icon" onclick="viewApplications('{job['job_id']}')" title="View Applications">
                        👥 {app_count}
                    </button>
                    <div class="dropdown">
                        <button class="btn-icon dropdown-toggle" onclick="toggleDropdown('{job['job_id']}')">⋮</button>
                        <div class="dropdown-menu" id="dropdown-{job['job_id']}">
                            <a href="#" onclick="shareJob('{job['job_id']}')">🔗 Share Portal</a>
                            <a href="#" onclick="duplicateJob('{job['job_id']}')">📋 Duplicate</a>
                            <a href="#" onclick="pauseJob('{job['job_id']}')">⏸️ Pause</a>
                            <a href="#" onclick="closeJob('{job['job_id']}')">🚫 Close</a>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="job-details">
                <p class="job-description">{job['description'][:150]}...</p>
                
                <div class="job-requirements">
                    <strong>Key Requirements:</strong>
                    <div class="skills-tags">
                        {' '.join([f'<span class="skill-tag">{skill.strip()}</span>' for skill in job.get('required_skills', '').split(',')[:5] if skill.strip()])}
                    </div>
                </div>
                
                <div class="job-stats">
                    <div class="stat">
                        <span class="stat-label">Applications</span>
                        <span class="stat-value">{app_count}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Salary</span>
                        <span class="stat-value">{job.get('salary_range', 'Not specified')}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Location</span>
                        <span class="stat-value">{job.get('location', 'Remote')}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Type</span>
                        <span class="stat-value">{job.get('employment_type', 'Full-time')}</span>
                    </div>
                </div>
                
                <div class="portal-section">
                    <div class="portal-url-container">
                        <label>📝 Application Portal:</label>
                        <div class="portal-url-box">
                            <code id="portal-{job['job_id']}">http://localhost:8000/apply/{job['job_id']}</code>
                            <button class="copy-btn" onclick="copyToClipboard('portal-{job['job_id']}')">📋</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    if not job_cards_html:
        job_cards_html = """
        <div class="empty-state">
            <div class="empty-icon">📋</div>
            <h3>No Jobs Posted Yet</h3>
            <p>Create your first job posting to start receiving applications</p>
            <button class="btn btn-primary" onclick="showCreateForm()">➕ Create First Job</button>
        </div>
        """
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Kampu-Hire HR Portal</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            
            .header {{
                background: white;
                padding: 20px 0;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                border-bottom: 3px solid #667eea;
            }}
            
            .header-content {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .logo-section h1 {{
                color: #667eea;
                font-size: 28px;
                font-weight: 700;
                margin-bottom: 4px;
            }}
            
            .logo-section p {{
                color: #666;
                font-size: 14px;
            }}
            
            .header-actions {{
                display: flex;
                gap: 12px;
                align-items: center;
            }}
            
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s ease;
                font-size: 14px;
            }}
            
            .btn-primary {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            
            .btn-primary:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }}
            
            .btn-secondary {{
                background: #f8f9fa;
                color: #667eea;
                border: 2px solid #e9ecef;
            }}
            
            .btn-secondary:hover {{
                background: #e9ecef;
                border-color: #667eea;
            }}
            
            .dashboard {{
                max-width: 1400px;
                margin: 0 auto;
                padding: 30px 20px;
            }}
            
            .dashboard-stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: white;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                text-align: center;
                border-left: 4px solid #667eea;
            }}
            
            .stat-number {{
                font-size: 32px;
                font-weight: 700;
                color: #667eea;
                margin-bottom: 8px;
            }}
            
            .stat-label {{
                color: #666;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .dashboard-controls {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 16px;
            }}
            
            .filter-section {{
                display: flex;
                gap: 12px;
                align-items: center;
            }}
            
            .filter-select {{
                padding: 8px 12px;
                border: 2px solid #e9ecef;
                border-radius: 6px;
                background: white;
                color: #333;
                cursor: pointer;
            }}
            
            .jobs-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
                gap: 20px;
            }}
            
            .job-card {{
                background: white;
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                transition: all 0.2s ease;
                border: 1px solid #e9ecef;
            }}
            
            .job-card:hover {{
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                transform: translateY(-2px);
            }}
            
            .job-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 16px;
            }}
            
            .job-title {{
                font-size: 18px;
                font-weight: 700;
                color: #333;
                margin-bottom: 8px;
            }}
            
            .job-meta {{
                display: flex;
                gap: 12px;
                align-items: center;
                flex-wrap: wrap;
            }}
            
            .badge {{
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            
            .urgency, .date {{
                font-size: 12px;
                color: #666;
                background: #f8f9fa;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            
            .job-actions {{
                display: flex;
                gap: 8px;
                align-items: center;
            }}
            
            .btn-icon {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 8px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s ease;
            }}
            
            .btn-icon:hover {{
                background: #e9ecef;
                transform: scale(1.05);
            }}
            
            .dropdown {{
                position: relative;
            }}
            
            .dropdown-menu {{
                position: absolute;
                top: 100%;
                right: 0;
                background: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-width: 150px;
                z-index: 1000;
                display: none;
            }}
            
            .dropdown-menu.show {{
                display: block;
            }}
            
            .dropdown-menu a {{
                display: block;
                padding: 12px 16px;
                color: #333;
                text-decoration: none;
                font-size: 14px;
                transition: background 0.2s ease;
            }}
            
            .dropdown-menu a:hover {{
                background: #f8f9fa;
            }}
            
            .job-description {{
                color: #666;
                line-height: 1.5;
                margin-bottom: 16px;
            }}
            
            .job-requirements {{
                margin-bottom: 16px;
            }}
            
            .skills-tags {{
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-top: 8px;
            }}
            
            .skill-tag {{
                background: #e8f5e8;
                color: #2e7d32;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }}
            
            .job-stats {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-bottom: 16px;
                padding: 16px;
                background: #f8f9fa;
                border-radius: 8px;
            }}
            
            .stat {{
                text-align: center;
            }}
            
            .stat-label {{
                font-size: 12px;
                color: #666;
                display: block;
                margin-bottom: 4px;
            }}
            
            .stat-value {{
                font-weight: 600;
                color: #333;
                font-size: 14px;
            }}
            
            .portal-section {{
                border-top: 1px solid #e9ecef;
                padding-top: 16px;
            }}
            
            .portal-url-container label {{
                font-size: 12px;
                color: #666;
                font-weight: 600;
                margin-bottom: 8px;
                display: block;
            }}
            
            .portal-url-box {{
                display: flex;
                align-items: center;
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 8px;
            }}
            
            .portal-url-box code {{
                flex: 1;
                background: none;
                border: none;
                font-size: 12px;
                color: #667eea;
                word-break: break-all;
            }}
            
            .copy-btn {{
                background: #667eea;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                margin-left: 8px;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 60px 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }}
            
            .empty-icon {{
                font-size: 64px;
                margin-bottom: 20px;
            }}
            
            .empty-state h3 {{
                color: #333;
                margin-bottom: 12px;
            }}
            
            .empty-state p {{
                color: #666;
                margin-bottom: 24px;
            }}
            
            .modal {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 10000;
                overflow-y: auto;
            }}
            
            .modal.show {{
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .modal-content {{
                background: white;
                border-radius: 12px;
                width: 100%;
                max-width: 800px;
                max-height: 90vh;
                overflow-y: auto;
                position: relative;
            }}
            
            .modal-header {{
                padding: 24px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .modal-header h2 {{
                color: #333;
                font-size: 24px;
            }}
            
            .close-btn {{
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
                padding: 4px;
            }}
            
            .modal-body {{
                padding: 24px;
            }}
            
            @media (max-width: 768px) {{
                .dashboard {{
                    padding: 20px 10px;
                }}
                
                .jobs-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .dashboard-stats {{
                    grid-template-columns: repeat(2, 1fr);
                }}
                
                .job-stats {{
                    grid-template-columns: 1fr;
                }}
                
                .header-content {{
                    flex-direction: column;
                    gap: 16px;
                    text-align: center;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="logo-section">
                    <h1>🎯 Kampu-Hire</h1>
                    <p>AI-Powered HR Recruitment Platform</p>
                </div>
                <div class="header-actions">
                    <button class="btn btn-secondary" onclick="showAnalytics()">📊 Analytics</button>
                    <button class="btn btn-primary" onclick="showCreateForm()">➕ Create New Job</button>
                </div>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="dashboard-stats">
                <div class="stat-card">
                    <div class="stat-number">{total_jobs}</div>
                    <div class="stat-label">Total Jobs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{active_jobs}</div>
                    <div class="stat-label">Active Jobs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_applications}</div>
                    <div class="stat-label">Total Applications</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{recent_apps}</div>
                    <div class="stat-label">This Week</div>
                </div>
            </div>
            
            <div class="dashboard-controls">
                <div class="filter-section">
                    <label>Filter Jobs:</label>
                    <select class="filter-select" onchange="filterJobs(this.value)">
                        <option value="all">All Jobs</option>
                        <option value="active">Active</option>
                        <option value="paused">Paused</option>
                        <option value="closed">Closed</option>
                    </select>
                    
                    <select class="filter-select" onchange="sortJobs(this.value)">
                        <option value="newest">Newest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="most-apps">Most Applications</option>
                        <option value="urgent">Most Urgent</option>
                    </select>
                </div>
                
                <div class="filter-section">
                    <button class="btn btn-secondary" onclick="exportData()">📥 Export Data</button>
                    <button class="btn btn-secondary" onclick="bulkActions()">⚙️ Bulk Actions</button>
                </div>
            </div>
            
            <div class="jobs-grid" id="jobsGrid">
                {job_cards_html}
            </div>
        </div>
        
        <!-- Create Job Modal (will be loaded via another endpoint) -->
        <div class="modal" id="createJobModal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>➕ Create New Job Posting</h2>
                    <button class="close-btn" onclick="closeModal('createJobModal')">&times;</button>
                </div>
                <div class="modal-body" id="createJobContent">
                    <!-- Job creation form will be loaded here -->
                </div>
            </div>
        </div>
        
        <script>
            function showCreateForm() {{
                document.getElementById('createJobModal').classList.add('show');
                loadCreateJobForm();
            }}
            
            function closeModal(modalId) {{
                document.getElementById(modalId).classList.remove('show');
            }}
            
            function loadCreateJobForm() {{
                fetch('/hr/create-job-form')
                    .then(response => response.text())
                    .then(html => {{
                        document.getElementById('createJobContent').innerHTML = html;
                    }});
            }}
            
            function editJob(jobId) {{
                alert(`Edit job: ${{jobId}}`);
                // TODO: Implement job editing
            }}
            
            function viewApplications(jobId) {{
                window.location.href = `/hr/jobs/${{jobId}}/candidates`;
            }}
            
            function toggleDropdown(jobId) {{
                const dropdown = document.getElementById(`dropdown-${{jobId}}`);
                dropdown.classList.toggle('show');
                
                // Close other dropdowns
                document.querySelectorAll('.dropdown-menu').forEach(menu => {{
                    if (menu.id !== `dropdown-${{jobId}}`) {{
                        menu.classList.remove('show');
                    }}
                }});
            }}
            
            function shareJob(jobId) {{
                const url = `http://localhost:8000/apply/${{jobId}}`;
                navigator.clipboard.writeText(url).then(() => {{
                    alert('Application portal URL copied to clipboard!');
                }});
            }}
            
            function copyToClipboard(elementId) {{
                const element = document.getElementById(elementId);
                navigator.clipboard.writeText(element.textContent).then(() => {{
                    alert('URL copied to clipboard!');
                }});
            }}
            
            function filterJobs(status) {{
                const jobCards = document.querySelectorAll('.job-card');
                jobCards.forEach(card => {{
                    if (status === 'all' || card.dataset.status === status) {{
                        card.style.display = 'block';
                    }} else {{
                        card.style.display = 'none';
                    }}
                }});
            }}
            
            function sortJobs(criteria) {{
                // TODO: Implement job sorting
                console.log('Sorting by:', criteria);
            }}
            
            function showAnalytics() {{
                alert('Analytics dashboard coming soon!');
                // TODO: Implement analytics view
            }}
            
            function exportData() {{
                alert('Data export coming soon!');
                // TODO: Implement data export
            }}
            
            function bulkActions() {{
                alert('Bulk actions coming soon!');
                // TODO: Implement bulk actions
            }}
            
            function pauseJob(jobId) {{
                if (confirm('Are you sure you want to pause this job?')) {{
                    // TODO: Implement job pausing
                    alert(`Job ${{jobId}} paused`);
                }}
            }}
            
            function closeJob(jobId) {{
                if (confirm('Are you sure you want to close this job? This will stop accepting new applications.')) {{
                    // TODO: Implement job closing
                    alert(`Job ${{jobId}} closed`);
                }}
            }}
            
            function duplicateJob(jobId) {{
                if (confirm('Create a copy of this job posting?')) {{
                    // TODO: Implement job duplication
                    alert(`Job ${{jobId}} duplicated`);
                }}
            }}
            
            // Close dropdowns when clicking outside
            document.addEventListener('click', function(event) {{
                if (!event.target.matches('.dropdown-toggle')) {{
                    document.querySelectorAll('.dropdown-menu').forEach(menu => {{
                        menu.classList.remove('show');
                    }});
                }}
            }});
            
            // Close modal when clicking outside
            document.addEventListener('click', function(event) {{
                if (event.target.classList.contains('modal')) {{
                    event.target.classList.remove('show');
                }}
            }});
        </script>
    </body>
    </html>
    """)

@router.get('/hr/create-job-form', response_class=HTMLResponse)
async def get_create_job_form():
    """Comprehensive Job Creation Form with all HR settings"""
    return HTMLResponse("""
    <form id="createJobForm" method="post" action="/hr/jobs" onsubmit="submitJob(event)">
        <div class="form-sections">
            <!-- Basic Job Information -->
            <div class="form-section">
                <h3>📋 Basic Information</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="jobTitle">Job Title *</label>
                        <input type="text" id="jobTitle" name="title" required 
                               placeholder="e.g., Senior Data Analyst">
                    </div>
                    
                    <div class="form-group">
                        <label for="department">Department</label>
                        <select id="department" name="department">
                            <option value="">Select Department</option>
                            <option value="engineering">Engineering</option>
                            <option value="data">Data & Analytics</option>
                            <option value="marketing">Marketing</option>
                            <option value="sales">Sales</option>
                            <option value="hr">Human Resources</option>
                            <option value="finance">Finance</option>
                            <option value="operations">Operations</option>
                            <option value="product">Product</option>
                            <option value="design">Design</option>
                            <option value="customer-success">Customer Success</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="jobDescription">Job Description *</label>
                    <textarea id="jobDescription" name="description" required rows="4"
                              placeholder="Describe the role, responsibilities, and what the candidate will be doing..."></textarea>
                </div>
                
                <div class="form-group">
                    <label for="requirements">Requirements & Qualifications *</label>
                    <textarea id="requirements" name="requirements" required rows="4"
                              placeholder="List required skills, experience, education, certifications..."></textarea>
                </div>
            </div>
            
            <!-- Employment Details -->
            <div class="form-section">
                <h3>💼 Employment Details</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="employmentType">Employment Type *</label>
                        <select id="employmentType" name="employment_type" required>
                            <option value="full-time">Full-time</option>
                            <option value="part-time">Part-time</option>
                            <option value="contract">Contract</option>
                            <option value="temporary">Temporary</option>
                            <option value="internship">Internship</option>
                            <option value="freelance">Freelance</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="workLocation">Work Location *</label>
                        <select id="workLocation" name="work_location" required>
                            <option value="remote">Remote</option>
                            <option value="onsite">On-site</option>
                            <option value="hybrid">Hybrid</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="location">Office Location</label>
                        <input type="text" id="location" name="location" 
                               placeholder="e.g., Phnom Penh, Cambodia">
                    </div>
                    
                    <div class="form-group">
                        <label for="experienceLevel">Experience Level *</label>
                        <select id="experienceLevel" name="experience_level" required>
                            <option value="entry">Entry Level (0-2 years)</option>
                            <option value="mid">Mid Level (2-5 years)</option>
                            <option value="senior">Senior Level (5-8 years)</option>
                            <option value="lead">Lead Level (8+ years)</option>
                            <option value="executive">Executive Level</option>
                        </select>
                    </div>
                </div>
            </div>
            
            <!-- Compensation & Benefits -->
            <div class="form-section">
                <h3>💰 Compensation & Benefits</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="salaryMin">Minimum Salary</label>
                        <input type="number" id="salaryMin" name="salary_min" 
                               placeholder="e.g., 1000">
                    </div>
                    
                    <div class="form-group">
                        <label for="salaryMax">Maximum Salary</label>
                        <input type="number" id="salaryMax" name="salary_max" 
                               placeholder="e.g., 1500">
                    </div>
                    
                    <div class="form-group">
                        <label for="currency">Currency</label>
                        <select id="currency" name="currency">
                            <option value="USD">USD ($)</option>
                            <option value="KHR">KHR (៛)</option>
                            <option value="EUR">EUR (€)</option>
                            <option value="GBP">GBP (£)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="salaryPeriod">Salary Period</label>
                        <select id="salaryPeriod" name="salary_period">
                            <option value="monthly">Monthly</option>
                            <option value="annually">Annually</option>
                            <option value="hourly">Hourly</option>
                            <option value="project">Per Project</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="benefits">Benefits & Perks</label>
                    <textarea id="benefits" name="benefits" rows="3"
                              placeholder="List benefits like health insurance, vacation days, remote work, professional development..."></textarea>
                </div>
            </div>
            
            <!-- Skills & Requirements -->
            <div class="form-section">
                <h3>🛠️ Skills & Technical Requirements</h3>
                <div class="form-group">
                    <label for="requiredSkills">Required Skills *</label>
                    <input type="text" id="requiredSkills" name="required_skills" required
                           placeholder="e.g., Python, SQL, Tableau, Data Analysis (comma separated)">
                    <small>Separate skills with commas. These will be used for AI-powered candidate matching.</small>
                </div>
                
                <div class="form-group">
                    <label for="preferredSkills">Preferred Skills</label>
                    <input type="text" id="preferredSkills" name="preferred_skills"
                           placeholder="e.g., Machine Learning, AWS, Power BI (comma separated)">
                </div>
                
                <div class="form-group">
                    <label for="technologies">Technologies & Tools</label>
                    <input type="text" id="technologies" name="technologies"
                           placeholder="e.g., Excel, Jupyter, Git, Docker (comma separated)">
                </div>
                
                <div class="form-grid">
                    <div class="form-group">
                        <label for="educationLevel">Education Level</label>
                        <select id="educationLevel" name="education_level">
                            <option value="">Not specified</option>
                            <option value="high-school">High School</option>
                            <option value="associate">Associate Degree</option>
                            <option value="bachelor">Bachelor's Degree</option>
                            <option value="master">Master's Degree</option>
                            <option value="phd">PhD</option>
                            <option value="certification">Professional Certification</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="languageRequirements">Language Requirements</label>
                        <input type="text" id="languageRequirements" name="language_requirements"
                               placeholder="e.g., English (Fluent), Khmer (Native)">
                    </div>
                </div>
            </div>
            
            <!-- Job Settings & Preferences -->
            <div class="form-section">
                <h3>⚙️ Job Settings & Preferences</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="urgency">Hiring Urgency *</label>
                        <select id="urgency" name="urgency" required>
                            <option value="low">🗓️ Low - Fill within 3+ months</option>
                            <option value="medium" selected>⏰ Medium - Fill within 1-2 months</option>
                            <option value="high">🔥 High - Fill within 2-4 weeks</option>
                            <option value="urgent">🚨 Urgent - Fill ASAP</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="positionsAvailable">Number of Positions</label>
                        <input type="number" id="positionsAvailable" name="positions_available" 
                               value="1" min="1" max="50">
                    </div>
                    
                    <div class="form-group">
                        <label for="applicationDeadline">Application Deadline</label>
                        <input type="date" id="applicationDeadline" name="application_deadline">
                    </div>
                    
                    <div class="form-group">
                        <label for="startDate">Expected Start Date</label>
                        <input type="date" id="startDate" name="start_date">
                    </div>
                </div>
                
                <div class="form-group">
                    <label>Application Requirements</label>
                    <div class="checkbox-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="require_cover_letter" value="true">
                            <span>Require Cover Letter</span>
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" name="require_portfolio" value="true">
                            <span>Require Portfolio/Work Samples</span>
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" name="require_references" value="true">
                            <span>Require References</span>
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" name="require_availability" value="true">
                            <span>Require Availability Information</span>
                        </label>
                    </div>
                </div>
            </div>
            
            <!-- AI Evaluation Settings -->
            <div class="form-section">
                <h3>🤖 AI Evaluation Settings</h3>
                <div class="form-group">
                    <label>Evaluation Weights</label>
                    <div class="weight-controls">
                        <div class="weight-item">
                            <label>Skills Match</label>
                            <input type="range" name="skills_weight" min="0" max="100" value="40" 
                                   oninput="updateWeight(this, 'skillsValue')">
                            <span id="skillsValue">40%</span>
                        </div>
                        <div class="weight-item">
                            <label>Experience Level</label>
                            <input type="range" name="experience_weight" min="0" max="100" value="30" 
                                   oninput="updateWeight(this, 'experienceValue')">
                            <span id="experienceValue">30%</span>
                        </div>
                        <div class="weight-item">
                            <label>Education</label>
                            <input type="range" name="education_weight" min="0" max="100" value="15" 
                                   oninput="updateWeight(this, 'educationValue')">
                            <span id="educationValue">15%</span>
                        </div>
                        <div class="weight-item">
                            <label>Cultural Fit</label>
                            <input type="range" name="culture_weight" min="0" max="100" value="15" 
                                   oninput="updateWeight(this, 'cultureValue')">
                            <span id="cultureValue">15%</span>
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="evaluationCriteria">Custom Evaluation Criteria</label>
                    <textarea id="evaluationCriteria" name="evaluation_criteria" rows="3"
                              placeholder="Specify any custom criteria for AI evaluation (e.g., specific industry experience, leadership skills...)"></textarea>
                </div>
            </div>
            
            <!-- Company Information -->
            <div class="form-section">
                <h3>🏢 Company Information</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label for="company">Company Name *</label>
                        <input type="text" id="company" name="company" required
                               placeholder="Your company name">
                    </div>
                    
                    <div class="form-group">
                        <label for="companySize">Company Size</label>
                        <select id="companySize" name="company_size">
                            <option value="">Not specified</option>
                            <option value="startup">Startup (1-10)</option>
                            <option value="small">Small (11-50)</option>
                            <option value="medium">Medium (51-200)</option>
                            <option value="large">Large (201-1000)</option>
                            <option value="enterprise">Enterprise (1000+)</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="companyDescription">Company Description</label>
                    <textarea id="companyDescription" name="company_description" rows="3"
                              placeholder="Brief description of your company, culture, and mission..."></textarea>
                </div>
                
                <div class="form-grid">
                    <div class="form-group">
                        <label for="hrContact">HR Contact Email *</label>
                        <input type="email" id="hrContact" name="hr_contact" required
                               placeholder="hr@company.com">
                    </div>
                    
                    <div class="form-group">
                        <label for="website">Company Website</label>
                        <input type="url" id="website" name="website"
                               placeholder="https://www.company.com">
                    </div>
                </div>
            </div>
            
            <!-- Screening Questions -->
            <div class="form-section">
                <h3>❓ Screening Questions (Optional)</h3>
                <div class="form-group">
                    <label>Pre-screening Questions</label>
                    <div id="screeningQuestions">
                        <div class="question-item">
                            <input type="text" name="screening_questions[]" 
                                   placeholder="e.g., Do you have experience with SQL databases?">
                            <button type="button" onclick="removeQuestion(this)">❌</button>
                        </div>
                    </div>
                    <button type="button" class="btn btn-secondary" onclick="addQuestion()">➕ Add Question</button>
                </div>
            </div>
        </div>
        
        <div class="form-actions">
            <button type="button" class="btn btn-secondary" onclick="saveDraft()">💾 Save as Draft</button>
            <button type="button" class="btn btn-secondary" onclick="previewJob()">👁️ Preview</button>
            <button type="submit" class="btn btn-primary">🚀 Publish Job</button>
        </div>
    </form>
    
    <style>
        .form-sections {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        
        .form-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .form-section h3 {
            color: #333;
            margin-bottom: 16px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .form-group label {
            font-weight: 600;
            color: #555;
            font-size: 14px;
        }
        
        .form-group input,
        .form-group select,
        .form-group textarea {
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.2s ease;
        }
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .form-group small {
            color: #666;
            font-size: 12px;
            font-style: italic;
        }
        
        .checkbox-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: normal !important;
            cursor: pointer;
        }
        
        .checkbox-label input[type="checkbox"] {
            width: auto;
            margin: 0;
        }
        
        .weight-controls {
            display: flex;
            flex-direction: column;
            gap: 12px;
            background: white;
            padding: 16px;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }
        
        .weight-item {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .weight-item label {
            flex: 1;
            font-weight: 500;
            margin-bottom: 0;
        }
        
        .weight-item input[type="range"] {
            flex: 2;
            margin: 0;
        }
        
        .weight-item span {
            flex: 0 0 50px;
            font-weight: 600;
            color: #667eea;
            text-align: right;
        }
        
        .question-item {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            align-items: center;
        }
        
        .question-item input {
            flex: 1;
        }
        
        .question-item button {
            background: #dc3545;
            color: white;
            border: none;
            padding: 8px;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .form-actions {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            padding-top: 24px;
            border-top: 1px solid #e9ecef;
            margin-top: 24px;
        }
        
        @media (max-width: 768px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            .form-actions {
                flex-direction: column;
            }
            
            .weight-item {
                flex-direction: column;
                align-items: stretch;
                gap: 4px;
            }
        }
    </style>
    
    <script>
        function updateWeight(slider, valueId) {
            document.getElementById(valueId).textContent = slider.value + '%';
        }
        
        function addQuestion() {
            const questionsDiv = document.getElementById('screeningQuestions');
            const questionItem = document.createElement('div');
            questionItem.className = 'question-item';
            questionItem.innerHTML = `
                <input type="text" name="screening_questions[]" 
                       placeholder="Enter your screening question...">
                <button type="button" onclick="removeQuestion(this)">❌</button>
            `;
            questionsDiv.appendChild(questionItem);
        }
        
        function removeQuestion(button) {
            button.parentElement.remove();
        }
        
        function saveDraft() {
            alert('Draft saved! (Feature coming soon)');
        }
        
        function previewJob() {
            alert('Job preview coming soon!');
        }
        
        function submitJob(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            
            // Validate required fields
            const requiredFields = ['title', 'description', 'requirements', 'company', 'hr_contact'];
            const missingFields = [];
            
            requiredFields.forEach(field => {
                if (!formData.get(field)) {
                    missingFields.push(field);
                }
            });
            
            if (missingFields.length > 0) {
                alert(`Please fill in all required fields: ${missingFields.join(', ')}`);
                return;
            }
            
            // Submit the form
            fetch('/hr/jobs', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    alert('Job posted successfully!');
                    closeModal('createJobModal');
                    window.location.reload();
                } else {
                    alert('Error posting job. Please try again.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error posting job. Please try again.');
            });
        }
    </script>
    """)

@router.post('/hr/jobs', response_class=HTMLResponse)
async def create_job(
    title: str = Form(...),
    description: str = Form(...),
    requirements: str = Form(...),
    company: str = Form(...),
    hr_contact: str = Form(...),
    department: str = Form(''),
    employment_type: str = Form('full-time'),
    work_location: str = Form('remote'),
    location: str = Form(''),
    experience_level: str = Form('mid'),
    salary_min: int = Form(None),
    salary_max: int = Form(None),
    currency: str = Form('USD'),
    salary_period: str = Form('monthly'),
    benefits: str = Form(''),
    required_skills: str = Form(''),
    preferred_skills: str = Form(''),
    technologies: str = Form(''),
    education_level: str = Form(''),
    language_requirements: str = Form(''),
    urgency: str = Form('medium'),
    positions_available: int = Form(1),
    application_deadline: str = Form(''),
    start_date: str = Form(''),
    require_cover_letter: str = Form(''),
    require_portfolio: str = Form(''),
    require_references: str = Form(''),
    require_availability: str = Form(''),
    skills_weight: int = Form(40),
    experience_weight: int = Form(30),
    education_weight: int = Form(15),
    culture_weight: int = Form(15),
    evaluation_criteria: str = Form(''),
    company_size: str = Form(''),
    company_description: str = Form(''),
    website: str = Form('')
):
    """Create comprehensive job posting with all settings"""
    try:
        # Build salary range string
        salary_range = ""
        if salary_min or salary_max:
            if salary_min and salary_max:
                salary_range = f"{currency} {salary_min:,} - {salary_max:,} ({salary_period})"
            elif salary_min:
                salary_range = f"{currency} {salary_min:,}+ ({salary_period})"
            elif salary_max:
                salary_range = f"Up to {currency} {salary_max:,} ({salary_period})"
        
        # Build application requirements
        app_requirements = []
        if require_cover_letter:
            app_requirements.append("Cover Letter")
        if require_portfolio:
            app_requirements.append("Portfolio/Work Samples")
        if require_references:
            app_requirements.append("References")
        if require_availability:
            app_requirements.append("Availability Information")
        
        # Build evaluation weights
        evaluation_weights = {
            'skills': skills_weight,
            'experience': experience_weight,
            'education': education_weight,
            'culture': culture_weight
        }
        
        job = job_manager.create_job(
            title=title,
            description=description,
            requirements=requirements,
            company=company,
            hr_contact=hr_contact,
            department=department,
            employment_type=employment_type,
            work_location=work_location,
            location=location,
            experience_level=experience_level,
            salary_range=salary_range,
            benefits=benefits,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            technologies=technologies,
            education_level=education_level,
            language_requirements=language_requirements,
            urgency=urgency,
            positions_available=positions_available,
            application_deadline=application_deadline,
            start_date=start_date,
            application_requirements=app_requirements,
            evaluation_weights=evaluation_weights,
            evaluation_criteria=evaluation_criteria,
            company_size=company_size,
            company_description=company_description,
            website=website
        )
        
        return RedirectResponse(url='/', status_code=302)
        
    except Exception as e:
        return HTMLResponse(f"""
        <h1>Error Creating Job</h1>
        <p>Error: {str(e)}</p>
        <a href="/">← Back to HR Portal</a>
        """, status_code=500)

@router.get('/hr/jobs/{job_id}/candidates', response_class=HTMLResponse)
async def view_candidates(job_id: str):
    """View all candidates for a specific job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    applications = job_manager.get_job_applications(job_id)
    stats = job_manager.get_application_stats(job_id)
    
    # Build candidates table
    candidates_html = ""
    for app in applications:
        eval_data = app.get('evaluation', {})
        candidate_id = app.get('candidate_id', 'Unknown')
        score = eval_data.get('overall_score', 0)
        recommendation = eval_data.get('recommendation', 'unknown')
        submitted_date = app.get('submitted_at', '')[:10]
        
        # Color code recommendation
        rec_colors = {'hire': '#28a745', 'interview': '#ffc107', 'reject': '#dc3545'}
        rec_color = rec_colors.get(recommendation.lower(), '#6c757d')
        
        # Extract evaluation details for transparency
        skills_found = eval_data.get('skills_found', [])
        experience_match = eval_data.get('experience_match', 0)
        education_match = eval_data.get('education_match', 0)
        culture_fit = eval_data.get('culture_fit', 0)
        key_strengths = eval_data.get('key_strengths', [])
        improvement_areas = eval_data.get('improvement_areas', [])
        ai_reasoning = eval_data.get('reasoning', '')
        
        candidates_html += f"""
        <tr onclick="viewCandidateDetails('{app.get('application_id')}')" style="cursor: pointer;">
            <td>
                <div class="candidate-id">{candidate_id}</div>
                <div class="candidate-anonymous">Anonymous Candidate</div>
                <div class="candidate-meta">Applied: {submitted_date}</div>
            </td>
            <td>
                <div class="score-breakdown">
                    <div class="overall-score" style="background: {rec_color}; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold;">
                        {int(score * 100)}% Overall
                    </div>
                    <div class="sub-scores" style="margin-top: 8px; font-size: 12px;">
                        <div>Skills: {int(experience_match * 100)}%</div>
                        <div>Education: {int(education_match * 100)}%</div>
                        <div>Culture: {int(culture_fit * 100)}%</div>
                    </div>
                </div>
            </td>
            <td>
                <span class="recommendation-badge" style="background: {rec_color}; color: white; padding: 6px 12px; border-radius: 20px; font-size: 14px; font-weight: 600;">
                    {recommendation.title()}
                </span>
                <div class="skills-preview" style="margin-top: 8px; font-size: 12px; color: #666;">
                    Skills: {', '.join(skills_found[:3])}{'...' if len(skills_found) > 3 else ''}
                </div>
            </td>
            <td>
                <div class="ai-evaluation" style="font-size: 12px;">
                    <div class="strengths" style="color: #28a745; margin-bottom: 4px;">
                        <strong>Strengths:</strong> {key_strengths[0] if key_strengths else 'N/A'}
                    </div>
                    <div class="areas" style="color: #ffc107;">
                        <strong>Growth Areas:</strong> {improvement_areas[0] if improvement_areas else 'N/A'}
                    </div>
                </div>
            </td>
            <td>
                <div class="candidate-actions">
                    <button class="btn-small" onclick="event.stopPropagation(); viewUnbiasedProfile('{app.get('application_id')}')">� View Profile</button>
                    <button class="btn-small" onclick="event.stopPropagation(); viewAIEvaluation('{app.get('application_id')}')">🤖 AI Analysis</button>
                    <button class="btn-small" onclick="event.stopPropagation(); revealIdentity('{app.get('application_id')}')">� Reveal</button>
                </div>
            </td>
        </tr>
        """
    
    if not candidates_html:
        candidates_html = """
        <tr>
            <td colspan="5" style="text-align: center; padding: 40px; color: #666;">
                <div>📭 No applications yet</div>
                <div style="margin-top: 8px;">Share the application portal to start receiving applications</div>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Candidates - {job['title']}</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: system-ui; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .header {{ margin-bottom: 30px; }}
            .header h1 {{ color: #333; margin-bottom: 8px; }}
            .header p {{ color: #666; }}
            .back-link {{ color: #667eea; text-decoration: none; font-weight: 600; }}
            .back-link:hover {{ text-decoration: underline; }}
            
            .job-info {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .job-meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
            .meta-item {{ text-align: center; }}
            .meta-value {{ font-size: 18px; font-weight: 700; color: #667eea; }}
            .meta-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
            
            .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
            .stat {{ background: #f8f9fa; padding: 16px; border-radius: 6px; text-align: center; }}
            .stat-number {{ font-size: 24px; font-weight: 700; color: #667eea; }}
            .stat-label {{ color: #666; font-size: 14px; }}
            
            .controls {{ display: flex; justify-content: space-between; align-items: center; margin: 20px 0; }}
            .btn {{ padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; text-decoration: none; display: inline-block; }}
            .btn-primary {{ background: #667eea; color: white; }}
            .btn-secondary {{ background: #f8f9fa; color: #667eea; border: 1px solid #e9ecef; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 16px 12px; text-align: left; border-bottom: 1px solid #e9ecef; }}
            th {{ background: #f8f9fa; font-weight: 600; position: sticky; top: 0; }}
            tr:hover {{ background: #f8f9fa; }}
            
            .candidate-id {{ font-weight: 600; color: #667eea; font-family: monospace; }}
            .candidate-name {{ font-size: 12px; color: #666; margin-top: 4px; }}
            
            .score-circle {{ 
                width: 50px; height: 50px; border-radius: 50%; 
                display: flex; align-items: center; justify-content: center;
                color: white; font-weight: 700; font-size: 12px;
            }}
            
            .recommendation-badge {{ 
                padding: 4px 12px; border-radius: 20px; 
                font-size: 12px; font-weight: 600; text-transform: uppercase;
            }}
            
            .candidate-actions {{ display: flex; gap: 8px; }}
            .btn-small {{ 
                padding: 4px 8px; font-size: 11px; border: none; 
                border-radius: 4px; cursor: pointer; background: #e9ecef; color: #666;
            }}
            .btn-small:hover {{ background: #667eea; color: white; }}
            
            .portal-share {{ background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 30px 0; }}
            .portal-url {{ background: white; padding: 12px; border-radius: 6px; font-family: monospace; word-break: break-all; }}
            
            .filters {{ display: flex; gap: 12px; align-items: center; margin: 20px 0; }}
            .filter-select {{ padding: 8px 12px; border: 1px solid #e9ecef; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-link">← Back to HR Portal</a>
                <h1>📋 {job['title']}</h1>
                <p><strong>Job ID:</strong> {job_id} | <strong>Company:</strong> {job.get('company', 'Not specified')}</p>
            </div>
            
            <div class="job-info">
                <div class="job-meta">
                    <div class="meta-item">
                        <div class="meta-value">{job.get('employment_type', 'Full-time')}</div>
                        <div class="meta-label">Employment Type</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-value">{job.get('work_location', 'Remote')}</div>
                        <div class="meta-label">Work Location</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-value">{job.get('experience_level', 'Mid')}</div>
                        <div class="meta-label">Experience Level</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-value">{job.get('urgency', 'Medium').title()}</div>
                        <div class="meta-label">Urgency</div>
                    </div>
                </div>
            </div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{stats['total_applications']}</div>
                    <div class="stat-label">Total Applications</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{stats['hire_recommended']}</div>
                    <div class="stat-label">Recommended for Hire</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{stats['interview_recommended']}</div>
                    <div class="stat-label">Interview Recommended</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{int(stats['average_score'] * 100)}%</div>
                    <div class="stat-label">Average Score</div>
                </div>
            </div>
            
            <div class="controls">
                <div class="filters">
                    <select class="filter-select" onchange="filterCandidates(this.value)">
                        <option value="all">All Candidates</option>
                        <option value="hire">Recommended for Hire</option>
                        <option value="interview">Interview Recommended</option>
                        <option value="reject">Not Recommended</option>
                    </select>
                    
                    <select class="filter-select" onchange="sortCandidates(this.value)">
                        <option value="score-desc">Highest Score First</option>
                        <option value="score-asc">Lowest Score First</option>
                        <option value="date-desc">Newest First</option>
                        <option value="date-asc">Oldest First</option>
                    </select>
                </div>
                
                <div>
                    <button class="btn btn-secondary" onclick="exportCandidates()">📊 Export Data</button>
                    <button class="btn btn-secondary" onclick="bulkContact()">📧 Bulk Contact</button>
                </div>
            </div>
            
            <table id="candidatesTable">
                <thead>
                    <tr>
                        <th>Anonymous Candidate</th>
                        <th>AI Assessment</th>
                        <th>Recommendation</th>
                        <th>Transparent Evaluation</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {candidates_html}
                </tbody>
            </table>
            
            <div class="portal-share">
                <h4>🔗 Share Application Portal</h4>
                <p><strong>Public Application URL:</strong></p>
                <div class="portal-url">http://localhost:8000/apply/{job_id}</div>
                <p style="margin-top: 12px;">Share this link with candidates or post it on job boards for direct applications.</p>
                <button class="btn btn-primary" onclick="copyPortalUrl()">📋 Copy URL</button>
            </div>
        </div>
        
        <script>
            function viewCandidateDetails(applicationId) {{
                // TODO: Implement candidate details modal
                alert(`View candidate details: ${{applicationId}}`);
            }}
            
            function viewResume(applicationId) {{
                // TODO: Implement resume viewer
                alert(`View resume: ${{applicationId}}`);
            }}
            
            function contactCandidate(applicationId) {{
                // TODO: Implement contact form
                alert(`Contact candidate: ${{applicationId}}`);
            }}
            
            function filterCandidates(filter) {{
                // TODO: Implement candidate filtering
                console.log('Filter candidates:', filter);
            }}
            
            function sortCandidates(sort) {{
                // TODO: Implement candidate sorting
                console.log('Sort candidates:', sort);
            }}
            
            function exportCandidates() {{
                // TODO: Implement data export
                alert('Export candidates data coming soon!');
            }}
            
            function bulkContact() {{
                // TODO: Implement bulk contact
                alert('Bulk contact feature coming soon!');
            }}
            
            function copyPortalUrl() {{
                const url = 'http://localhost:8000/apply/{job_id}';
                navigator.clipboard.writeText(url).then(() => {{
                    alert('Application portal URL copied to clipboard!');
                }});
            }}
            
            function viewUnbiasedProfile(applicationId) {{
                // Show candidate profile without revealing name or bias-inducing information
                fetch(`/api/candidate/${{applicationId}}/unbiased`)
                    .then(response => response.json())
                    .then(data => {{
                        const modal = document.createElement('div');
                        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center;';
                        modal.innerHTML = `
                            <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
                                <h3>Anonymous Candidate Profile</h3>
                                <div style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                                    <h4>Professional Summary</h4>
                                    <p>${{data.summary || 'Not provided'}}</p>
                                </div>
                                <div style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                                    <h4>Skills Identified</h4>
                                    <p>${{data.skills?.join(', ') || 'None identified'}}</p>
                                </div>
                                <div style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                                    <h4>Application Date</h4>
                                    <p>${{data.applied_date}}</p>
                                </div>
                                <button onclick="this.parentElement.parentElement.remove()" style="background: #667eea; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">Close</button>
                            </div>
                        `;
                        document.body.appendChild(modal);
                    }})
                    .catch(error => alert('Error loading candidate profile'));
            }}
            
            function viewAIEvaluation(applicationId) {{
                // Show detailed AI evaluation reasoning
                fetch(`/api/candidate/${{applicationId}}/evaluation`)
                    .then(response => response.json())
                    .then(data => {{
                        const modal = document.createElement('div');
                        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center;';
                        modal.innerHTML = `
                            <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 700px; max-height: 80vh; overflow-y: auto;">
                                <h3>🤖 AI Evaluation Analysis</h3>
                                <div style="margin: 1rem 0; padding: 1rem; background: #e8f5e8; border-radius: 8px; border-left: 4px solid #28a745;">
                                    <h4>Overall Score: ${{Math.round(data.overall_score * 100)}}%</h4>
                                    <p><strong>Recommendation:</strong> ${{data.recommendation.toUpperCase()}}</p>
                                </div>
                                <div style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                                    <h4>Scoring Breakdown</h4>
                                    <p><strong>Skills Match:</strong> ${{Math.round(data.experience_match * 100)}}%</p>
                                    <p><strong>Education Match:</strong> ${{Math.round(data.education_match * 100)}}%</p>
                                    <p><strong>Culture Fit:</strong> ${{Math.round(data.culture_fit * 100)}}%</p>
                                </div>
                                <div style="margin: 1rem 0; padding: 1rem; background: #f0f8ff; border-radius: 8px;">
                                    <h4>AI Reasoning</h4>
                                    <p style="line-height: 1.6;">${{data.reasoning || 'No detailed reasoning provided'}}</p>
                                </div>
                                <div style="margin: 1rem 0; padding: 1rem; background: #f0f8ff; border-radius: 8px;">
                                    <h4>Key Strengths</h4>
                                    <ul>${{data.key_strengths?.map(s => `<li>${{s}}</li>`).join('') || '<li>None identified</li>'}}</ul>
                                </div>
                                <div style="margin: 1rem 0; padding: 1rem; background: #fff8dc; border-radius: 8px;">
                                    <h4>Growth Areas</h4>
                                    <ul>${{data.improvement_areas?.map(s => `<li>${{s}}</li>`).join('') || '<li>None identified</li>'}}</ul>
                                </div>
                                <button onclick="this.parentElement.parentElement.remove()" style="background: #667eea; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">Close</button>
                            </div>
                        `;
                        document.body.appendChild(modal);
                    }})
                    .catch(error => alert('Error loading AI evaluation'));
            }}
            
            function viewExplainableAI(applicationId) {{
                // Show explainable AI analysis with SHAP-like values
                fetch(`/api/candidate/${{applicationId}}/explainable-analysis`)
                    .then(response => response.json())
                    .then(data => {{
                        const modal = document.createElement('div');
                        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center; overflow-y: auto;';
                        
                        // Create feature importance chart
                        const featureChart = Object.entries(data.feature_importance || {{}})
                            .map(([feature, importance]) => {{
                                const percentage = Math.round(importance * 100);
                                const barWidth = percentage;
                                return `
                                    <div style="margin: 0.5rem 0;">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                                            <span style="font-weight: 500; text-transform: capitalize;">${{feature.replace('_', ' ')}}</span>
                                            <span style="font-weight: bold; color: #0066cc;">${{percentage}}%</span>
                                        </div>
                                        <div style="background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden;">
                                            <div style="background: linear-gradient(90deg, #28a745, #ffc107, #dc3545); width: ${{barWidth}}%; height: 100%; transition: width 0.3s ease;"></div>
                                        </div>
                                    </div>
                                `;
                            }}).join('');
                        
                        modal.innerHTML = `
                            <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 900px; max-height: 90vh; overflow-y: auto; width: 90%;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                                    <h3 style="margin: 0; color: #2c3e50;">📊 Explainable AI Analysis</h3>
                                    <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6c757d;">&times;</button>
                                </div>
                                
                                <!-- Overall Score -->
                                <div style="margin: 1rem 0; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; text-align: center;">
                                    <h2 style="margin: 0; font-size: 2.5rem;">${{Math.round(data.overall_score * 100)}}%</h2>
                                    <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">Overall Suitability Score</p>
                                    <p style="margin: 0.25rem 0 0 0; opacity: 0.9;">Confidence: ${{Math.round(data.confidence_level * 100)}}%</p>
                                </div>
                                
                                <!-- SHAP-like Feature Importance -->
                                <div style="margin: 1.5rem 0; padding: 1.5rem; background: #f8f9fa; border-radius: 12px;">
                                    <h4 style="margin: 0 0 1rem 0; color: #2c3e50;">🎯 Feature Impact Analysis (SHAP-like)</h4>
                                    <p style="margin: 0 0 1rem 0; color: #666; font-size: 0.9rem;">Shows how much each factor contributes to the final decision</p>
                                    ${{featureChart}}
                                </div>
                                
                                <!-- Component Breakdown -->
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1.5rem 0;">
                                    <div style="padding: 1rem; background: #e8f5e8; border-radius: 8px; border-left: 4px solid #28a745;">
                                        <h5 style="margin: 0 0 0.5rem 0; color: #155724;">Skills Analysis</h5>
                                        <p style="margin: 0; font-size: 0.9rem;">Score: ${{Math.round((data.component_analysis?.skills?.score || 0) * 100)}}%</p>
                                        <p style="margin: 0; font-size: 0.9rem;">Weight: ${{Math.round((data.component_analysis?.skills?.weight || 0) * 100)}}%</p>
                                        <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #666;">Found: ${{(data.component_analysis?.skills?.relevant_skills || []).join(', ') || 'None identified'}}</p>
                                    </div>
                                    
                                    <div style="padding: 1rem; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                                        <h5 style="margin: 0 0 0.5rem 0; color: #856404;">Experience Analysis</h5>
                                        <p style="margin: 0; font-size: 0.9rem;">Score: ${{Math.round((data.component_analysis?.experience?.score || 0) * 100)}}%</p>
                                        <p style="margin: 0; font-size: 0.9rem;">Weight: ${{Math.round((data.component_analysis?.experience?.weight || 0) * 100)}}%</p>
                                        <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #666;">Years: ${{data.component_analysis?.experience?.years || 'Unknown'}}</p>
                                    </div>
                                    
                                    <div style="padding: 1rem; background: #d4edda; border-radius: 8px; border-left: 4px solid #155724;">
                                        <h5 style="margin: 0 0 0.5rem 0; color: #155724;">Education Analysis</h5>
                                        <p style="margin: 0; font-size: 0.9rem;">Score: ${{Math.round((data.component_analysis?.education?.score || 0) * 100)}}%</p>
                                        <p style="margin: 0; font-size: 0.9rem;">Weight: ${{Math.round((data.component_analysis?.education?.weight || 0) * 100)}}%</p>
                                        <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #666;">Level: ${{data.component_analysis?.education?.level || 'Unknown'}}</p>
                                    </div>
                                    
                                    <div style="padding: 1rem; background: #f0f8ff; border-radius: 8px; border-left: 4px solid #0066cc;">
                                        <h5 style="margin: 0 0 0.5rem 0; color: #003d82;">Culture Fit Analysis</h5>
                                        <p style="margin: 0; font-size: 0.9rem;">Score: ${{Math.round((data.component_analysis?.culture_fit?.score || 0) * 100)}}%</p>
                                        <p style="margin: 0; font-size: 0.9rem;">Weight: ${{Math.round((data.component_analysis?.culture_fit?.weight || 0) * 100)}}%</p>
                                        <p style="margin: 0.5rem 0 0 0; font-size: 0.8rem; color: #666;">${{data.component_analysis?.culture_fit?.communication_style || 'Not assessed'}}</p>
                                    </div>
                                </div>
                                
                                <!-- Decision Explanation -->
                                <div style="margin: 1.5rem 0; padding: 1.5rem; background: #ffffff; border: 1px solid #dee2e6; border-radius: 12px;">
                                    <h4 style="margin: 0 0 1rem 0; color: #2c3e50;">🔍 Decision Explanation</h4>
                                    
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                        <div>
                                            <h6 style="margin: 0 0 0.5rem 0; color: #28a745;">✅ Primary Strengths</h6>
                                            <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                                                ${{(data.primary_strengths || []).map(s => `<li>${{s}}</li>`).join('') || '<li>None identified</li>'}}
                                            </ul>
                                        </div>
                                        
                                        <div>
                                            <h6 style="margin: 0 0 0.5rem 0; color: #dc3545;">⚠️ Main Concerns</h6>
                                            <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                                                ${{(data.main_concerns || []).map(c => `<li>${{c}}</li>`).join('') || '<li>None identified</li>'}}
                                            </ul>
                                        </div>
                                    </div>
                                    
                                    <div style="margin: 1rem 0 0 0;">
                                        <h6 style="margin: 0 0 0.5rem 0; color: #6f42c1;">🎯 Key Decision Drivers</h6>
                                        <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                                            ${{(data.decision_drivers || []).map(d => `<li>${{d}}</li>`).join('') || '<li>General assessment</li>'}}
                                        </ul>
                                    </div>
                                </div>
                                
                                <!-- HR Recommendations -->
                                <div style="margin: 1.5rem 0; padding: 1.5rem; background: #e3f2fd; border-radius: 12px;">
                                    <h4 style="margin: 0 0 1rem 0; color: #1976d2;">💡 HR Action Items</h4>
                                    <ul style="margin: 0; padding-left: 1.5rem;">
                                        ${{(data.hr_recommendations || ['Review application manually']).map(r => `<li style="margin: 0.25rem 0;">${{r}}</li>`).join('')}}
                                    </ul>
                                </div>
                                
                                <!-- Detailed Reasoning -->
                                <div style="margin: 1.5rem 0; padding: 1.5rem; background: #f8f9fa; border-radius: 8px;">
                                    <h4 style="margin: 0 0 1rem 0; color: #495057;">🤖 AI Detailed Reasoning</h4>
                                    <p style="margin: 0; line-height: 1.6; font-size: 0.95rem;">${{data.reasoning || 'No detailed reasoning available'}}</p>
                                </div>
                                
                                <div style="text-align: center; margin-top: 2rem;">
                                    <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: #6c757d; color: white; border: none; padding: 0.75rem 2rem; border-radius: 6px; cursor: pointer; font-size: 1rem;">Close Analysis</button>
                                </div>
                            </div>
                        `;
                        document.body.appendChild(modal);
                    }})
                    .catch(error => {{
                        console.error('Error:', error);
                        alert('Error loading explainable AI analysis');
                    }});
            }}
            
            function revealIdentity(applicationId) {{
                // Only reveal identity after evaluation is complete
                if (confirm('⚠️ BIAS WARNING: Revealing candidate identity may introduce unconscious bias. Are you sure you want to proceed?')) {{
                    fetch(`/api/candidate/${{applicationId}}/identity`)
                        .then(response => response.json())
                        .then(data => {{
                            const modal = document.createElement('div');
                            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; display: flex; align-items: center; justify-content: center;';
                            modal.innerHTML = `
                                <div style="background: white; padding: 2rem; border-radius: 12px; max-width: 500px;">
                                    <h3>Candidate Identity</h3>
                                    <div style="margin: 1rem 0; padding: 1rem; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                                        <p><strong>⚠️ Bias Notice:</strong> This information is revealed only for contact purposes after evaluation.</p>
                                    </div>
                                    <div style="margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                                        <p><strong>Name:</strong> ${{data.name}}</p>
                                        <p><strong>Email:</strong> ${{data.email}}</p>
                                        <p><strong>Phone:</strong> ${{data.phone || 'Not provided'}}</p>
                                    </div>
                                    <div style="display: flex; gap: 1rem;">
                                        <button onclick="window.open('mailto:' + '${{data.email}}' + '?subject=Regarding your application')" style="background: #28a745; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">📧 Contact</button>
                                        <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: #6c757d; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer;">Close</button>
                                    </div>
                                </div>
                            `;
                            document.body.appendChild(modal);
                        }})
                        .catch(error => alert('Error loading candidate identity'));
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(html)


@router.get('/apply', response_class=HTMLResponse)
async def applicant_portal():
    """Public applicant portal for job applications"""
    template_path = Path(__file__).parent.parent / "templates" / "apply.html"
    return HTMLResponse(template_path.read_text(encoding='utf-8'))


@router.get('/api/jobs')
async def get_public_jobs():
    """API endpoint to get all active jobs for applicants"""
    jobs = job_manager.list_jobs()
    # Filter only active jobs and remove sensitive information
    public_jobs = []
    for job in jobs:
        if job.get('status', 'active') == 'active':
            public_job = {
                'job_id': job['job_id'],
                'title': job['title'],
                'company': job['company'],
                'description': job['description'],
                'requirements': job['requirements'],
                'employment_type': job.get('employment_type', 'full-time'),
                'work_location': job.get('work_location', 'remote'),
                'location': job.get('location', ''),
                'experience_level': job.get('experience_level', 'mid'),
                'salary_range': job.get('salary_range', ''),
                'benefits': job.get('benefits', ''),
                'required_skills': job.get('required_skills', ''),
                'preferred_skills': job.get('preferred_skills', ''),
                'technologies': job.get('technologies', ''),
                'education_level': job.get('education_level', ''),
                'language_requirements': job.get('language_requirements', ''),
                'application_deadline': job.get('application_deadline', ''),
                'start_date': job.get('start_date', ''),
                'company_size': job.get('company_size', ''),
                'company_description': job.get('company_description', ''),
                'website': job.get('website', ''),
                'created_at': job.get('created_at', '')
            }
            public_jobs.append(public_job)
    
    return {'jobs': public_jobs}


@router.post('/api/apply')
async def submit_application(
    job_id: str = Form(...),
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    candidate_phone: str = Form(""),
    candidate_summary: str = Form(""),
    resume: UploadFile = File(...)
):
    """Submit job application with resume evaluation"""
    try:
        # Validate job exists
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Save uploaded resume
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        resume_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{resume.filename}"
        resume_path = upload_dir / resume_filename
        
        with open(resume_path, "wb") as f:
            content = await resume.read()
            f.write(content)
        
        # Extract actual text content from the uploaded resume file
        from app.services.pdf_extractor import extract_resume_text
        
        try:
            # Extract real text from the uploaded PDF/DOC file
            resume_text = extract_resume_text(str(resume_path))
            
            if not resume_text or len(resume_text.strip()) < 50:
                # Fallback if extraction fails or text is too short
                resume_text = f"Resume file: {resume.filename}\n[Error: Could not extract readable text from the uploaded file. Please ensure the file is a readable PDF or DOC file.]"
                print(f"Warning: Failed to extract text from {resume.filename}")
            else:
                # Successfully extracted text - add metadata
                resume_text = f"Resume file: {resume.filename}\n\nExtracted content:\n{resume_text}"
                print(f"Successfully extracted {len(resume_text)} characters from {resume.filename}")
                
        except Exception as e:
            # Error handling for extraction failures
            print(f"Error extracting text from {resume.filename}: {e}")
            resume_text = f"Resume file: {resume.filename}\n[Error: Text extraction failed - {str(e)}]"
        
        # Evaluate candidate using AI
        evaluation = evaluate_candidate_simple(
            resume_text=resume_text,
            job_title=job['title'],
            job_description=job['description']
        )
        
        # Submit application
        result = job_manager.submit_application(
            job_id=job_id,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
            candidate_summary=candidate_summary,
            resume_filename=resume_filename,
            resume_text=resume_text,
            evaluation=evaluation
        )
        
        return {
            'success': True,
            'message': 'Application submitted successfully!',
            'application_id': result['application_id'],
            'candidate_id': result['candidate_id']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting application: {str(e)}")


@router.get('/api/candidate/{application_id}/unbiased')
async def get_candidate_unbiased_profile(application_id: str):
    """Get candidate profile without bias-inducing information"""
    try:
        # Find application across all jobs
        for job in job_manager.list_jobs():
            applications = job_manager.get_job_applications(job['job_id'])
            for app in applications:
                if app.get('application_id') == application_id:
                    return {
                        'summary': app.get('candidate_summary', 'Not provided'),
                        'skills': app.get('evaluation', {}).get('skills_found', []),
                        'applied_date': app.get('submitted_at', '')[:10] if app.get('submitted_at') else 'Unknown',
                        'candidate_id': app.get('candidate_id', 'Unknown')
                    }
        
        raise HTTPException(status_code=404, detail="Application not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading candidate profile: {str(e)}")


@router.get('/api/candidate/{application_id}/evaluation')
async def get_candidate_evaluation(application_id: str):
    """Get detailed AI evaluation for transparency"""
    try:
        # Find application across all jobs
        for job in job_manager.list_jobs():
            applications = job_manager.get_job_applications(job['job_id'])
            for app in applications:
                if app.get('application_id') == application_id:
                    evaluation = app.get('evaluation', {})
                    return {
                        'overall_score': evaluation.get('overall_score', 0),
                        'recommendation': evaluation.get('recommendation', 'unknown'),
                        'experience_match': evaluation.get('experience_match', 0),
                        'education_match': evaluation.get('education_match', 0),
                        'culture_fit': evaluation.get('culture_fit', 0),
                        'reasoning': evaluation.get('reasoning', 'No detailed reasoning provided'),
                        'key_strengths': evaluation.get('key_strengths', []),
                        'improvement_areas': evaluation.get('improvement_areas', []),
                        'skills_found': evaluation.get('skills_found', [])
                    }
        
        raise HTTPException(status_code=404, detail="Application not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading evaluation: {str(e)}")


@router.get('/api/candidate/{application_id}/explainable-analysis')
async def get_candidate_explainable_analysis(application_id: str):
    """Get explainable AI analysis with SHAP-like feature importance"""
    try:
        # Find application across all jobs
        for job in job_manager.list_jobs():
            applications = job_manager.get_job_applications(job['job_id'])
            for app in applications:
                if app.get('application_id') == application_id:
                    evaluation = app.get('evaluation', {})
                    
                    # Extract explainable AI components
                    explainable_data = evaluation.get('explainable_analysis', {})
                    feature_importance = evaluation.get('feature_importance', {})
                    decision_explanation = evaluation.get('decision_explanation', {})
                    hr_insights = evaluation.get('hr_insights', [])
                    
                    return {
                        'application_id': application_id,
                        'overall_score': evaluation.get('overall_score', 0),
                        'confidence_level': evaluation.get('confidence_level', 0.5),
                        
                        # SHAP-like feature importance (what affects the decision most)
                        'feature_importance': feature_importance,
                        
                        # Detailed breakdown by component
                        'component_analysis': {
                            'skills': {
                                'score': explainable_data.get('skills_breakdown', {}).get('skill_score', 0),
                                'weight': explainable_data.get('skills_breakdown', {}).get('contribution_weight', 0),
                                'relevant_skills': explainable_data.get('skills_breakdown', {}).get('relevant_skills', []),
                                'missing_skills': explainable_data.get('skills_breakdown', {}).get('missing_skills', [])
                            },
                            'experience': {
                                'score': explainable_data.get('experience_breakdown', {}).get('relevance_score', 0),
                                'weight': explainable_data.get('experience_breakdown', {}).get('contribution_weight', 0),
                                'description': explainable_data.get('experience_breakdown', {}).get('description', ''),
                                'years': explainable_data.get('experience_breakdown', {}).get('years', 0)
                            },
                            'education': {
                                'score': explainable_data.get('education_breakdown', {}).get('relevance_score', 0),
                                'weight': explainable_data.get('education_breakdown', {}).get('contribution_weight', 0),
                                'level': explainable_data.get('education_breakdown', {}).get('level', 'unknown')
                            },
                            'culture_fit': {
                                'score': explainable_data.get('culture_breakdown', {}).get('culture_score', 0),
                                'weight': explainable_data.get('culture_breakdown', {}).get('contribution_weight', 0),
                                'communication_style': explainable_data.get('culture_breakdown', {}).get('communication_style', ''),
                                'work_indicators': explainable_data.get('culture_breakdown', {}).get('work_indicators', [])
                            }
                        },
                        
                        # Decision explanation
                        'decision_drivers': decision_explanation.get('decision_drivers', []),
                        'risk_factors': decision_explanation.get('risk_factors', []),
                        'primary_strengths': decision_explanation.get('primary_strengths', []),
                        'main_concerns': decision_explanation.get('main_concerns', []),
                        
                        # HR actionable insights
                        'hr_recommendations': hr_insights,
                        'reasoning': evaluation.get('reasoning', 'No detailed reasoning available')
                    }
        
        raise HTTPException(status_code=404, detail="Application not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading explainable analysis: {str(e)}")


@router.get('/api/candidate/{application_id}/identity')
async def get_candidate_identity(application_id: str):
    """Reveal candidate identity with bias warning (use only for contact)"""
    try:
        # Find application across all jobs
        for job in job_manager.list_jobs():
            applications = job_manager.get_job_applications(job['job_id'])
            for app in applications:
                if app.get('application_id') == application_id:
                    return {
                        'name': app.get('candidate_name', 'Unknown'),
                        'email': app.get('candidate_email', 'Unknown'),
                        'phone': app.get('candidate_phone', 'Not provided'),
                        'warning': 'This information is revealed only for contact purposes after evaluation'
                    }
        
        raise HTTPException(status_code=404, detail="Application not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading candidate identity: {str(e)}")
