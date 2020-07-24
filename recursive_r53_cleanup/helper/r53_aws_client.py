from botocore.exceptions import ClientError
from botocore.exceptions import ParamValidationError 
import boto3

DEBUG = False

class R53AWSClient(object):

    def __init__(self, hosted_zone_id, aws_access_key_id=None, aws_secret_access_key=None):
        try:
            self.rc = boto3.client('route53', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        except ClientError as e:
            print('Failed to connect to Route53')
            print("{error}".format(error=e))
            self.rc = None

        self.hosted_zone_id = hosted_zone_id
        self.resource_records = []

    def _get_remaining_record_set(self, next_record_name=None, next_record_type=None):
        """http://boto3.readthedocs.io/en/latest/reference/services/route53.html#Route53.Client.list_resource_record_sets"""
        if self.rc:
            try:
                if next_record_type and next_record_name:
                    response = self.rc.list_resource_record_sets(
                            HostedZoneId = self.hosted_zone_id,
                            StartRecordName = next_record_name,
                            StartRecordType = next_record_type,
                            MaxItems = '100'
                            )
                else:
                    response = self.rc.list_resource_record_sets(
                            HostedZoneId = self.hosted_zone_id,
                            MaxItems = '100'
                            )
            except ClientError as e:
                print('Failed to get resource record list')
                print("{error}".format(error=e))
                response = None

            except ParamValidationError as e:
                print('Invalid inputs to list resource records')
                print("{error}".format(error=e))
                response = None
        else:
            response = None

        return response

    def _format_resource_record_set(self, resource_record_set):
        for record in resource_record_set:
            if DEBUG:
                print(record)

            alias = 0 # Boolean represented as 0 and 1 in sqlite
            weighted = 0
            weight = -1
            ttl = 0
            name = record['Name']
            rtype = record['Type']
            values = []
            set_id = 'null'

            if 'Weight' in record.keys():
                weighted = 1
                weight = record['Weight']
                set_id = record['SetIdentifier']

            if 'AliasTarget' in record.keys():
                alias = 1
                values.append(record['AliasTarget']['DNSName'])
            else:
                ttl = record['TTL']
                for r in record['ResourceRecords']:
                    values.append(r['Value'].strip('"'))

            # Append data to resource_records
            for value in values:
                row = {
                    'alias': alias,
                    'weighted': weighted,
                    'weight': weight,
                    'name': name,
                    'value': value,
                    'ttl': ttl,
                    'type': rtype,
                    'set_id': set_id
                    }

                if DEBUG:
                    print(row)

                self.resource_records.append(row)

    def get_all_resource_records(self):
        is_truncated = True
        next_record_name = None
        next_record_type = None

        while is_truncated:
            if DEBUG:
                print("{0}, {1}, {2}".format(is_truncated, next_record_name, next_record_type))

            response = self._get_remaining_record_set(next_record_name, next_record_type)

            if response:
                self._format_resource_record_set(response['ResourceRecordSets'])
                is_truncated = response['IsTruncated']

                if is_truncated:
                    next_record_name = response['NextRecordName']
                    next_record_type = response['NextRecordType']
            else:
                is_truncated = False

    def delete_record_set(self, name, rtype, value, ttl, set_id=None, weight=None):
        """http://boto3.readthedocs.io/en/latest/reference/services/route53.html#Route53.Client.change_resource_record_sets"""
        resource_records = { 'Value': value }
        resource_record_set = { 'Name': name,
                                'Type': rtype,
                                'TTL': ttl,
                                'ResourceRecords': [resource_records],
                              }
        if set_id:
            resource_record_set['SetIdentifier'] = set_id
            resource_record_set['Weight'] = weight

        change_set = { 'Action': 'DELETE',
                       'ResourceRecordSet': resource_record_set
                     }
        if self.rc:
            try:
                self.rc.change_resource_record_sets(
                            HostedZoneId= self.hosted_zone_id,
                            ChangeBatch={
                                'Comment': 'Deleted part of clean up',
                                'Changes': [ change_set ]
                            })
                return True
            except ClientError as e:
                print("Failed to delete record {name}".format(name=name))
                print("{error}".format(error=e))
                return False
        else:
            return False
