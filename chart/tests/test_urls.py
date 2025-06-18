from django.urls import path
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.sessions.backends.db import SessionStore
import json
from cryptography.fernet import Fernet
from django.conf import settings

# Simulate password history
password_history = set()

@csrf_exempt
def register(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode())
        except Exception:
            return JsonResponse({'error': 'invalid json'}, status=400)
            
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        # Simulate password complexity: must be at least 8 chars, contain @, and a digit
        if not password or len(password) < 8 or '@' not in password or not any(c.isdigit() for c in password):
            return JsonResponse({'error': 'password'}, status=400)
        # Simulate password history
        if password in password_history:
            return JsonResponse({'error': 'password_reuse'}, status=400)
        password_history.add(password)
        return JsonResponse({'status': 'success'}, status=201)
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode())
        except Exception:
            return JsonResponse({'error': 'invalid json'}, status=400)
            
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        # Simulate password reuse check
        if new_password in password_history:
            return JsonResponse({'error': 'password_reuse'}, status=400)
        password_history.add(new_password)
        return JsonResponse({'status': 'changed'}, status=200)
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def upload(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        # Debug print
        print('UPLOAD DEBUG:', file, getattr(file, 'size', None), settings.MAX_UPLOAD_SIZE)
        if file:
            if hasattr(file, 'size') and file.size > settings.MAX_UPLOAD_SIZE:
                return JsonResponse({'error': 'file too large'}, status=413)
            # Simulate file type check
            if file.name.endswith('.php'):
                return JsonResponse({'error': 'bad file type'}, status=400)
        return JsonResponse({'status': 'uploaded'}, status=200)
    return JsonResponse({'status': 'error'}, status=400)

@api_view(['GET'])
def test_view(request):
    # Ensure session is created
    if not request.session.session_key:
        request.session.create()
    return JsonResponse({'status': 'ok'})

@api_view(['GET', 'POST'])
def data_view(request):
    print('DATA_VIEW DEBUG: method:', request.method, 'headers:', dict(request.headers))
    print('DATA_VIEW ENCRYPTION_KEY:', settings.ENCRYPTION_KEY)
    if request.method == 'GET':
        return JsonResponse({'data': 'test'})
    # Accept encrypted POST for test_encryption
    if request.headers.get('X-Encryption') == 'true':
        print('ENCRYPTION DEBUG: Entered encrypted POST block')
        try:
            print('DATA_VIEW: type(request.body):', type(request.body), 'repr:', repr(request.body))
            f = Fernet(settings.ENCRYPTION_KEY.encode())
            decrypted = f.decrypt(request.body)
            print('ENCRYPTION DEBUG: Decrypted bytes:', decrypted)
            data = json.loads(decrypted.decode())
            print('ENCRYPTION DEBUG: Parsed data:', data)
            # Check for 'data' key
            if 'data' not in data:
                print('ENCRYPTION DEBUG: "data" key not found in:', data)
                return JsonResponse({'error': 'Missing required field: data'}, status=400)
            # Return encrypted response
            return HttpResponse(f.encrypt(json.dumps({'ok': True}).encode()), content_type='application/octet-stream')
        except Exception as e:
            import traceback
            print('ENCRYPTION ERROR: Exception occurred:', e)
            traceback.print_exc()
            return JsonResponse({'error': f'decryption failed: {e}'}, status=400)
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('register/', register, name='register'),
    path('change_password/', change_password, name='change_password'),
    path('upload/', upload, name='upload'),
    path('api/v1.0/test/', test_view, name='test'),
    path('api/data/', data_view, name='data'),
] 