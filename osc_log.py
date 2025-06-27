#!/usr/bin/python

import argparse
import subprocess
from osc.core import get_prj_results, makeurl
import osc.conf

def main():
    osc.conf.get_config()
    apiurl = osc.conf.config['apiurl']

    parser = argparse.ArgumentParser(description='Run logdetective on all failed OBS builds.')
    parser.add_argument('--project', required=True, help='Project name (e.g. openSUSE:Factory)')

    args = parser.parse_args()

    results = get_prj_results(
        apiurl=apiurl,
        prj=args.project,
        status_filter='failed',
        repo=['standard'],
        csv=False,
        brief=True,
    )

    for line in results:
        parts = line.strip().split()
        if len(parts) != 4:
            continue  # skip malformed lines
        package, repo, arch, status = parts
        if status != 'failed':
            continue

        log_url = makeurl(apiurl, ['public','build', args.project, repo, arch, package, '_log'])
        print(f"\n🔍 Running logdetective for {package} ({repo}/{arch})...")
        try:
            subprocess.run(['logdetective', log_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for {package}: {e}")

if __name__ == '__main__':
    main()



'''
import subprocess
from osc.core import get_prj_results, makeurl
from osc import conf
from osc.cmdln import option

@option('--arch', metavar='ARCH', default='x86_64',
        help='Architecture to filter on (default: x86_64)')
@option('--repo', metavar='REPO', default='standard',
        help='Repository to filter on (default: standard)')
@option('--name-filter', metavar='REGEX',
        help='Regex to filter package names')
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

    results = get_prj_results(
        apiurl=apiurl,
        prj=project,
        status_filter='failed',
        repo=[opts.repo],
        arch=[opts.arch],
        name_filter=opts.name_filter,
        csv=False,
        brief=True,
    )

    for line in results:
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        package, repo, arch, status = parts
        if status != 'failed':
            continue

        log_url = makeurl(apiurl, ['public','build', project, repo, arch, package, '_log'])

        print(f"\n🔍 Running logdetective for {package} ({repo}/{arch})...")
        try:
            subprocess.run(['logdetective', log_url], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ logdetective failed for {package}: {e}")

'''