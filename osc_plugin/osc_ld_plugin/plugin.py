import os
import sys
import re
import subprocess
import requests
import json
import textwrap
import urllib.parse

from urllib.parse import urlsplit, quote
from osc.core import get_results, get_prj_results, makeurl, BUFSIZE, buildlog_strip_time
from osc import conf
from osc.cmdln import option
from osc.core import store_read_project, store_read_package
from osc.oscerr import OscIOError
import osc.build

import tempfile


from osc.commandline import OscCommand


class LogDetective(OscCommand):
    """
    LogDetective integration plugin: https://log-detective.com/
    """

    name = "ld"

    def init_arguments(self):
        self.add_argument("-p", "--project", help="The OBS project")
        self.add_argument("--package", help="Regex to filter package names")
        self.add_argument("--arch", default="x86_64", help="OBS build architecture")
        self.add_argument("--repo", default="standard", help="OBS build repository")
        self.add_argument("--show_excluded", action="store_true", help="Include excluded packages")
        self.add_argument("-l", "--local-log", action="store_true", help="Process the log of the newest last local build")
        self.add_argument("-r", "--remote", action="store_true", help="Use LogDetective remote API instead of requiring the CLI tool")
        self.add_argument("-a", "--all", action="store_true", help="Look for all packages failing in a project")
        self.add_argument("--strip-time", action="store_true", help="(For --local-log) Remove timestamps from the local build log output when displaying")
        self.add_argument("--offset", type=int, default=0, help="(For --local-log) Start reading the local build log from a specific byte offset when displaying")
        self.add_argument("-m", "--model", help="Select the model to use in Log Detective")

        self.add_argument("--submit-log", action="store_true", help="Submit the log to log-detective for contribution")
        self.add_argument("--fail-reason", help="(For --submit-log) The reason for the build failure")
        self.add_argument("--how-to-fix", help="(For --submit-log) Suggested fix for the build failure")


    def run(self, args):
        """
        ld: Run logdetective on failed OBS builds or local build log

        This command finds all failed builds for the given PROJECT
        (or processes the last local build), and runs logdetective
        on each one by fetching the build log or using the local log.
        """

        conf.get_config()
        self.apiurl = conf.config["apiurl"]
        self.apihost = urlsplit(self.apiurl)[1]
        self.args = args

        if args.local_log:
            self.do_local_log(args)
            return

        if args.all:
            self.do_remote_log_all(args)
            return

        self.do_remote_log(args)


    def run_log_detective(self, logfile):
        args = []
        if self.args.model:
            args = [self.args.model]
        try:
            subprocess.run(["logdetective", *args, logfile], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for local log: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(f"❌ 'logdetective' not found in PATH.", file=sys.stderr)

    def run_log_detective_remote(self, log_url):
        print(f"🌐 Sending log to LogDetective API...")
        response = requests.post(
            "https://log-detective.com/frontend/explain/",
            json={"prompt": log_url}
        )
        response.raise_for_status()
        explain = response.json()["explanation"]
        for line in explain.split("\n"):
            if not line:
                print("\n\n")
                continue
            print(textwrap.fill(line, width=80, drop_whitespace=True))

    def get_local_log(self, project, package, repo, arch, offset=0, strip_time=False):
        """
        Look for local build log and parses the whole text applying
        the offset and strip_time filters

        Return the path to a new tempfile with the log content
        """

        try:
            buildroot = osc.build.calculate_build_root(self.apihost, project, package, repo, arch)
        except Exception as e:
            print(f"Error: Failed to determine local build root: {e}", file=sys.stderr)
            sys.exit(1)

        logfile = os.path.join(buildroot, ".build.log")
        if not os.path.isfile(logfile):
            print(f"Error: Local build log not found: {logfile}", file=sys.stderr)
            sys.exit(1)

        print(f"Found local build log: {logfile}")
        try:
            with open(logfile, "rb") as f, tempfile.NamedTemporaryFile(delete=False) as fp:
                logfile_path = fp.name  # Use a distinct variable name
                f.seek(offset)
                data = f.read(BUFSIZE)
                while data:
                    if strip_time:
                        data = buildlog_strip_time(data)
                    fp.write(data)
                    data = f.read(BUFSIZE)
                fp.close()
        except Exception as e:
            print(f"Error reading local build log: {e}", file=sys.stderr)
            sys.exit(1)

        return logfile_path # Return the path of the temporary file

    def do_local_log(self, args):
        project = args.project or store_read_project(".")
        package = args.package or store_read_package(".")

        logfile = self.get_local_log(project, package, args.repo, args.arch, args.offset, args.strip_time)
        
        # Correctly implement the logic with an if/elif/else structure and add validation
        if args.submit_log:
            if not args.fail_reason or not args.how_to_fix:
                print("❌ Both --fail-reason and --how-to-fix are required for --submit-log.", file=sys.stderr)
                os.unlink(logfile) # Ensure cleanup
                return
            print(f"🚀 Submitting local build log to logdetective: {logfile}")
            self.submit_local_log(logfile, args.fail_reason, args.how_to_fix)
        
        elif args.remote:
            # TODO: upload the log somewhere to use log detective
            # self.run_log_detective_remote(logfile)
            print(f"Can't use remote log-detective with local log", file=sys.stderr)
        else:
            print(f"🚀 Analyzing local build log: {logfile}")
            self.run_log_detective(logfile)

        os.unlink(logfile)

    def do_remote_log_all(self, args):
        project = args.project or store_read_project(".")
        name_pattern = re.compile(f"^{re.escape(args.package)}$") if args.package else None

        results = get_prj_results(
            apiurl=self.apiurl,
            prj=project,
            status_filter="failed",
            repo=args.repo,
            arch=[args.arch],
            name_filter=None,
            csv=False,
            brief=True,
            show_excluded=args.show_excluded
        )

        if not results:
            print("✅ No failed builds found.")
            return

        found = False
        for line in results:
            parts = line.strip().split()
            if len(parts) != 4:
                continue
            package, repo, arch, status = parts
            if name_pattern and not name_pattern.fullmatch(package):
                continue
            if status != "failed":
                continue

            found = True
            log_url = self.get_log_url(project, package, repo, arch)
            print(f"🔍 Running logdetective for {package} ({repo}/{arch})...")

            if args.remote:
                self.run_log_detective_remote(log_url)
            else:
                self.run_log_detective(log_url)

        if not found:
            print("✅ No matching failed packages found.")

    def do_remote_log(self, args):
        project = args.project or store_read_project(".")
        package = args.package or store_read_package(".")
        repo, arch = args.repo, args.arch

        result = get_results(
            apiurl=self.apiurl,
            project=project,
            package=package,
            repository=repo,
            arch=[arch],
        )

        if not result or not result[0] or not "failed" in result[0]:
            print("✅ No failed builds found.")
            return

        log_url = self.get_log_url(project, package, repo, arch)
        print(f"Log url: {log_url}")
        
        # Move the submit log check to the top for clarity and to prevent running analysis
        if args.submit_log:
            if not args.fail_reason or not args.how_to_fix:
                print("❌ Both --fail-reason and --how-to-fix are required for --submit-log.", file=sys.stderr)
                return
            print(f"🚀 Submitting remote build log to logdetective: {log_url}")
            self.submit_remote_log(log_url, args.fail_reason, args.how_to_fix)
            return

        print(f"🔍 Running logdetective for {package} ({repo}/{arch})...")

        if args.remote:
            self.run_log_detective_remote(log_url)
        else:
            self.run_log_detective(log_url)

    def get_log_url(self, project, package, repo, arch):
        return makeurl(self.apiurl, ["public", "build", project, repo, arch, package, "_log"])

    def build_payload(self, log_content, fail_reason, how_to_fix):
        return {
            "username": "testuser",
            "fail_reason": fail_reason,
            "how_to_fix": how_to_fix,
            "container_file": {"name": "", "content": ""},
            "logs": [
                {
                    "name": "build.log",
                    "content": log_content,
                    "snippets": [
                        {
                            "start_index": 0,
                            "end_index": 0,
                            "user_comment": "string to test the snippet",
                            "text": "this is a sample test string"
                        }
                    ]
                }
            ]
        }

    def submit_remote_log(self, url, fail_reason, how_to_fix):
        encoded_url = urllib.parse.quote(urllib.parse.quote(url, safe=''), safe='')
        log_response = requests.get(url)
        if log_response.status_code != 200:
            print(f"Error fetching log file: {log_response.status_code}")
            return None

        log_content = log_response.text
        payload = self.build_payload(log_content, fail_reason, how_to_fix)
        try:
            response = requests.post(
                f"https://log-detective.com/frontend/contribute/url/{encoded_url}",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            print("Logfile submitted successfully ✅")
        except requests.RequestException as e:
            print(f"❌ Error submitting log: {e}")

    def submit_local_log(self, log_path, fail_reason, how_to_fix):
        if not os.path.exists(log_path):
            print(f"Error: Log file not found: {log_path}")
            return None

        with open(log_path, "r", encoding="utf-8") as f:
            log_content = f.read()
        payload = self.build_payload(log_content, fail_reason, how_to_fix)

        try:
            response = requests.post(
                "https://log-detective.com/frontend/contribute/upload",
                json=payload,
                timeout=60
            )
            response.raise_for_status()  # raises error for 4xx/5xx
            print("Logfile submitted successfully ✅")
        except requests.RequestException as e:
            print(f"❌ Error submitting log: {e}")