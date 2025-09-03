import requests
import json
import sys
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


def get_org_repos(org, token=None):
    """
    获取组织下所有公开仓库列表（处理分页）。
    """
    repos = []
    page = 1
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            for repo_data in data:
                repos.append(repo_data["full_name"])  # e.g., "bytedance/repo-name"
            page += 1
            time.sleep(1)  # 延时避免速率限制
        except Exception as e:
            print(f"Error fetching repos for {org}: {e}")
            break
    return repos


def check_dep_in_repo(repo, dep_prefix, branch="main", headers=None, timeout=10):
    """
    检查仓库的 package.json 是否存在，以及是否包含指定依赖前缀。
    Returns: (repo, status)
    """
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/package.json"
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 404:
            return repo, "No package.json"
        response.raise_for_status()
        if response.status_code == 200:
            try:
                data = json.loads(response.text)
                deps = data.get("dependencies", {})
                dev_deps = data.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}
                for key in all_deps:
                    if key.startswith(dep_prefix):
                        return repo, f"Has {dep_prefix}"
                return repo, f"No {dep_prefix}"
            except json.JSONDecodeError:
                return repo, "Error"
    except requests.RequestException:
        return repo, "Error"


def main():
    parser = argparse.ArgumentParser(description="Check dependencies in GitHub organization repositories.")
    parser.add_argument("txt_file", help="Path to the txt file containing organization names (one per line).")
    parser.add_argument("--dep", default="ag-grid",
                        help="Dependency prefix to check (e.g., 'ag-grid' or 'lodash'). Default: ag-grid")
    parser.add_argument("--branch", default="main", help="Branch to check (e.g., 'main' or 'master'). Default: main")
    parser.add_argument("--max-workers", type=int, default=5, help="Number of concurrent threads. Default: 5")

    args = parser.parse_args()
    txt_file = args.txt_file
    dep_prefix = args.dep
    branch = args.branch
    max_workers = args.max_workers

    if not os.path.exists(txt_file):
        print(f"File not found: {txt_file}")
        sys.exit(1)

    # 读取组织列表
    with open(txt_file, "r") as f:
        orgs = [line.strip() for line in f if line.strip()]

    if not orgs:
        print("No organizations found in the file.")
        sys.exit(1)

    # 获取 GitHub Token（从环境变量）
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    # 对于每个组织，获取仓库并检查
    all_results = {}
    for org in orgs:
        print(f"\nFetching repositories for organization: {org}")
        repos = get_org_repos(org, token=token)
        if not repos:
            print(f"No repositories found for {org}")
            continue

        org_results = {}
        total_repos = len(repos)
        print(f"Found {total_repos} repositories. Checking for '{dep_prefix}'...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {executor.submit(check_dep_in_repo, repo, dep_prefix, branch, headers): repo for repo in
                              repos}
            for future in tqdm(as_completed(future_to_repo), total=total_repos, desc=f"Checking {org} repos"):
                repo, status = future.result()
                org_results[repo] = status
                time.sleep(0.5)  # 额外延时避免速率限制

        all_results[org] = org_results

    # 按组织和状态分组输出
    print(f"\nFinal Results for '{dep_prefix}' (grouped by organization and status):")
    for org, results in all_results.items():
        print(f"\nOrganization: {org}")
        status_groups = {
            f"Has {dep_prefix}": [],
            f"No {dep_prefix}": [],
            "No package.json": [],
            "Error": []
        }
        for repo, status in sorted(results.items()):
            status_groups[status].append(repo)

        for status, repos in status_groups.items():
            if repos:
                print(f"  {status}:")
                for repo in sorted(repos):
                    print(f"    {repo}")

    # 保存到 output.txt
    with open("output.txt", "w") as out:
        out.write(f"Final Results for '{dep_prefix}' (grouped by organization and status):\n")
        for org, results in all_results.items():
            out.write(f"\nOrganization: {org}\n")
            status_groups = {
                f"Has {dep_prefix}": [],
                f"No {dep_prefix}": [],
                "No package.json": [],
                "Error": []
            }
            for repo, status in sorted(results.items()):
                status_groups[status].append(repo)

            for status, repos in status_groups.items():
                if repos:
                    out.write(f"  {status}:\n")
                    for repo in sorted(repos):
                        out.write(f"    {repo}\n")
    print("\nResults saved to output.txt")


if __name__ == "__main__":
    main()