import boto3
import botocore


class redis3Client():
    
    BUCKET_PREFIX = 'redis3'
    
    def __init__(self, cache_name: str, db: int = 0, **kwargs):
        """
        Store inside the class the s3 client, the cache name, the db number
        that will be used for all the ops. Note that you can pass credentials
        to boto3 at init phase using kwargs when instantiating the class.
        
        You can also override the default bucket prefix by passing a different
        bucket_prefix as kwarg.
        """
        self.s3_client = boto3.client('s3', **kwargs)
        self.bucket_name = self._get_bucket_from_cache_name(cache_name)
        self.db = db
        self.cache_name = cache_name
        if 'bucket_prefix' in kwargs and kwargs['bucket_prefix'] is not None:
            self.BUCKET_PREFIX = kwargs['bucket_prefix']
        #bucket_configuration = {
            #'Location': {
                #'Type': 'AvailabilityZone',
                #'Name': 'use1-az5' # this is us-east-1f Availability Zone.
            #},
            #'Bucket': {
                #'DataRedundancy': 'SingleAvailabilityZone',
                #'Type': 'Directory'  # this is the "express" option
            #}
       # }
        try:
            self.s3_client.create_bucket(
                Bucket=self.bucket_name,
                CreateBucketConfiguration={}
            )
        except botocore.exceptions.ClientError as e:
            print(e.response['Error']['Code'])
            print('Error Message: {}'.format(e.response['Error']['Message']))
            print("Bucket {} already exists. Using it as cache".format(cache_name))
        
        return None
    
    @property
    def bucket_name(self):
        """
        Return the name of the bucket used to back the cache
        """
        return self._bucket_name
    
    @bucket_name.setter
    def bucket_name(self, value):
        """
        Set the name of the bucket used to back the cache
        """
        self._bucket_name = value
    
    def _get_bucket_from_cache_name(self, cache_name: str):
        """
        Produce a distinct bucket name from the cache name supplied by the user
        """
        return '{}-{}'.format(self.BUCKET_PREFIX, cache_name)
    
    def _get_object_key_from_key_name(self, key: str):
        """
        Make sure that the key is prefixed with the db number as 
        a natural namespacing of the keys
        """
        return '{}/{}'.format(self.db, key)
    
    def set(self, key: str, value: str):
        """
        Redis SET equivalent: set a string value for a given string key
        
        Ref: https://redis.io/commands/set/
        """
        return None
    
    def get(self, key: str):
        """
        Redis GET equivalent: get a string value for a given string key
        
        Ref: https://redis.io/commands/get/
        """
        return None