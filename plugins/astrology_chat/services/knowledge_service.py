import os
import logging
import hashlib
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import PyPDF2
from docx import Document
import re
import json
from ..models import KnowledgeDocument, KnowledgeCategory

logger = logging.getLogger(__name__)

class KnowledgeService:
    """
    Service for managing the astrology knowledge base
    """
    
    def __init__(self):
        self.chunk_size = 1000  # Characters per chunk
        self.chunk_overlap = 200  # Overlap between chunks
        self.vector_db_path = os.path.join(settings.BASE_DIR, 'data', 'vector_db')
        
        # Ensure vector database directory exists
        os.makedirs(self.vector_db_path, exist_ok=True)
    
    def process_document(self, document: KnowledgeDocument) -> bool:
        """
        Process a knowledge document for search and retrieval
        
        Args:
            document: KnowledgeDocument instance
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            # Update processing status
            document.processing_status = 'processing'
            document.save(update_fields=['processing_status'])
            
            # Extract text content
            content = self._extract_text(document)
            if not content:
                raise Exception("No content extracted from document")
            
            # Store original content
            document.original_content = content
            document.content = content
            
            # Create text chunks for vector storage
            chunks = self._create_chunks(content)
            document.chunk_count = len(chunks)
            
            # Store chunks in vector database
            embedding_id = self._store_chunks(document, chunks)
            document.embedding_id = embedding_id
            
            # Mark as processed
            document.is_processed = True
            document.processing_status = 'completed'
            document.save()
            
            logger.info(f"Successfully processed document: {document.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {document.title}: {str(e)}")
            document.processing_status = 'failed'
            document.processing_error = str(e)
            document.save(update_fields=['processing_status', 'processing_error'])
            return False
    
    def _extract_text(self, document: KnowledgeDocument) -> str:
        """
        Extract text content from uploaded document
        
        Args:
            document: KnowledgeDocument instance
            
        Returns:
            Extracted text content
        """
        try:
            if document.file_type == 'pdf':
                return self._extract_pdf_text(document)
            elif document.file_type == 'docx':
                return self._extract_docx_text(document)
            elif document.file_type in ['txt', 'md', 'html']:
                return self._extract_text_file(document)
            else:
                raise Exception(f"Unsupported file type: {document.file_type}")
                
        except Exception as e:
            logger.error(f"Error extracting text from {document.title}: {str(e)}")
            raise
    
    def _extract_pdf_text(self, document: KnowledgeDocument) -> str:
        """
        Extract text from PDF file
        
        Args:
            document: KnowledgeDocument instance
            
        Returns:
            Extracted text
        """
        try:
            if document.file_path and os.path.exists(document.file_path):
                with open(document.file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text.strip():
                            text_parts.append(text)
                    
                    return '\n'.join(text_parts)
            else:
                raise Exception("PDF file not found")
                
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            raise
    
    def _extract_docx_text(self, document: KnowledgeDocument) -> str:
        """
        Extract text from Word document
        
        Args:
            document: KnowledgeDocument instance
            
        Returns:
            Extracted text
        """
        try:
            if document.file_path and os.path.exists(document.file_path):
                doc = Document(document.file_path)
                text_parts = []
                
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text)
                
                return '\n'.join(text_parts)
            else:
                raise Exception("Word document not found")
                
        except Exception as e:
            logger.error(f"Error extracting Word document text: {str(e)}")
            raise
    
    def _extract_text_file(self, document: KnowledgeDocument) -> str:
        """
        Extract text from text file
        
        Args:
            document: KnowledgeDocument instance
            
        Returns:
            Extracted text
        """
        try:
            if document.file_path and os.path.exists(document.file_path):
                with open(document.file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            else:
                raise Exception("Text file not found")
                
        except Exception as e:
            logger.error(f"Error extracting text file: {str(e)}")
            raise
    
    def _create_chunks(self, text: str) -> List[str]:
        """
        Create overlapping text chunks for vector storage
        
        Args:
            text: Full text content
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                sentence_endings = ['. ', '! ', '? ', '\n\n']
                for ending in sentence_endings:
                    pos = text.rfind(ending, start, end)
                    if pos != -1:
                        end = pos + len(ending)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _store_chunks(self, document: KnowledgeDocument, chunks: List[str]) -> str:
        """
        Store document chunks in vector database
        
        Args:
            document: KnowledgeDocument instance
            chunks: List of text chunks
            
        Returns:
            Embedding ID for the document
        """
        try:
            # Generate unique embedding ID
            embedding_id = f"doc_{document.id}_{hashlib.md5(document.title.encode()).hexdigest()[:8]}"
            
            # Store chunks in simple JSON format (in production, use proper vector DB)
            chunk_data = {
                'document_id': str(document.id),
                'title': document.title,
                'category': document.category.name if document.category else 'Uncategorized',
                'chunks': chunks,
                'metadata': {
                    'created_at': document.created_at.isoformat(),
                    'word_count': document.word_count,
                    'chunk_count': len(chunks),
                }
            }
            
            # Save to file (in production, use ChromaDB or similar)
            chunk_file_path = os.path.join(self.vector_db_path, f"{embedding_id}.json")
            with open(chunk_file_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)
            
            return embedding_id
            
        except Exception as e:
            logger.error(f"Error storing chunks: {str(e)}")
            raise
    
    def search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Search the knowledge base for relevant content
        
        Args:
            query: Search query
            limit: Maximum number of results
            category: Optional category filter
            
        Returns:
            List of search results
        """
        try:
            results = []
            query_lower = query.lower()
            
            # Search through all processed documents
            documents = KnowledgeDocument.objects.filter(
                is_processed=True,
                is_active=True
            )
            
            if category:
                documents = documents.filter(category__name=category)
            
            for document in documents:
                # Simple keyword-based search (in production, use semantic search)
                relevance_score = self._calculate_relevance(query_lower, document)
                
                if relevance_score > 0:
                    # Get relevant chunks
                    relevant_chunks = self._get_relevant_chunks(document, query_lower)
                    
                    for chunk in relevant_chunks:
                        results.append({
                            'document_id': str(document.id),
                            'title': document.title,
                            'category': document.category.name if document.category else 'Uncategorized',
                            'content': chunk,
                            'relevance_score': relevance_score,
                            'source_url': f'/chat/knowledge/{document.id}/'
                        })
            
            # Sort by relevance and limit results
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return []
    
    def _calculate_relevance(self, query: str, document: KnowledgeDocument) -> float:
        """
        Calculate relevance score for a document
        
        Args:
            query: Search query (lowercase)
            document: KnowledgeDocument instance
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            score = 0.0
            content_lower = document.content.lower()
            
            # Check title relevance
            if query in document.title.lower():
                score += 0.5
            
            # Check content relevance
            query_words = query.split()
            for word in query_words:
                if len(word) > 2:  # Skip short words
                    count = content_lower.count(word)
                    if count > 0:
                        score += min(count * 0.1, 0.3)  # Cap at 0.3 per word
            
            # Check category relevance
            if document.category and query in document.category.name.lower():
                score += 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating relevance: {str(e)}")
            return 0.0
    
    def _get_relevant_chunks(self, document: KnowledgeDocument, query: str) -> List[str]:
        """
        Get relevant chunks from a document
        
        Args:
            document: KnowledgeDocument instance
            query: Search query
            
        Returns:
            List of relevant text chunks
        """
        try:
            if not document.embedding_id:
                return []
            
            # Load chunks from storage
            chunk_file_path = os.path.join(self.vector_db_path, f"{document.embedding_id}.json")
            if not os.path.exists(chunk_file_path):
                return []
            
            with open(chunk_file_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            relevant_chunks = []
            query_words = query.split()
            
            for chunk in chunk_data.get('chunks', []):
                chunk_lower = chunk.lower()
                relevance = 0
                
                for word in query_words:
                    if len(word) > 2 and word in chunk_lower:
                        relevance += 1
                
                if relevance > 0:
                    relevant_chunks.append(chunk)
            
            return relevant_chunks[:3]  # Limit to 3 most relevant chunks
            
        except Exception as e:
            logger.error(f"Error getting relevant chunks: {str(e)}")
            return []
    
    def get_document_statistics(self) -> Dict:
        """
        Get statistics about the knowledge base
        
        Returns:
            Dictionary with statistics
        """
        try:
            total_documents = KnowledgeDocument.objects.filter(is_active=True).count()
            processed_documents = KnowledgeDocument.objects.filter(is_active=True, is_processed=True).count()
            total_words = sum(doc.word_count for doc in KnowledgeDocument.objects.filter(is_active=True))
            
            # Category breakdown
            categories = KnowledgeCategory.objects.all()
            category_stats = {}
            for category in categories:
                doc_count = KnowledgeDocument.objects.filter(category=category, is_active=True).count()
                if doc_count > 0:
                    category_stats[category.name] = doc_count
            
            return {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'processing_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0,
                'total_words': total_words,
                'categories': category_stats,
                'average_words_per_document': total_words / total_documents if total_documents > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"Error getting document statistics: {str(e)}")
            return {}
    
    def cleanup_old_documents(self, days_old: int = 30) -> int:
        """
        Clean up old inactive documents
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of documents cleaned up
        """
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_date = timezone.now() - timedelta(days=days_old)
            old_documents = KnowledgeDocument.objects.filter(
                is_active=False,
                updated_at__lt=cutoff_date
            )
            
            count = old_documents.count()
            old_documents.delete()
            
            logger.info(f"Cleaned up {count} old documents")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old documents: {str(e)}")
            return 0 