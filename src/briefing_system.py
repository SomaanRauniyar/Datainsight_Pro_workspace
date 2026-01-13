"""
Smart Briefing System for DataInsight Pro
Auto-generates executive summaries and meeting prep materials
"""
import json
from typing import Dict, List, Optional
from src.llm import ask_llm
from src.database import save_briefing, get_briefings, track_file_upload, log_token_usage

class BriefingSystem:
    """Generates intelligent briefings and summaries"""
    
    EXECUTIVE_SUMMARY_PROMPT = """
You are an executive briefing assistant. Analyze the following data/document content and generate a concise executive summary.

DATA CONTENT:
{content}

Generate exactly 3 bullet points that capture:
1. The most important finding or insight
2. A key trend or pattern
3. An actionable recommendation

IMPORTANT: Return ONLY valid JSON, no other text before or after. Format:
{{
    "bullets": [
        "First key insight with specific numbers if available",
        "Second key trend or pattern observed",
        "Third actionable recommendation"
    ],
    "headline": "One-line summary headline"
}}

Be specific, use numbers when available, and focus on business value.
"""

    MEETING_PREP_PROMPT = """
You are a meeting preparation assistant. Based on the following context and recent analysis, generate key talking points for an upcoming meeting.

CONTEXT:
{context}

RECENT INSIGHTS:
{insights}

Generate 4-5 talking points that would be valuable for a business meeting. Include:
- Key metrics to highlight
- Questions to address
- Potential discussion topics
- Action items to propose

IMPORTANT: Return ONLY valid JSON, no other text before or after. Format:
{{
    "talking_points": [
        {{"point": "First talking point here", "type": "metric"}},
        {{"point": "Second talking point here", "type": "question"}},
        {{"point": "Third talking point here", "type": "topic"}},
        {{"point": "Fourth talking point here", "type": "action"}}
    ],
    "meeting_focus": "Suggested meeting focus area"
}}

Types must be one of: metric, question, topic, action
"""

    @staticmethod
    def _extract_json(response: str) -> dict:
        """Extract JSON from LLM response, handling various formats"""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        # Try to find JSON object
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_str = response[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        return None

    @staticmethod
    def generate_executive_summary(content: str, user_id: int = None, file_id: int = None) -> Dict:
        """Generate 3-bullet executive summary from content"""
        try:
            # Get user's model preference (default to "auto" which uses llama-3.1-8b-instant)
            model = "auto"
            if user_id:
                try:
                    from src.user_keys import get_user_preference
                    saved_model = get_user_preference(str(user_id), "model", "auto")
                    # Only use saved model if it's valid
                    if saved_model and saved_model != "llama-3.1-70b-versatile":  # Skip deprecated
                        model = saved_model
                    print(f"[Briefing] User {user_id} model preference: {saved_model} → using: {model}")
                except Exception as e:
                    print(f"[Briefing] Error getting model preference: {e}")
            
            # Truncate content if too long
            max_content = 4000
            if len(content) > max_content:
                content = content[:max_content] + "...[truncated]"
            
            prompt = BriefingSystem.EXECUTIVE_SUMMARY_PROMPT.format(content=content)
            print(f"[Briefing] Calling LLM with model={model}")
            response = ask_llm(prompt, model=model, user_id=str(user_id) if user_id else None)
            print(f"[Briefing] Got response ({len(response)} chars)")
            
            # Track token usage (estimate)
            if user_id:
                estimated_tokens = len(prompt.split()) + len(response.split())
                log_token_usage(user_id, estimated_tokens, "executive_summary")
            
            # Parse JSON response
            result = BriefingSystem._extract_json(response)
            if not result:
                result = {"bullets": [response], "headline": "Summary"}
            
            # Ensure required fields exist
            if "bullets" not in result:
                result["bullets"] = [response]
            if "headline" not in result:
                result["headline"] = "Summary"
            
            # Save briefing if user_id provided
            if user_id:
                save_briefing(user_id, result, "executive_summary", file_id)
            
            return {
                "success": True,
                "summary": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": {"bullets": ["Unable to generate summary"], "headline": "Error"}
            }
    
    @staticmethod
    def generate_meeting_prep(context: str, insights: str, user_id: int = None) -> Dict:
        """Generate meeting preparation talking points"""
        try:
            # Get user's model preference
            model = "auto"
            if user_id:
                try:
                    from src.user_keys import get_user_preference
                    model = get_user_preference(str(user_id), "model", "auto")
                except:
                    pass
            
            prompt = BriefingSystem.MEETING_PREP_PROMPT.format(
                context=context[:2000] if len(context) > 2000 else context,
                insights=insights[:2000] if len(insights) > 2000 else insights
            )
            response = ask_llm(prompt, model=model, user_id=str(user_id) if user_id else None)
            
            if user_id:
                estimated_tokens = len(prompt.split()) + len(response.split())
                log_token_usage(user_id, estimated_tokens, "meeting_prep")
            
            # Parse JSON response
            result = BriefingSystem._extract_json(response)
            if not result:
                result = {"talking_points": [{"point": response, "type": "topic"}], "meeting_focus": "General"}
            
            # Ensure required fields exist
            if "talking_points" not in result:
                result["talking_points"] = [{"point": response, "type": "topic"}]
            if "meeting_focus" not in result:
                result["meeting_focus"] = "General Discussion"
            
            if user_id:
                save_briefing(user_id, result, "meeting_prep")
            
            return {
                "success": True,
                "prep": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_recent_briefings(user_id: int, briefing_type: str = None, limit: int = 5) -> List[Dict]:
        """Get recent briefings for a user"""
        briefings = get_briefings(user_id, briefing_type)
        results = []
        
        for b in briefings[:limit]:
            content = b.get('content')
            
            # Ensure content is properly parsed
            # The get_briefings function should have already parsed it,
            # but let's make sure
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except:
                    pass
            
            # Handle {"text": "json_string"} wrapper
            if isinstance(content, dict) and 'text' in content and len(content) == 1:
                text_val = content['text']
                if isinstance(text_val, str):
                    try:
                        content = json.loads(text_val)
                    except:
                        content = {"text": text_val}
            
            results.append({
                "id": b.get('id'),
                "briefing_type": b.get('briefing_type'),
                "content": content,
                "created_at": b.get('created_at')
            })
        
        return results
    
    @staticmethod
    def generate_data_summary_for_upload(data_preview: List[Dict], filename: str, user_id: int = None) -> Dict:
        """Generate quick summary when file is uploaded"""
        content = f"File: {filename}\n\nData Preview:\n"
        for i, row in enumerate(data_preview[:10]):
            content += f"Row {i+1}: {row}\n"
        
        return BriefingSystem.generate_executive_summary(content, user_id)

    @staticmethod
    def delete_briefing(briefing_id: int, user_id: str) -> bool:
        """Delete a briefing by ID (only if owned by user)"""
        from src.database import delete_briefing_by_id
        return delete_briefing_by_id(briefing_id, user_id)
