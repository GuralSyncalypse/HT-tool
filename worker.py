from redis import Redis
from rq import Worker, Queue

redis_conn = Redis(host="redis", port=6379)

q = Queue("default", connection=redis_conn)
worker = Worker([q])
worker.work()