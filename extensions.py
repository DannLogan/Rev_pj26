from flask_limiter import Limiter

from utils.security import device_rate_key

limiter = Limiter(key_func=device_rate_key, default_limits=[])
