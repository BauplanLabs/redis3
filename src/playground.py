"""

This is a playground script that shows how to use the redis3Client class
by performing some basic operations on the "cache".

To cover edge cases and benchmarking, you can inspect and run run_tests.py
instead.

"""

from redis3 import redis3Client
from datetime import datetime
from utils import measure_func


@measure_func
def set_key_with_timing(client):
    return client.set('foo', 'bar')


@measure_func
def get_key_with_timing(client):
    return client.get('foo')


@measure_func
def set_keys_with_timing():
    
    return


@measure_func
def get_keys_with_timing():
    
    return 


def run_playground(
    cache_name: str
):
    # say hi
    print("Started playground at {}\n".format(datetime.now()))
    
    # first, instantiate redis3Client and check all is well
    my_client = redis3Client(cache_name=cache_name, db=0)
    # for debugging purposes, print the name of the bucket used to back the cache
    print("Using bucket {} as cache".format(my_client.bucket_name))
    
    # now, some basic ops
    
    # set a key and get it back
    r = my_client.set('foo', 'bar')
    print(r)
    assert r is True, "Expected True, got {}".format(r)
    r = my_client.get('foo')
    print(r) 
    assert r == 'bar', "Expected 'bar', got {}".format(r)
    assert isinstance(r, str), "Expected a string, got {}".format(type(r))
    # set a list of keys and get them back
    
    # finally, do the same ops, wrapped in a timing decorator now
    set_key_with_timing(my_client)
    get_key_with_timing(my_client)
    
    # say bye
    print("\nFinished playground at {}. See you, s3ace cowboy".format(datetime.now()))
    return


if __name__ == "__main__":
    import sys 
    # make sure we have a cache name
    assert len(sys.argv) == 2, "Please provide a cache name"
    cache_name = sys.argv[1]
    run_playground(cache_name=cache_name)