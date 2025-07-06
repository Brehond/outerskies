#!/usr/bin/env python3
"""
Docker Integration Tests for Production Deployment

Tests Docker configurations, build processes, and container orchestration
without requiring actual Docker daemon running.
"""

import os
import sys
import yaml
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import subprocess

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class TestDockerBuildProcess(unittest.TestCase):
    """Test Docker build process and configurations"""
    
    def setUp(self):
        self.dockerfile_path = project_root / "Dockerfile"
        self.docker_compose_dev = project_root / "docker-compose.yml"
        self.docker_compose_prod = project_root / "docker-compose.prod.yml"
        
    def test_dockerfile_multi_stage_build(self):
        """Test Dockerfile multi-stage build configuration"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for multi-stage build
        self.assertIn('FROM python:3.11-slim as base', content)
        self.assertIn('FROM base as production', content)
        
        # Check for development stage
        self.assertIn('FROM base as development', content)
        
    def test_dockerfile_security_practices(self):
        """Test Dockerfile security best practices"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for non-root user
        self.assertIn('RUN adduser --disabled-password --gecos "" appuser', content)
        self.assertIn('USER appuser', content)
        
        # Check for security updates
        self.assertIn('apt-get update', content)
        self.assertIn('apt-get upgrade', content)
        
        # Check for cleanup
        self.assertIn('apt-get clean', content)
        self.assertIn('rm -rf /var/lib/apt/lists/*', content)
        
    def test_dockerfile_dependencies(self):
        """Test Dockerfile dependency management"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for requirements installation
        self.assertIn('COPY requirements.txt', content)
        self.assertIn('pip install', content)
        
        # Check for project files
        self.assertIn('COPY manage.py', content)
        self.assertIn('COPY outer_skies', content)
        self.assertIn('COPY chart', content)
        
    def test_dockerfile_environment(self):
        """Test Dockerfile environment configuration"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for environment variables
        self.assertIn('ENV PYTHONPATH', content)
        self.assertIn('ENV DJANGO_SETTINGS_MODULE', content)
        
        # Check for working directory
        self.assertIn('WORKDIR /app', content)
        
    def test_dockerfile_expose_ports(self):
        """Test Dockerfile port exposure"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for port exposure
        self.assertIn('EXPOSE 8000', content)

class TestDockerComposeConfigurations(unittest.TestCase):
    """Test Docker Compose configurations"""
    
    def setUp(self):
        self.docker_compose_dev = project_root / "docker-compose.yml"
        self.docker_compose_prod = project_root / "docker-compose.prod.yml"
        
    def test_dev_compose_exists(self):
        """Test that development Docker Compose exists"""
        self.assertTrue(self.docker_compose_dev.exists())
        
    def test_prod_compose_exists(self):
        """Test that production Docker Compose exists"""
        self.assertTrue(self.docker_compose_prod.exists())
        
    def test_dev_compose_structure(self):
        """Test development Docker Compose structure"""
        with open(self.docker_compose_dev, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for required services
        required_services = ['web', 'db', 'redis']
        for service in required_services:
            self.assertIn(service, config['services'])
            
    def test_prod_compose_structure(self):
        """Test production Docker Compose structure"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for required services
        required_services = ['web', 'db', 'redis', 'nginx']
        for service in required_services:
            self.assertIn(service, config['services'])
            
    def test_prod_compose_environment_variables(self):
        """Test production environment variables"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        web_service = config['services']['web']
        environment = web_service.get('environment', [])
        
        # Check for required environment variables
        required_vars = [
            'DJANGO_SETTINGS_MODULE',
            'DATABASE_URL',
            'REDIS_URL',
            'SECRET_KEY',
            'DEBUG',
            'ALLOWED_HOSTS'
        ]
        
        env_dict = {}
        for env in environment:
            if isinstance(env, str) and '=' in env:
                key, value = env.split('=', 1)
                env_dict[key] = value
                
        for var in required_vars:
            self.assertIn(var, env_dict, f"Missing environment variable: {var}")
            
    def test_prod_compose_volumes(self):
        """Test production volume configurations"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check database volumes
        db_service = config['services']['db']
        self.assertIn('volumes', db_service)
        
        # Check redis volumes
        redis_service = config['services']['redis']
        self.assertIn('volumes', redis_service)
        
    def test_prod_compose_networks(self):
        """Test production network configurations"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for network configuration
        self.assertIn('networks', config)
        
        # Check that services use the network
        for service_name, service_config in config['services'].items():
            self.assertIn('networks', service_config)

class TestDockerSecurity(unittest.TestCase):
    """Test Docker security configurations"""
    
    def setUp(self):
        self.dockerfile_path = project_root / "Dockerfile"
        self.docker_compose_prod = project_root / "docker-compose.prod.yml"
    
    def test_dockerfile_security_scan(self):
        """Test Dockerfile for security vulnerabilities"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for security issues
        security_issues = [
            'USER root',  # Should not run as root
            'RUN chmod 777',  # Overly permissive permissions
            'COPY . /app',  # Copying everything
        ]
        
        for issue in security_issues:
            self.assertNotIn(issue, content, f"Security issue found: {issue}")
            
    def test_docker_compose_security(self):
        """Test Docker Compose security configurations"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for security configurations
        for service_name, service_config in config['services'].items():
            # Check for read-only root filesystem
            if 'security_opt' in service_config:
                self.assertIn('no-new-privileges', service_config['security_opt'])
                
            # Check for resource limits
            if 'deploy' in service_config:
                self.assertIn('resources', service_config['deploy'])

class TestDockerPerformance(unittest.TestCase):
    """Test Docker performance optimizations"""
    
    def setUp(self):
        self.dockerfile_path = project_root / "Dockerfile"
        self.docker_compose_prod = project_root / "docker-compose.prod.yml"
    
    def test_dockerfile_optimization(self):
        """Test Dockerfile optimization techniques"""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
            
        # Check for optimization techniques
        optimizations = [
            'COPY requirements.txt',  # Copy requirements first
            'pip install --no-cache-dir',  # No cache for pip
            'apt-get clean',  # Clean apt cache
            'rm -rf /var/lib/apt/lists/*',  # Remove apt lists
        ]
        
        for opt in optimizations:
            self.assertIn(opt, content, f"Missing optimization: {opt}")
            
    def test_docker_compose_performance(self):
        """Test Docker Compose performance configurations"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for performance configurations
        for service_name, service_config in config['services'].items():
            # Check for resource limits
            if 'deploy' in service_config:
                deploy_config = service_config['deploy']
                if 'resources' in deploy_config:
                    resources = deploy_config['resources']
                    self.assertIn('limits', resources)
                    self.assertIn('reservations', resources)

