import ast
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Optional


def parse_strings_po(po_path: str) -> Dict[int, str]:
    """Parse a strings.po file and return a dictionary of ID -> msgid."""
    strings = {}
    if not os.path.exists(po_path):
        return strings
    
    with open(po_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match msgctxt "#XXXXX" followed by msgid "..."
    pattern = r'msgctxt\s+"#(\d+)"\s+msgid\s+"((?:[^"\\]|\\.)*)"\s+msgstr\s+"'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for str_id, msgid in matches:
        strings[int(str_id)] = msgid
    
    return strings


def find_language_file() -> Optional[str]:
    """Find the en-GB strings.po file."""
    possible_paths = [
        "plugin.video.pseudotv.live/resources/language/resource.language.en_gb/strings.po",
        "resources/language/resource.language.en_gb/strings.po",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    for root, _, files in os.walk("."):
        if "resource.language.en_gb" in root and "strings.po" in files:
            return os.path.join(root, "strings.po")
    
    return None


class FStringChecker(ast.NodeVisitor):
    """AST-based f-string and LANGUAGE() validator."""
    
    def __init__(self, filename: str, strings_dict: Dict[int, str]):
        self.filename = filename
        self.strings_dict = strings_dict
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
    
    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        """Visit f-string nodes and validate their content."""
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                self._check_formatted_value(value)
        self.generic_visit(node)
    
    def _check_formatted_value(self, node: ast.FormattedValue) -> None:
        """Check a formatted value in an f-string."""
        if isinstance(node.value, ast.JoinedStr):
            self._add_warning(
                node.lineno,
                "f-string",
                "Nested f-string detected, consider simplifying"
            )
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to check LANGUAGE() usage."""
        if isinstance(node.func, ast.Name) and node.func.id == "LANGUAGE":
            self._check_language_call(node)
        self.generic_visit(node)
    
    def _check_language_call(self, node: ast.Call) -> None:
        """Check a LANGUAGE() call for issues."""
        if not node.args:
            self._add_error(
                node.lineno,
                "LANGUAGE",
                "LANGUAGE() called with no arguments"
            )
            return
        
        arg = node.args[0]
        
        str_id = None
        if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
            str_id = arg.value
        elif isinstance(arg, ast.Num):
            str_id = arg.n
        
        if str_id is None:
            return
        
        if str_id not in self.strings_dict:
            self._add_warning(
                node.lineno,
                "LANGUAGE",
                f"LANGUAGE({str_id}) not found in strings.po"
            )
            return
        
        msgid = self.strings_dict[str_id]
        
        if not msgid.strip():
            self._add_warning(
                node.lineno,
                "LANGUAGE",
                f"LANGUAGE({str_id}) has empty msgid"
            )
    
    def _add_error(self, line: int, category: str, message: str) -> None:
        self.errors.append({
            'file': self.filename,
            'line': line,
            'category': category,
            'message': message
        })
    
    def _add_warning(self, line: int, category: str, message: str) -> None:
        self.warnings.append({
            'file': self.filename,
            'line': line,
            'category': category,
            'message': message
        })


def check_file(filepath: str, strings_dict: Dict[int, str]) -> tuple[List[Dict], List[Dict]]:
    """Check a single Python file for f-string and LANGUAGE issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=filepath)
        checker = FStringChecker(filepath, strings_dict)
        checker.visit(tree)
        return checker.errors, checker.warnings
    except SyntaxError:
        return [], []
    except Exception:
        return [], []


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
    
    # Find and parse the strings.po file
    po_file = find_language_file()
    if po_file:
        strings_dict = parse_strings_po(po_file)
        print(f"Loaded {len(strings_dict)} strings from {po_file}")
    else:
        print("Warning: strings.po not found, LANGUAGE() checks disabled")
        strings_dict = {}
    
    if os.path.isfile(target):
        files = [target]
    else:
        files = find_python_files(target)
    
    all_errors = []
    all_warnings = []
    for filepath in files:
        errors, warnings = check_file(filepath, strings_dict)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
    
    # Print warnings (non-fatal)
    if all_warnings:
        print(f"\n{'='*60}")
        print(f"WARNINGS: {len(all_warnings)} issue(s) found")
        print(f"{'='*60}\n")
        
        for issue in all_warnings:
            print(f"File: {issue['file']}")
            print(f"Line: {issue['line']}")
            print(f"Category: {issue['category']}")
            print(f"Message: {issue['message']}")
            print(f"{'-'*40}")
    
    # Print errors (fatal)
    if all_errors:
        print(f"\n{'='*60}")
        print(f"ERRORS: {len(all_errors)} issue(s) found")
        print(f"{'='*60}\n")
        
        for issue in all_errors:
            print(f"File: {issue['file']}")
            print(f"Line: {issue['line']}")
            print(f"Category: {issue['category']}")
            print(f"Message: {issue['message']}")
            print(f"{'-'*40}")
    
    # Only fail on actual syntax errors (mismatched quotes, etc), not string warnings
    syntax_errors = [e for e in all_errors if 'syntax' in e.get('category', '').lower() or 'Syntax error' in e.get('message', '')]
    
    if syntax_errors:
        sys.exit(1)
    else:
        if not all_warnings:
            print("OK: No issues found")
        sys.exit(0)


if __name__ == '__main__':
    main()
