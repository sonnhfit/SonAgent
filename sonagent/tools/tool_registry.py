"""
Tool Registry for dynamic loading of user-defined tools.
"""
import importlib.util
import inspect
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import sys

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for dynamically loading tools from user_data/tools directory.
    
    Tools are Python functions defined in .py files in user_data/tools/.
    Functions starting with '_' are considered private helpers and are ignored.
    """
    
    def __init__(self, config: dict) -> None:
        """
        Initialize the tool registry.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.user_data_dir = Path(config.get('user_data_dir', 'user_data'))
        self.tools_dir = self.user_data_dir / 'tools'
        
        # Ensure tools directory exists
        self._ensure_tools_directory()
        
        # Registry state
        self.tools: Dict[str, Dict[str, Any]] = {}  # name -> tool info
        self.tool_functions: Dict[str, Any] = {}  # name -> function object
        self.last_scan_time = 0
        self.cached_file_hashes: Set[str] = set()
        self.scan_interval = 30  # Scan every 30 seconds
        
        # Initial scan
        self.scan_and_load_tools()
        
        logger.info(f"ToolRegistry initialized with {len(self.tools)} tools from {self.tools_dir}")
    
    def _ensure_tools_directory(self) -> None:
        """Create tools directory if it doesn't exist."""
        if not self.tools_dir.exists():
            try:
                self.tools_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created tools directory: {self.tools_dir}")
                
                # Add .gitkeep file
                gitkeep_file = self.tools_dir / '.gitkeep'
                if not gitkeep_file.exists():
                    gitkeep_file.touch()
                    logger.info(f"Added .gitkeep to tools directory")
            except Exception as e:
                logger.error(f"Failed to create tools directory {self.tools_dir}: {e}")
                raise
    
    def _get_file_hash(self, file_path: Path) -> str:
        """
        Get a hash representing file content and modification time.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hash string
        """
        try:
            stat = file_path.stat()
            # Use modification time and file size for quick change detection
            return f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        except Exception as e:
            logger.error(f"Error getting file hash for {file_path}: {e}")
            return str(file_path)
    
    def should_scan(self) -> bool:
        """
        Check if it's time to scan for tool changes.
        
        Returns:
            True if should scan, False otherwise
        """
        current_time = time.time()
        if current_time - self.last_scan_time >= self.scan_interval:
            return True
        return False
    
    def scan_and_load_tools(self, force: bool = False) -> bool:
        """
        Scan tools directory and load/reload tools if changes detected.
        
        Args:
            force: Force reload even if no changes detected
            
        Returns:
            True if tools were reloaded, False otherwise
        """
        if not force and not self.should_scan():
            return False
        
        self.last_scan_time = time.time()
        
        # Get current file hashes
        current_hashes = set()
        if self.tools_dir.exists():
            for entry in self.tools_dir.rglob('*.py'):
                if entry.is_file() and not entry.name.startswith('__'):
                    current_hashes.add(self._get_file_hash(entry))
        
        # Check if files have changed
        if current_hashes != self.cached_file_hashes or force:
            logger.info(f"Tools changed or force reload. Current: {len(current_hashes)} files")
            self.cached_file_hashes = current_hashes
            self._load_tools_from_directory()
            return True
        
        return False
    
    def _load_tools_from_directory(self) -> None:
        """
        Load all tools from the tools directory.
        Skips files with syntax errors to ensure other files work normally.
        """
        logger.info(f"Loading tools from directory: {self.tools_dir}")
        
        # Clear existing tools
        self.tools.clear()
        self.tool_functions.clear()
        
        if not self.tools_dir.exists():
            logger.warning(f"Tools directory does not exist: {self.tools_dir}")
            return
        
        # Scan for Python files
        tool_files = list(self.tools_dir.rglob('*.py'))
        logger.info(f"Found {len(tool_files)} Python files in tools directory")
        
        successful_files = 0
        failed_files = 0
        
        for tool_file in tool_files:
            if tool_file.name.startswith('__'):
                continue  # Skip __init__.py etc.
            
            try:
                tools_loaded = self._load_tools_from_file(tool_file)
                if tools_loaded > 0:
                    successful_files += 1
                else:
                    logger.debug(f"No tools found in {tool_file.name}")
            except SyntaxError as e:
                logger.error(f"Syntax error in {tool_file}: {e}. Skipping this file.")
                failed_files += 1
            except ImportError as e:
                logger.error(f"Import error in {tool_file}: {e}. Skipping this file.")
                failed_files += 1
            except Exception as e:
                logger.error(f"Error loading tools from {tool_file}: {e}", exc_info=True)
                failed_files += 1
        
        logger.info(f"Loaded {len(self.tools)} tools from {successful_files} files ({failed_files} files failed)")
    
    def _load_tools_from_file(self, file_path: Path) -> int:
        """
        Load tools from a single Python file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Number of tools loaded from this file
        """
        # Get module name from file stem
        module_name = file_path.stem
        
        # Add parent directory to sys.path temporarily
        parent_dir = str(file_path.parent)
        original_sys_path = sys.path.copy()
        
        tools_loaded = 0
        
        try:
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Load module
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec is None:
                logger.error(f"Could not load spec from {file_path}")
                return 0
            
            module = importlib.util.module_from_spec(spec)
            
            try:
                spec.loader.exec_module(module)  # type: ignore
            except SyntaxError as e:
                # Re-raise syntax errors to be caught by caller
                raise SyntaxError(f"Syntax error in {file_path}: {e}") from e
            except ImportError as e:
                # Re-raise import errors to be caught by caller
                raise ImportError(f"Import error in {file_path}: {e}") from e
            except Exception as e:
                logger.error(f"Error executing module {file_path}: {e}")
                return 0
            
            # Find all callable functions that don't start with '_'
            for name, obj in inspect.getmembers(module):
                if (callable(obj) and 
                    not name.startswith('_') and 
                    inspect.isfunction(obj) and
                    obj.__module__ == module_name):
                    
                    # Get function signature and docstring
                    try:
                        signature = inspect.signature(obj)
                        docstring = inspect.getdoc(obj) or "No description"
                        
                        # Extract parameter information
                        params = []
                        for param_name, param in signature.parameters.items():
                            param_type = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                            param_default = param.default if param.default != inspect.Parameter.empty else None
                            param_info = {
                                "name": param_name,
                                "type": param_type,
                                "default": param_default,
                                "required": param.default == inspect.Parameter.empty
                            }
                            params.append(param_info)
                        
                        # Get return type
                        return_type = str(signature.return_annotation) if signature.return_annotation != inspect.Signature.empty else "Any"
                        
                        # Store tool information
                        tool_info = {
                            "name": name,
                            "function": obj,
                            "docstring": docstring,
                            "params": params,
                            "return_type": return_type,
                            "file": file_path.name,
                            "file_path": str(file_path),
                            "module": module_name
                        }
                        
                        self.tools[name] = tool_info
                        self.tool_functions[name] = obj
                        tools_loaded += 1
                        
                        logger.info(f"Loaded tool: {name} from {file_path.name}")
                        
                    except Exception as e:
                        logger.error(f"Error processing tool {name} from {file_path}: {e}")
                        
        except (SyntaxError, ImportError):
            # Re-raise these specific errors
            raise
        except Exception as e:
            logger.error(f"Error loading tools from {file_path}: {e}", exc_info=True)
        finally:
            # Restore sys.path
            sys.path = original_sys_path
        
        return tools_loaded
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all loaded tools.
        
        Returns:
            List of tool information dictionaries
        """
        return list(self.tools.values())
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool information dictionary or None if not found
        """
        return self.tools.get(name)
    
    def get_tool_function(self, name: str) -> Optional[Any]:
        """
        Get the actual function object for a tool.
        
        Args:
            name: Tool name
            
        Returns:
            Function object or None if not found
        """
        return self.tool_functions.get(name)
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name with given arguments.
        
        Args:
            tool_name: Tool name
            **kwargs: Arguments to pass to tool
            
        Returns:
            Tool execution result
            
        Raises:
            KeyError: If tool not found
            Exception: If tool execution fails
        """
        if tool_name not in self.tool_functions:
            raise KeyError(f"Tool not found: {tool_name}")
        
        tool_func = self.tool_functions[tool_name]
        return tool_func(**kwargs)
    
    def format_tools_list(self) -> str:
        """
        Format loaded tools as a readable string.
        
        Returns:
            Formatted tools list
        """
        if not self.tools:
            return "📭 *No tools loaded.*"
        
        tools_list = []
        tools_list.append(f"📋 *Available Tools* ({len(self.tools)} total):\n")
        
        for i, (name, tool_info) in enumerate(self.tools.items(), 1):
            tools_list.append(f"{i}. *File:* `{tool_info['file']}`")
            tools_list.append(f"   *Function:* `{name}`")
            
            # Truncate docstring if too long
            docstring = tool_info['docstring']
            if len(docstring) > 200:
                docstring = docstring[:197] + "..."
            tools_list.append(f"   *Description:* {docstring}")
            
            # Add parameters if available
            if tool_info['params']:
                params_str = ", ".join([
                    f"{p['name']} ({p['type']})" 
                    for p in tool_info['params']
                ])
                tools_list.append(f"   *Parameters:* {params_str}")
            
            tools_list.append("")  # Empty line between tools
        
        return "\n".join(tools_list)
    
    def reload_tools(self) -> None:
        """
        Force reload of all tools.
        """
        logger.info("Force reloading tools")
        self.scan_and_load_tools(force=True)