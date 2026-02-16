"""
Tests for SkillBuilder and dynamic skill generation.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sonagent.tools.sandbox_executor import SandboxExecutor
from sonagent.tools.skill_generator import SkillGenerator


class TestSandboxExecutor(unittest.TestCase):
    """Test sandbox execution functionality."""
    
    def setUp(self):
        self.sandbox = SandboxExecutor()
    
    def test_simple_execution(self):
        """Test simple code execution."""
        code = "result = 2 + 2"
        result = self.sandbox.execute(code)
        
        self.assertTrue(result['success'])
        self.assertIn('result', result['locals'])
        self.assertEqual(result['locals']['result'], 4)
    
    def test_print_capture(self):
        """Test stdout capture."""
        code = "print('Hello, World!')"
        result = self.sandbox.execute(code)
        
        self.assertTrue(result['success'])
        self.assertIn('Hello, World!', result['output'])
    
    def test_syntax_error(self):
        """Test syntax error handling."""
        code = "def invalid syntax:"
        result = self.sandbox.execute(code)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_safe_imports_allowed(self):
        """Test that safe imports are allowed."""
        code = """
import json
import math
data = json.dumps({'value': math.pi})
"""
        result = self.sandbox.execute(code)
        self.assertTrue(result['success'])
    
    def test_unsafe_imports_blocked(self):
        """Test that unsafe imports are blocked."""
        code = "import os"
        result = self.sandbox.execute(code)
        
        self.assertFalse(result['success'])
        self.assertIn('not allowed', result['error'])
    
    def test_code_validation(self):
        """Test code validation without execution."""
        valid_code = "x = 1 + 1"
        is_valid, error = self.sandbox.validate_code(valid_code)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        invalid_code = "def broken syntax:"
        is_valid, error = self.sandbox.validate_code(invalid_code)
        self.assertFalse(is_valid)
        self.assertIn('Syntax error', error)


class TestSkillGenerator(unittest.TestCase):
    """Test skill code generation."""
    
    def setUp(self):
        self.generator = SkillGenerator()
    
    def test_simple_skill_generation(self):
        """Test generating a simple skill."""
        code = self.generator.generate_skill(
            skill_name='TestSkill',
            description='A test skill'
        )
        
        self.assertIn('class TestSkill', code)
        self.assertIn('BaseModel', code)
        self.assertIn('A test skill', code)
    
    def test_skill_with_parameters(self):
        """Test generating a skill with parameters."""
        parameters = [
            {'name': 'text', 'type': 'str', 'description': 'Input text'},
            {'name': 'count', 'type': 'int', 'description': 'Number of times'}
        ]
        
        code = self.generator.generate_skill(
            skill_name='RepeatSkill',
            description='Repeat text multiple times',
            parameters=parameters
        )
        
        self.assertIn('class RepeatSkill', code)
        self.assertIn('text: str', code)
        self.assertIn('count: int', code)
        self.assertIn('Input text', code)
    
    def test_skill_with_implementation(self):
        """Test generating a skill with custom implementation."""
        implementation = '''result = text * count
IOMsg.send_msg(result)
return result'''
        
        code = self.generator.generate_skill(
            skill_name='MultiplySkill',
            description='Multiply text',
            parameters=[
                {'name': 'text', 'type': 'str', 'description': 'Text to multiply'},
                {'name': 'count', 'type': 'int', 'description': 'Multiplier'}
            ],
            implementation=implementation
        )
        
        self.assertIn('result = text * count', code)
    
    def test_invalid_skill_name(self):
        """Test that invalid skill names are rejected."""
        with self.assertRaises(ValueError):
            self.generator.generate_skill(
                skill_name='invalid_name',  # Should be CamelCase
                description='Test'
            )
    
    def test_skill_saving(self):
        """Test saving generated skill to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            
            code = self.generator.generate_skill(
                skill_name='SaveTestSkill',
                description='Test skill saving'
            )
            
            skill_file = self.generator.save_skill(code, 'SaveTestSkill', skills_dir)
            
            self.assertTrue(skill_file.exists())
            self.assertEqual(skill_file.name, 'SaveTestSkill.py')
            
            # Verify content
            saved_code = skill_file.read_text()
            self.assertEqual(saved_code, code)
    
    def test_generate_simple_skill_from_prompt(self):
        """Test generating a skill from a natural language prompt."""
        code = self.generator.generate_simple_skill_from_prompt(
            prompt='Calculate the sum of two numbers',
            skill_name='SumCalculator'
        )
        
        self.assertIn('class SumCalculator', code)
        self.assertIn('Calculate the sum of two numbers', code)
        self.assertIn('def sum_calculator', code)


class TestSkillBuilderIntegration(unittest.TestCase):
    """Integration tests for SkillBuilder."""
    
    def setUp(self):
        # Mock IOMsg
        class MockIOMsg:
            @staticmethod
            def send_msg(msg):
                pass
        
        import sonagent.rpc as rpc_module
        rpc_module.IOMsg = MockIOMsg
        
        # Add skills directory to path
        sys.path.insert(0, str(Path(__file__).parent.parent / 'user_data' / 'skills'))
        
        # Set environment variable
        self.tmpdir = tempfile.mkdtemp()
        os.environ['USER_DATA_DIR'] = self.tmpdir
    
    def tearDown(self):
        # Clean up
        import shutil
        if Path(self.tmpdir).exists():
            shutil.rmtree(self.tmpdir)
    
    def test_create_simple_skill(self):
        """Test creating a simple skill through SkillBuilder."""
        from SkillBuilder import SkillBuilder
        
        builder = SkillBuilder()
        result = builder.create_simple_skill(
            skill_name='IntegrationTestSkill',
            prompt='Test skill for integration'
        )
        
        self.assertIn('created', result)
        
        # Verify file was created
        skill_file = Path(self.tmpdir) / 'skills' / 'IntegrationTestSkill.py'
        self.assertTrue(skill_file.exists())
    
    def test_generate_skill_with_parameters(self):
        """Test generating a skill with parameters."""
        from SkillBuilder import SkillBuilder
        
        builder = SkillBuilder()
        
        parameters = json.dumps([
            {'name': 'value', 'type': 'int', 'description': 'Input value'}
        ])
        
        result = builder.generate_skill(
            skill_name='DoubleSkill',
            description='Double a number',
            parameters=parameters,
            implementation='result = value * 2\nIOMsg.send_msg(str(result))\nreturn result'
        )
        
        self.assertIn('successfully', result)
        
        # Verify file
        skill_file = Path(self.tmpdir) / 'skills' / 'DoubleSkill.py'
        self.assertTrue(skill_file.exists())
        
        # Verify content
        code = skill_file.read_text()
        self.assertIn('class DoubleSkill', code)
        self.assertIn('value * 2', code)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSandboxExecutor))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillBuilderIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
