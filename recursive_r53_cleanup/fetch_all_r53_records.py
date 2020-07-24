from helper.r53_sqlite_database import R53SQLDatabase
from helper.r53_aws_client import R53AWSClient
import argparse

DEBUG = False

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
    r53_db = R53SQLDatabase(args.hosted_zone_id)

    # Fetch all resource records for the zone
    r53.get_all_resource_records()

    r53_db.initialize_database() # Create records table

    # Populate resource records database
    r53_db.upload_resource_records(r53.resource_records)
    r53_db.close_connection()
