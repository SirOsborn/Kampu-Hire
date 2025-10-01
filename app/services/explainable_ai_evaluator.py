"""
Pure LLM Resume Evaluation Service with Explainable AI
Let SEA-LION AI handle evaluation with transparent SHAP-like explanations
"""

import json
import hashlib
import re
from typing import Dict, Any, List
from app.services.sealion_skill_extractor import SEALionSkillExtractor

class SimpleAIEvaluator:
    """Pure LLM-based evaluator with explainable AI features"""
    
    def __init__(self):
        self.extractor = SEALionSkillExtractor()
    
    def evaluate_resume(self, resume_text: str, job_title: str, job_description: str = None) -> Dict[str, Any]:
        """
        Pure LLM evaluation with explainable AI components
        Returns detailed breakdown of decision factors with weights
        """
        try:
            # Generate anonymous candidate ID
            candidate_id = f"CAND-{hashlib.md5(resume_text.encode()).hexdigest()[:8].upper()}"
            
            # Use SEA-LION AI for comprehensive evaluation with explanations
            if not job_description:
                job_description = f"We are looking for a qualified {job_title} candidate"
            
            # Enhanced prompt for explainable evaluation
            evaluation_prompt = f"""You are an expert HR recruiter with explainable AI capabilities. Evaluate this candidate for: {job_title}

JOB POSITION: {job_title}
JOB DESCRIPTION: {job_description}

CANDIDATE RESUME:
{resume_text[:3000]}

Provide a comprehensive evaluation with detailed explanations of each factor's contribution to the final decision.

Respond in this EXACT JSON format:
{{
    "overall_score": 0.75,
    "recommendation": "hire/interview/reject",
    "skills_analysis": {{
        "relevant_skills_found": ["skill1", "skill2"],
        "missing_critical_skills": ["skill3", "skill4"],
        "skill_match_score": 0.8,
        "skill_weight_contribution": 0.32
    }},
    "experience_analysis": {{
        "relevant_experience": "description of relevant experience",
        "years_of_experience": 3,
        "experience_relevance": 0.7,
        "experience_weight_contribution": 0.21
    }},
    "education_analysis": {{
        "education_level": "bachelor/master/phd/certificate",
        "field_relevance": 0.6,
        "education_weight_contribution": 0.12
    }},
    "cultural_fit_analysis": {{
        "communication_style": "assessment",
        "work_style_indicators": ["indicator1", "indicator2"],
        "culture_score": 0.8,
        "culture_weight_contribution": 0.16
    }},
    "explanation_breakdown": {{
        "primary_strengths": ["strength1", "strength2"],
        "main_concerns": ["concern1", "concern2"],
        "decision_drivers": ["driver1", "driver2"],
        "risk_factors": ["risk1", "risk2"]
    }},
    "shap_like_values": {{
        "skills_impact": 0.32,
        "experience_impact": 0.21,
        "education_impact": 0.12,
        "culture_impact": 0.16,
        "other_factors_impact": 0.19
    }},
    "confidence_level": 0.85,
    "reasoning": "Detailed step-by-step explanation of the evaluation",
    "recommendations_for_hr": ["actionable insight 1", "actionable insight 2"]
}}

Ensure all weight contributions sum to 1.0 and provide specific, actionable insights."""

            # Get LLM evaluation
            llm_response = self.extractor._call_sealion_api(evaluation_prompt, "resume_evaluation")
            print(f"🔍 LLM Response type: {type(llm_response)}")
            print(f"🔍 LLM Response keys: {llm_response.keys() if isinstance(llm_response, dict) else 'Not a dict'}")
            
            # Parse the LLM response with aggressive recovery
            evaluation_data = {}
            try:
                # Try to extract JSON from response
                if isinstance(llm_response, dict):
                    # If already parsed, use directly
                    print("🔍 Response is already a dict")
                    evaluation_data = llm_response
                elif isinstance(llm_response, dict) and 'response' in llm_response:
                    print("🔍 Response is dict with 'response' key")
                    response_text = llm_response['response']
                    evaluation_data = self._parse_json_safely(response_text)
                else:
                    print("🔍 Converting response to string and parsing")
                    response_text = str(llm_response)
                    evaluation_data = self._parse_json_safely(response_text)
                
                # If we got some data, process it (even if partial)
                if evaluation_data and len(evaluation_data) > 0:
                    print(f"✅ Successfully parsed evaluation data with {len(evaluation_data)} fields")
                    print(f"   Score: {evaluation_data.get('overall_score', 'missing')}")
                    print(f"   Recommendation: {evaluation_data.get('recommendation', 'missing')}")
                    result = self._process_explainable_evaluation(evaluation_data, candidate_id, job_title)
                    print(f"   Final result score: {result.get('overall_score', 'missing')}")
                    print(f"   Final result recommendation: {result.get('recommendation', 'missing')}")
                    return result
                else:
                    print(f"❌ No evaluation data recovered from LLM response")
                    return self._fallback_explainable_evaluation(candidate_id, job_title, resume_text)
                
            except Exception as e:
                print(f"Error processing LLM response: {e}")
                # Try one more time with the raw response if we have it
                if 'response_text' in locals():
                    print(f"Attempting emergency recovery from raw response...")
                    emergency_data = self._emergency_data_extraction(response_text)
                    if emergency_data:
                        print(f"Emergency recovery successful!")
                        result = self._process_explainable_evaluation(emergency_data, candidate_id, job_title)
                        return result
                
                return self._fallback_explainable_evaluation(candidate_id, job_title, resume_text)
                
        except Exception as e:
            print(f"Error in LLM evaluation: {e}")
            return self._fallback_explainable_evaluation(candidate_id, job_title, resume_text)
    
    def _parse_json_safely(self, response_text: str) -> Dict[str, Any]:
        """Safely parse JSON from LLM response with aggressive recovery"""
        try:
            # If already a dict, return as-is
            if isinstance(response_text, dict):
                return response_text
            
            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Try direct JSON parsing
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Response preview: {response_text[:500]}...")
            
            # Try aggressive recovery methods
            try:
                # Method 1: Find complete JSON blocks
                json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group()
                    return json.loads(json_text)
            except:
                pass
            
            try:
                # Method 2: Extract key information manually
                result = {}
                
                # Extract overall score
                score_match = re.search(r'"overall_score":\s*([\d.]+)', response_text)
                if score_match:
                    result['overall_score'] = float(score_match.group(1))
                    print(f"Recovered overall_score: {result['overall_score']}")
                
                # Extract recommendation
                rec_match = re.search(r'"recommendation":\s*"([^"]+)"', response_text)
                if rec_match:
                    result['recommendation'] = rec_match.group(1)
                    print(f"Recovered recommendation: {result['recommendation']}")
                
                # Extract relevant skills
                skills_pattern = r'"relevant_skills_found":\s*\[(.*?)\]'
                skills_match = re.search(skills_pattern, response_text, re.DOTALL)
                if skills_match:
                    skills_text = skills_match.group(1)
                    skills = re.findall(r'"([^"]+)"', skills_text)
                    result['skills_analysis'] = {
                        'relevant_skills_found': skills,
                        'skill_match_score': result.get('overall_score', 0.5)
                    }
                    print(f"Recovered skills: {skills}")
                
                # Extract experience data
                exp_rel_match = re.search(r'"experience_relevance":\s*([\d.]+)', response_text)
                years_match = re.search(r'"years_of_experience":\s*(\d+)', response_text)
                if exp_rel_match or years_match:
                    result['experience_analysis'] = {}
                    if exp_rel_match:
                        result['experience_analysis']['experience_relevance'] = float(exp_rel_match.group(1))
                    if years_match:
                        result['experience_analysis']['years_of_experience'] = int(years_match.group(1))
                
                # Extract education level
                edu_match = re.search(r'"education_level":\s*"([^"]+)"', response_text)
                if edu_match:
                    result['education_analysis'] = {'education_level': edu_match.group(1)}
                
                # Extract confidence level
                conf_match = re.search(r'"confidence_level":\s*([\d.]+)', response_text)
                if conf_match:
                    result['confidence_level'] = float(conf_match.group(1))
                
                if result:
                    print(f"Partial recovery successful: {len(result)} fields recovered")
                    return result
                    
            except Exception as recovery_error:
                print(f"Recovery attempt failed: {recovery_error}")
            
            # If all else fails, return empty dict to trigger fallback
            print("Complete parsing failure, triggering fallback evaluation")
            return {}
    
    def _emergency_data_extraction(self, response_text: str) -> Dict[str, Any]:
        """Last resort data extraction from LLM response"""
        result = {}
        try:
            import re
            
            # Extract overall score (most critical)
            score_patterns = [
                r'"overall_score":\s*([\d.]+)',
                r'"overall_score".*?:\s*([\d.]+)',
                r'overall.*?score.*?:\s*([\d.]+)',
                r'score.*?:\s*([\d.]+)'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    try:
                        score = float(match.group(1))
                        if 0 <= score <= 1:
                            result['overall_score'] = score
                            print(f"Emergency: Found score {score}")
                            break
                    except:
                        continue
            
            # Extract recommendation
            rec_patterns = [
                r'"recommendation":\s*"([^"]+)"',
                r'recommendation.*?:\s*"([^"]+)"',
                r'"(hire|interview|reject)"'
            ]
            
            for pattern in rec_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    rec = match.group(1).lower()
                    if rec in ['hire', 'interview', 'reject']:
                        result['recommendation'] = rec
                        print(f"Emergency: Found recommendation {rec}")
                        break
            
            # If we found at least a score, create minimal valid structure
            if 'overall_score' in result:
                result.setdefault('recommendation', 'interview' if result['overall_score'] > 0.5 else 'reject')
                result.setdefault('skills_analysis', {'relevant_skills_found': ['Emergency extraction'], 'skill_match_score': result['overall_score']})
                result.setdefault('confidence_level', 0.6)  # Lower confidence for emergency extraction
                print(f"Emergency extraction created minimal evaluation: {result['overall_score']:.2f} - {result['recommendation']}")
                return result
                
        except Exception as e:
            print(f"Emergency extraction failed: {e}")
        
        return {}
    
    def _process_explainable_evaluation(self, evaluation_data: Dict, candidate_id: str, job_title: str) -> Dict[str, Any]:
        """Process and validate explainable evaluation data"""
        
        print(f"🔄 Processing evaluation data: {len(evaluation_data)} fields")
        print(f"   Input data keys: {list(evaluation_data.keys())}")
        
        # Handle empty or invalid data
        if not evaluation_data:
            print("❌ No evaluation data received, using fallback")
            return self._fallback_explainable_evaluation(candidate_id, job_title, "")
        
        # Extract main scores with safe defaults
        overall_score = float(evaluation_data.get('overall_score', 0.3))
        recommendation = evaluation_data.get('recommendation', 'reject').lower()
        
        # Extract analysis components with safe defaults
        skills_analysis = evaluation_data.get('skills_analysis', {})
        experience_analysis = evaluation_data.get('experience_analysis', {})
        education_analysis = evaluation_data.get('education_analysis', {})
        cultural_analysis = evaluation_data.get('cultural_fit_analysis', {})
        explanation = evaluation_data.get('explanation_breakdown', {})
        shap_values = evaluation_data.get('shap_like_values', {})
        
        # Normalize SHAP values to ensure they sum to 1.0
        shap_values = self._normalize_shap_values(shap_values)
        
        # Create comprehensive result with explainable components
        result = {
            # Core evaluation
            'candidate_id': candidate_id,
            'overall_score': overall_score,
            'recommendation': recommendation,
            'confidence_level': float(evaluation_data.get('confidence_level', 0.7)),
            
            # Component scores for compatibility
            'skills_found': skills_analysis.get('relevant_skills_found', []),
            'experience_match': float(experience_analysis.get('experience_relevance', overall_score * 0.8)),
            'education_match': float(education_analysis.get('field_relevance', overall_score * 0.6)),
            'culture_fit': float(cultural_analysis.get('culture_score', 0.5)),
            
            # Explainable AI components
            'explainable_analysis': {
                'skills_breakdown': {
                    'relevant_skills': skills_analysis.get('relevant_skills_found', []),
                    'missing_skills': skills_analysis.get('missing_critical_skills', []),
                    'skill_score': float(skills_analysis.get('skill_match_score', overall_score)),
                    'contribution_weight': float(skills_analysis.get('skill_weight_contribution', 0.4))
                },
                'experience_breakdown': {
                    'description': experience_analysis.get('relevant_experience', 'Experience assessment pending'),
                    'years': experience_analysis.get('years_of_experience', 0),
                    'relevance_score': float(experience_analysis.get('experience_relevance', overall_score * 0.8)),
                    'contribution_weight': float(experience_analysis.get('experience_weight_contribution', 0.3))
                },
                'education_breakdown': {
                    'level': education_analysis.get('education_level', 'unknown'),
                    'relevance_score': float(education_analysis.get('field_relevance', overall_score * 0.6)),
                    'contribution_weight': float(education_analysis.get('education_weight_contribution', 0.15))
                },
                'culture_breakdown': {
                    'communication_style': cultural_analysis.get('communication_style', 'Assessment pending'),
                    'work_indicators': cultural_analysis.get('work_style_indicators', []),
                    'culture_score': float(cultural_analysis.get('culture_score', 0.5)),
                    'contribution_weight': float(cultural_analysis.get('culture_weight_contribution', 0.15))
                }
            },
            
            # SHAP-like feature importance
            'feature_importance': shap_values,
            
            # Decision explanation
            'decision_explanation': {
                'primary_strengths': explanation.get('primary_strengths', ['Assessment in progress']),
                'main_concerns': explanation.get('main_concerns', ['Pending detailed evaluation']),
                'decision_drivers': explanation.get('decision_drivers', [f'Overall assessment for {job_title}']),
                'risk_factors': explanation.get('risk_factors', ['Standard evaluation risks'])
            },
            
            # HR actionable insights
            'hr_insights': evaluation_data.get('recommendations_for_hr', ['Complete comprehensive interview', 'Verify qualifications']),
            'reasoning': evaluation_data.get('reasoning', f'AI evaluation for {job_title} position'),
            
            # Legacy format compatibility
            'key_strengths': explanation.get('primary_strengths', ['AI assessment in progress']),
            'improvement_areas': explanation.get('main_concerns', ['Areas for development to be identified'])
        }
        
        return result
    
    def _normalize_shap_values(self, shap_values: Dict[str, float]) -> Dict[str, float]:
        """Normalize SHAP-like values to sum to 1.0"""
        if not shap_values:
            return {
                'skills_impact': 0.4,
                'experience_impact': 0.3,
                'education_impact': 0.15,
                'culture_impact': 0.15
            }
        
        # Calculate total and normalize
        total = sum(float(v) for v in shap_values.values())
        if total == 0:
            return self._normalize_shap_values({})
        
        return {k: float(v) / total for k, v in shap_values.items()}
    
    def _parse_text_response_with_explanation(self, response_text: str, job_title: str) -> Dict[str, Any]:
        """Parse non-JSON LLM response with explanation components"""
        response_lower = response_text.lower()
        
        # Determine recommendation based on keywords
        if any(word in response_lower for word in ['hire', 'excellent', 'strong fit', 'recommend']):
            recommendation = 'hire'
            score = 0.75
        elif any(word in response_lower for word in ['interview', 'potential', 'consider', 'further discussion']):
            recommendation = 'interview' 
            score = 0.55
        else:
            recommendation = 'reject'
            score = 0.3
            
        return {
            'overall_score': score,
            'recommendation': recommendation,
            'skills_analysis': {
                'relevant_skills_found': ['Skills from text analysis'],
                'missing_critical_skills': ['To be determined'],
                'skill_match_score': score,
                'skill_weight_contribution': 0.4
            },
            'experience_analysis': {
                'relevant_experience': 'Parsed from text',
                'years_of_experience': 1,
                'experience_relevance': score * 0.8,
                'experience_weight_contribution': 0.3
            },
            'education_analysis': {
                'education_level': 'unknown',
                'field_relevance': score * 0.7,
                'education_weight_contribution': 0.15
            },
            'cultural_fit_analysis': {
                'communication_style': 'Assessed from resume',
                'work_style_indicators': ['Professional communication'],
                'culture_score': 0.5,
                'culture_weight_contribution': 0.15
            },
            'explanation_breakdown': {
                'primary_strengths': ['Identified from text analysis'],
                'main_concerns': ['Areas needing assessment'],
                'decision_drivers': [f'Overall assessment for {job_title}'],
                'risk_factors': ['To be evaluated in interview']
            },
            'shap_like_values': {
                'skills_impact': 0.4,
                'experience_impact': 0.3,
                'education_impact': 0.15,
                'culture_impact': 0.15
            },
            'confidence_level': 0.6,
            'reasoning': f'Text-based evaluation for {job_title}',
            'recommendations_for_hr': ['Conduct detailed interview', 'Verify skills through assessment']
        }
    
    def _fallback_explainable_evaluation(self, candidate_id: str, job_title: str, resume_text: str) -> Dict[str, Any]:
        """Fallback explainable evaluation when LLM fails"""
        
        # Basic analysis of resume text
        resume_lower = resume_text.lower()
        word_count = len(resume_text.split())
        
        # Simple scoring based on content
        base_score = 0.3
        if word_count > 100:
            base_score += 0.1
        if job_title.lower() in resume_lower:
            base_score += 0.2
        if any(word in resume_lower for word in ['experience', 'education', 'skills']):
            base_score += 0.1
        
        base_score = min(base_score, 1.0)
        
        return {
            'candidate_id': candidate_id,
            'overall_score': base_score,
            'recommendation': 'interview' if base_score > 0.5 else 'reject',
            'confidence_level': 0.4,
            'skills_found': ['Basic assessment pending'],
            'experience_match': base_score * 0.8,
            'education_match': base_score * 0.6,
            'culture_fit': 0.5,
            'explainable_analysis': {
                'skills_breakdown': {
                    'relevant_skills': ['Assessment needed'],
                    'missing_skills': ['LLM evaluation failed'],
                    'skill_score': base_score,
                    'contribution_weight': 0.4
                },
                'experience_breakdown': {
                    'description': 'Evaluation pending',
                    'years': 0,
                    'relevance_score': base_score * 0.8,
                    'contribution_weight': 0.3
                },
                'education_breakdown': {
                    'level': 'unknown',
                    'relevance_score': base_score * 0.6,
                    'contribution_weight': 0.15
                },
                'culture_breakdown': {
                    'communication_style': 'Not assessed',
                    'work_indicators': [],
                    'culture_score': 0.5,
                    'contribution_weight': 0.15
                }
            },
            'feature_importance': {
                'skills_impact': 0.4,
                'experience_impact': 0.3,
                'education_impact': 0.15,
                'culture_impact': 0.15
            },
            'decision_explanation': {
                'primary_strengths': ['Resume provided'],
                'main_concerns': ['LLM evaluation failed'],
                'decision_drivers': ['Manual review required'],
                'risk_factors': ['Unable to complete AI assessment']
            },
            'hr_insights': ['Manual evaluation required', 'Consider alternative assessment methods'],
            'reasoning': f'Fallback evaluation for {job_title} - LLM unavailable',
            'key_strengths': ['Resume submission'],
            'improvement_areas': ['Complete AI evaluation needed']
        }


def evaluate_candidate_simple(resume_text: str, job_title: str, job_description: str = None) -> Dict[str, Any]:
    """Convenience function for simple evaluation"""
    evaluator = SimpleAIEvaluator()
    return evaluator.evaluate_resume(resume_text, job_title, job_description)