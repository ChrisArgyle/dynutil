import getpass
import argparse
import sys
import os
import yaml

from dyn.tm.session import DynectSession
from dyn.tm.zones import Zone, get_all_zones

CUSTOMER_NAME = "customer_name"
USER_NAME = "user_name"
PASSWORD = "password"

def list_zone(zone_name):
    """
    Print names of a zone or all zones
    """
    try:
        if zone_name == None:
            zones = get_all_zones()
        else:
            zones = [Zone(zone_name)]
    except Exception as e:
        errordie("failed to get zone(s): {}".format(e))

    for zone in zones:
        print(zone.name)

def list_redirect(zone_name):
    """
    Print information about redirects in a zone
    """
    try:
        zone = Zone(zone_name)
        redirects = zone.get_all_httpredirect()
    except Exception as e:
        errordie("failed to get redirects for zone '{}': {}".format(zone_name, e))

    for redirect in redirects:
        print("{} -> {}".format(redirect._fqdn, redirect._url))

def errordie(message):
    """
    Print error message then quit with exit code 1
    """
    prog = os.path.basename(sys.argv[0])
    sys.stderr.write("{}: error: {}\n".format(prog, message))
    sys.exit(1)

def main():
    """
    Handle command line and do API requests
    """
    # parse command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-z', '--zone', default=None, help="zone to run query against")
    parser_required = parser.add_argument_group('required arguments')
    parser_required.add_argument('-c', '--creds-file',
            help="API credentials yaml file: contains {}, {} and {}".format( CUSTOMER_NAME,
                USER_NAME, PASSWORD))
    parser_required.add_argument('-l', '--list', choices=['zone', 'redirect', 'dsf'],
            help="type of items to list: zones, redirects or DSF (Traffic Director) services")

    args = parser.parse_args()

    # validate args
    if getattr(args, 'creds_file', None) == None:
        errordie("Please specify API credentials file")
    if getattr(args, 'list', None) == None:
        errordie("Please specify type of items to list")
    # redirect and dsf queries need a zone to run against
    if args.zone == None and (args.list == 'redirect' or args.list == 'dsf'):
        errordie("Please specify zone to run query against")

    # validate creds yaml file
    try:
        creds_file = open(args.creds_file, "r")
        creds = yaml.load(creds_file)
        creds_file.close()
    except Exception as e:
        errordie("Could not load API credentials yaml file: {}".format(e))

    if CUSTOMER_NAME not in creds:
        errordie("API credentials file does not specify '{}'".format(CUSTOMER_NAME))
    if USER_NAME not in creds:
        errordie("API credentials file does not specify '{}'".format(USER_NAME))
    if PASSWORD not in creds:
        errordie("API credentials file does not specify '{}'".format(PASSWORD))

    # create authenticated session
    try:
        session = DynectSession(creds[CUSTOMER_NAME], creds[USER_NAME], creds[PASSWORD])
    except Exception as e:
        errordie("could not authenticate: {}".format(e))

    # do query
    if args.list == 'zone':
        list_zone(args.zone)
    if args.list == 'redirect':
        list_redirect(args.zone)
    if args.list == 'dsf':
        # list DSF services
        pass

if __name__ == "__main__":
    main()