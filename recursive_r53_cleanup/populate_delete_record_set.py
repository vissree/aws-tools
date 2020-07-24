from helper.r53_sqlite_database import R53SQLDatabase
from helper.ec2_aws_client import EC2AWSClient
import argparse
import re

DEBUG = False

def add_all_parent_records(result, filter_type):
    name, value, rtype, ttl, weight, set_id = result
    output = ec2.search_instance(filter_type, value, verbose=True)

    if not output:
        query = "INSERT INTO {table_name} (name, value, type, ttl, weight, set_id) VALUES (?, ?, ?, ?, ?, ?);".format(table_name=table_name_to_del)
        if DEBUG:
            print("{0} : {1} : {2}".format(name, rtype, value))
        r53_db.execute_query(query, (name, value, rtype, ttl, weight, set_id))

        # Get all parent records
        records_to_delete = r53_db.get_parent_records(name)

        if records_to_delete:
            for name, value, rtype, ttl, weighted, weight, set_id in records_to_delete:
                if DEBUG:
                    print("{0} : {1} : {2}".format(name, rtype, value))
                r53_db.execute_query(query, (name, value, rtype, ttl, weight, set_id))

def add_if_orphan(result):
    name, value, rtype, ttl, weight, set_id = result

    # Check both example.domain.com and example.domain.com.
    t_name = value.strip('.')

    query = "SELECT COUNT(*) FROM {table_name} WHERE name=? OR name=?;".format(table_name=table_name).format(table_name=table_name)
    output = r53_db.execute_query(query, (t_name, t_name+'.'))
    count, = output[0]

    if not count:
        query = "INSERT INTO {table_name} (name, value, type, ttl, weight, set_id) VALUES (?, ?, ?, ?, ?, ?);".format(table_name=table_name_to_del)
        if DEBUG:
            print("{0} : {1} : {2}".format(name, rtype, value))
        r53_db.execute_query(query, (name, value, rtype, ttl, weight, set_id))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a simple database of Route53 records')
    parser.add_argument('--access-key-id', '-a', dest='access_key_id', required=False, default=None, help='AWS Access Key Id')
    parser.add_argument('--secret-access-key', '-k', dest='secret_access_key', required=False, default=None, help='AWS Secret Access Key')
    parser.add_argument('--table', '-t', dest='table_name', required=False, default='records', help='Table name in the database')
    parser.add_argument('--hosted-zone-id', '-z', dest='hosted_zone_id', required=True, help='Route53 hosted zone ID')
    parser.add_argument('--domain', '-d', dest='domain', required=True, help='Domain name')
    args = parser.parse_args()

    if DEBUG:
        print("Access key: {0}\nSecret key: {1}\nHosted zone id: {2}\nTable Name: {3}".format(args.access_key_id, args.secret_access_key, args.hosted_zone_id, args.table_name))

    table_name = args.table_name
    table_name_to_del = "{0}_to_del".format(table_name)

    # Create all connection objects
    r53_db = R53SQLDatabase(args.hosted_zone_id)
    ec2 = EC2AWSClient(aws_access_key_id=args.access_key_id, aws_secret_access_key=args.secret_access_key)

    r53_db.initialize_delete_db()  # Create records_to_del table

    query = "SELECT name, value, type, ttl, weight, set_id FROM {table_name} WHERE (type='A' OR type='CNAME') AND alias=0;".format(table_name=table_name)
    results = r53_db.execute_query(query)

    d_regex = r"\S*\." + re.escape(args.domain) + "\.?$"

    for result in results:
        name, value, rtype, ttl, weight, set_id = result

        if rtype == 'A':
            add_all_parent_records(result, 'ip')

        if rtype == 'CNAME':
            name, value, rtype, ttl, weight, set_id = result
            if re.search(r'ec2(-\d{1,3}){4}\.compute-1\.amazonaws\.com\.?', value):
                add_all_parent_records(result, 'cname')
            elif re.search(r'ip(-\d{1,3}){4}\.ec2\.internal\.?', value):
                add_all_parent_records(result, 'private_dns')
            elif re.search(d_regex, value):
                add_if_orphan(result)

    r53_db.close_connection()
