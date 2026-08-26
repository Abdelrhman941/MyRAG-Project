"""Rate-limiter singleton.

The ``Limiter`` instance is created once here and attached to ``app.state.limiter``
in ``create_app``.  Route handlers import ``limiter`` directly to use the
``@limiter.limit(...)`` decorator.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