class TestDockerMonitoring(unittest.TestCase):
    """Test Docker monitoring configurations"""
    
    def setUp(self):
        self.dockerfile_path = project_root / "Dockerfile"
        self.docker_compose_prod = project_root / "docker-compose.prod.yml"
    
    def test_docker_compose_monitoring(self):
        """Test Docker Compose monitoring setup"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for monitoring configurations
        for service_name, service_config in config['services'].items():
            # Check for health checks
            if 'healthcheck' in service_config:
                healthcheck = service_config['healthcheck']
                self.assertIn('test', healthcheck)
                self.assertIn('interval', healthcheck)
                self.assertIn('timeout', healthcheck)
                self.assertIn('retries', healthcheck)
                
    def test_docker_logging_configuration(self):
        """Test Docker logging configuration"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for logging configurations
        for service_name, service_config in config['services'].items():
            if 'logging' in service_config:
                logging_config = service_config['logging']
                self.assertIn('driver', logging_config)
                self.assertIn('options', logging_config)

def run_docker_tests():
    """Run all Docker integration tests"""
    print("🐳 Starting Docker Integration Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDockerBuildProcess,
        TestDockerComposeConfigurations,
        TestDockerSecurity,
        TestDockerPerformance,
        TestDockerMonitoring
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 DOCKER TEST SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n❌ ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if not result.failures and not result.errors:
        print("\n✅ ALL DOCKER TESTS PASSED!")
    else:
        print("\n⚠️  Some Docker tests failed.")
    
    return result

if __name__ == "__main__":
    run_docker_tests() 