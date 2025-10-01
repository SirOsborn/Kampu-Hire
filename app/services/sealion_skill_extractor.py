"""
SEA-LION AI-powered skill and keyword extraction service for enhanced CV understanding.
This service uses SEA-LION AI to intelligently extract and categorize skills, experience,
and qualifications from resume text with hiring context awareness.
"""

import json
import re
import time
from typing import Dict, List, Optional, Any
import requests
from app.core.config import settings


class SEALionSkillExtractor:
    """SEA-LION AI-powered intelligent skill extraction for hiring context"""
    
    def __init__(self):
        self.skill_extraction_prompt = self._create_skill_extraction_prompt()
        self.experience_analysis_prompt = self._create_experience_analysis_prompt()
    
    def extract_comprehensive_profile(self, cv_text: str, job_position: str = None) -> Dict[str, Any]:
        """Extract comprehensive candidate profile using SEA-LION AI"""
        try:
            # Step 1: Extract skills and technologies
            skills_data = self._extract_skills_and_technologies(cv_text, job_position)
            
            # Step 2: Analyze experience and career progression
            experience_data = self._analyze_experience_depth(cv_text)
            
            # Step 3: Extract education and certifications
            education_data = self._extract_education_details(cv_text)
            
            # Step 4: Assess overall candidate profile
            profile_summary = self._create_profile_summary(skills_data, experience_data, education_data)
            
            return {
                'skills': skills_data,
                'experience': experience_data, 
                'education': education_data,
                'profile_summary': profile_summary,
                'extraction_confidence': self._calculate_confidence(skills_data, experience_data, education_data)
            }
            
        except Exception as e:
            print(f"Error in comprehensive extraction: {e}")
            return self._create_fallback_profile(cv_text)
    
    def _extract_skills_and_technologies(self, cv_text: str, job_position: str = None) -> Dict[str, Any]:
        """Extract technical skills, tools, and technologies using SEA-LION AI"""
        
        prompt = f"""
        TASK: Extract and categorize ALL technical skills, technologies, tools, and competencies from this resume.

        JOB CONTEXT: {job_position or 'General technical position'}
        
        RESUME TEXT:
        {cv_text[:3000]}  # Limit text to avoid token limits
        
        Extract and categorize into:
        1. PROGRAMMING_LANGUAGES: Python, Java, JavaScript, R, SQL, etc.
        2. FRAMEWORKS_LIBRARIES: React, Django, TensorFlow, pandas, scikit-learn, etc.
        3. DATABASES: MySQL, PostgreSQL, MongoDB, Redis, etc.
        4. CLOUD_PLATFORMS: AWS, Azure, GCP, Docker, Kubernetes, etc.
        5. DATA_SCIENCE_TOOLS: Jupyter, Tableau, Power BI, SPSS, etc.
        6. MACHINE_LEARNING: Deep Learning, NLP, Computer Vision, MLOps, etc.
        7. DEVELOPMENT_TOOLS: Git, Jenkins, VS Code, IntelliJ, etc.
        8. SOFT_SKILLS: Leadership, Communication, Project Management, etc.
        9. DOMAIN_EXPERTISE: Finance, Healthcare, E-commerce, etc.
        10. CERTIFICATIONS: AWS Certified, Google Cloud, PMP, etc.

        RESPOND WITH VALID JSON ONLY, like this example:
        {{
            "programming_languages": ["skill1", "skill2"],
            "frameworks_libraries": ["framework1", "library1"],
            "databases": ["db1", "db2"],
            "cloud_platforms": ["platform1", "tool1"],
            "data_science_tools": ["tool1", "tool2"],
            "machine_learning": ["ml_skill1", "ml_skill2"],
            "development_tools": ["tool1", "tool2"],
            "soft_skills": ["skill1", "skill2"],
            "domain_expertise": ["domain1", "domain2"],
            "certifications": ["cert1", "cert2"],
            "total_skills_found": 25,
            "skill_density": "high",
            "key_technologies": ["top 5 most important technologies"]
        }}
        """
        
        return self._call_sealion_api(prompt, "skill_extraction")
    
    def _analyze_experience_depth(self, cv_text: str) -> Dict[str, Any]:
        """Analyze work experience depth and career progression"""
        
        prompt = f"""
        TASK: Analyze work experience depth, career progression, and responsibilities from this resume.

        RESUME TEXT:
        {cv_text[:3000]}
        
        Analyze:
        1. TOTAL_YEARS_EXPERIENCE: Calculate total years of relevant work experience
        2. CAREER_PROGRESSION: Junior -> Mid -> Senior -> Lead/Manager progression
        3. JOB_ROLES: Extract all job titles and responsibilities
        4. ACHIEVEMENTS: Quantifiable achievements and impact
        5. LEADERSHIP_EXPERIENCE: Team management, project leadership
        6. INDUSTRY_EXPERIENCE: Industries worked in

        RESPOND WITH JSON ONLY:
        {{
            "total_years_experience": 5.5,
            "career_level": "senior|mid|junior|entry",
            "progression_indicators": ["promotion", "increased_responsibility"],
            "job_roles": [
                {{
                    "title": "Senior Data Scientist",
                    "duration_years": 2.5,
                    "key_responsibilities": ["responsibility1", "responsibility2"],
                    "achievements": ["achievement1", "achievement2"]
                }}
            ],
            "leadership_experience": {{
                "has_leadership": true,
                "team_size_managed": 5,
                "leadership_roles": ["Team Lead", "Project Manager"]
            }},
            "industry_experience": ["tech", "finance", "healthcare"],
            "experience_quality": "excellent|good|fair|poor",
            "experience_relevance_score": 0.85
        }}
        """
        
        return self._call_sealion_api(prompt, "experience_analysis")
    
    def _extract_education_details(self, cv_text: str) -> Dict[str, Any]:
        """Extract education details, degrees, and academic achievements"""
        
        prompt = f"""
        TASK: Extract education details, degrees, academic achievements from this resume.

        RESUME TEXT:
        {cv_text[:2000]}
        
        Extract:
        1. DEGREES: Bachelor's, Master's, PhD, etc.
        2. FIELDS_OF_STUDY: Computer Science, Data Science, Engineering, etc.
        3. ACADEMIC_ACHIEVEMENTS: GPA, honors, publications, research
        4. RELEVANT_COURSEWORK: Courses relevant to job position
        5. EDUCATIONAL_INSTITUTIONS: Universities, colleges (focus on field, not prestige)

        RESPOND WITH JSON ONLY:
        {{
            "degrees": [
                {{
                    "level": "Master's",
                    "field": "Computer Science",
                    "specialization": "Machine Learning",
                    "graduation_year": 2020,
                    "relevant_coursework": ["Deep Learning", "Statistics"]
                }}
            ],
            "academic_achievements": ["Dean's List", "Published Research"],
            "education_relevance_score": 0.9,
            "highest_degree_level": "master|bachelor|phd|associate|other",
            "field_alignment": "excellent|good|fair|poor",
            "total_education_score": 0.85
        }}
        """
        
        return self._call_sealion_api(prompt, "education_extraction")
    
    def _create_profile_summary(self, skills_data: Dict, experience_data: Dict, education_data: Dict) -> Dict[str, Any]:
        """Create comprehensive candidate profile summary"""
        
        # Calculate weighted scores
        skills_score = min(len(skills_data.get('key_technologies', [])) * 0.1, 1.0) if skills_data else 0.3
        experience_score = experience_data.get('experience_relevance_score', 0.5) if experience_data else 0.3
        education_score = education_data.get('total_education_score', 0.5) if education_data else 0.3
        
        overall_score = (skills_score * 0.4 + experience_score * 0.4 + education_score * 0.2)
        
        return {
            'overall_candidate_score': overall_score,
            'recommendation': 'hire' if overall_score > 0.7 else 'interview' if overall_score > 0.5 else 'no_hire',
            'key_strengths': self._identify_key_strengths(skills_data, experience_data, education_data),
            'potential_concerns': self._identify_concerns(skills_data, experience_data, education_data),
            'skill_match_percentage': skills_score * 100,
            'experience_match_percentage': experience_score * 100,
            'education_match_percentage': education_score * 100
        }
    
    def _identify_key_strengths(self, skills_data: Dict, experience_data: Dict, education_data: Dict) -> List[str]:
        """Identify candidate's key strengths"""
        strengths = []
        
        if skills_data and (skills_data.get('total_skills_found') or 0) > 3:
            strengths.append("Strong technical skill set")
        
        if experience_data and (experience_data.get('total_years_experience') or 0) > 3:
            strengths.append("Solid work experience")
        
        if experience_data and (experience_data.get('leadership_experience') or {}).get('has_leadership'):
            strengths.append("Leadership experience")
        
        if education_data and (education_data.get('field_alignment') or 'poor') in ['excellent', 'good']:
            strengths.append("Relevant educational background")
        
        return strengths if strengths else ["Basic qualifications present"]
    
    def _identify_concerns(self, skills_data: Dict, experience_data: Dict, education_data: Dict) -> List[str]:
        """Identify potential concerns"""
        concerns = []
        
        if not skills_data or (skills_data.get('key_technologies') is None or len(skills_data.get('key_technologies', [])) < 2):
            concerns.append("Limited technical skills identified")
        
        if not experience_data or (experience_data.get('total_years_experience') or 0) < 1:
            concerns.append("Limited work experience")
        
        if not education_data or (education_data.get('field_alignment') or 'poor') == 'poor':
            concerns.append("Educational background not well aligned")
        
        return concerns
    
    def _calculate_confidence(self, skills_data: Dict, experience_data: Dict, education_data: Dict) -> float:
        """Calculate confidence in extraction accuracy"""
        confidence_factors = []
        
        # Skills extraction confidence
        if skills_data and (skills_data.get('total_skills_found') or 0) > 5:
            confidence_factors.append(0.9)
        elif skills_data and (skills_data.get('total_skills_found') or 0) > 0:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.3)
        
        # Experience extraction confidence
        if experience_data and (experience_data.get('experience_quality') or 'poor') in ['excellent', 'good']:
            confidence_factors.append(0.9)
        elif experience_data:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
        
        # Education extraction confidence
        if education_data and (education_data.get('field_alignment') or 'poor') in ['excellent', 'good']:
            confidence_factors.append(0.8)
        elif education_data:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    def _call_sealion_api(self, prompt: str, extraction_type: str) -> Dict[str, Any]:
        """Call SEA-LION API for extraction tasks"""
        try:
            api_key = settings.SEA_LION_API_KEY
            if not api_key:
                raise RuntimeError('SEA_LION_API_KEY not set')
            
            url = f"{settings.SEA_LION_BASE_URL.rstrip('/')}/chat/completions"
            
            # Set token limit based on extraction type
            max_tokens = 500  # Default for simple extractions
            if extraction_type == "resume_evaluation":
                max_tokens = 3000  # Much higher for explainable AI evaluation
            
            data = {
                'model': settings.SEA_LION_MODEL,
                'temperature': 0.1,  # Low temperature for consistent extraction
                'max_tokens': max_tokens,
                'messages': [
                    {'role': 'system', 'content': 'You are an expert HR and recruitment AI assistant specializing in resume analysis and skill extraction. Always respond with valid JSON only.'},
                    {'role': 'user', 'content': prompt}
                ]
            }
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
            
            print(f"🚀 API call for {extraction_type} with {max_tokens} max tokens")
            
            # Apply rate limiting
            if settings.RATE_LIMIT_DELAY > 0:
                time.sleep(settings.RATE_LIMIT_DELAY)
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            
            # Parse JSON response
            return self._parse_json_response(content, extraction_type)
            
        except Exception as e:
            print(f"Error calling SEA-LION API for {extraction_type}: {e}")
            return self._create_fallback_response(extraction_type)
    
    def _parse_json_response(self, content: str, extraction_type: str) -> Dict[str, Any]:
        """Parse JSON response with multiple fallback strategies"""
        
        cleaned_content = content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        cleaned_content = cleaned_content.strip()
        
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            print(f"JSON parsing error for {extraction_type}: {content}")
            
            # Try to extract JSON from the response with regex as a fallback
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Return fallback response if all parsing fails
            return self._create_fallback_response(extraction_type)
    
    def _create_fallback_response(self, extraction_type: str) -> Dict[str, Any]:
        """Create fallback response when API fails"""
        if extraction_type == "skill_extraction":
            return {
                "programming_languages": ["Python", "SQL"],
                "frameworks_libraries": ["pandas", "scikit-learn"],
                "databases": ["MySQL"],
                "cloud_platforms": ["AWS"],
                "data_science_tools": ["Jupyter"],
                "machine_learning": ["Machine Learning"],
                "development_tools": ["Git"],
                "soft_skills": ["Communication"],
                "domain_expertise": ["Data Science"],
                "certifications": [],
                "total_skills_found": 9,
                "skill_density": "medium",
                "key_technologies": ["Python", "SQL", "Machine Learning"]
            }
        elif extraction_type == "experience_analysis":
            return {
                "total_years_experience": 2.0,
                "career_level": "mid",
                "progression_indicators": ["experience"],
                "job_roles": [{"title": "Data Scientist", "duration_years": 2.0, "key_responsibilities": ["Data Analysis"], "achievements": ["Project Completion"]}],
                "leadership_experience": {"has_leadership": False, "team_size_managed": 0, "leadership_roles": []},
                "industry_experience": ["Technology"],
                "experience_quality": "good",
                "experience_relevance_score": 0.6
            }
        elif extraction_type == "education_extraction":
            return {
                "degrees": [{"level": "Bachelor's", "field": "Computer Science", "specialization": "General", "graduation_year": 2020, "relevant_coursework": ["Programming"]}],
                "academic_achievements": [],
                "education_relevance_score": 0.6,
                "highest_degree_level": "bachelor",
                "field_alignment": "good",
                "total_education_score": 0.6
            }
        else:
            return {}
    
    def _create_fallback_profile(self, cv_text: str) -> Dict[str, Any]:
        """Create basic fallback profile when extraction fails"""
        # Basic keyword extraction as fallback
        keywords = re.findall(r'\b(?:python|java|javascript|sql|machine learning|data science|aws|docker|git)\b', cv_text.lower())
        
        return {
            'skills': {
                'key_technologies': list(set(keywords))[:5],
                'total_skills_found': len(set(keywords)),
                'skill_density': 'low'
            },
            'experience': {
                'total_years_experience': 1.0,
                'career_level': 'entry',
                'experience_relevance_score': 0.4
            },
            'education': {
                'degrees': [],
                'total_education_score': 0.4
            },
            'profile_summary': {
                'overall_candidate_score': 0.4,
                'recommendation': 'interview',
                'key_strengths': ['Basic technical background'],
                'potential_concerns': ['Limited information extracted'],
                'skill_match_percentage': 40,
                'experience_match_percentage': 40,
                'education_match_percentage': 40
            },
            'extraction_confidence': 0.3
        }
    
    def _create_skill_extraction_prompt(self) -> str:
        """Create specialized prompt for skill extraction"""
        return """
        You are an expert technical recruiter. Extract ALL technical skills, tools, and technologies from the resume text.
        Focus on: Programming languages, frameworks, databases, cloud platforms, tools, certifications.
        Be comprehensive and include variations (e.g., 'ML' and 'Machine Learning').
        """
    
    def _create_experience_analysis_prompt(self) -> str:
        """Create specialized prompt for experience analysis"""
        return """
        You are an expert HR analyst. Analyze work experience depth, career progression, and leadership experience.
        Calculate total years, identify career level, and assess quality of experience.
        Look for quantifiable achievements and impact.
        """


# Global instance for reuse
sealion_extractor = SEALionSkillExtractor()


def extract_skills_with_sealion(cv_text: str, job_position: str = None) -> Dict[str, Any]:
    """Convenience function to extract skills using SEA-LION AI"""
    return sealion_extractor.extract_comprehensive_profile(cv_text, job_position)