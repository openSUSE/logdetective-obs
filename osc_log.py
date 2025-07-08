#!/usr/bin/python

import argparse
import subprocess
from osc.core import get_prj_results, makeurl
import osc.conf
from osc.cmdln import option

def main():
    # Load osc configuration
    osc.conf.get_config()
    apiurl = osc.conf.config['apiurl']

    # Argument parser
    parser = argparse.ArgumentParser(description='Run logdetective on all failed OBS builds.')
    parser.add_argument('--project', required=True, help='Project name (e.g. openSUSE:Factory)')
    parser.add_argument('--package', help='Exact package name to run (e.g. leancrypto)')
    parser.add_argument('--arch', nargs='*', help='List of architectures (e.g. x86_64)')
    parser.add_argument('--show_excluded', action='store_true', help='Include excluded packages')

    args = parser.parse_args()

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

    if not found:
        print("✅ No matching failed packages found.")

if __name__ == '__main__':
    main()

'''
import subprocess
from osc.core import get_prj_results, makeurl
from osc import conf
from osc.cmdln import option

@option('--arch', metavar='ARCH', default='x86_64',
        help='Architecture to filter on (default: x86_64)')
@option('--package', metavar='REGEX',
        help='Regex to filter package names')
@option('--show_excluded', action='store_true',
        help='Include excluded packages')
def do_logs(self, subcmd, opts, project):
    """${cmd_name}: Run logdetective on all failed builds in a project

    This command finds all failed builds for the given PROJECT
    (in the given repository and architecture), and runs logdetective
    on each one by fetching the build log URL.

    ${cmd_usage}
    ${cmd_option_list}
    """

    conf.get_config()
    apiurl = conf.config['apiurl']

    # Convert --package to exact match regex
    name_pattern = re.compile(f'^{re.escape(args.package)}$') if args.package else None

    results = get_prj_results(
        apiurl=apiurl,
        prj=project,
        status_filter='failed',
        repo='standard',
        arch=[opts.arch],
        name_filter=None,
        csv=False,
        brief=True,
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

        log_url = makeurl(apiurl, ['public','build', project, repo, arch, package, '_log'])

        print(f"\n🔍 Running logdetective for {package} ({repo}/{arch})...")
        try:
            subprocess.run(['logdetective', log_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for {package}: {e}")

'''