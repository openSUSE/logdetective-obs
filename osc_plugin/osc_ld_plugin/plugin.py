import os
import sys
import re
import subprocess
import requests
from urllib.parse import urlsplit
from osc.core import get_prj_results, makeurl, BUFSIZE, buildlog_strip_time
from osc import conf
from osc.cmdln import option
from osc.core import store_read_project, store_read_package
from osc.oscerr import OscIOError
import osc.build



def run_log_detective_remote(log_content, filename_hint):
    import requests
    import json

    EXPLAIN_DIR = ".explanations"
    os.makedirs(EXPLAIN_DIR, exist_ok=True)

    output_filename = os.path.basename(filename_hint).replace('.log', '.json')
    output_path = os.path.join(EXPLAIN_DIR, output_filename)

    print(f"🌐 Sending log to LogDetective API...")
    try:
        response = requests.post(
            "https://log-detective.com/frontend/explain/",
            json={"prompt": log_content}
        )
        response.raise_for_status()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(response.json(), f, ensure_ascii=False, indent=4)
        print(f"✅ Remote analysis saved to {output_path}")
    except Exception as e:
        print(f"❌ Remote analysis failed: {e}", file=sys.stderr)

@option('--arch', metavar='ARCH', default='x86_64',
        help='Architecture to filter on (default: x86_64)')
@option('--package', metavar='REGEX',
        help='Regex to filter package names')
@option('--show_excluded', action='store_true',
        help='Include excluded packages')
@option('--local-log', action='store_true',
        help='Process the log of the newest last local build.')
@option('--strip-time', action='store_true',
        help='(For --local-log) Remove timestamps from the local build log output when displaying.')
@option('--offset', type=int, default=0,
        help='(For --local-log) Start reading the local build log from a specific byte offset when displaying.')
@option('--no-display', action='store_true',
        help='(For --local-log) Do not display the local log content to stdout; just feed it to logdetective.')
@option('-r', '--remote', action='store_true',
        help='Use LogDetective remote API instead of requiring the CLI tool')
def do_ld(self, subcmd, opts, *args):
    """${cmd_name}: Run logdetective on failed OBS builds or local build log

    This command finds all failed builds for the given PROJECT
    (or processes the last local build), and runs logdetective
    on each one by fetching the build log or using the local log.

    ${cmd_usage}
    ${cmd_option_list}
    """
    conf.get_config()
    apiurl = conf.config['apiurl']

    if opts.local_log:
        try:
            project = store_read_project('.')
            package = store_read_package('.')
        except Exception as e:
            print(f"Error: Not in a project/package directory: {e}", file=sys.stderr)
            sys.exit(1)

        apihost = urlsplit(apiurl)[1]

        try:
            buildroot = osc.build.calculate_build_root(apihost, project, package, 'standard', 'x86_64')
        except Exception as e:
            print(f"Error: Failed to determine local build root: {e}", file=sys.stderr)
            sys.exit(1)

        logfile = os.path.join(buildroot, '.build.log')
        if not os.path.isfile(logfile):
            print(f"Error: Local build log not found: {logfile}", file=sys.stderr)
            sys.exit(1)

        print(f"Found local build log: {logfile}")

        if not opts.no_display:
            try:
                with open(logfile, 'rb') as f:
                    f.seek(opts.offset)
                    data = f.read(BUFSIZE)
                    while data:
                        if opts.strip_time:
                            data = buildlog_strip_time(data)
                        sys.stdout.buffer.write(data)
                        data = f.read(BUFSIZE)
            except Exception as e:
                print(f"Error reading local build log: {e}", file=sys.stderr)
                sys.exit(1)

        print(f"\n🚀 Analyzing local build log: {logfile}")
        try:
            with open(logfile, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
            if opts.remote:
                run_log_detective_remote(log_content, logfile)
            else:
                subprocess.run(['logdetective', logfile], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for local log: {e}", file=sys.stderr)
        except FileNotFoundError:
            if opts.remote:
                pass  # Already handled
            else:
                print(f"❌ 'logdetective' not found in PATH.", file=sys.stderr)
        return

    if not args:
       print("❌ Error: PROJECT is required unless --local-log is used.", file=sys.stderr)
       sys.exit(1)
    
    project= args[0]

    name_pattern = re.compile(f'^{re.escape(opts.package)}$') if opts.package else None

    results = get_prj_results(
        apiurl=apiurl,
        prj=project,
        status_filter='failed',
        repo='standard',
        arch=[opts.arch],
        name_filter=None,
        csv=False,
        brief=True,
        show_excluded=opts.show_excluded
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
        if status != 'failed':
            continue

        found = True
        log_url = makeurl(apiurl, ['public', 'build', project, repo, arch, package, '_log'])
        print(f"\n🔍 Running logdetective for {package} ({repo}/{arch})...")
        try:
            if opts.remote:
                print(f"📥 Downloading log from: {log_url}")
                import requests
                try:
                    response = requests.get(log_url)
                    response.raise_for_status()
                    run_log_detective_remote(response.text, f"{package}.log")
                except Exception as e:
                    print(f"❌ Failed to fetch or analyze log for {package}: {e}", file=sys.stderr)
            else:
                subprocess.run(['logdetective', log_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for {package}: {e}")
        except FileNotFoundError:
            print(f"❌ 'logdetective' not found in PATH.", file=sys.stderr)
            print(f"   (Failed for {package}: {log_url})", file=sys.stderr)

    if not found:
        print("✅ No matching failed packages found.")