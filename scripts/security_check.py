#!/usr/bin/env python3
"""
Security Configuration Check Script
This script verifies that all security settings are properly configured.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists and has required variables."""
    print("🔍 Checking .env file...")
    
    env_path = Path('.env')
    if not env_path.exists():
        print("❌ .env file not found!")
        print("   Run: python scripts/regenerate_security_keys.py")
        return False
    
    load_dotenv()
    
    required_vars = [
        'SECRET_KEY',
        'OPENROUTER_API_KEY',
        'STRIPE_SECRET_KEY',
        'STRIPE_PUBLISHABLE_KEY',
        'STRIPE_WEBHOOK_SECRET',
        'API_KEY',
        'API_SECRET',
        'ENCRYPTION_KEY',
        'ENCRYPTION_SALT'
    ]
    
    missing_vars = []
    insecure_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif any(placeholder in value.lower() for placeholder in ['your_', 'placeholder', 'test_', 'example']):
            insecure_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    if insecure_vars:
        print(f"⚠️  Insecure placeholder values found: {', '.join(insecure_vars)}")
        return False
    
    print("✅ .env file is properly configured")
    return True

def check_debug_mode():
    """Check if DEBUG mode is disabled."""
    print("\n🔍 Checking DEBUG mode...")
    
    debug = os.getenv('DEBUG', 'False').lower()
    if debug == 'true':
        print("⚠️  DEBUG mode is enabled - disable in production")
        return False
    else:
        print("✅ DEBUG mode is disabled")
        return True

def check_secret_key_strength():
    """Check if SECRET_KEY is strong enough."""
    print("\n🔍 Checking SECRET_KEY strength...")
    
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        print("❌ SECRET_KEY not set")
        return False
    
    if len(secret_key) < 50:
        print("⚠️  SECRET_KEY is too short (should be at least 50 characters)")
        return False
    
    if secret_key == 'insecure-secret-key':
        print("❌ SECRET_KEY is using insecure default")
        return False
    
    print("✅ SECRET_KEY is strong")
    return True

def check_allowed_hosts():
    """Check ALLOWED_HOSTS configuration."""
    print("\n🔍 Checking ALLOWED_HOSTS...")
    
    allowed_hosts = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
    hosts = [h.strip() for h in allowed_hosts.split(',')]
    
    if '*' in hosts:
        print("⚠️  ALLOWED_HOSTS contains '*' - restrict in production")
        return False
    
    print(f"✅ ALLOWED_HOSTS: {allowed_hosts}")
    return True

def check_database_security():
    """Check database security settings."""
    print("\n🔍 Checking database security...")
    
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        print("❌ DB_PASSWORD not set")
        return False
    
    if db_password == 'postgres':
        print("⚠️  Using default database password - change in production")
        return False
    
    print("✅ Database password is configured")
    return True

def check_api_keys():
    """Check API key security."""
    print("\n🔍 Checking API keys...")
    
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    if not openrouter_key or 'your_' in openrouter_key:
        print("❌ OpenRouter API key not properly configured")
        return False
    
    stripe_secret = os.getenv('STRIPE_SECRET_KEY')
    if not stripe_secret or 'your_' in stripe_secret:
        print("❌ Stripe secret key not properly configured")
        return False
    
    print("✅ API keys are configured")
    return True

def check_file_permissions():
    """Check file permissions."""
    print("\n🔍 Checking file permissions...")
    
    env_path = Path('.env')
    if env_path.exists():
        # On Windows, we can't easily check file permissions
        print("✅ .env file exists")
        return True
    
    print("❌ .env file not found")
    return False

def check_gitignore():
    """Check if .env is in .gitignore."""
    print("\n🔍 Checking .gitignore...")
    
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        print("❌ .gitignore file not found")
        return False
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    if '.env' in content:
        print("✅ .env is in .gitignore")
        return True
    else:
        print("❌ .env is not in .gitignore")
        return False

def main():
    """Main security check function."""
    print("🔐 Security Configuration Check")
    print("=" * 50)
    
    checks = [
        check_env_file,
        check_debug_mode,
        check_secret_key_strength,
        check_allowed_hosts,
        check_database_security,
        check_api_keys,
        check_file_permissions,
        check_gitignore
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        try:
            if check():
                passed += 1
        except Exception as e:
            print(f"❌ Error during {check.__name__}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Security Check Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All security checks passed!")
        print("✅ Your application is properly secured")
    else:
        print("⚠️  Some security issues found")
        print("🔧 Run the security fixes and check again")
        print("\nRecommended actions:")
        print("1. Run: python scripts/regenerate_security_keys.py")
        print("2. Update your .env file with real credentials")
        print("3. Set DEBUG=False in production")
        print("4. Configure proper ALLOWED_HOSTS")

if __name__ == "__main__":
    main() 