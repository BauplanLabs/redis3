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

Note that `my-cache-name` will be used to produce a bucket name with the name `redis3-my-cache-name`, which needs to be unique in the region as per S3 naming rules.

## 5-min explanation

WIP

## Running some tests

WIP

### Bonus: a lambda-based use-case

WIP

## TO-DOs, misc. notes and all that jazz

WIP

## License

This code is released "As Is", with no guarantees whatsover, under the MIT license. This was a fun coding excercise in-between serious tasks, and should be taken with the appropriate dose of sense of humour.
