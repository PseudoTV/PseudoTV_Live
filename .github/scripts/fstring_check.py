import ast
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict


class FStringChecker(ast.NodeVisitor):
    """AST-based f-string validator for Python code."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[Dict] = []
    
    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Visit f-string nodes and validate their content."""
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                self._check_formatted_value(value)
        self.generic_visit(node)
    
    def _check_formatted_value(self, node: ast.FormattedValue) -> None:
        """Check a formatted value in an f-string."""
        # Check for potential issues with the expression
        if isinstance(node.value, ast.Name):
            # Check if variable name suggests it might be unused
            if node.value.id.startswith('_'):
                self._add_issue(
                    node.lineno,
                    "f-string",
                    f"Private variable '{node.value.id}' used in f-string"
                )
        
        # Check for nested f-strings (potential performance issue)
        if isinstance(node.value, ast.JoinedStr):
            self._add_issue(
                node.lineno,
                "f-string",
                "Nested f-string detected, consider simplifying"
            )
        
        # Check conversion flag
        if node.conversion not in (-1, 115, 114, 97):  # -1=none, 115=str, 114=repr, 97=ascii
            self._add_issue(
                node.lineno,
                "f-string",
                f"Unexpected conversion flag: {node.conversion}"
            )
    
    def _add_issue(self, line: int, category: str, message: str) -> None:
        """Add an issue to the list."""
        self.issues.append({
            'file': self.filename,
            'line': line,
            'category': category,
            'message': message
        })


def check_file(filepath: str) -> List[Dict]:
    """Check a single Python file for f-string issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=filepath)
        checker = FStringChecker(filepath)
        checker.visit(tree)
        return checker.issues
    except SyntaxError as e:
        return [{
            'file': filepath,
            'line': e.lineno or 0,
            'category': 'syntax',
            'message': f"Syntax error: {e.msg}"
        }]
    except Exception as e:
        return [{
            'file': filepath,
            'line': 0,
            'category': 'error',
            'message': f"Error reading file: {str(e)}"
        }]


def find_python_files(directory: str) -> List[str]:
    """Find all Python files in directory."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def main():
    """Main entry point."""
    target = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    if os.path.isfile(target):
        files = [target]
    else:
        files = find_python_files(target)
    
    all_issues = []
    for filepath in files:
        issues = check_file(filepath)
        all_issues.extend(issues)
    
    if all_issues:
        print(f"\n{'='*60}")
        print(f"F-String Check Results: {len(all_issues)} issue(s) found")
        print(f"{'='*60}\n")
        
        for issue in all_issues:
            print(f"File: {issue['file']}")
            print(f"Line: {issue['line']}")
            print(f"Category: {issue['category']}")
            print(f"Message: {issue['message']}")
            print(f"{'-'*40}")
        
        sys.exit(1)
    else:
        print("✓ No f-string issues found")
        sys.exit(0)


if __name__ == '__main__':
    main()
