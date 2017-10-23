import getpass
import argparse
import sys
import os
import yaml
import re

from dyn.tm.session import DynectSession
from dyn.tm.zones import Zone, get_all_zones
from dyn.tm.services.dsf import get_all_dsf_services, get_all_records

CUSTOMER_NAME = "customer_name"
USER_NAME = "user_name"
PASSWORD = "password"


def operate_record(operation, zone_name, node_name, value, record_type_arg):
    """
    Update address of a record
    """
    record_type_map = {
            "a": "A",
            "cname": "CNAME",
            "mx": "MX",
            }
    record_type = record_type_map[record_type_arg]

    try: 
        # get zone
        zone = Zone(zone_name)

        # update/delete
        if operation == "update" or operation == "delete":
            # if node_name is empty string then we're using the root node, use None
            if node_name == '':
                node = zone.get_node(None)
            else:
                node = zone.get_node(node_name)
            records = node.get_all_records_by_type(record_type)

            if not records:
                raise Exception("did not find {} records under {}".format(record_type, node.fqdn))

            if operation == "update":
                records[0].address = value
            elif operation == "delete":
                records[0].delete()

        #create
        elif operation == "create":
            if record_type == 'A':
                kwargs = {'address': value}
            elif record_type == 'CNAME':
                kwargs = {'cname': value}
            elif record_type == 'MX':
                kwargs = {'exchange': value}
            zone.add_record(node_name, record_type, **kwargs)

        # publish changes to zone
        zone.publish()

    except Exception as e:
        errordie("Failed to make record change: {}".format(e))


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

def list_record(zone_name, record_type_arg):
    """
    Print information about records in a zone
    """
    record_type_map = {
            "a": "a_records",
            "cname": "cname_records",
            "mx": "mx_records",
            }
    record_type = record_type_map[record_type_arg]

    try:
        zone = Zone(zone_name)
        records = zone.get_all_records()
    except Exception as e:
        errordie("failed to get records for zone '{}': {}".format(zone_name, e))

    # bail out if there weren't any records of the requested type
    if record_type not in records:
        return

    # build list of records
    record_list = []
    for record in records[record_type]:
        if record_type_arg == "a":
            value = record.address
        elif record_type_arg == "cname":
            value = record.cname
        elif record_type_arg == "mx":
            value = record.exchange
        record_list.append({ record.fqdn: value })


    # build and output yaml document
    recordset_dict = [{
            "recordset": {
                "type": record_type_arg,
                "zone": zone_name,
                "records": record_list,
                },
            }]
    print(yaml.safe_dump(recordset_dict, default_flow_style=False))

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
    parser.add_argument('-z', '--zone', help="zone to run query against")
    parser.add_argument('-n', '--node', help="node to operate on (use empty string for root node)")
    parser.add_argument('-v', '--value', default=None, help="value to assign")
    parser_required = parser.add_argument_group('required arguments')
    parser_required.add_argument('-o', '--operation',
            choices=['list', 'update', 'create', 'delete'],
            help="operation to perform: list, update, create, delete")
    parser_required.add_argument('-c', '--creds-file',
            help="API credentials yaml file: contains {}, {} and {}".format( CUSTOMER_NAME,
                USER_NAME, PASSWORD))
    parser_required.add_argument('-t', '--type',
            choices=['zone', 'mx', 'cname', 'a', 'redirect', 'dsf'],
            help="type of items to operate on: zones, A/MX/CNAME records, redirects, DSF (Traffic Director) services")

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
        if (args.zone == None and
                re.match(r'^(redirect|a|cname|mx)$', args.type)):
            errordie("Please specify zone to run query against")
    if args.operation == "update" or args.operation == "create" or args.operation == "delete":
        if getattr(args, 'node', None) == None:
            errordie("Please specify node to operate on")
        if args.operation == "update" or args.operation == "create":
            if getattr(args, 'value', None) == None:
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
        if args.type == 'a' or args.type == 'cname' or args.type == 'mx':
            list_record(args.zone, args.type)
        if args.type == 'redirect':
            list_redirect(args.zone)
        if args.type == 'dsf':
            list_dsf()
    elif args.operation == 'update' or args.operation == 'create' or args.operation == 'delete':
        operate_record(args.operation, args.zone, args.node, args.value, args.type)


if __name__ == "__main__":
    main()
