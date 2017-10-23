=======
dynutil
=======
Use this utility to manage DNS records (A, MX, CNAME, DSF, Redirect) on Dyn Managed DNS.  This utility can list, update, create and delete records.

How do I use it?
================
**First, create a credentials file**

  *For example*::

    $ cat ~/dyncreds.yml
    ---
    customer_name: examplecust
    user_name: exampleuser
    password: examplepass

**Next, issue a command**

* *Listing records*::
 
    $ python dynutil.py -c ~/dyncreds.yml -t a -o list -z example.com
    - recordset:
        records:
        - example.org: 1.1.1.1
        - www.example.com: 1.1.1.1
        type: a
        zone: example.com

* *Updating records*::

  $ python dynutil.py -c ~/dyncreds.yml -t a -o update -z example.com -n ns -v 4.4.2.2

* *Creating records*::

  $ python dynutil.py -c ~/dyncreds.yml -t a -o create -z example.com -n ns2 -v 8.8.8.8

* *Deleting records*::

  $ python dynutil.py -c ~/dyncreds.yml -t a -o delete -z example.com -n ns2

Detailed command usage info
===========================
  ::  

    usage: dynutil.py [-h] [-z ZONE] [-n NODE] [-v VALUE]
                      [-o {list,update,create,delete}] [-c CREDS_FILE]
                      [-t {zone,mx,cname,a,redirect,dsf}]
    
    optional arguments:
      -h, --help            show this help message and exit
      -z ZONE, --zone ZONE  zone to run query against
      -n NODE, --node NODE  node to operate on (use empty string for root node)
      -v VALUE, --value VALUE
                            value to assign
    
    required arguments:
      -o {list,update,create,delete}, --operation {list,update,create,delete}
                            operation to perform: list, update, create, delete
      -c CREDS_FILE, --creds-file CREDS_FILE
                            API credentials yaml file: contains customer_name,
                            user_name and password
      -t {zone,mx,cname,a,redirect,dsf}, --type {zone,mx,cname,a,redirect,dsf}
                            type of items to operate on: zones, A/MX/CNAME
                            records, redirects, DSF (Traffic Director) services

