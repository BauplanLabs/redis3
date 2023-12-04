"""

Simple script to run some tests on the cache: some functional tests, and some performance tests,
in which we compare standard S3 buckets with the express bucket.

"""

import boto3
import uuid
from time import time
from statistics import median, mean
from tqdm import tqdm
from datetime import datetime
from redis3 import redis3Client
import math
import json
import uuid


def print_test_info(
    timing_list: list,
    target_percentile: int = 95
):
    def percentile(input, q):
        """
        I don't want to import numpy just for this
        """
        data_sorted = sorted(input)
        
        return data_sorted[math.ceil(q / 100 * len(data_sorted))]

    print("Average time: {}".format(mean(timing_list)))
    print("Median time: {}".format(median(timing_list)))
    print("95th percentile time: {}".format(percentile(timing_list, target_percentile)))
    return


def run_normal_bucket_tests(
    test_keys: list, # list of keys to set / get
    test_values: list,
    **kwargs
):
    print("\nStart of testing standard buckets at {}\n".format(datetime.now()))
    # start a client
    s3_client = boto3.client('s3', **kwargs)
    # create a bucket with a temp name
    # bucket creation is not part of the benchmark
    bucket_name = "redis3-test-{}".format(uuid.uuid4())
    s3_client.create_bucket(Bucket=bucket_name)
    # set all keys + values
    set_times = []
    for i in tqdm(range(len(test_keys))):
        start = time()
        s3_client.put_object(Bucket=bucket_name, Key=test_keys[i], Body=test_values[i])
        set_times.append(time() - start)
    # print out average and median set times
    print_test_info(set_times, target_percentile=95)
    # read them back
    get_times = []
    for i in tqdm(range(len(test_keys))):
        start = time()
        obj = s3_client.get_object(Bucket=bucket_name, Key=test_keys[i])
        v = obj['Body'].read().decode('utf-8')
        get_times.append(time() - start)
        # check we get the right value back!
        assert v == test_values[i], "Expected {}, got {}".format(test_values[i], v)
    # print out average and median set times
    print_test_info(get_times, target_percentile=95)
    
    # loop over all keys and delete them (otherwise we can't delete the bucket)
    for test_key in tqdm(test_keys):
        # TODO: we should totally parallelize this
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
    
    # delete the bucket
    s3_client.delete_bucket(Bucket=bucket_name)
    
    print("\nEnd of testing standard buckets at {}\n".format(datetime.now()))
    
    return
    

def run_cache_tests(
    test_keys: list, # list of keys to set / get
    test_values: list,
    cache_name: str, # name of the cache to use
    **kwargs
):
    print("\nStart of testing the cache at {}\n".format(datetime.now()))
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=False, **kwargs)
    # set all keys + values
    set_times = []
    for i in tqdm(range(len(test_keys))):
        start = time()
        my_client.set(test_keys[i], test_values[i])
        set_times.append(time() - start)
    # print out average and median set times
    print_test_info(set_times, target_percentile=95)
    # read them back
    get_times = []
    for i in tqdm(range(len(test_keys))):
        start = time()
        v = my_client.get(test_keys[i])
        get_times.append(time() - start)
        # check we get the right value back!
        assert v == test_values[i], "Expected {}, got {}".format(test_values[i], v)
    # print out average and median set times
    print_test_info(get_times, target_percentile=95)

    # end
    print("\nEnd of testing the cache at {}\n".format(datetime.now()))
    
    return 

