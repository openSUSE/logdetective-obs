#!/usr/bin/python3

import os
import subprocess
import requests
import argparse
import json
import urllib.parse

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
        "-p",
        "--package",
        help="Specific package name to check within the project (e.g., leancrypto)",
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
    parser.add_argument("--contribute-log", action="store_true",
                        help="Enable contributing logs to LogDetective")
    parser.add_argument("--log-url", type=str, help="URL to the build log")
    parser.add_argument("--log-path", type=str, help="Path to the local log file")
    parser.add_argument("--fail-reason", type=str, help="Reason for build failure")
    parser.add_argument("--how-to-fix", type=str, help="How to fix the build issue")
    return parser.parse_args()

def get_failed_builds(project_or_package_path):
    """
    Retrieves a list of failed builds for a given project or a specific package within a project.
    Args:
        project_or_package_path (str): The OBS project name or a combined project/package path
                                       (e.g., "openSUSE:Factory" or "openSUSE:Factory/leancrypto").
    Returns:
        list: A list of strings, where each string represents a failed build entry.
              Returns an empty list if no failures are found or an error occurs.
    """
    try:
        print(f"Running 'osc results -f {project_or_package_path}'...")
        result = subprocess.run(
            ["osc", "results", "-f", project_or_package_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        # The original code had a print statement after return, which is unreachable.
        # Moving the print statement here to show the results before returning.
        if result.stdout.strip():
            print(f"The failed builds are:\n{result.stdout.strip()}")
        else:
            print("No failed builds found by osc.")
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running osc: {e.stderr}")
        return []

def parse_build_failure(line: str, project: str, is_package_specific_query: bool):
    """
    Parses a line from the 'osc results' output to extract build details and construct a log URL.
    Args:
        line (str): A single line from the 'osc results' output.
        project (str): The base OBS project name (e.g., "openSUSE:Factory").
                       This is used to construct the public build URL.
        is_package_specific_query (bool): True if the osc command was run with a specific package,
                                          False otherwise. This helps in parsing the output format.
    Returns:
        tuple: A tuple containing the log URL (str) and the desired filename (str).
    Raises:
        ValueError: If the input line does not match the expected format.
    """
    parts = line.strip().split()

    if len(parts) < 4:
        raise ValueError("Expected format: '<package> <repository> <arch> failed' or '<repository> <arch> <package> failed'")

    if is_package_specific_query:
        # When querying for a specific package (e.g., osc results -f project/package)
        # The output format is: <repository> <arch> <package> failed
        # Example: "standard x86_64 leancrypto failed"
        repository, arch, package = parts[0], parts[1], parts[2]
    else:
        # When querying for a general project (e.g., osc results -f project)
        # The output format is: <package> <repository> <arch> failed
        # Example: "leancrypto standard x86_64 failed"
        package, repository, arch = parts[0], parts[1], parts[2]

    # Construct the URL using the base project name, not the combined project/package path
    url = f"https://build.opensuse.org/public/build/{project}/{repository}/{arch}/{package}/_log"
    filename = f"{package}_{repository}_{arch}.log"
    return url, filename

def download_log(url: str, filename: str, project: str):
    """
    Downloads a build log from the given URL and saves it to the appropriate directory.
    Args:
        url (str): The URL of the build log to download.
        filename (str): The desired filename for the downloaded log.
        project (str): The OBS project name, used for creating the log subdirectory.
    Returns:
        str or None: The path to the downloaded log file if successful, otherwise None.
    """
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
    """
    Runs the local 'logdetective' tool on a given log file.
    Args:
        log_path (str): The path to the log file to analyze.
        project (str): The OBS project name, used for creating the explanation subdirectory.
    Returns:
        str or None: The path to the analysis output file if successful, otherwise None.
    """
    project_explain_dir = os.path.join(EXPLAIN_DIR, project)
    os.makedirs(project_explain_dir, exist_ok=True)
    output_filename = os.path.basename(log_path).replace('.log', '.txt')
    output_path = os.path.join(project_explain_dir, output_filename)

    try:
        print(f"Running local log-detective on {log_path}...")
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
        print(f"❌ Error analyzing {log_path} with local log-detective: {e.stderr}")
        return None

def run_log_detective_remote(url, log_path, project):
    """
    Sends a log URL to the remote log-detective.com service for explanation.
    Args:
        url (str): The URL of the build log to explain.
        log_path (str): The local path of the log file (used for naming the output file).
        project (str): The OBS project name, used for creating the explanation subdirectory.
    Returns:
        str or None: The path to the analysis output file if successful, otherwise None.
    """
    project_explain_dir = os.path.join(EXPLAIN_DIR, project)
    os.makedirs(project_explain_dir, exist_ok=True)
    output_filename = os.path.basename(log_path).replace('.log', '.json')
    output_path = os.path.join(project_explain_dir, output_filename)

    print(f"🖥️ Sending log to Log Detective for remote explanation: {url}")
    try:
        data = requests.post("https://log-detective.com/frontend/explain/", json={"prompt": url})
        data.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data.json(), f, ensure_ascii=False, indent=4)
        print(f"🕵️ Analysis saved to {output_path}")
        return output_path
    except requests.exceptions.RequestException as e:
        print(f"❌ Error during remote log-detective analysis for {url}: {e}")
        return None

def build_payload(log_content, fail_reason, how_to_fix):
    return {
        "username": "testuser",  # Replace with actual username handling if needed
        "fail_reason": fail_reason,
        "how_to_fix": how_to_fix,
        "spec_file": {"name": "", "content": ""},
        "container_file": {"name": "", "content": ""},
        "logs": [
            {
                "name": "build.log",
                "content": log_content,
                "snippets": []
            }
        ]
    }

def submit_log_to_log_detective(url, fail_reason, how_to_fix):
    """
    Submits a log URL to the remote log-detective.com service for contribution
    Args:
        url (str): The URL of the build log to explain.
        fail_reason (str): The reason for the build failure.
        how_to_fix (str): The suggested fix for the build failure.
    """
    encoded_url = urllib.parse.quote(urllib.parse.quote(url, safe=''), safe='')
    # Fetch log content
    log_response = requests.get(url)
    if log_response.status_code != 200:
        print(f"Error fetching log file: {log_response.status_code}")
        return None

        log_content = log_response.text
    payload = build_payload(log_content, fail_reason, how_to_fix)
    response = requests.post(url, json=payload)
    return response.json()

def submit_local_log_to_log_detective(log_path, fail_reason, how_to_fix):
    """
    Submits a local log file to the remote log-detective.com service for contribution
    Args:
        log_path (str): The path to the local log file to submit.
        fail_reason (str): The reason for the build failure.
        how_to_fix (str): The suggested fix for the build failure.
    """
    if not os.path.exists(log_path):
        print(f"Error: Log file not found: {log_path}")
        return None
    
    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
    payload = build_payload(log_content, fail_reason, how_to_fix)
    response = requests.post(url, json=payload)
    return response.json()


# === Main Script ===
if __name__ == "__main__":
    args = parse_args()

    # The base project name for directory creation and URL construction
    base_project = args.project_name

    # The path used for 'osc results' command
    osc_project_path = args.project_name
    is_package_specific_query = bool(args.package) # Flag to indicate if a specific package was queried

    if args.contribute_log:
        if args.log_url and args.log_path:
            parser.error("Please use only one of --log-url or --log-path, not both.")
        if args.log_url:
            result = submit_log_to_log_detective(args.log_url, args.fail_reason, args.how_to_fix)
        elif args.log_path:
            result = submit_local_log_to_log_detective(args.log_path, args.fail_reason, args.how_to_fix)
        else:
            parser.error("Please provide either --log-url or --log-path with --contribute-log")

    if args.package:
        osc_project_path = f"{args.project_name}/{args.package}"
        print(f"🔍 Checking failed builds for package '{args.package}' in project '{args.project_name}' ({osc_project_path})...\n")
    else:
        print(f"🔍 Checking failed builds in project '{args.project_name}'...\n")

    failures = get_failed_builds(osc_project_path)

    if not failures or (len(failures) == 1 and not failures[0].strip()): # Handle case where osc returns empty string or just newline
        print("🎉 No failed builds found!")
    else:
        downloaded_files = []
        explained_files = []

        for line in failures:
            if not line.strip(): # Skip empty lines that might result from split()
                continue
            try:
                # Pass the is_package_specific_query flag to parse_build_failure
                url, filename = parse_build_failure(line, base_project, is_package_specific_query)
                log_path = download_log(url, filename, base_project)
                if log_path:
                    downloaded_files.append(log_path)
                    if args.explain:
                        if args.local:
                            explained_path = run_log_detective(log_path, base_project)
                        else:
                            explained_path = run_log_detective_remote(url, log_path, base_project)
                        if explained_path:
                            explained_files.append(explained_path)
            except ValueError as ve:
                print(f"⚠️ Skipping line: {line}\nReason: {ve}")
