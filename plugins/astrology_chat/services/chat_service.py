import time
import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from ai_integration.openrouter_api import generate_interpretation, get_available_models
from .knowledge_service import KnowledgeService
from ..models import ChatSession, ChatMessage, ChatAnalytics
import json

logger = logging.getLogger(__name__)

class ChatService:
    """
    Service for handling chat interactions with AI
    """
    
    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.available_models = get_available_models()
    
    def generate_response(
        self, 
        session: ChatSession, 
        user_message: str,
        model_name: str = 'gpt-4',
        temperature: float = 0.7,
        max_tokens: int = 1000,
        include_knowledge: bool = True
    ) -> str:
        """
        Generate an AI response to a user message
        
        Args:
            session: The chat session
            user_message: The user's message
            model_name: AI model to use
            temperature: Response creativity (0.0-1.0)
            max_tokens: Maximum response length
            include_knowledge: Whether to include knowledge base context
            
        Returns:
            Generated AI response
        """
        start_time = time.time()
        
        try:
            # Build the prompt with context
            prompt = self._build_prompt(session, user_message, include_knowledge)
            
            # Generate AI response
            response = generate_interpretation(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=60
            )
            
            # Calculate response time and tokens
            response_time = time.time() - start_time
            
            # Estimate token usage (rough approximation)
            estimated_tokens = len(response.split()) * 1.3  # Rough estimate
            
            # Calculate cost (approximate based on model)
            cost = self._calculate_cost(model_name, estimated_tokens)
            
            # Update session analytics
            self._update_analytics(session, estimated_tokens, cost, response_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return self._get_fallback_response()
    
    def _build_prompt(
        self, 
        session: ChatSession, 
        user_message: str, 
        include_knowledge: bool = True
    ) -> str:
        """
        Build a comprehensive prompt for the AI
        
        Args:
            session: Chat session with context
            user_message: User's message
            include_knowledge: Whether to include knowledge base context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # System context
        system_context = """You are an expert astrologer and AI assistant specializing in natal chart analysis. 
        You provide insightful, accurate, and helpful responses about astrology, planetary positions, aspects, 
        and their meanings in natal charts. Always be respectful, professional, and supportive in your responses.
        
        When analyzing charts or answering questions:
        1. Consider the planetary positions and aspects mentioned
        2. Provide both traditional and modern astrological perspectives
        3. Be specific and detailed in your explanations
        4. Use clear, accessible language
        5. Offer practical insights and interpretations
        6. Always maintain a positive and constructive tone"""
        
        prompt_parts.append(system_context)
        
        # Add natal chart context if available
        if session.chart_data:
            chart_context = self._format_chart_context(session.chart_data)
            prompt_parts.append(f"\nNATAL CHART CONTEXT:\n{chart_context}")
        
        # Add session context notes if available
        if session.context_notes:
            prompt_parts.append(f"\nSESSION CONTEXT:\n{session.context_notes}")
        
        # Add knowledge base context if requested
        if include_knowledge:
            knowledge_context = self._get_knowledge_context(user_message)
            if knowledge_context:
                prompt_parts.append(f"\nRELEVANT ASTROLOGICAL KNOWLEDGE:\n{knowledge_context}")
        
        # Add conversation history
        conversation_history = self._get_conversation_history(session)
        if conversation_history:
            prompt_parts.append(f"\nCONVERSATION HISTORY:\n{conversation_history}")
        
        # Add user message
        prompt_parts.append(f"\nUSER QUESTION:\n{user_message}")
        
        # Add response instructions
        response_instructions = """
        Please provide a comprehensive, helpful response to the user's question. 
        If referencing specific astrological concepts, explain them clearly. 
        If the question relates to their natal chart, incorporate the chart data provided.
        Keep your response informative, supportive, and well-structured."""
        
        prompt_parts.append(response_instructions)
        
        return "\n".join(prompt_parts)
    
    def _format_chart_context(self, chart_data: Dict) -> str:
        """
        Format natal chart data for the prompt
        
        Args:
            chart_data: Chart data dictionary
            
        Returns:
            Formatted chart context string
        """
        try:
            context_parts = []
            
            # Add basic chart info
            if 'birth_date' in chart_data and 'birth_time' in chart_data:
                context_parts.append(f"Birth Date: {chart_data['birth_date']} at {chart_data['birth_time']}")
            
            if 'location' in chart_data:
                context_parts.append(f"Birth Location: {chart_data['location']}")
            
            # Add planetary positions
            if 'positions' in chart_data:
                context_parts.append("\nPlanetary Positions:")
                for planet, data in chart_data['positions'].items():
                    if isinstance(data, dict) and 'sign' in data:
                        degree = data.get('degree_in_sign', '')
                        context_parts.append(f"  {planet}: {data['sign']} {degree}°")
            
            # Add aspects
            if 'aspects' in chart_data:
                context_parts.append("\nKey Aspects:")
                for planet, aspects in chart_data['aspects'].items():
                    for aspect in aspects[:3]:  # Limit to first 3 aspects per planet
                        context_parts.append(f"  {planet} {aspect['type']} {aspect['planet']} (orb: {aspect['orb']}°)")
            
            # Add house information
            if 'houses' in chart_data:
                context_parts.append("\nHouse Cusps:")
                for i, house_data in enumerate(chart_data['houses'][:12], 1):
                    if isinstance(house_data, dict) and 'sign' in house_data:
                        context_parts.append(f"  House {i}: {house_data['sign']}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error formatting chart context: {str(e)}")
            return "Chart data available but formatting error occurred."
    
    def _get_knowledge_context(self, user_message: str) -> str:
        """
        Get relevant knowledge base context for the user message
        
        Args:
            user_message: User's message to search for relevant knowledge
            
        Returns:
            Relevant knowledge context string
        """
        try:
            # Search knowledge base for relevant information
            search_results = self.knowledge_service.search(user_message, limit=3)
            
            if not search_results:
                return ""
            
            context_parts = []
            for result in search_results:
                context_parts.append(f"Source: {result['title']}")
                context_parts.append(f"Content: {result['content'][:300]}...")
                context_parts.append("")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting knowledge context: {str(e)}")
            return ""
    
    def _get_conversation_history(self, session: ChatSession, limit: int = 5) -> str:
        """
        Get recent conversation history for context
        
        Args:
            session: Chat session
            limit: Number of recent messages to include
            
        Returns:
            Formatted conversation history
        """
        try:
            recent_messages = session.messages.order_by('-created_at')[:limit]
            if not recent_messages:
                return ""
            
            history_parts = []
            for message in reversed(recent_messages):  # Show in chronological order
                role = "AI" if message.is_ai else "User"
                history_parts.append(f"{role}: {message.content}")
            
            return "\n".join(history_parts)
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return ""
    
    def _calculate_cost(self, model_name: str, tokens: int) -> float:
        """
        Calculate approximate cost for AI response
        
        Args:
            model_name: AI model used
            tokens: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Approximate costs per 1K tokens (these would need to be updated based on actual pricing)
        cost_per_1k_tokens = {
            'gpt-4': 0.03,
            'gpt-3.5-turbo': 0.002,
            'claude-3-opus': 0.015,
            'claude-3-sonnet': 0.003,
            'mistral-medium': 0.002,
            'mistral-7b': 0.001,
        }
        
        base_cost = cost_per_1k_tokens.get(model_name, 0.01)
        return (tokens / 1000) * base_cost
    
    def _update_analytics(self, session: ChatSession, tokens: int, cost: float, response_time: float):
        """
        Update chat analytics for the session
        
        Args:
            session: Chat session
            tokens: Tokens used
            cost: Cost incurred
            response_time: Response time in seconds
        """
        try:
            # Update session totals
            session.total_tokens_used += int(tokens)
            session.total_cost += cost
            session.save(update_fields=['total_tokens_used', 'total_cost'])
            
            # Update daily analytics
            today = timezone.now().date()
            analytics, created = ChatAnalytics.objects.get_or_create(
                user=session.user,
                date=today,
                defaults={
                    'ai_responses_received': 0,
                    'total_tokens_used': 0,
                    'total_cost': 0,
                    'avg_response_time': 0,
                }
            )
            
            # Update analytics
            analytics.ai_responses_received += 1
            analytics.total_tokens_used += int(tokens)
            analytics.total_cost += cost
            
            # Update average response time
            if analytics.ai_responses_received > 1:
                current_avg = analytics.avg_response_time
                new_avg = ((current_avg * (analytics.ai_responses_received - 1)) + response_time) / analytics.ai_responses_received
                analytics.avg_response_time = new_avg
            else:
                analytics.avg_response_time = response_time
            
            analytics.save()
            
        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")
    
    def _get_fallback_response(self) -> str:
        """
        Get a fallback response when AI generation fails
        
        Returns:
            Fallback response message
        """
        return """I apologize, but I'm experiencing technical difficulties at the moment. 
        Please try again in a few moments, or feel free to rephrase your question. 
        If the issue persists, please contact support."""
    
    def get_session_summary(self, session: ChatSession) -> Dict:
        """
        Get a summary of the chat session
        
        Args:
            session: Chat session
            
        Returns:
            Session summary dictionary
        """
        try:
            messages = session.messages.all()
            user_messages = messages.filter(is_ai=False).count()
            ai_messages = messages.filter(is_ai=True).count()
            
            # Get most common topics from user messages
            topics = self._extract_topics([msg.content for msg in messages.filter(is_ai=False)])
            
            return {
                'total_messages': messages.count(),
                'user_messages': user_messages,
                'ai_messages': ai_messages,
                'total_tokens': session.total_tokens_used,
                'total_cost': float(session.total_cost),
                'topics': topics,
                'duration': (session.last_activity - session.created_at).total_seconds() / 3600,  # hours
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            return {}
    
    def _extract_topics(self, messages: List[str]) -> List[str]:
        """
        Extract common topics from messages
        
        Args:
            messages: List of message contents
            
        Returns:
            List of common topics
        """
        # Simple keyword-based topic extraction
        astrology_keywords = {
            'planets': ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto'],
            'signs': ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'],
            'houses': ['house', 'houses', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th'],
            'aspects': ['conjunction', 'opposition', 'trine', 'square', 'sextile', 'aspect'],
            'concepts': ['natal chart', 'birth chart', 'astrology', 'zodiac', 'horoscope', 'transit', 'synastry']
        }
        
        topics = set()
        all_text = ' '.join(messages).lower()
        
        for category, keywords in astrology_keywords.items():
            for keyword in keywords:
                if keyword in all_text:
                    topics.add(category)
                    break
        
        return list(topics) 