def run_functional_tests(
    cache_name: str, # name of the cache to use
    **kwargs
):
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=False, **kwargs)

    # set a key and get it back
    r = my_client.set('foo', 'bar')
    assert r is True, "Expected True, got {}".format(r)
    r = my_client.get('foo')
    assert r == 'bar', "Expected 'bar', got {}".format(r)
    assert isinstance(r, str), "Expected a string, got {}".format(type(r))
    # overwrite the key and get it back
    r = my_client.set('foo', 'bar2')
    assert my_client.get('foo') == 'bar2', "Expected 'bar2', got {}".format(r)
    # store something more complex, as long as you can serialize it to a string
    my_obj = { 'k_{}'.format(i): 'v_{}'.format(i) for i in range(5) }
    r = my_client.set('foo_dic', json.dumps(my_obj))
    r = json.loads(my_client.get('foo_dic'))
    assert r['k_0'] == 'v_0', "Expected 'v_0', got {}".format(r['k_0'])
    # get a key that doesn't exist by randomly picking a uuid
    r = my_client.get(str(uuid.uuid4()))
    assert r is None, "Expected None, got {}".format(r)
    # set a list of keys and get them back in one go
    key_list = ['playground_{}'.format(i) for i in range(5)]
    val_list = ['bar_{}'.format(i) for i in range(5)]
    r = my_client.mset(key_list, val_list)
    assert all(r), "Expected all True, got {}".format(r)
    val_list_back = my_client.mget(key_list)    
    assert val_list_back == val_list, "Expected {}, got {}".format(val_list, val_list_back)
    # use the keys command to get all keys in the cache
    all_keys_in_db = list([k for k in my_client.keys()])
    print("Found {} keys in cache, first three: {}".format(len(all_keys_in_db), all_keys_in_db[:3]))
    # delete one
    r = my_client.delete(all_keys_in_db[0])
    assert r is True, "Expected True, got {}".format(r)
    # delete one that does not exist by getting a random string
    # it should be ignored and get True back again
    r = my_client.delete(str(uuid.uuid4()))
    assert r is True, "Expected True, got {}".format(r)
    # switch to a different bucket by passing a non-int (should get an error)
    try:
        my_client.db = 'ciao'
    except ValueError:
        pass
    # now switch db for real to a magic number
    my_client.db = "100"
    # set a key and list all keys in the cache (should be only one)
    my_client.set('foo_100', 'bar_100')
    all_keys_in_db = list([k for k in my_client.keys()])
    assert len(all_keys_in_db) == 1, "Expected 1 key, got {}".format(len(all_keys_in_db))
    assert all_keys_in_db[0] == 'foo_100', "Expected 'foo_100', got {}".format(all_keys_in_db[0])
    # finally delete the key and check it's gone
    r = my_client.delete('foo_100')
    # do it twice, nothings should happen
    r = my_client.delete('foo_100')
    # now, try to get it back, it should return None
    r = my_client.get('foo_100')
    assert r is None, "Expected None, got {}".format(r)
    # end
    print("\nEnd of functional tests {}\n".format(datetime.now()))
    
    return

def run_tests(
    cache_name: str, # name of the cache to use
    k: int, # number of keys to set / get during tests
    **kwargs
):
    print("Started testing at {}\n".format(datetime.now()))
    # first, run some functional cache tests
    run_functional_tests(cache_name, **kwargs)
    # if nothing fails, create a list of keys and values for perf. testing
    test_keys = ['foo_{}'.format(i) for i in range(k)]
    test_values = ['bar_{}'.format(i) for i in range(k)]
    # test performance of a normal bucket
    run_normal_bucket_tests(test_keys, test_values, **kwargs)
    # test performance of the cache
    run_cache_tests(test_keys, test_values, cache_name, **kwargs)
    print("\n====> Now running the tests again with 5x keys and values <====\n")
    test_keys = ['foo_{}'.format(i) for i in range(k * 5)]
    test_values = ['bar_{}'.format(i) for i in range(k * 5)]
    run_normal_bucket_tests(test_keys, test_values, **kwargs)
    run_cache_tests(test_keys, test_values, cache_name, **kwargs)

    print("\nFinished testing at {}. See you, s3ace cowboy".format(datetime.now()))
    return


if __name__ == "__main__":
    import sys 
    # make sure we have a cache name
    assert len(sys.argv) == 2, "Please provide a cache name"
    cache_name = sys.argv[1]
    # note that k < 100 will create a problem with the percentile function
    run_tests(cache_name, k=100)
    
    # note that you can provide AWS crednetials through the credential file in the machine,
    # or through env variables or as kwargs, just as you would do with any instance
    # of boto3.client: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
    #aws_client_auth = { "aws_access_key_id": "", "aws_secret_access_key": "" }
    #run_tests(cache_name, k=100, **aws_client_auth)
    
   