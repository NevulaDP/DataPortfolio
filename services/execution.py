import sys
import os
import subprocess
import pickle
import base64
import logging

class ExecutionService:
    """
    Manages secure execution of user code in a separate subprocess.
    """

    WORKER_SCRIPT = """
import sys
import os
import pickle
import base64
import io
import builtins
import types
import shutil
import ast

# 1. Load Input
try:
    input_data = sys.stdin.buffer.read()
    payload = pickle.loads(input_data)
    code = payload['code']
    scope = payload['scope']
except Exception as e:
    sys.stderr.write(f"System Error: {e}")
    sys.exit(1)

# 2. Setup Sandbox Environment
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import math
import datetime
import re

matplotlib.use('Agg')

stdout_buffer = io.StringIO()
sys.stdout = stdout_buffer

# 3. Security Lockdown - "Sanitization Strategy"

# A. Sanitize 'os' module
DANGEROUS_OS_ATTRS = {
    'system', 'popen', 'spawn', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe',
    'spawnv', 'spawnve', 'spawnvp', 'spawnvpe', 'execl', 'execle', 'execlp',
    'execlpe', 'execv', 'execve', 'execvp', 'execvpe', 'fork', 'forkpty',
    'kill', 'killpg', 'plock', 'remove', 'removedirs', 'rename', 'renames',
    'rmdir', 'symlink', 'unlink', 'walk', 'fchmod', 'fchown', 'chmod', 'chown',
    'chroot', 'chdir'
}

for attr in DANGEROUS_OS_ATTRS:
    if hasattr(os, attr):
        try:
            delattr(os, attr)
        except:
            setattr(os, attr, None)

# B. Sanitize 'shutil'
if 'shutil' in sys.modules:
    s = sys.modules['shutil']
    for attr in {'rmtree', 'move', 'chown', 'disk_usage'}:
        if hasattr(s, attr):
             try:
                delattr(s, attr)
             except:
                setattr(s, attr, None)

# C. Sanitize 'builtins'
safe_open = builtins.open
del builtins.open
del builtins.quit
del builtins.exit

# D. Secure Importer
# We explicitly block 'sys' so users can't mess with modules.
# We also block 'os' and 'shutil' from being re-imported from disk;
# we verify return the sanitized versions we already have.

BLOCKED_MODULES = {
    'sys', 'subprocess', 'socket', 'requests', 'urllib', 'http', 'ftplib',
    'poplib', 'imaplib', 'smtplib', 'telnetlib',
    'importlib', 'imp', 'pkgutil', 'modulefinder', 'zipimport',
    'pydoc', 'pdb', 'webbrowser'
}

# Keep references to sanitized modules
_sanitized_os = os
_sanitized_shutil = sys.modules.get('shutil')

def secure_importer(name, globals=None, locals=None, fromlist=(), level=0):
    base_name = name.split('.')[0]

    if base_name in BLOCKED_MODULES:
         raise ImportError(f"Security: Import of '{name}' is restricted.")

    # Force return of sanitized instances for critical modules
    if base_name == 'os':
        return _sanitized_os
    if base_name == 'shutil' and _sanitized_shutil:
        return _sanitized_shutil

    return __original_import__(name, globals, locals, fromlist, level)

__original_import__ = builtins.__import__
builtins.__import__ = secure_importer


# 4. Execute User Code with AST Logic (Rich Output)
execution_error = None
result_obj = None

try:
    # AST Parse to separate last expression
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Fallback to exec if syntax error (let it raise naturally)
        exec(code, scope)
        tree = None

    if tree and tree.body:
        last_node = tree.body[-1]
        if isinstance(last_node, ast.Expr):
            # Compile and exec everything before the last expression
            if len(tree.body) > 1:
                module = ast.Module(body=tree.body[:-1], type_ignores=[])
                # Execute body
                exec(compile(module, filename="<string>", mode="exec"), scope)

            # Eval the last expression
            expr = ast.Expression(body=last_node.value)
            result_obj = eval(compile(expr, filename="<string>", mode="eval"), scope)
        else:
            # No expression at end, just exec all
            exec(code, scope)
    elif tree is None:
        pass # Already handled
    else:
        # Empty code
        pass

except Exception as e:
    execution_error = str(e)
    # print(f"{type(e).__name__}: {e}") # Do not print to stdout to avoid cluttering output

# 5. Restore Environment
builtins.__import__ = __original_import__
builtins.open = safe_open

# Capture Plots
plots = []
try:
    for i in plt.get_fignums():
        fig = plt.figure(i)
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plots.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
        plt.close(fig)
except Exception as e:
    print(f"Error capturing plots: {e}")

# Filter Scope
output_scope = {}
for k, v in scope.items():
    if k.startswith('_'): continue
    if isinstance(v, (types.ModuleType, type(sys))): continue
    output_scope[k] = v

output = {
    'stdout': stdout_buffer.getvalue(),
    'plots': plots,
    'scope': output_scope,
    'error': execution_error,
    'result': result_obj if result_obj is not None else None
    # Note: result_obj might not be pickleable (e.g. function).
    # If not, pickle.dumps below will fail. We should handle that.
}

sys.stdout = sys.__stdout__
try:
    sys.stdout.buffer.write(pickle.dumps(output))
except Exception as e:
    # If pickling failed (likely due to result_obj), try setting result to string representation
    if 'result' in output and output['result'] is not None:
        output['result'] = str(output['result'])
        try:
            sys.stdout.buffer.write(pickle.dumps(output))
        except Exception as e2:
             sys.stderr.write(f"Serialization Error (Retry): {e2}")
    else:
        sys.stderr.write(f"Serialization Error: {e}")
"""

    @staticmethod
    def execute_code(code: str, scope: dict) -> dict:
        clean_scope = {}
        for k, v in scope.items():
            if k.startswith('_'): continue
            if hasattr(v, '__module__') and v.__module__ and v.__module__.startswith('streamlit'): continue
            clean_scope[k] = v

        payload = {'code': code, 'scope': clean_scope}

        try:
            serialized_payload = pickle.dumps(payload)
        except Exception as e:
            return {'stdout': "", 'plots': [], 'scope': scope, 'error': f"Serialization Error (Sending): {e}"}

        try:
            process = subprocess.Popen(
                [sys.executable, "-c", ExecutionService.WORKER_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout_data, stderr_data = process.communicate(input=serialized_payload)

            if process.returncode != 0:
                return {
                    'stdout': "",
                    'plots': [],
                    'scope': scope,
                    'error': f"Process Crash: {stderr_data.decode()}"
                }

            if not stdout_data:
                return {
                    'stdout': "",
                    'plots': [],
                    'scope': scope,
                    'error': f"No output received. Stderr: {stderr_data.decode()}"
                }

            result = pickle.loads(stdout_data)
            return result

        except Exception as e:
             return {'stdout': "", 'plots': [], 'scope': scope, 'error': f"Execution System Error: {e}"}
