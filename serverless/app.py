"""

Simple lambda function to test redis3 and s3 performance when running compute next to storage.
All of this is hacky / manual / one-off testing, but it's a start to get a more realistic
sense of potential performance gains.

Note that for this to work you need to make the AWS lambda role (created by serverless)
aware of the bucket that is underlying the redis3 cache.

S3 express policies are a drag, so beware:

https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-security-iam-identity-policies.html

Note that to make it work, I had to actually copy the ARN for the bucket from the s3 console.

Finally the AWS lambda role should also have access to buckets with the pattern used by normal
s3 client to do the comparison, e.g.:

bucket_name = "redis3-test-{}".format(uuid.uuid4())

Note 2: we included a redis client in the lambda function to test the performance of 
actual Redis on Redis Lab in us-east-1: this is done for the purpose of the comparison
in the Medium blog post, so treat the code as a throw-away example (you will need to provide your own
credentials for Redis and spin up your own free Redis instance on Redis Labs).

"""


import time
import uuid
import boto3
import json
from redis3 import redis3Client
import redis
from statistics import mean, median


# default number of keys to try to set / get
DEFAULT_K = 50
# check that the version of boto3 supports the s3 express feature
print("Boto3 version: {}".format(boto3.__version__))


def wrap_response(body):
    """
    Just make sure the response is in the right format given this is a HTTP GET
    """
    return {
        "statusCode": 200,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json"
        }
    }


def run_redis_tests(
    key_list: list,
    val_list: list
):
    my_client = redis.Redis(
        host='redis-xxx.cloud.redislabs.com', 
        password='mypwd',
        port=14665, 
        db=0)
    
    set_times = []
    for k, v in zip(key_list, val_list):
        s_set_time = time.time()
        r = my_client.set(k, v)
        set_times.append(time.time() - s_set_time)
        
    get_times = []
    for k, v in zip(key_list, val_list):
        s_get_time = time.time()
        r = my_client.get(k)
        get_times.append(time.time() - s_get_time) 
    
    return get_times, set_times
    

def run_redis3_many_keys_tests(
    cache_name: str,
    key_list: list,
    val_list: list
):
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=False)
    
    set_times = []
    get_times = []
    # do it few times to get a sense of the performance
    for _ in range(3):
        s_set_time = time.time()
        r = my_client.mset(key_list, val_list)
        set_times.append(time.time() - s_set_time)
        s_get_time = time.time()
        r = my_client.mget(key_list)
        get_times.append(time.time() - s_get_time)
        assert r == val_list, "Expected {}, got {}".format(val_list, r)
    
    return get_times, set_times


def run_redis3_tests(
    cache_name: str,
    key_list: list,
    val_list: list
):
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=False)
    
    set_times = []
    for k, v in zip(key_list, val_list):
        s_set_time = time.time()
        r = my_client.set(k, v)
        set_times.append(time.time() - s_set_time)
        
    get_times = []
    for k, v in zip(key_list, val_list):
        s_get_time = time.time()
        r = my_client.get(k)
        get_times.append(time.time() - s_get_time)
        assert r == v, "Expected {}, got {}".format(v, r)    
    
    return get_times, set_times


def run_s3_tests(
    key_list: list,
    val_list: list
):
    # we assume the lambda role has access to buckets with the name redis3-test-*
    s3_client = boto3.client('s3')
    # create a bucket with a temp name
    bucket_name = "redis3-test-{}".format(uuid.uuid4())
    s3_client.create_bucket(Bucket=bucket_name)
    # set all keys + values
    set_times = []
    for i in range(len(key_list)):
        start = time.time()
        s3_client.put_object(Bucket=bucket_name, Key=key_list[i], Body=val_list[i])
        set_times.append(time.time() - start)
    # read them back
    get_times = []
    for i in range(len(key_list)):
        start = time.time()
        obj = s3_client.get_object(Bucket=bucket_name, Key=key_list[i])
        v = obj['Body'].read().decode('utf-8')
        get_times.append(time.time() - start)
        assert v == val_list[i], "Expected {}, got {}".format(val_list[i], v)
        
    # loop over all keys and delete them (otherwise we can't delete the bucket)
    for key in key_list:
        s3_client.delete_object(Bucket=bucket_name, Key=key)
    
    # delete the bucket
    s3_client.delete_bucket(Bucket=bucket_name)
        
    return get_times, set_times


def lambda_handler(event, context):
    """
    
    Simple lambda function to test redis3 and s3 performance.
    
    No error checking, no fancy stuff, just throw-away code to get some get / set 
    performance numbers.
    
    """
    start = time.time()
    data = {}
    # debug
    print(event)
    query_args = event.get('queryStringParameters', None)
    # set a default input_k 
    cnt_k = query_args['k'] if query_args and 'k' in query_args else DEFAULT_K
    key_list = ['playground_{}'.format(i) for i in range(cnt_k)]
    val_list = ['bar_{}'.format(i) for i in range(cnt_k)]
    # set a default cache name
    cache_name = query_args['cache'] if query_args and 'cache' in query_args else 'mytestcache'
    get_times, set_times = run_redis3_tests(cache_name, key_list, val_list)
    # add some stats to the data object we return
    data['set_times'] = set_times
    data['set_time_mean'] = mean(set_times)
    data['set_time_median'] = median(set_times)
    data['get_times'] = get_times
    data['get_time_mean'] = mean(get_times)
    data['get_time_median'] = median(get_times)
    # run some basic ops in s3
    get_times, set_times = run_s3_tests(key_list, val_list)
    # add some stats to the data object we return
    data['set_times_s3'] = set_times
    data['set_time_mean_s3'] = mean(set_times)
    data['set_time_median_s3'] = median(set_times)
    data['get_times_s3'] = get_times
    data['get_time_mean_s3'] = mean(get_times)
    data['get_time_median_s3'] = median(get_times)
    # run some basic ops in s3
    get_times, set_times = run_redis_tests(key_list, val_list)
    # add some stats to the data object we return
    data['set_times_redis'] = set_times
    data['set_time_mean_redis'] = mean(set_times)
    data['set_time_median_redis'] = median(set_times)
    data['get_times_redis'] = get_times
    data['get_time_mean_redis'] = mean(get_times)
    data['get_time_median_redis'] = median(get_times)
    # finally test the redis3 client with many keys at once
    get_times, set_times = run_redis3_many_keys_tests(cache_name, key_list, val_list)
    data['set_times_many'] = set_times
    data['set_time_mean_many'] = mean(set_times)
    data['set_time_median_many'] = median(set_times)
    data['get_times_many'] = get_times
    data['get_time_mean_many'] = mean(get_times)
    data['get_time_median_many'] = median(get_times)
      
    body = {
        "metadata": {
            "timeMs": int((time.time() - start) * 1000.0),
            "epochMs": int(time.time() * 1000),
            "eventId": str(uuid.uuid4()),
            'inputK': cnt_k,
        },
        "data": data
    }

    return wrap_response(body)