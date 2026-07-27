from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

cache = Cache()
limiter = Limiter(get_remote_address, default_limits=["2000 per day", "50 per hour"])