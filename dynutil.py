import getpass
import argparse
import sys
import os
import yaml

from dyn.tm.session import DynectSession
from dyn.tm.zones import Zone, get_all_zones
from dyn.tm.services.dsf import get_all_dsf_services, get_all_records

CUSTOMER_NAME = "customer_name"
USER_NAME = "user_name"
PASSWORD = "password"


def list_dsf():
    """
    Print information about DSF services
    """
    try:
        services = get_all_dsf_services()
    except Exception as e:
        errordie("failed to get DSF services: {}".format(e))

    # build and output yaml document
    services_dict = []
    for service in services:
        service_dict = {
                'label': service.label,
                'nodes': service.nodes,
                'records': [],
            }

        # get records for this DSF service
        try:
            records = get_all_records(service)
        except Exception as e:
            errordie("failed to get records for DSF service '{}': {}".format(service.label, e))

        for record in records:
            service_dict['records'].append({ record.label: str(record) })

        services_dict.append({ 'trafficdirector': service_dict })

    print(yaml.dump(services_dict))


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

    # build list of redirects
    redirect_list = []
    for redirect in redirects:
        redirect_list.append({ redirect._fqdn: redirect._url })

    # bail out if there weren't any redirects
    if len(redirect_list) == 0:
        return

    # build and output yaml document
    redirect_dict = [{
            "zoneredirects": {
                "zone": zone_name,
                "redirects": redirect_list,
                },
            }]
    print(yaml.dump(redirect_dict, default_flow_style=False))

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
    if args.zone == None and (args.list == 'redirect'):
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
        list_dsf()

if __name__ == "__main__":
    main()
