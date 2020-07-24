import attr
import boto3
from botocore.exceptions import ClientError
from time import sleep

MAX_RETRIES = 30

# Decorators
def validate_conn(func):
    """
    Validate the connection object
    """
    def func_wrapper(self, *args, **kwargs):
        if self.conn:
            return func(self, *args, **kwargs)
        else:
            print("Invalid kinesis connection object")
            return None
    return func_wrapper

def handle_exceptions(func):
    """
    Catch common errors
    """
    def func_wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ClientError as e:
            print("CONNECTION ERROR.")
            print("{}".format(e))
            return None
        except self.conn.exceptions.LimitExceededException as e:
            # TODO - Catch self.conn.exceptions.LimitExceededException and 
            # implement an exponential backoff
            print("Please check stream limits")
            print("{}".format(e))
            return None
    return func_wrapper


@attr.s
class KinesisClient(object):
    name = attr.ib()
    aws_secret_access_key = attr.ib(default=None)
    aws_access_key_id = attr.ib(default=None)
    region = attr.ib(default='us-east-1')
    shard_details_dict = attr.ib(default=attr.Factory(dict))

    conn = attr.ib()

    @conn.default
    def init_conn(self):
        return boto3.client('kinesis', region_name=self.region,
                            aws_access_key_id=self.aws_access_key_id,
                            aws_secret_access_key=self.aws_secret_access_key,)

    @handle_exceptions
    @validate_conn
    def update_shard_count(self, target_count):
        """
        Split/Merge the current shards to make the number of 
        shards equal to the target_count.
        """
        status = self._get_stream_status()

        if status != 'ACTIVE':
            print("{} status is {}. Aborting update shard count".format(self.name, status))
            return False

        response = self.conn.update_shard_count(StreamName=self.name,
                                                TargetShardCount=target_count,
                                                ScalingType='UNIFORM_SCALING',)

        current_shard_count = response['CurrentShardCount']
        target_shard_count = response['TargetShardCount']

        print("Current Shard Count: {}\nTarget Shard Count: {}".format(current_shard_count, target_shard_count))

        print("Waiting for stream status to be active")
        retries = 0
        status = self._get_stream_status()

        while status != 'ACTIVE' and retries < MAX_RETRIES:
            retries += 1
            status = self._get_stream_status()
            print('.', end='')
            sleep(1)

        print("Number of tries: {}".format(retries))
        print("Shard count after update: {}".format(self.get_shard_count(refresh=True)))
        return True

    def is_a_valid_shard(self, shard_id):
        """
        Check if the given shard_id exists in shard_details_dict
        """
        return shard_id in self.shard_details_dict

    @validate_conn
    @handle_exceptions
    def get_shard_details(self):
        """
        Create a dictionary of shard id details.
        syntax: {shard_id: {starting_hash_key: key, ending_hash_key: key}}
        """

        response = self.conn.list_shards(StreamName=self.name,)
        shard_list = response['Shards']

        while True:
            if 'NextToken' in response:
                next_token = response['NextToken']
                try:
                    response = self.conn.list_shards(NextToken=next_token)
                    shard_list.append(response['Shards'])
                except self.conn.exceptions.ExpiredNextTokenException as e:
                    print("Invalid/Expired NextToken. Shard details incomplete")
                    print("{}".format(e))
                    break
            else:
                break

        print("Fetched {} shards".format(len(shard_list)))
        for el in shard_list:
            shard_id = el['ShardId']
            print("Adding shard {}".format(shard_id))
            starting_hash_key = el['HashKeyRange']['StartingHashKey']
            ending_hash_key = el['HashKeyRange']['EndingHashKey']

            self.shard_details_dict[shard_id] = {'starting_hash_key': starting_hash_key,
                                                    'ending_hash_key': ending_hash_key}

        return self.shard_details_dict

    def get_shard_count(self, refresh=False):
        """
        Return the number of shards in the stream.
        Update the shard_details_dict if refresh is True
        """

        if refresh:
            self.get_shard_details()

        return len(self.shard_details_dict)

    @handle_exceptions
    @validate_conn
    def split_shard(self, shard_id):
        """
        Split the shard and return True
        """

        # Check if the stream is in ACTIVE state
        status = self._get_stream_status()

        if status != 'ACTIVE':
            print("{} status is {}. Aborting shard split".format(self.name, status))
            return False

        if self.is_a_valid_shard(shard_id):
            hash_keys = self.shard_details_dict[shard_id]
        else:
            print("Shard {} not found in shard details".format(shard_id))
            return False

        starting_hash_key = str((int(hash_keys['starting_hash_key']) + int(hash_keys['ending_hash_key']))/2)

        self.conn.split_shard(StreamName=self.name,
                                ShardToSplit=shard_id,
                                NewStartingHashKey=starting_hash_key,)

        print("Waiting for stream status to be active")
        status = self._get_stream_status()
        retries = 0

        while status != 'ACTIVE' and retries < MAX_RETRIES:
            retries += 1
            status = self._get_stream_status()
            print('.', end='')
            sleep(1)

        return True

    @handle_exceptions
    @validate_conn
    def _get_stream_status(self):
        """
        Return stream status as string
        CREATING | DELETING | ACTIVE | UPDATING | *IN_USE*
        * IN_USE is not a standard aws status, but custom one returned
        in the event of ResourceInUseException.
        """
        try:
            response = self.conn.describe_stream(StreamName=self.name,
                                                Limit=1,)
            return response['StreamDescription']['StreamStatus']
        except self.conn.exceptions.ResourceInUseException:
            return 'IN_USE'
