import os
import sys
import re
import subprocess
import requests
import json
import textwrap

from urllib.parse import urlsplit
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
        self.add_argument("--strip-time", action="store_true", help="(For --local-log) Remove timestamps from the local build log output when displaying")
        self.add_argument("--offset", type=int, default=0, help="(For --local-log) Start reading the local build log from a specific byte offset when displaying")
        self.add_argument("-r", "--remote", action="store_true", help="Use LogDetective remote API instead of requiring the CLI tool")
        self.add_argument("-a", "--all", action="store_true", help="Look for all packages failing in a project")

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
        try:
            subprocess.run(["logdetective", logfile], check=True)
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
                logfile = fp.name
                f.seek(offset)
                data = f.read(BUFSIZE)
                while data:
                    if strip_time:
                        data = buildlog_strip_time(data)
                    fp.write(data)
                    data = f.read(BUFSIZE)
        except Exception as e:
            print(f"Error reading local build log: {e}", file=sys.stderr)
            sys.exit(1)

        return logfile

    def do_local_log(self, args):
        project = args.project or store_read_project(".")
        package = args.package or store_read_package(".")

        logfile, data = self.get_local_log(project, package, args.repo, args.arch, args.offset, args.strip_time)
        print(f"🚀 Analyzing local build log: {logfile}")
        if args.remote:
            # TODO: upload the log somewhwere to use log detective
            # self.run_log_detective_remote(logfile)
            print(f"Can't use remote log-detective with local log", file=sys.stderr)
        else:
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
        print(f"🔍 Running logdetective for {package} ({repo}/{arch})...")
        print(f"Log url: {log_url}")

        if args.remote:
            self.run_log_detective_remote(log_url)
        else:
            self.run_log_detective(log_url)

    def get_log_url(self, project, package, repo, arch):
        return makeurl(self.apiurl, ["public", "build", project, repo, arch, package, "_log"])
