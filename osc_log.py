#!/usr/bin/python

import argparse
import subprocess
import re
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

# Import necessary osc modules and functions
import osc.conf
from osc.core import get_prj_results, makeurl, BUFSIZE, buildlog_strip_time, \
                     store_read_project, store_read_package, \
                     is_package_dir
from osc.oscerr import OscIOError
import osc.build # For calculate_build_root

def get_local_buildlog_path():
    """
    Finds and returns the path to the last local build log.
    Does not print the content, only finds the file path.
    """
    # Assuming this script runs in a package directory for store_read_project/package
    try:
        project = store_read_project('.')
        package = store_read_package('.')

    except Exception as e:
        print(f"Error: Not in a project/package directory or could not read project/package info: {e}", file=sys.stderr)
        print("Please run this script from your local osc checkout (project or package directory).", file=sys.stderr)
        sys.exit(1)

    apiurl = osc.conf.config['apiurl']
    apihost = urlsplit(apiurl)[1]

    buildroot = None
    try:
        buildroot = osc.build.calculate_build_root(apihost, project, package, 'standard', 'x86_64')
    except Exception as e:
        print(f"Error: Failed to determine local build root. Ensure a local build has been performed. Details: {e}", file=sys.stderr)
        sys.exit(1)

    logfile = os.path.join(buildroot, '.build.log')
    print(logfile)
    print(buildroot)
    if not os.path.isfile(logfile):
        raise OscIOError(None, f'Local build logfile \'{logfile}\' does not exist. Has a local build been performed?')

    return logfile

def display_buildlog_content(logfile_path, strip_time=False, offset=0):
    """
    Reads and prints the content of a given build log file.
    """
    print(f"\n--- Displaying local build log from: {logfile_path} ---")
    try:
        with open(logfile_path, 'rb') as f:
            f.seek(offset)
            data = f.read(BUFSIZE)
            while len(data):
                if strip_time:
                    # FIXME from original code: this is not working when the time is split between 2 chunks
                    data = buildlog_strip_time(data)
                sys.stdout.buffer.write(data)
                data = f.read(BUFSIZE)
    except Exception as e:
        print(f"Error reading local build log: {e}", file=sys.stderr)
        sys.exit(1)
    print("\n--- End of local build log ---")


def main():
    # Load osc configuration
    osc.conf.get_config()
    apiurl = osc.conf.config['apiurl']

    # Argument parser
    parser = argparse.ArgumentParser(description='Run logdetective on all failed OBS builds or process last local buildlog.')
    
    # New argument for local log
    parser.add_argument('--local-log', action='store_true',
                        help='Process the log of the newest last local build.')
    parser.add_argument('--strip-time', action='store_true',
                        help='(For --local-log) Remove timestamps from the local build log output when displaying.')
    parser.add_argument('--offset', type=int, default=0,
                        help='(For --local-log) Start reading the local build log from a specific byte offset when displaying.')
    parser.add_argument('--no-display', action='store_true',
                        help='(For --local-log) Do not display the local log content to stdout; just feed it to logdetective.')

    # Existing arguments for OBS builds
    parser.add_argument('--project', help='Project name (e.g. openSUSE:Factory)')
    parser.add_argument('--package', help='Exact package name to run (e.g. leancrypto)')
    parser.add_argument('--arch', nargs='*', help='List of architectures (e.g. x86_64)')
    parser.add_argument('--show_excluded', action='store_true', help='Include excluded packages')

    args = parser.parse_args()

    # Determine which mode to run in
    if args.local_log:
        # Check for mutually exclusive arguments with OBS functionality
        if args.project or args.package or args.arch or args.show_excluded:
            parser.error("--local-log cannot be used with --project, --package, --arch, or --show_excluded.")
        
        try:
            logfile_path = get_local_buildlog_path()
            print(f"Found local build log: {logfile_path}")

            # Display log content if not --no-display
            if not args.no_display:
                display_buildlog_content(logfile_path, strip_time=args.strip_time, offset=args.offset)

            print(f"\n🚀 Feeding local build log to logdetective: {logfile_path}")
            try:
                subprocess.run(['logdetective', logfile_path], check=True)
            except subprocess.CalledProcessError as e:
                print(f"❌ logdetective failed for local build log ({logfile_path}): {e}", file=sys.stderr)
            except FileNotFoundError:
                print(f"❌ Error: 'logdetective' command not found. Please ensure it's installed and in your PATH.", file=sys.stderr)
                print(f"   (Failed to process local log: {logfile_path})", file=sys.stderr)
            
        except OscIOError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while processing local log: {e}", file=sys.stderr)
            sys.exit(1)
            
        return # Exit after processing local log

    # --- Original script logic for failed OBS builds continues below ---
    
    # Ensure --project is provided if not using --local-log
    if not args.project:
        parser.error("--project is required unless --local-log is used.")

    # Convert --package to exact match regex
    name_pattern = re.compile(f'^{re.escape(args.package)}$') if args.package else None

    # Get results in brief format
    results = get_prj_results(
        apiurl=apiurl,
        prj=args.project,
        status_filter='failed',
        name_filter=None,  # We'll filter ourselves
        arch=args.arch,
        repo=['standard'],
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
            continue  # skip malformed lines

        package, repo, arch, status = parts

        if name_pattern and not name_pattern.fullmatch(package):
            continue

        if status != 'failed':
            continue

        found = True
        log_url = makeurl(apiurl, ['public', 'build', args.project, repo, arch, package, '_log'])
        print(f"\n🔍 Running logdetective for {package} ({repo}/{arch})...")
        try:
            subprocess.run(['logdetective', log_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for {package}: {e}")
        except FileNotFoundError:
            print(f"❌ Error: 'logdetective' command not found. Please ensure it's installed and in your PATH.", file=sys.stderr)
            print(f"   (Failed for {package}: {log_url})", file=sys.stderr)

    if not found:
        print("✅ No matching failed packages found.")

if __name__ == '__main__':
    main()

'''
import os
import sys
import re
import subprocess
from urllib.parse import urlsplit
from osc.core import get_prj_results, makeurl, BUFSIZE, buildlog_strip_time
from osc import conf
from osc.cmdln import option
from osc.core import store_read_project, store_read_package
from osc.oscerr import OscIOError
import osc.build

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
def do_logs(self, subcmd, opts, project):
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

        print(f"\n🚀 Feeding local build log to logdetective: {logfile}")
        try:
            subprocess.run(['logdetective', logfile], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for local log: {e}", file=sys.stderr)
        except FileNotFoundError:
            print(f"❌ 'logdetective' not found in PATH.", file=sys.stderr)
        return

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
            subprocess.run(['logdetective', log_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for {package}: {e}")
        except FileNotFoundError:
            print(f"❌ 'logdetective' not found in PATH.", file=sys.stderr)
            print(f"   (Failed for {package}: {log_url})", file=sys.stderr)

    if not found:
        print("✅ No matching failed packages found.")

'''