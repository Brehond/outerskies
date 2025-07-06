#!/usr/bin/env python3
"""
Deployment and CI/CD Pipeline Tests

Tests deployment scripts, CI/CD configurations, and automation workflows
for production deployment.
"""

import os
import sys
import yaml
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import subprocess
import tempfile

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class TestDeploymentScripts(unittest.TestCase):
    """Test deployment scripts"""
    
    def setUp(self):
        self.deploy_script_linux = project_root / "scripts" / "deploy.sh"
        self.deploy_script_windows = project_root / "scripts" / "deploy.bat"
        self.backup_script = project_root / "scripts" / "backup.sh"
        
    def test_deploy_scripts_exist(self):
        """Test that deployment scripts exist"""
        self.assertTrue(self.deploy_script_linux.exists())
        self.assertTrue(self.deploy_script_windows.exists())
        
    def test_backup_script_exists(self):
        """Test that backup script exists"""
        self.assertTrue(self.backup_script.exists())
        
    def test_linux_deploy_script_content(self):
        """Test Linux deployment script content"""
        with open(self.deploy_script_linux, 'r') as f:
            content = f.read()
            
        # Check for required components
        required_components = [
            '#!/bin/bash',
            'set -e',
            'docker-compose',
            'git pull',
            'migrate',
            'collectstatic',
            'restart'
        ]
        
        for component in required_components:
            self.assertIn(component, content)
            
    def test_windows_deploy_script_content(self):
        """Test Windows deployment script content"""
        with open(self.deploy_script_windows, 'r') as f:
            content = f.read()
            
        # Check for required components
        required_components = [
            '@echo off',
            'docker-compose',
            'git pull',
            'migrate',
            'collectstatic',
            'restart'
        ]
        
        for component in required_components:
            self.assertIn(component, content)
            
    def test_backup_script_content(self):
        """Test backup script content"""
        with open(self.backup_script, 'r') as f:
            content = f.read()
            
        # Check for required components
        required_components = [
            '#!/bin/bash',
            'BACKUP_DIR',
            'TIMESTAMP',
            'pg_dump',
            'tar',
            'gzip',
            'rsync'
        ]
        
        for component in required_components:
            self.assertIn(component, content)
            
    def test_deploy_script_permissions(self):
        """Test deployment script permissions"""
        # Check if scripts are executable (Unix-like systems)
        if os.name != 'nt':  # Not Windows
            self.assertTrue(os.access(self.deploy_script_linux, os.X_OK))
            self.assertTrue(os.access(self.backup_script, os.X_OK))
            
    def test_deploy_script_structure(self):
        """Test deployment script structure"""
        with open(self.deploy_script_linux, 'r') as f:
            content = f.read()
            
        # Check for proper script structure
        lines = content.split('\n')
        
        # Should start with shebang
        self.assertTrue(lines[0].startswith('#!/bin/bash'))
        
        # Should have error handling
        self.assertIn('set -e', content)
        
        # Should have comments
        self.assertTrue(any(line.strip().startswith('#') for line in lines))
        
    def test_deploy_script_environment_handling(self):
        """Test deployment script environment handling"""
        with open(self.deploy_script_linux, 'r') as f:
            content = f.read()
            
        # Check for environment variable handling
        env_handling = [
            'export',
            'source',
            '.env'
        ]
        
        for env_component in env_handling:
            self.assertIn(env_component, content)

