from helper.r53_sqlite_database import R53SQLDatabase
from helper.r53_aws_client import R53AWSClient
import argparse

DEBUG = True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a simple database of Route53 records')
    parser.add_argument('--access-key-id', '-a', dest='access_key_id', required=False, default=None, help='AWS Access Key Id')
    parser.add_argument('--secret-access-key', '-k', dest='secret_access_key', required=False, default=None, help='AWS Secret Access Key')
    parser.add_argument('--table', '-t', dest='table_name', required=False, default='records', help='Table name in the database')
    parser.add_argument('--hosted-zone-id', '-z', dest='hosted_zone_id', required=True, help='Route53 hosted zone ID')
    args = parser.parse_args()

    if DEBUG:
        print("Access key: {0}\nSecret key: {1}\nHosted zone id: {2}\nTable Name: {3}".format(args.access_key_id, args.secret_access_key, args.hosted_zone_id, args.table_name))

    table_name = args.table_name
    table_name_to_del = "{0}_to_del".format(table_name)

    # Create all connection objects
    r53 = R53AWSClient(args.hosted_zone_id, aws_access_key_id=args.access_key_id, aws_secret_access_key=args.secret_access_key)
    r53_db = R53SQLDatabase(args.hosted_zone_id)# Get the records that needs to be deleted

    # Get the records that needs to be deleted
    query = "SELECT name, value, type, ttl, set_id, weight from {table_name};".format(table_name=table_name_to_del)
    all_records_to_delete = r53_db.execute_query(query)
    deleted_records = []
    failed_to_del = []

    for name, value, rtype, ttl, set_id, weight in all_records_to_delete:
        set_id = set_id if set_id != 'null' else None
        if r53.delete_record_set(name, rtype, value, ttl, set_id, weight):
            deleted_records.append((name, rtype, value, ttl))
        else:
            failed_to_del.append((name, rtype, value, ttl))

    if DEBUG:
        print('DELETED RECORDS')
        print('===============')
        for name, rtype, value, ttl in deleted_records:
            print("{0} {1} {2}".format(name, rtype, value))

        print("FAILED TO DELETE")
        print('=================')
        for name, rtype, value, ttl in failed_to_del:
            print("{0} {1} {2}".format(name, rtype, value))

    r53_db.close_connection()
