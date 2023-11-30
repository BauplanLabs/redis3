
import time
import uuid
import boto3
import json
from redis3 import redis3Client
from statistics import mean, median


# default number of keys to try to set / get
DEFAULT_K = 100

# check the version of boto3
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


def lambda_handler(event, context):
    """
    
    Simple lambda function to test redis3 and s3 performance.
    
    No error checking, no fancy stuff, just throw-away code to get some get / set 
    performance numbers.
    
    """
    start = time.time()
    data = []
    # debug
    print(event)
    query_args = event.get('queryStringParameters', None)
    # set a default input_k 
    cnt_k = query_args['k'] if query_args and 'k' in query_args else DEFAULT_K
    # set a default cache name
    cache_name = query_args['cache'] if query_args and 'cache' in query_args else 'mytestcache'
    # run some redis3 ops and append to data
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=True)
    
    key_list = ['playground_{}'.format(i) for i in range(cnt_k)]
    val_list = ['bar_{}'.format(i) for i in range(cnt_k)]
    
    set_times = []
    for k, v in zip(key_list, val_list):
        s_set_time = time.time()
        r = my_client.set(k, v)
        set_times.append(s_set_time - time.time())
        
    data['set_times'] = set_times
    data['set_time_mean'] = mean(set_times)
    data['set_time_median'] = median(set_times)
    
    get_times = []
    for k, v in zip(key_list, val_list):
        s_get_time = time.time()
        r = my_client.get(k)
        get_times.append(s_get_time - time.time())
        assert r == v, "Expected {}, got {}".format(v, r)    
    
    data['get_times'] = get_times
    data['get_time_mean'] = mean(get_times)
    data['get_time_median'] = median(get_times)
    
    # run some basic s3 ops and append to data
    
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