class TestCICDPipeline(unittest.TestCase):
    """Test CI/CD pipeline configurations"""
    
    def setUp(self):
        self.github_workflow = project_root / ".github" / "workflows" / "deploy.yml"
        
    def test_github_workflow_exists(self):
        """Test that GitHub workflow exists"""
        self.assertTrue(self.github_workflow.exists())
        
    def test_github_workflow_structure(self):
        """Test GitHub workflow structure"""
        with open(self.github_workflow, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for required top-level keys
        required_keys = ['name', 'on', 'jobs']
        for key in required_keys:
            self.assertIn(key, config)
            
        # Check workflow name
        self.assertIn('deploy', config['name'].lower())
        
        # Check trigger events
        trigger_events = config['on']
        self.assertTrue(isinstance(trigger_events, (dict, list)))
        
        # Check jobs
        jobs = config['jobs']
        self.assertIn('deploy', jobs)
        
    def test_github_workflow_jobs(self):
        """Test GitHub workflow jobs"""
        with open(self.github_workflow, 'r') as f:
            config = yaml.safe_load(f)
            
        deploy_job = config['jobs']['deploy']
        
        # Check job configuration
        required_job_keys = ['runs-on', 'steps']
        for key in required_job_keys:
            self.assertIn(key, deploy_job)
            
        # Check runner
        self.assertIn('ubuntu', deploy_job['runs-on'])
        
        # Check steps
        steps = deploy_job['steps']
        self.assertTrue(isinstance(steps, list))
        self.assertGreater(len(steps), 0)
        
    def test_github_workflow_steps(self):
        """Test GitHub workflow steps"""
        with open(self.github_workflow, 'r') as f:
            config = yaml.safe_load(f)
            
        steps = config['jobs']['deploy']['steps']
        step_names = [step.get('name', '') for step in steps]
        
        # Check for required steps
        required_steps = [
            'Checkout',
            'Setup Python',
            'Install dependencies',
            'Run tests',
            'Deploy'
        ]
        
        for step in required_steps:
            self.assertTrue(
                any(step.lower() in name.lower() for name in step_names),
                f"Missing step: {step}"
            )
            
    def test_github_workflow_secrets(self):
        """Test GitHub workflow secrets handling"""
        with open(self.github_workflow, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for secrets usage
        config_str = yaml.dump(config)
        
        # Should use secrets for sensitive data
        secrets_usage = [
            '${{ secrets.',
            'secrets.DATABASE_URL',
            'secrets.SECRET_KEY'
        ]
        
        for secret in secrets_usage:
            self.assertIn(secret, config_str)

class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment configuration"""
    
    def setUp(self):
        self.env_prod_example = project_root / "env.production.example"
        
    def test_env_prod_example_exists(self):
        """Test that production environment example exists"""
        self.assertTrue(self.env_prod_example.exists())
        
    def test_env_prod_example_content(self):
        """Test production environment example content"""
        with open(self.env_prod_example, 'r') as f:
            content = f.read()
            
        # Check for required environment variables
        required_vars = [
            'DJANGO_SETTINGS_MODULE',
            'DATABASE_URL',
            'REDIS_URL',
            'SECRET_KEY',
            'DEBUG',
            'ALLOWED_HOSTS',
            'STRIPE_PUBLISHABLE_KEY',
            'STRIPE_SECRET_KEY',
            'OPENROUTER_API_KEY'
        ]
        
        for var in required_vars:
            self.assertIn(var, content)
            
    def test_env_prod_example_structure(self):
        """Test production environment example structure"""
        with open(self.env_prod_example, 'r') as f:
            content = f.read()
            
        lines = content.split('\n')
        
        # Check for proper format
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Should be KEY=VALUE format
                self.assertIn('=', line)
                
    def test_env_prod_example_comments(self):
        """Test production environment example comments"""
        with open(self.env_prod_example, 'r') as f:
            content = f.read()
            
        # Should have helpful comments
        comment_lines = [line for line in content.split('\n') if line.strip().startswith('#')]
        self.assertGreater(len(comment_lines), 0)

class TestDockerComposeProduction(unittest.TestCase):
    """Test production Docker Compose configuration"""
    
    def setUp(self):
        self.docker_compose_prod = project_root / "docker-compose.prod.yml"
        
    def test_prod_compose_exists(self):
        """Test that production Docker Compose exists"""
        self.assertTrue(self.docker_compose_prod.exists())
        
    def test_prod_compose_services(self):
        """Test production Docker Compose services"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for required services
        required_services = ['web', 'db', 'redis', 'nginx']
        for service in required_services:
            self.assertIn(service, config['services'])
            
    def test_prod_compose_environment(self):
        """Test production Docker Compose environment"""
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
        """Test production Docker Compose volumes"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for volume configurations
        for service_name, service_config in config['services'].items():
            if 'volumes' in service_config:
                volumes = service_config['volumes']
                self.assertTrue(isinstance(volumes, list))
                
    def test_prod_compose_networks(self):
        """Test production Docker Compose networks"""
        with open(self.docker_compose_prod, 'r') as f:
            config = yaml.safe_load(f)
            
        # Check for network configuration
        self.assertIn('networks', config)
        
        # Check that services use networks
        for service_name, service_config in config['services'].items():
            self.assertIn('networks', service_config)

class TestSecurityConfigurations(unittest.TestCase):
    """Test security configurations"""
    
    def test_security_audit_report_exists(self):
        """Test that security audit report exists"""
        security_report = project_root / "SECURITY_AUDIT_REPORT.md"
        self.assertTrue(security_report.exists())
        
    def test_security_audit_report_content(self):
        """Test security audit report content"""
        security_report = project_root / "SECURITY_AUDIT_REPORT.md"
        with open(security_report, 'r') as f:
            content = f.read()
            
        # Check for required sections
        required_sections = [
            'Security Audit Report',
            'Authentication',
            'Authorization',
            'Data Protection',
            'API Security',
            'Infrastructure Security'
        ]
        
        for section in required_sections:
            self.assertIn(section, content)
            
    def test_nginx_security_config(self):
        """Test nginx security configuration"""
        nginx_conf = project_root / "nginx.prod.conf"
        
        if nginx_conf.exists():
            with open(nginx_conf, 'r') as f:
                content = f.read()
                
            # Check for security headers
            security_headers = [
                'X-Frame-Options',
                'X-Content-Type-Options',
                'X-XSS-Protection',
                'Strict-Transport-Security'
            ]
            
            for header in security_headers:
                self.assertIn(header, content)

class TestDocumentation(unittest.TestCase):
    """Test documentation completeness"""
    
    def test_production_deployment_docs_exist(self):
        """Test that production deployment documentation exists"""
        prod_docs = project_root / "PRODUCTION_DEPLOYMENT.md"
        self.assertTrue(prod_docs.exists())
        
    def test_phase1_completion_summary_exists(self):
        """Test that Phase 1 completion summary exists"""
        phase1_summary = project_root / "PHASE1_COMPLETION_SUMMARY.md"
        self.assertTrue(phase1_summary.exists())
        
    def test_readme_updated(self):
        """Test that README includes production deployment info"""
        readme = project_root / "README.md"
        with open(readme, 'r') as f:
            content = f.read()
            
        # Check for production deployment section
        self.assertIn('Production Deployment', content)
        self.assertIn('docker-compose.prod.yml', content)

def run_deployment_ci_tests():
    """Run all deployment and CI/CD tests"""
    print("🚀 Starting Deployment and CI/CD Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDeploymentScripts,
        TestCICDPipeline,
        TestEnvironmentConfiguration,
        TestDockerComposeProduction,
        TestSecurityConfigurations,
        TestDocumentation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT & CI/CD TEST SUMMARY")
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
        print("\n✅ ALL DEPLOYMENT & CI/CD TESTS PASSED!")
    else:
        print("\n⚠️  Some deployment and CI/CD tests failed.")
    
    return result

if __name__ == "__main__":
    run_deployment_ci_tests() 