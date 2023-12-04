"""

This is a playground script that shows how to use the redis3Client class
by performing some basic operations on the "cache".

To cover edge cases and benchmarking, you can inspect and run run_tests.py
instead.

Note that this script assumes your interpreter can run:

s3_client = boto3.client('s3')

either through a local AWS credentials file or through ENVs etc. (you can also
modify this script to pass credentials to boto3 using kwargs for redis3Client).

"""

from redis3 import redis3Client
from datetime import datetime
from utils import measure_func
import uuid
import json

@measure_func
def set_key_with_timing(client):
    return client.set('foo', 'bar')


@measure_func
def get_key_with_timing(client):
    return client.get('foo')


@measure_func
def set_keys_with_timing(client, size=50):
    _list = ['playground_{}'.format(i) for i in range(size)]
    return client.mset(_list, _list)


@measure_func
def get_keys_with_timing(client, size=50):
    key_list = ['playground_{}'.format(i) for i in range(size)]
    return client.mget(key_list)


def run_playground(
    cache_name: str
):
    # say hi
    print("Started playground at {}\n".format(datetime.now()))
    
    # first, instantiate redis3Client and check all is well
    # we set verbose to True to see what's going on under the hood as this
    # a playground script
    my_client = redis3Client(cache_name=cache_name, db=0, verbose=True)
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
    # overwrite the key and get it back
    r = my_client.set('foo', 'bar2')
    assert my_client.get('foo') == 'bar2', "Expected 'bar2', got {}".format(r)
    # store something more complex, as long as you can serialize it to a string
    # e.g. dump it to a JSON string
    my_obj = { 'k_{}'.format(i): 'v_{}'.format(i) for i in range(5) }
    r = my_client.set('foo_dic', json.dumps(my_obj))
    r = json.loads(my_client.get('foo_dic'))
    assert r['k_0'] == 'v_0', "Expected 'v_0', got {}".format(r['k_0'])
    # get a key that doesn't exist
    r = my_client.get('baz')
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
    r = my_client.delete(str(uuid.uuid4()))
    assert r is True, "Expected True, got {}".format(r)
    # finally, do the same ops, wrapped in a timing decorator
    # to avoid spamming the console, we 'manually' toggle verbose off
    my_client._verbose = False
    
    r = set_key_with_timing(my_client)
    r = get_key_with_timing(my_client)
    r = get_keys_with_timing(my_client)
    r = set_keys_with_timing(my_client)
    
    # how does the many ops scale with more keys?
    for i in [25, 50, 100, 500, 1000]:
        print("\nRunning ops with {} keys".format(i))
        r = set_keys_with_timing(my_client, size=i)
        r = get_keys_with_timing(my_client, size=i)
    
    # say bye
    print("\nFinished playground at {}. See you, s3ace cowboy".format(datetime.now()))
    return


if __name__ == "__main__":
    import sys 
    # make sure we have a cache name
    assert len(sys.argv) == 2, "Please provide a cache name"
    cache_name = sys.argv[1]
    run_playground(cache_name=cache_name)