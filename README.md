# redis3

A one-afternoon implementation of (a small set of) redis-like primitives with s3 Express.

## Overview

AWS recently announced [s3 Express](https://aws.amazon.com/it/s3/storage-classes/express-one-zone/), a new type of s3 buckets tailored for low-latency access targeting (especially) small files, frequently accessed. In AWS own [words](https://aws.amazon.com/it/blogs/aws/new-amazon-s3-express-one-zone-high-performance-storage-class/): "This new storage class can handle objects of any size, but is especially awesome for smaller objects. (...) Because of s3 Express One Zone’s consistent very low latency, small objects can be read up to 10x faster compared to s3 Standard."

Even the pricing is geared towards small objects: "you pay $0.16/GB/month in the US East (N. Virginia) Region (...) and an additional per-GB fee for the portion of any request that exceeds 512 KB."

One of the primary (even if far from the only) use cases for things like Redis is consistent performance for key-value queries: you set 'bar' for the key 'foo', and then you retrieve it by asking 'foo' later. While Redis (and other key-value stores) are indubitably faster than s3 (even in its new express version), they are incredibly more costly: these are some prices (in US East) as of Dec 2023.

| Service | Monthly Cost ($) |
| ------------- | ------------- |
| S3 Express (1 GB) | 0.16 |
| cache.t4g.micro (0.5 GB)  | 11.52 (0.016 / hour) |
| cache.t4g.small (1.37 GB) | 23.04 (0.032 / hour) |

In this small experiment we set out to investigate which type of performance / cost trade-off is now unlocked thanks to the new s3 Express option: since we mostly care about key-value queries for "small objects", can we build a redis-like client entirely backed by s3 Express?

## 1-min hello-world

If you have [AWS credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) set up so that you can run arbitrary s3 and s3 express stuff on your account, you can run this in one minute, by creating a virtual env and cd-ing into `src`:  

```shell
 python3 -m venv venv
 source venv/bin/activate
 pip install .
 python
```

In the Python REPL, you can now do (compare to [redis-py](https://github.com/redis/redis-py)):

```shell
>>> from redis3.redis3 import redis3Client
>>> r = redis3Client(cache_name='mytestcache', db=0)
>>> r.set('foo', 'bar')
True
>>> r.get('foo')
'bar'
```

Note that:

* `my-cache-name` will be used (together with an availability zone, default to `use1-az5` as it assumes you are stuck with `us-east-1` like the rest of us) to produce a bucket like `redis3-mytestcache--use1-az5--x-s3`, which needs to be unique in the region as per s3 naming rules;
* `redis3Client` uses the boto3 client behind the scenes, so the usual authentication rules apply (credential file, environment variables or passing `aws_access_key_id` and the like as `**kwargs`).

If you want to see more ops, you can run `playground.py` with your own `my-cache-name` as argument:

```shell
cd src
python playground.py my-cache-name
```

## 5-min explanation

Sometimes we want a full-fledged NoSQL store (no shortage of that!), sometimes we just want to set some value somewhere, possibly namespaced in some way, and get it back at a later time. Object storage like s3 was never fast and reliable enough in first byte latency to be an actual contender, until the release of s3 Express, which, for key-value type of queries, proposes a novel price/latency trade-off compared to more traditional solutions (Redis, dynamo etc.).

`redis3` is a 100 LOC (or whatever) class that puts together a redis-py interface to s3 Express, easy to be used as a slowish, but infinite and cheap cache (no worries about provisioning a larger instance, or evicting keys); `redis3` now implements GET and SET, namespaced by a database integer (Redis-like), plus few other commands, such as a version of MGET and MSET "suited" to object storage - i.e. it cannot be an atomic operation, but it runs in parallel through a thread pool, allowing to SET / GET many values with one command relatively fast (from my local machine - a pretty decent Mac in US East -, getting 25 keys with MGET takes 0.1286s, 50 takes 0.1362s and 100 takes 0.1960s). When instantiating the client (e.g. `redis3Client(cache_name='mytestcache', db=0)`) you can specify a `db` as a namespacing device, exactly as it happens in Redis (there is no limitation to `16` for the number of db of course).

| Redis Command | redis3 Command | Intended Semantics |
| ------------- | ------------- | ------------- |
| GET  | `get(key)` | get the value from a string key |
| SET  | `set(key, value)`  | set a string value for a key |
| MGET | `mget(keys)` | get multiple keys in parallel |
| MSET | `mset(keys, values)`  | set multiple values for keys in parallel |
| KEYS | `keys(starts_with)`  | list all keys in the current db |
| DEL | `delete(key)`  |  delete the key (no error is thrown if key does not exist) |

Note that redis (which, btw, runs single-threaded in-memory for a reason) can offer not only 316136913 more commands, but also atomicity guarantees (INCR, WATCH, etc.) that object storage cannot (s3 offers however [strong read-after-write consistency](https://aws.amazon.com/it/s3/consistency/): after a successful write of a new object, any subsequent read - including listin keys - request receives the latest version of the object). On the other hand, a s3-backed cache can offer more concurrent troughput at no additional effort, a truly "serverless experience" and a "thin client" which falls back on standard AWS libraries, inheriting automatically all security policies you can think of (e.g. since "db" in redis3 are just folder in an express bucket, access can controlled at that level by leveraging the usual IAM magic).

## Running some tests

Some more (horribly repetitive) code to test the difference between s3 express and normal s3 (plus some tests to actually make sure the client behaves as it should) can be run here:

```shell
cd src
python run_tests.py my-cache-name
```

With EC2s, you can specify at creation the same availability zone as the s3 cache and run a comparison of normal buckets vs express in the best possible (in theory) latency conditions (vs a free [Redis](https://redis.com/) instance in us-east-1 as baseline comparison). My manual runs on a throw-away EC2 (k=100) gave the following results (in seconds):

| Test | Standard Bucket (s) | Express Bucket (s) | Redis Labs |
| ------------- | ------------- | ------------- | ------------- |
| GET (avg) | 0.016 | 0.005  | 0.001  |
| GET (median) | 0.014  | 0.005  | 0.0009  |
| GET (95th latency) | 0.027  | 0.005  | 0.002  | 

TL;DR: an express bucket is not just 3x faster in the average case, but significantly more reliable in the tail. Redis is still much faster than both, but (remember) it is also much more expensive.

Note: don't take these tests too seriously!

### Bonus: a lambda-based use-case

If you know the [serverless framework](https://www.serverless.com/framework/) and have it avalaible on your machine, you can publish a lambda function that performs some (horribly repetitive) tests to evaluate AWS-lambda-to-s3 latency. Note that:

* on top of serverless, you will need Docker, as the `boto3` version inside Lamdbas is too old and does not support s3 express buckets yet;
* after deployment, you need to make sure the lambda role created for the function can access the s3 resources backing up the cache. Note that s3 express policies are [a bit of a drag](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-security-iam-identity-policies.html), so beware.

If you feel adventurous and ready to fight IAM roles, then do:

```shell
cd serverless
serverless deploy
```

(if you don't, you can just trust my numbers below!).

At the end, you'll get and endpoint such as `https://xxx.execute-api.us-east-1.amazonaws.com/dev/test?k=50&cache=mytestcache` that you can open in your browser to trigger the tests (`k` and `cache` are optional - check `app.py` for the defaults). One request will generate something like this, i.e. a comparison of _k_ ops in s3 express vs normal vs Redis Labs:

```json
{
    "metadata": {
        "timeMs": 7373,
        "epochMs": 1701377819320,
        "eventId": "971ca40d-8f50-4c27-a816-76bb7df292c4",
        "inputK": 50
    },
    "data": {
        "set_time_mean": 0.011164916356404623,
        "set_time_median": 0.009434223175048828,
        "get_time_mean": 0.006322011947631836,
        "get_time_median": 0.006218910217285156,
        "set_time_mean_s3": 0.026339941024780274,
        "set_time_median_s3": 0.024151086807250977,
        "get_time_mean_s3": 0.019532273610432943,
        "get_time_median_s3": 0.016076326370239258,
        "set_time_mean_redis": 0.0018777799606323241,
        "set_time_median_redis": 0.000904083251953125,
        "set_time_mean_many": 0.406483252843221,
        "set_time_median_many": 0.3329179286956787,
        "get_time_mean_many": 0.31602056821187335,
        "get_time_median_many": 0.3195207118988037
    }
}
```

In this particular example, with _k=50_, setting a key with s3 Express is ~10ms, and 6 to get it back, vs ~25 and 18 from standard s3. Setting 50 keys at once with multi-threading takes ~400ms, while reading them back ~300. Not bad!

## TO-DOs, misc. notes and all that jazz

* Since the only real dependency is boto3 and AWS access, make it easier to configure the client wrt AWS would be nice: right now, I've mostly running either in a DEV environment with semi-god IAM access, or in a carefully crafted IAM-role attached to the lambda;
* if this is useful, move to poetry and auto-deploy to PyPyi would make it easy to just start using all around repos;
* if lambda-based latency benchmarks are useful, built in the `serverless.yml` the proper AWS permission so that the deployment becomes seamless (now the entire serverless part is really manual, ad hoc and redundant).

Everything is left as an exercise to the reader.

## License

This code is released "As Is", with no guarantees whatsover, under the MIT license. This was a fun coding excercise in-between serious tasks, and should be taken with the appropriate dose of sense of humour.
