import boto3
import botocore
from time import time
import concurrent.futures


class redis3Client():
    
    BUCKET_PREFIX = 'redis3'
    
    def __init__(
        self, 
        cache_name: str, 
        db: int = 0, 
        availability_zone: str = 'use1-az5',
        verbose: bool = False,
        **kwargs
        ):
        """
        Store inside the class the s3 client, the cache name, the db number
        that will be used for all the ops. Note that you can pass credentials
        to boto3 at init phase using kwargs when instantiating the class.
        
        You can also override the default bucket prefix by passing a different
        bucket_prefix as kwarg.
        """
        init_start_time = time()
        # override the default bucket prefix if needed
        if 'bucket_prefix' in kwargs and kwargs['bucket_prefix'] is not None:
            self.BUCKET_PREFIX = kwargs['bucket_prefix']
        
        # setup basic class attributes and objects
        self._s3_client = boto3.client('s3', **kwargs)
        self.bucket_name = self._get_bucket_from_cache_name(
            availability_zone,
            cache_name
            )
        self.db = db
        self._cache_name = cache_name
        self._availability_zone = availability_zone
        self._verbose = verbose
        try:
            if verbose:
                print("Trying to create bucket {} in AZ {}".format(self.bucket_name, self._availability_zone))
            
            r = self._s3_client.create_bucket(
                Bucket=self.bucket_name,
                CreateBucketConfiguration={
                    'Location': {
                        'Type': 'AvailabilityZone',
                        'Name': self._availability_zone
                    },
                    'Bucket': {
                        'DataRedundancy': 'SingleAvailabilityZone',
                        'Type': 'Directory'
                    }
                },
            )
        except botocore.exceptions.ClientError as e:
            # if the bucket already exists, just use it
            if e.response['Error']['Code'] == "BucketAlreadyOwnedByYou":
                if self._verbose:
                    print("Bucket {} already exists. Using it as cache".format(self.bucket_name))
            else:
                raise e    
            
        if self._verbose:
            print("Init completed in {:.4f}s".format(time() - init_start_time))
            
        return None
    
    @property
    def db(self):
        """
        Return the db for the cache (i.e. this is a prefix in the bucket)
        """
        return self._db
    
    @db.setter
    def db(self, value):
        """
        Set the db for the cache (i.e. this is a prefix in the bucket)
        """
        try:
            self._db = int(value)
        except ValueError:
            print('db must be an integer or something that can be casted as such, got {}'.format(value))
            raise ValueError
    
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
    
    def _get_bucket_from_cache_name(self, availability_zone: str, cache_name: str):
        """
        Produce a distinct bucket name from the cache name supplied by the user.
        
        Note that we need to comply with the following naming rules:
        
        https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-bucket-naming-rules.html
        """
        return '{}-{}--{}--x-s3'.format(self.BUCKET_PREFIX, cache_name, availability_zone)
    
    def _get_object_key_from_key_name(self, key: str):
        """
        Make sure that the key is prefixed with the db number as 
        a natural namespacing of the keys
        """
        return '{}/{}'.format(self.db, key)
    
    def set(self, key: str, value: str):
        """
        Redis SET equivalent: set a string value for a given string key.
        
        Note that if you want to store a JSON object, you need to serialize it
        to a string first.
        
        Ref: https://redis.io/commands/set/
        """
        assert isinstance(value, str), "Expected value to be a string, got {}".format(type(value))
        _key = self._get_object_key_from_key_name(key)
        try:
            r = self._s3_client.put_object(
                Bucket=self.bucket_name,
                Key=_key,
                Body=value
                )
        except botocore.exceptions.ClientError as e:
            if self._verbose:
                print("!!! Failed operation: error code {}".format(e.response['Error']['Code']))
                
            raise e
        # if put_object succeeded, return True    
        return True
    
    def get(self, key: str):
        """
        Redis GET equivalent: get a string value for a given string key.
        
        It returns None if the key doesn't exist.
        
        Ref: https://redis.io/commands/get/
        
        """
        _key = self._get_object_key_from_key_name(key)
        try:
            r = self._s3_client.get_object(
                Bucket=self.bucket_name,
                Key=_key,
                )
            # if get_object succeeded, return the value
            if self._verbose:
                print("{} last modified on {}".format(_key, r['LastModified']))
            
            return r['Body'].read().decode('utf-8')
        except botocore.exceptions.ClientError as e:
            # this is where we handle the case where the key doesn't exist
            if e.response['Error']['Code'] == "NoSuchKey":
                return None
            if self._verbose:
                print("!!! Failed operation: error code {}".format(e.response['Error']['Code']))
                
            raise e
        
    def mset(self, keys: list, values: list):
        """
        Set multiple keys to multiple values. 
        Note that it's a threaded execution of set() for each key, so the return value
        can be True (success) or the command may fail if any error occurs.
        
        Note that this is not an atomic operation and there is now way to know
        which keys existed and which didn't.
        
        Ref: https://redis.io/commands/mset/
        """
                
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            for ctr, (k, v) in enumerate(zip(keys, values)):
                futures[executor.submit(self.set, key=k, value=v)] = ctr
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append((future.result(), futures[future]))
                except Exception as ex:
                    raise ex
                
        results, _ = zip(*sorted(results, key=lambda x: x[1]))
                
        return list(results)
        
    def mget(self, keys: list):
        """
        Return the values associated with the specified keys.
        Note that it's a threaded execution of get() for each key, so the return value
        can be a string (success), a None (no key found) or the command may fail if 
        any error occurs.
        
        Note that this is not an atomic operation.
        
        Ref: https://redis.io/commands/mget/
        """
        values = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {}
            for ctr, k in enumerate(keys):
                futures[executor.submit(self.get, key=k)] = ctr
            for future in concurrent.futures.as_completed(futures):
                try:
                    values.append((future.result(), futures[future]))
                except Exception as ex:
                    raise ex
                
        values, _ = zip(*sorted(values, key=lambda x: x[1]))
                
        return list(values)
    
    def keys(self, starts_with=None):
        """
        Return all the keys matching the specified pattern in the current db, modeled
        after the Redis "KEYS pattern" command (usual caveat on atomicity 
        applies).
        
        This is a generator function, so you can use it like:
        
        for key in my_client.keys():
            print(key)
        
        Ref: https://redis.io/commands/keys/
        """
        
        return self._get_matching_s3_keys(
            self.bucket_name, 
            # for express, only prefixes that end in a delimiter ( /) are supported.
            '{}/'.format(self.db), 
            starts_with
            )

    def _get_matching_s3_keys(self, bucket, prefix, pattern):
        """
        Code gently inspired by: https://alexwlchan.net/2017/listing-s3-keys/
        """
        kwargs = {'Bucket': bucket}
        if prefix:
            kwargs['Prefix'] = prefix
        while True:
            resp = self._s3_client.list_objects_v2(**kwargs)
            for obj in resp['Contents']:
                key = obj['Key']
                # we want to make sure keys start with the prefix (i.e. the db number)
                assert key.startswith(prefix)
                # if no pattern is specified or the key starts with the pattern
                if pattern is None or key.startswith(pattern):
                    yield key[len(prefix):]

            # The S3 API is paginated, so we pass the continuation token into the next response
            try:
                kwargs['ContinuationToken'] = resp['NextContinuationToken']
            except KeyError:
                break
            
    def delete(self, key: str):
        """
        Delete a key in the current database (a non-existent key gets ignored
        as the AWS boto client won't raise any error). We use "delete" to avoid confliucts
        with the Python keyword "del".

        Ref: https://redis.io/commands/del/
        """
        _key = self._get_object_key_from_key_name(key)
        r = self._s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=_key,
                )
            
        return True
