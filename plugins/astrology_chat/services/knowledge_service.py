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
            embedding_id = hashlib.md5(f"{document.id}_{document.title}".encode()).hexdigest()

            # Store chunks as JSON file (simplified vector storage)
            chunk_data = {
                'document_id': str(document.id),
                'title': document.title,
                'chunks': chunks,
                'metadata': {
                    'category': document.category.name if document.category else None,
                    'uploaded_by': str(document.uploaded_by.id) if document.uploaded_by else None,
                    'created_at': document.created_at.isoformat(),
                }
            }

            chunk_file_path = os.path.join(self.vector_db_path, f"{embedding_id}.json")
            with open(chunk_file_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, ensure_ascii=False, indent=2)

            return embedding_id

        except Exception as e:
            logger.error(f"Error storing chunks for {document.title}: {str(e)}")
            raise

    def search(self, query: str, limit: int = 5, category: Optional[str] = None) -> List[Dict]:
        """
        Search the knowledge base for relevant documents

        Args:
            query: Search query
            limit: Maximum number of results
            category: Optional category filter

        Returns:
            List of relevant documents with relevance scores
        """
        try:
            # Get all processed documents
            documents = KnowledgeDocument.objects.filter(
                is_processed=True,
                is_active=True
            )

            if category:
                documents = documents.filter(category__name=category)

            # Calculate relevance scores
            scored_documents = []
            for doc in documents:
                relevance_score = self._calculate_relevance(query, doc)
                if relevance_score > 0:
                    scored_documents.append({
                        'document': doc,
                        'relevance_score': relevance_score
                    })

            # Sort by relevance score and return top results
            scored_documents.sort(key=lambda x: x['relevance_score'], reverse=True)
            top_results = scored_documents[:limit]

            return [item['document'] for item in top_results]

        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return []

    def _calculate_relevance(self, query: str, document: KnowledgeDocument) -> float:
        """
        Calculate relevance score between query and document

        Args:
            query: Search query
            document: KnowledgeDocument instance

        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            query_terms = set(query.lower().split())
            document_text = f"{document.title} {document.description} {document.content}".lower()
            document_terms = set(document_text.split())

            # Simple TF-IDF inspired scoring
            matching_terms = query_terms.intersection(document_terms)
            if not matching_terms:
                return 0.0

            # Calculate score based on term frequency and document length
            score = len(matching_terms) / len(query_terms)
            score *= min(1.0, 1000 / len(document_text))  # Prefer shorter, focused documents

            # Boost score for title matches
            title_matches = query_terms.intersection(set(document.title.lower().split()))
            if title_matches:
                score *= 1.5

            return min(1.0, score)

        except Exception as e:
            logger.error(f"Error calculating relevance: {str(e)}")
            return 0.0

    def _get_relevant_chunks(self, document: KnowledgeDocument, query: str) -> List[str]:
        """
        Get relevant text chunks from a document

        Args:
            document: KnowledgeDocument instance
            query: Search query

        Returns:
            List of relevant text chunks
        """
        try:
            if not document.embedding_id:
                return []

            chunk_file_path = os.path.join(self.vector_db_path, f"{document.embedding_id}.json")
            if not os.path.exists(chunk_file_path):
                return []

            with open(chunk_file_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)

            chunks = chunk_data.get('chunks', [])
            query_terms = set(query.lower().split())

            relevant_chunks = []
            for chunk in chunks:
                chunk_terms = set(chunk.lower().split())
                matching_terms = query_terms.intersection(chunk_terms)
                if matching_terms:
                    relevance_score = len(matching_terms) / len(query_terms)
                    relevant_chunks.append((chunk, relevance_score))

            # Sort by relevance and return top chunks
            relevant_chunks.sort(key=lambda x: x[1], reverse=True)
            return [chunk for chunk, score in relevant_chunks[:3]]

        except Exception as e:
            logger.error(f"Error getting relevant chunks: {str(e)}")
            return []

    def get_document_statistics(self) -> Dict:
        """
        Get statistics about the knowledge base

        Returns:
            Dictionary with knowledge base statistics
        """
        try:
            total_documents = KnowledgeDocument.objects.count()
            processed_documents = KnowledgeDocument.objects.filter(is_processed=True).count()
            pending_documents = KnowledgeDocument.objects.filter(processing_status='pending').count()
            failed_documents = KnowledgeDocument.objects.filter(processing_status='failed').count()

            # Get documents by category
            category_stats = {}
            for category in KnowledgeCategory.objects.all():
                count = KnowledgeDocument.objects.filter(category=category, is_processed=True).count()
                if count > 0:
                    category_stats[category.name] = count

            return {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'pending_documents': pending_documents,
                'failed_documents': failed_documents,
                'category_stats': category_stats,
                'processing_success_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0,
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
                created_at__lt=cutoff_date
            )

            count = old_documents.count()
            old_documents.delete()

            logger.info(f"Cleaned up {count} old documents")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up old documents: {str(e)}")
            return 0

    def get_pending_documents(self) -> List[KnowledgeDocument]:
        """
        Get documents pending processing

        Returns:
            List of pending documents
        """
        return KnowledgeDocument.objects.filter(processing_status='pending').order_by('created_at')
