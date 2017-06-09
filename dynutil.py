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

def update_record(zone_name, record_name, value, record_type):
    """
    Update address of a record
    """
    try:
        zone = Zone(zone_name)
        node = zone.get_node(record_name)
        records = node.get_all_records_by_type(record_type)
    except Exception as e:
        errordie("failed to get {} record '{}.{}': {}".format(record_type,
            record_name, zone_name, e))

    try:
        records[0].address = value
        zone.publish()
    except Exception as e:
        errordie("failed to update {} record '{}.{}': {}".format(record_type,
            record_name, zone_name, e))


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
            errordie("failed to get records for DSF service '{}': {}".format(
                service.label, e))

        for record in records:
            service_dict['records'].append({ "label": record.label, "record": str(record) })

        services_dict.append({ 'trafficdirector': service_dict })

    print(yaml.safe_dump(services_dict))


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
            "webredirects": {
                "zone": zone_name,
                "redirects": redirect_list,
                },
            }]
    print(yaml.safe_dump(redirect_dict, default_flow_style=False))

def list_record(zone_name, record_type):
    """
    Print information about records in a zone
    """
    try:
        zone = Zone(zone_name)
        records = zone.get_all_records()
    except Exception as e:
        errordie("failed to get records for zone '{}': {}".format(zone_name, e))

    # build list of records
    record_list = []
    for record in records[record_type]:
        record_list.append("{} {}".format(record.fqdn, record.address))

    # bail out if there weren't any records
    if len(record_list) == 0:
        return

    # build and output yaml document
    record_dict = [{
            "records": {
                "zone": zone_name,
                "records": record_list,
                },
            }]
    print(yaml.safe_dump(record_dict, default_flow_style=False))

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
    parser.add_argument('-r', '--record', default=None, help="record to operate on")
    parser.add_argument('-v', '--value', default=None, help="value to assign")
    parser_required = parser.add_argument_group('required arguments')
    parser_required.add_argument('-o', '--operation',
            choices=['list', 'update', 'create', 'delete'],
            help="operation to perform: list, update, create, delete")
    parser_required.add_argument('-c', '--creds-file',
            help="API credentials yaml file: contains {}, {} and {}".format( CUSTOMER_NAME,
                USER_NAME, PASSWORD))
    parser_required.add_argument('-t', '--type', choices=['zone', 'arecord', 'redirect', 'dsf'],
            help="type of items to operate on: zones, A records, redirects, DSF (Traffic Director) services")

    args = parser.parse_args()

    # validate args
    if getattr(args, 'creds_file', None) == None:
        errordie("Please specify API credentials file")
    if getattr(args, 'type', None) == None:
        errordie("Please specify type of items to operate on")
    if getattr(args, 'operation', None) == None:
        errordie("Please specify operation to perform")
    if args.operation == "list":
        # record and redirect queries need a zone to run against
        if args.zone == None and (args.type == 'redirect' or args.type == 'arecord'):
            errordie("Please specify zone to run query against")
    if args.operation == "update" or args.operation == "create" or args.operation == "delete":
        if getattr(args, 'record', None) == None:
            errordie("Please specify record to operate on")
        if args.type != "arecord":
            errordie("Update/delete/create is only supported for A records")
        if ((args.operation == "update" or args.operation=="create") and
            getattr(args, 'value', None) == None):
            errordie("Please specify value to assign")

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
    if args.operation == 'list':
        if args.type == 'zone':
            list_zone(args.zone)
        if args.type == 'arecord':
            list_record(args.zone, 'a_records')
        if args.type == 'redirect':
            list_redirect(args.zone)
        if args.type == 'dsf':
            list_dsf()
    elif args.operation == 'update':
        update_record(args.zone, args.record, args.value, 'A')
    elif args.operation == 'create':
        errordie("Create not yet implemented")
    elif args.operation == 'delete':
        errordie("Delete not yet implemented")

if __name__ == "__main__":
    main()
