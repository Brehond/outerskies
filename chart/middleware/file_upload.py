import os
import logging
from django.conf import settings
from django.http import JsonResponse
from django.core.files.uploadedfile import UploadedFile
import hashlib
import mimetypes
import re

logger = logging.getLogger('security')


class FileUploadSecurityMiddleware:
    """
    File upload security middleware that handles:
    - File type validation
    - File size limits
    - Virus scanning
    - Content validation
    - File sanitization
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # File upload settings
        self.max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)  # 10MB
        self.allowed_types = getattr(settings, 'ALLOWED_UPLOAD_TYPES', {
            'image/jpeg', 'image/png', 'image/gif',
            'application/pdf', 'text/plain', 'text/csv',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        })
        self.blocked_extensions = getattr(settings, 'BLOCKED_UPLOAD_EXTENSIONS', {
            '.exe', '.dll', '.bat', '.cmd', '.sh', '.php', '.asp', '.aspx',
            '.jsp', '.js', '.vbs', '.ps1', '.py', '.rb', '.pl'
        })
        self.scan_files = getattr(settings, 'SCAN_UPLOADED_FILES', True)
        self.sanitize_files = getattr(settings, 'SANITIZE_UPLOADED_FILES', True)

        # Initialize MIME type detection
        mimetypes.init()

    def __call__(self, request):
        # Only process file upload requests
        if not self._is_file_upload(request):
            return self.get_response(request)

        try:
            # Validate files
            errors = self._validate_files(request)
            if errors:
                return JsonResponse({
                    'error': 'File validation failed',
                    'details': errors
                }, status=400)

            # Scan files for viruses
            if self.scan_files:
                errors = self._scan_files(request)
                if errors:
                    return JsonResponse({
                        'error': 'File scanning failed',
                        'details': errors
                    }, status=400)

            # Sanitize files
            if self.sanitize_files:
                self._sanitize_files(request)

            return self.get_response(request)

        except Exception as e:
            logger.error(f'Error processing file upload: {str(e)}')
            return JsonResponse({
                'error': 'Error processing file upload'
            }, status=500)

    def _is_file_upload(self, request):
        """Check if the request contains file uploads."""
        return (
            request.method == 'POST'
            and request.content_type
            and 'multipart/form-data' in request.content_type
        )

    def _validate_files(self, request):
        """Validate uploaded files."""
        errors = []

        for field_name, files in request.FILES.items():
            # Handle multiple files
            if not isinstance(files, list):
                files = [files]

            for file in files:
                if not isinstance(file, UploadedFile):
                    continue

                # Check file size
                if file.size > self.max_size:
                    errors.append(f'File {file.name} exceeds maximum size of {self.max_size} bytes')
                    continue

                # Check file extension
                ext = os.path.splitext(file.name)[1].lower()
                if ext in self.blocked_extensions:
                    errors.append(f'File type {ext} is not allowed')
                    continue

                # Check MIME type
                mime_type, _ = mimetypes.guess_type(file.name)
                if not mime_type:
                    # Fallback to content-type header
                    mime_type = file.content_type or 'application/octet-stream'

                if mime_type not in self.allowed_types:
                    errors.append(f'File type {mime_type} is not allowed')
                    continue

                # Check file content
                if not self._validate_content(file):
                    errors.append(f'File {file.name} contains invalid content')
                    continue

        return errors

    def _scan_files(self, request):
        """Scan files for viruses and malware."""
        errors = []

        for field_name, files in request.FILES.items():
            if not isinstance(files, list):
                files = [files]

            for file in files:
                if not isinstance(file, UploadedFile):
                    continue

                # Here you would integrate with a virus scanning service
                # For example, using ClamAV or a cloud-based scanner
                if self._is_malicious(file):
                    errors.append(f'File {file.name} appears to be malicious')

        return errors

    def _sanitize_files(self, request):
        """Sanitize uploaded files."""
        for field_name, files in request.FILES.items():
            if not isinstance(files, list):
                files = [files]

            for file in files:
                if not isinstance(file, UploadedFile):
                    continue

                # Generate safe filename
                safe_name = self._generate_safe_filename(file.name)
                file.name = safe_name

                # Add file hash to request
                file_hash = self._calculate_file_hash(file)
                setattr(request, f'{field_name}_hash', file_hash)

    def _validate_content(self, file):
        """Validate file content."""
        # Read first few bytes to check for magic numbers
        header = file.read(1024)
        file.seek(0)

        # Check for common file signatures
        if file.content_type.startswith('image/'):
            return self._validate_image(header)
        elif file.content_type == 'application/pdf':
            return self._validate_pdf(header)
        elif file.content_type.startswith('text/'):
            return self._validate_text(header)

        return True

    def _validate_image(self, header):
        """Validate image file content."""
        # Check for common image signatures
        signatures = {
            b'\xFF\xD8\xFF': 'JPEG',
            b'\x89PNG\r\n\x1a\n': 'PNG',
            b'GIF87a': 'GIF',
            b'GIF89a': 'GIF'
        }

        return any(header.startswith(sig) for sig in signatures)

    def _validate_pdf(self, header):
        """Validate PDF file content."""
        return header.startswith(b'%PDF-')

    def _validate_text(self, header):
        """Validate text file content."""
        # Check for binary content in text files
        return not any(b'\x00' in header)

    def _is_malicious(self, file):
        """Check if file appears to be malicious."""
        # Read file content
        content = file.read()
        file.seek(0)

        # Check for common malware signatures
        malware_patterns = [
            re.compile(rb'eval\s*\('),
            re.compile(rb'exec\s*\('),
            re.compile(rb'system\s*\('),
            re.compile(rb'shell_exec\s*\('),
            re.compile(rb'passthru\s*\('),
            re.compile(rb'base64_decode\s*\(')
        ]

        return any(pattern.search(content) for pattern in malware_patterns)

    def _generate_safe_filename(self, filename):
        """Generate a safe filename."""
        # Remove path components
        filename = os.path.basename(filename)

        # Remove non-alphanumeric characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

        # Ensure unique filename
        name, ext = os.path.splitext(filename)
        return f"{name}_{hashlib.md5(filename.encode()).hexdigest()[:8]}{ext}"

    def _calculate_file_hash(self, file):
        """Calculate file hash for tracking."""
        file_hash = hashlib.sha256()
        for chunk in file.chunks():
            file_hash.update(chunk)
        file.seek(0)
        return file_hash.hexdigest()
