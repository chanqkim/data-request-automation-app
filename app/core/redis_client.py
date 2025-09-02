import redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from app.config import REDIS_URL

# redis retry strategy
retry_strategy = Retry(
    retries=3,  # max-retry count
    backoff=ExponentialBackoff(
        base=0.1, cap=2.0
    ),  # 0.1 delay for retry , maximum-wait-time = 2sec
)

# create redis client object
redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=3,  # add connection timeout
    socket_timeout=3,  # redis read/write waiting timeout
    retry_on_timeout=True,
    retry=retry_strategy,
)
