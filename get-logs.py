#!/usr/bin/python3

import os
import subprocess
import requests
import argparse
import json

LOGS_DIR = "logs"
EXPLAIN_DIR = "explain"

def parse_args():
    parser = argparse.ArgumentParser(description="Download and explain openSUSE build logs")
    parser.add_argument(
        "project_name",
        nargs="?",
        default="openSUSE:Factory",
        help="OBS project to download failing logs (e.g., openSUSE:Factory)",
    )
    parser.add_argument(
        "-e",
        "--explain",
        action="store_true",
        help="Try to explain the log using log-detective.com",
    )
    parser.add_argument(
    "-l",
    "--local",
    action="store_true",
    help="Try to explain the log using a local log-detective model"
    )
    return parser.parse_args()

def get_failed_builds(project_name):
    try:
        result = subprocess.run(
            ["osc", "results", "-f", project_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return result.stdout.strip().split('\n')
        print(f"The failed builds are: \n {result}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running osc: {e.stderr}")
        return []

def parse_build_failure(line: str, project: str):
    parts = line.strip().split()
    if len(parts) < 4:
        raise ValueError("Expected format: '<package> <repository> <arch> failed'")

    package, repository, arch = parts[:3]
    url = f"https://build.opensuse.org/public/build/{project}/{repository}/{arch}/{package}/_log"
    filename = f"{package}_{repository}_{arch}.log"
    return url, filename

def download_log(url: str, filename: str, project: str):
    project_logs_dir = os.path.join(LOGS_DIR, project)
    os.makedirs(project_logs_dir, exist_ok=True)
    path = os.path.join(project_logs_dir, filename)

    print(f"📥 Downloading: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(path, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"✅ Saved to {path}")
        return path
    else:
        print(f"❌ Failed: {response.status_code} - {url}")
        return None

def run_log_detective(log_path, project):
    project_explain_dir = os.path.join(EXPLAIN_DIR, project)
    os.makedirs(project_explain_dir, exist_ok=True)
    output_filename = os.path.basename(log_path).replace('.log', '.txt')
    output_path = os.path.join(project_explain_dir, output_filename)

    try:
        result = subprocess.run(
          ["logdetective", log_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)
        print(f"🕵️ Analysis saved to {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Error analyzing {log_path}: {e.stderr}")
        return None

def run_log_detective_remote(url, log_path, project):
    project_explain_dir = os.path.join(EXPLAIN_DIR, project)
    os.makedirs(project_explain_dir, exist_ok=True)
    output_filename = os.path.basename(log_path).replace('.log', '.json')
    output_path = os.path.join(project_explain_dir, output_filename)

    print(f"🖥️ Log Detective explain: {url}")
    data = requests.post("https://log-detective.com/frontend/explain/", json={"prompt": url})
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data.json(), f, ensure_ascii=False, indent=4)
    print(f"🕵️ Analysis saved to {output_path}")
    return output_path

# === Main Script ===
if __name__ == "__main__":
    args = parse_args()
    project = args.project_name
    print(f"🔍 Checking failed builds in {project}...\n")
    failures = get_failed_builds(project)

    if not failures:
        print("🎉 No failed builds found!")
    else:
        downloaded_files = []
        explained_files = []

        for line in failures:
            try:
                url, filename = parse_build_failure(line, project)
                log_path = download_log(url, filename, project)
                if log_path:
                    downloaded_files.append(log_path)
                    if args.explain:
                        if args.local:
                            explained_path = run_log_detective(log_path, project)
                        else:
                           explained_path = run_log_detective_remote(url, log_path, project)
                        if explained_path:
                            explained_files.append(explained_path)
            except ValueError as ve:
                print(f"⚠️ Skipping line: {line}\nReason: {ve}")
