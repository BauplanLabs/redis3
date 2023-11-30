import boto3
import uuid
from time import time
from statistics import median, mean
from tqdm import tqdm
from datetime import datetime
from redis3 import redis3Client
import math


def print_test_info(
    timing_list: list,
    target_percentile: int = 95
):
    print("Average time: {}".format(mean(timing_list)))
    print("Median time: {}".format(median(timing_list)))
    print("95th percentile time: {}".format(percentile(timing_list, target_percentile)))
    return


def percentile(input, q):
    """
    I don't want to import numpy just for this
    """
    data_sorted = sorted(input)
    
    return data_sorted[math.ceil(q / 100 * len(data_sorted))]


def run_normal_bucket_tests(
    test_keys: list, # list of keys to set / get
    test_values: list,
    **kwargs
):
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

    del s3_client
    
    print("\nEnd of testing standard buckets at {}\n".format(datetime.now()))
    
    return
    

def run_cache_tests(
    test_keys: list, # list of keys to set / get
    test_values: list,
    cache_name: str, # name of the cache to use
    **kwargs
):
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
    
    del my_client
    # end
    print("\nEnd of testing the cache at {}\n".format(datetime.now()))
    
    return 

def run_functional_tests(
    cache_name: str, # name of the cache to use
    **kwargs
):
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=False, **kwargs)
    
    del my_client
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
    
    print("\nFinished testing at {}. See you, s3ace cowboy".format(datetime.now()))
    return



if __name__ == "__main__":
    import sys 
    # make sure we have a cache name
    assert len(sys.argv) == 2, "Please provide a cache name"
    cache_name = sys.argv[1]
    run_tests(cache_name, k=1000)