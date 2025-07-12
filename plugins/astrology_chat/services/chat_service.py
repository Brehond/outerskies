import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from django.conf import settings
from django.utils import timezone
from ai_integration.openrouter_api import generate_interpretation, get_available_models
from .knowledge_service import KnowledgeService
from ..models import ChatSession, ChatMessage, ChatAnalytics
import json
from decimal import Decimal

logger = logging.getLogger(__name__)


class ChatService:
    """
    Service for handling chat interactions with AI
    """

    def __init__(self):
        self.knowledge_service = KnowledgeService()
        self.available_models = get_available_models()

    def get_response(
        self,
        session: ChatSession,
        user_message: str,
        user=None,
        model_name: str = 'gpt-4',
        temperature: float = 0.7,
        max_tokens: int = 1000,
        include_knowledge: bool = True
    ) -> Dict[str, Any]:
        """
        Get AI response (backward compatibility method)

        Args:
            session: The chat session
            user_message: The user's message
            user: User object (for backward compatibility)
            model_name: AI model to use
            temperature: Response creativity (0.0-1.0)
            max_tokens: Maximum response length
            include_knowledge: Whether to include knowledge base context

        Returns:
            Dictionary with response data
        """
        response_text = self.generate_response(
            session=session,
            user_message=user_message,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            include_knowledge=include_knowledge
        )

        return {
            'content': response_text,
            'tokens_used': 0,  # Will be updated by generate_response
            'response_time': 0  # Will be updated by generate_response
        }

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
            # Search knowledge base for relevant content
            relevant_docs = self.knowledge_service.search(user_message, limit=3)

            if not relevant_docs:
                return ""

            context_parts = []
            for doc in relevant_docs:
                context_parts.append(f"From '{doc.title}': {doc.content[:300]}...")

            return "\n\n".join(context_parts)

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
            Formatted conversation history string
        """
        try:
            recent_messages = session.messages.order_by('-created_at')[:limit]
            if not recent_messages:
                return ""

            history_parts = []
            for msg in reversed(recent_messages):  # Show in chronological order
                role = "AI" if msg.is_ai else "User"
                history_parts.append(f"{role}: {msg.content}")

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
        # Approximate costs per 1K tokens (these are rough estimates)
        cost_per_1k = {
            'gpt-4': 0.03,
            'gpt-3.5-turbo': 0.002,
            'claude-3-opus': 0.015,
            'claude-3-sonnet': 0.003,
            'claude-3-haiku': 0.00025,
        }

        base_cost = cost_per_1k.get(model_name, 0.01)  # Default cost
        return (tokens / 1000) * base_cost

    def _update_analytics(self, session: ChatSession, tokens: int, cost: float, response_time: float):
        """
        Update session analytics with usage data

        Args:
            session: Chat session
            tokens: Tokens used
            cost: Cost incurred
            response_time: Response time in seconds
        """
        try:
            # Update session totals
            session.total_tokens_used += tokens
            session.total_cost += Decimal(str(cost))
            session.message_count += 1
            session.save(update_fields=['total_tokens_used', 'total_cost', 'message_count'])

            # Update daily analytics
            today = timezone.now().date()
            analytics, created = ChatAnalytics.objects.get_or_create(
                user=session.user,
                date=today,
                defaults={
                    'sessions_created': 0,
                    'messages_sent': 0,
                    'ai_responses_received': 1,
                    'total_tokens_used': tokens,
                    'total_cost': Decimal(str(cost)),
                    'knowledge_searches': 0,
                    'knowledge_documents_accessed': 0,
                    'avg_response_time': response_time,
                }
            )

            if not created:
                analytics.ai_responses_received += 1
                analytics.total_tokens_used += tokens
                analytics.total_cost += Decimal(str(cost))
                analytics.avg_response_time = (
                    (analytics.avg_response_time * (analytics.ai_responses_received - 1) + response_time)
                    / analytics.ai_responses_received
                )
                analytics.save()

        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")

    def _get_fallback_response(self) -> str:
        """
        Get a fallback response when AI generation fails

        Returns:
            Fallback response text
        """
        return """I apologize, but I'm having trouble generating a response right now.
        This could be due to a temporary issue with the AI service or network connectivity.
        Please try again in a moment, or feel free to rephrase your question."""

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
            user_messages = [msg.content for msg in messages if not msg.is_ai]
            ai_messages = [msg.content for msg in messages if msg.is_ai]

            # Extract topics from user messages
            topics = self._extract_topics(user_messages)

            return {
                'session_id': str(session.id),
                'title': session.title,
                'message_count': session.message_count,
                'total_tokens': session.total_tokens_used,
                'total_cost': float(session.total_cost),
                'topics_discussed': topics,
                'user_message_count': len(user_messages),
                'ai_response_count': len(ai_messages),
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting session summary: {str(e)}")
            return {}

    def _extract_topics(self, messages: List[str]) -> List[str]:
        """
        Extract main topics from user messages

        Args:
            messages: List of user messages

        Returns:
            List of identified topics
        """
        # Simple topic extraction based on keywords
        astrology_keywords = [
            'sun sign', 'moon sign', 'rising sign', 'ascendant', 'planets',
            'houses', 'aspects', 'natal chart', 'birth chart', 'zodiac',
            'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
            'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'
        ]

        topics = set()
        for message in messages:
            message_lower = message.lower()
            for keyword in astrology_keywords:
                if keyword in message_lower:
                    topics.add(keyword)

        return list(topics)[:5]  # Return top 5 topics
