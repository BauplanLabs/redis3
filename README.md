# redis3
A one-afternoon implementation of redis-like primitives with S3 Express

## Overview

WIP

## 1-min hello-world

```shell
 python3 -m venv venv
 source venv/bin/activate
 pip install -r requirements.txt
 cd src
```

Open a Python REPL and do some SETs / GETs (compare to [redis-py](https://github.com/redis/redis-py) for example):

```shell
>>> from redis3 import redis3Client
>>> r = my_client = redis3Client(cache_name=cache_name, db=0)
>>> r.set('foo', 'bar')
True
>>> r.get('foo')
b'bar'
```

or run `playground.py` with your own `my-cache-name` as argument to see a variety of examples:

```shell
python playground.py my-cache-name
```

Note that `my-cache-name` will be used (together with an availability zone) to produce a bucket name with a name like `redis3-mytestcache--use1-az5--x-s3`, which needs to be unique in the region as per S3 naming rules.

## 5-min explanation

WIP

## Running some tests

WIP

### Bonus: a lambda-based use-case


`https://xxx.execute-api.us-east-1.amazonaws.com/dev/test`

Without custom parameters, it will generate something like this, i.e. a comparison of K SETs and GETs in S3 express vs normal s3.

```json
{
    "metadata": {
        "timeMs": 7373,
        "epochMs": 1701377819320,
        "eventId": "971ca40d-8f50-4c27-a816-76bb7df292c4",
        "inputK": 75
    },
    "data": {
        "set_times": [],
        "set_time_mean": 0.011164916356404623,
        "set_time_median": 0.009434223175048828,
        "get_times": [],
        "get_time_mean": 0.006322011947631836,
        "get_time_median": 0.006218910217285156,
        "set_times_s3": [],
        "set_time_mean_s3": 0.026339941024780274,
        "set_time_median_s3": 0.024151086807250977,
        "get_times_s3": [],
        "get_time_mean_s3": 0.019532273610432943,
        "get_time_median_s3": 0.016076326370239258
    }
}
```

## TO-DOs, misc. notes and all that jazz

WIP

## License

This code is released "As Is", with no guarantees whatsover, under the MIT license. This was a fun coding excercise in-between serious tasks, and should be taken with the appropriate dose of sense of humour.
