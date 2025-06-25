#!/usr/bin/python

import argparse
from osc.core import get_prj_results
import osc.conf

def main():
    osc.conf.get_config()
    apiurl = osc.conf.config['apiurl']

    parser = argparse.ArgumentParser(description='Fetch OBS project build results.')
    parser.add_argument('--project', required=True, help='Project name (e.g. openSUSE:Factory)')
    parser.add_argument('--name_filter', help='Regex to filter package names')
    parser.add_argument('--arch', nargs='*', help='List of architectures (e.g. x86_64)')
    parser.add_argument('--csv', action='store_true', help='Output in CSV format')
    parser.add_argument('--vertical', action='store_true', help='Vertical layout')
    parser.add_argument('--hide_legend', action='store_true', help='Hide legend')
    parser.add_argument('--show_excluded', action='store_true', help='Include excluded packages')

    args = parser.parse_args()

    results = get_prj_results(
        apiurl=apiurl,
        prj=args.project,
        status_filter='failed',
        name_filter=args.name_filter,
        arch=args.arch,
        repo='standard',
        csv=args.csv,
        brief=True,
        vertical=args.vertical,
        hide_legend=args.hide_legend,
        show_excluded=args.show_excluded
    )

    for line in results:
        print(line)

if __name__ == '__main__':
    main()




""" 
def do_failed_builds(self, subcmd, opts, project):
    """${cmd_name}: Show failed builds in 'standard' repo of a project

    This command lists all packages in a given project that failed to build
    in the 'standard' repository. It is filtered to only show failed results.

    ${cmd_usage}
    ${cmd_option_list}
    """

    results = get_prj_results(
        apiurl=conf.config['apiurl'],
        prj=project,
        status_filter='failed',
        repo=['standard'],
        arch=['x86_64'],       # Optional: remove this line if you want all arches
        brief=True,            # Clean one-line output per failure
    )

    for line in results:
        print(line)
 """