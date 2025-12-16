import ast

class SecurityError(Exception):
    pass

class SafeExecutor:
    BLOCKED_IMPORTS = {
        'os', 'sys', 'subprocess', 'shutil', 'importlib', 'socket',
        'requests', 'urllib', 'http', 'pickle', 'base64'
    }
    BLOCKED_FUNCTIONS = {
        'open', 'exec', 'eval', 'compile', 'input', 'exit', 'quit'
    }

    @classmethod
    def validate(cls, code: str):
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Let the actual execution handle syntax errors, or return early
            return # Syntax errors are safe-ish (code wont run)

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name.split('.')[0] in cls.BLOCKED_IMPORTS:
                            raise SecurityError(f"Importing module '{name.name}' is not allowed.")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split('.')[0] in cls.BLOCKED_IMPORTS:
                        raise SecurityError(f"Importing from module '{node.module}' is not allowed.")

            # Check function calls (basic check, can be bypassed but filters casual misuse)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.BLOCKED_FUNCTIONS:
                        raise SecurityError(f"Function '{node.func.id}()' is blocked.")
                # Check for __import__
                if isinstance(node.func, ast.Name) and node.func.id == '__import__':
                     raise SecurityError("Using '__import__' is not allowed.")
