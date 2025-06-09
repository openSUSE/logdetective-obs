import os
import subprocess
import requests
import argparse

LOGS_DIR = "logs"
EXPLAIN_DIR = "explain"def get_project_name():
    suffix = input("Enter openSUSE project suffix (e.g., Factory): ").strip()
    return f"openSUSE:{suffix}"

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

def download_log(url: str, filename: str):
    os.makedirs(LOGS_DIR, exist_ok=True)
    path = os.path.join(LOGS_DIR, filename)
    
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

def run_log_detective(log_path):
    os.makedirs(EXPLAIN_DIR, exist_ok=True)
    output_filename = os.path.basename(log_path).replace('.log', '.txt')
    output_path = os.path.join(EXPLAIN_DIR, output_filename)
    
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

def git_commit(files, message="Add new build logs and explanations"):
    try:
        subprocess.run(["git", "add"] + files, check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Changes pushed to Git")
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")

# === Main Script ===
if __name__ == "__main__":
    project = get_project_name()
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
                log_path = download_log(url, filename)
                if log_path:
                    downloaded_files.append(log_path)
                    explained_path = run_log_detective(log_path)
                    if explained_path:
                        explained_files.append(explained_path)
            except ValueError as ve:
                print(f"⚠️ Skipping line: {line}\nReason: {ve}")

        # Commit both logs and explanations
        if downloaded_files or explained_files:
            git_commit(downloaded_files + explained_files)
