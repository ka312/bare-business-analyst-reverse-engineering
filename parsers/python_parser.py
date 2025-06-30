import ast


def parse_python_code(code_string):
    """Parse Python code and extract summary information."""
    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        print(f"Syntax error in code: {e}")
        return {
            'functions': [],
            'classes': [],
            'imports': [],
            'variables': [],
            'error': str(e)
        }
    
    summary = {
        'functions': [],
        'classes': [],
        'imports': [],
        'variables': []
    }

    # Add parent links for better analysis
    add_parent_links(tree)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            try:
                start_line = node.lineno - 1
                # More robust end line detection
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    end_line = node.end_lineno
                else:
                    # Fallback: estimate end line by looking at the next node
                    end_line = start_line + 20  # Default fallback
                
                lines = code_string.splitlines()
                if start_line < len(lines):
                    if end_line > len(lines):
                        end_line = len(lines)
                    func_source = "\n".join(lines[start_line:end_line])
                    
                    summary['functions'].append({
                        'name': node.name,
                        'source': func_source,
                        'start_line': start_line + 1,
                        'end_line': end_line
                    })
            except Exception as e:
                print(f"Error processing function {node.name}: {e}")
                continue
                
        elif isinstance(node, ast.ClassDef):
            try:
                start_line = node.lineno - 1
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    end_line = node.end_lineno
                else:
                    end_line = start_line + 30  # Default fallback for classes
                
                lines = code_string.splitlines()
                if start_line < len(lines):
                    if end_line > len(lines):
                        end_line = len(lines)
                    class_source = "\n".join(lines[start_line:end_line])
                    
                    summary['classes'].append({
                        'name': node.name,
                        'source': class_source,
                        'start_line': start_line + 1,
                        'end_line': end_line
                    })
            except Exception as e:
                print(f"Error processing class {node.name}: {e}")
                continue
                
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            try:
                start_line = node.lineno - 1
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    end_line = node.end_lineno
                else:
                    end_line = start_line + 1
                
                lines = code_string.splitlines()
                if start_line < len(lines):
                    if end_line > len(lines):
                        end_line = len(lines)
                    import_source = "\n".join(lines[start_line:end_line])
                    summary['imports'].append(import_source.strip())
            except Exception as e:
                print(f"Error processing import: {e}")
                continue
                
        elif isinstance(node, ast.Assign):
            try:
                # Only top-level assignments (global variables)
                if is_top_level_node(node):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            summary['variables'].append(target.id)
            except Exception as e:
                print(f"Error processing assignment: {e}")
                continue

    return summary


def add_parent_links(tree):
    """Add parent links to AST nodes for better analysis."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def is_top_level_node(node):
    """Check if a node is at the top level (not inside a function or class)."""
    parent = getattr(node, 'parent', None)
    if parent is None:
        return True
    
    # Walk up the parent chain
    current = parent
    while current:
        if isinstance(current, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            return False
        current = getattr(current, 'parent', None)
    
    return True


def extract_functions(code_string):
    """Extract only functions from Python code."""
    if not code_string or not code_string.strip():
        return []
    
    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        print(f"Syntax error in code: {e}")
        return []
    
    functions = []
    lines = code_string.splitlines()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            try:
                start_line = node.lineno - 1
                
                # Better end line detection
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    end_line = node.end_lineno
                else:
                    # Fallback: find the end by looking for the next function/class or end of file
                    end_line = len(lines)
                    
                    # Look for next top-level definition
                    for next_node in ast.walk(tree):
                        if (isinstance(next_node, (ast.FunctionDef, ast.ClassDef)) and 
                            next_node != node and 
                            next_node.lineno > node.lineno):
                            end_line = min(end_line, next_node.lineno - 1)
                
                # Ensure we don't go beyond the file
                if start_line < len(lines):
                    if end_line > len(lines):
                        end_line = len(lines)
                    
                    func_source = "\n".join(lines[start_line:end_line])
                    
                    # Basic validation - ensure we captured the function properly
                    if func_source.strip().startswith(('def ', 'async def ')):
                        functions.append({
                            'name': node.name,
                            'source': func_source,
                            'start_line': start_line + 1,
                            'end_line': end_line
                        })
                    else:
                        # Fallback: just get a reasonable chunk
                        fallback_end = min(start_line + 50, len(lines))
                        func_source = "\n".join(lines[start_line:fallback_end])
                        functions.append({
                            'name': node.name,
                            'source': func_source,
                            'start_line': start_line + 1,
                            'end_line': fallback_end
                        })
                        
            except Exception as e:
                print(f"Error extracting function {getattr(node, 'name', 'unknown')}: {e}")
                continue

    return functions


def extract_classes(code_string):
    """Extract only classes from Python code."""
    if not code_string or not code_string.strip():
        return []
    
    try:
        tree = ast.parse(code_string)
    except SyntaxError as e:
        print(f"Syntax error in code: {e}")
        return []
    
    classes = []
    lines = code_string.splitlines()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            try:
                start_line = node.lineno - 1
                
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    end_line = node.end_lineno
                else:
                    # Fallback for classes
                    end_line = len(lines)
                    for next_node in ast.walk(tree):
                        if (isinstance(next_node, (ast.FunctionDef, ast.ClassDef)) and 
                            next_node != node and 
                            next_node.lineno > node.lineno):
                            end_line = min(end_line, next_node.lineno - 1)
                
                if start_line < len(lines):
                    if end_line > len(lines):
                        end_line = len(lines)
                    
                    class_source = "\n".join(lines[start_line:end_line])
                    
                    classes.append({
                        'name': node.name,
                        'source': class_source,
                        'start_line': start_line + 1,
                        'end_line': end_line
                    })
                    
            except Exception as e:
                print(f"Error extracting class {getattr(node, 'name', 'unknown')}: {e}")
                continue

    return classes


def get_function_calls(code_string):
    """Extract function calls from Python code."""
    try:
        tree = ast.parse(code_string)
    except SyntaxError:
        return []
    
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
    
    return list(set(calls))  # Remove duplicates