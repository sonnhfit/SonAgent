"""
Sandbox Executor for safe Python code execution.
Provides isolated environment for testing dynamically generated skills.
"""
import io
import logging
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class SandboxExecutor:
    """Execute Python code in a restricted sandbox environment."""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize sandbox executor.
        
        Args:
            timeout: Maximum execution time in seconds (not enforced in basic version)
        """
        self.timeout = timeout
        self.allowed_imports = {
            'json', 'math', 'datetime', 'time', 're', 'random',
            'typing', 'pathlib', 'collections', 'itertools',
            'pydantic', 'requests', 'sonagent.rpc'  # Common safe modules
        }
    
    def execute(self, code: str, globals_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute Python code in a sandbox environment.
        
        Args:
            code: Python code to execute
            globals_dict: Optional global variables to provide to the code
            
        Returns:
            Dictionary with execution results:
            - success: bool - whether execution succeeded
            - output: str - captured stdout
            - error: str - captured stderr or exception message
            - result: Any - return value if code defines a function and calls it
            - locals: dict - local variables after execution
        """
        result = {
            'success': False,
            'output': '',
            'error': '',
            'result': None,
            'locals': {}
        }
        
        # Create restricted globals
        restricted_globals = {
            '__builtins__': self._get_safe_builtins(),
            '__name__': '__sandbox__',
            '__doc__': None,
            '__package__': None,
        }
        
        # Add user-provided globals
        if globals_dict:
            restricted_globals.update(globals_dict)
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute the code
                exec_locals = {}
                exec(code, restricted_globals, exec_locals)
                
                result['success'] = True
                result['output'] = stdout_capture.getvalue()
                result['locals'] = exec_locals
                
                # If there's a result value (last expression), capture it
                if exec_locals:
                    # Try to find a main result or return value
                    result['result'] = exec_locals
                    
        except Exception as e:
            result['success'] = False
            result['error'] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            result['output'] = stdout_capture.getvalue()
            logger.error(f"Sandbox execution failed: {result['error']}")
        
        return result
    
    def _get_safe_builtins(self) -> Dict[str, Any]:
        """
        Get a restricted set of builtin functions.
        
        Returns:
            Dictionary of safe builtin functions
        """
        # Get actual builtins for essential features
        import builtins
        
        safe_builtins = {
            # Essential for class creation
            '__build_class__': builtins.__build_class__,
            '__name__': '__main__',
            
            # Type constructors
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'frozenset': frozenset,
            'bytes': bytes,
            'bytearray': bytearray,
            
            # Type checking
            'isinstance': isinstance,
            'issubclass': issubclass,
            'type': type,
            
            # Iteration
            'enumerate': enumerate,
            'range': range,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'reversed': reversed,
            'iter': iter,
            'next': next,
            
            # Data manipulation
            'len': len,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'round': round,
            'pow': pow,
            'divmod': divmod,
            
            # Conversion
            'chr': chr,
            'ord': ord,
            'hex': hex,
            'oct': oct,
            'bin': bin,
            
            # Object introspection (limited)
            'dir': dir,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,
            
            # String formatting
            'format': format,
            'repr': repr,
            'ascii': ascii,
            
            # Functional
            'all': all,
            'any': any,
            
            # Other safe functions
            'print': print,
            'hash': hash,
            'id': id,
            
            # Allow importing safe modules
            '__import__': self._safe_import,
        }
        
        return safe_builtins
    
    def _safe_import(self, name, *args, **kwargs):
        """
        Safe import function that only allows whitelisted modules.
        
        Args:
            name: Module name to import
            
        Returns:
            Imported module if allowed
            
        Raises:
            ImportError: If module is not in whitelist
        """
        # Check if the full module name or base module is allowed
        base_module = name.split('.')[0]
        if name not in self.allowed_imports and base_module not in self.allowed_imports:
            raise ImportError(f"Import of '{name}' is not allowed in sandbox")
        
        # Use standard import
        return __import__(name, *args, **kwargs)
    
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate Python code syntax without executing it.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            compile(code, '<sandbox>', 'exec')
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def test_skill_code(self, code: str, test_cases: Optional[list] = None) -> Dict[str, Any]:
        """
        Test skill code with optional test cases.
        
        Args:
            code: Skill code to test
            test_cases: Optional list of test cases (each a dict with 'args' and 'expected')
            
        Returns:
            Dictionary with test results
        """
        # First validate syntax
        is_valid, error_msg = self.validate_code(code)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'validation_failed': True
            }
        
        # Execute the code to load the skill class
        exec_result = self.execute(code)
        
        if not exec_result['success']:
            return {
                'success': False,
                'error': exec_result['error'],
                'execution_failed': True
            }
        
        # If test cases provided, run them
        if test_cases:
            test_results = []
            for i, test_case in enumerate(test_cases):
                try:
                    # This is a simplified test runner
                    # In practice, would need to instantiate the skill and call methods
                    test_results.append({
                        'test_id': i,
                        'status': 'skipped',
                        'message': 'Test execution not yet implemented'
                    })
                except Exception as e:
                    test_results.append({
                        'test_id': i,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            exec_result['test_results'] = test_results
        
        return exec_result
