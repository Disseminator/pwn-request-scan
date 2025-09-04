import os
import json
import argparse
from pathlib import Path

def check_package_json(file_path, dep_prefix="ag-grid"):
    """检查 package.json 是否包含 ag-grid 相关依赖"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for key in deps:
                if key.startswith(dep_prefix):
                    return True, f"Found {key} in {file_path}"
            return False, f"No {dep_prefix} in {file_path}"
    except (json.JSONDecodeError, FileNotFoundError):
        return False, f"Invalid or missing {file_path}"

def check_file_content(file_path, keywords=["ag-grid-community", "ag-grid-enterprise"]):
    """检查文件中是否包含 ag-grid 的 CDN 或 import 语句"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for keyword in keywords:
                if keyword in content:
                    return True, f"Found {keyword} in {file_path}"
            return False, f"No ag-grid reference in {file_path}"
    except (UnicodeDecodeError, FileNotFoundError):
        return False, f"Could not read {file_path}"

def scan_project_directory(project_dir, dep_prefix="ag-grid"):
    """扫描项目目录，检查 ag-grid 引入"""
    project_dir = Path(project_dir).resolve()
    results = []

    # 查找所有 package.json 文件
    for package_file in project_dir.rglob("package.json"):
        found, message = check_package_json(package_file, dep_prefix)
        results.append((package_file, found, message))

    # 查找 HTML 和 JS 文件中的 CDN 或 import
    for ext in ["*.html", "*.js", "*.jsx", "*.ts", "*.tsx"]:
        for file in project_dir.rglob(ext):
            found, message = check_file_content(file)
            results.append((file, found, message))

    return results

def main():
    parser = argparse.ArgumentParser(description="Check for ag-grid in a local project directory.")
    parser.add_argument("project_dir", help="Path to the project directory to scan")
    parser.add_argument("--dep", default="ag-grid", help="Dependency prefix to check (default: ag-grid)")
    args = parser.parse_args()

    project_dir = args.project_dir
    dep_prefix = args.dep

    if not os.path.exists(project_dir):
        print(f"Error: Directory {project_dir} does not exist")
        return

    print(f"Scanning {project_dir} for ag-grid usage...")
    results = scan_project_directory(project_dir, dep_prefix)

    # 输出结果
    found_any = False
    print("\nResults:")
    for file_path, found, message in results:
        if found:
            found_any = True
            print(f"[FOUND] {message}")
        else:
            print(f"[NOT FOUND] {message}")

    if not found_any:
        print("\nNo ag-grid usage found in the project.")
    else:
        print("\nWarning: ag-grid usage detected. Check for potential vulnerabilities (e.g., GHSL-2025-082).")

if __name__ == "__main__":
    main()