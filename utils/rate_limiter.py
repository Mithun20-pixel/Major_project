"""
utils/rate_limiter.py - Zero-Dependency In-Memory Rate Limiter
===============================================================
Provides a lightweight rate limiting decorator for Flask routes using a
sliding window algorithm per client IP address.

Designed to be zero-dependency, fast, and completely safe for development,
demonstration, and student final-year project grading.
"""

import time
from functools import wraps
from collections import defaultdict
from flask import request, flash, redirect, url_for, render_template

# Storage: endpoint -> IP -> list of timestamps
_request_history = defaultdict(lambda: defaultdict(list))


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    Decorator to rate limit a Flask route by IP address.

    Args:
        max_requests: Maximum allowed requests within the time window.
        window_seconds: Time window in seconds.

    Usage:
        @auth_bp.route("/login", methods=["GET", "POST"])
        @rate_limit(max_requests=10, window_seconds=60)
        def login():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app
            if current_app.config.get("TESTING"):
                return f(*args, **kwargs)

            # Get client IP address
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            if ip and "," in ip:
                ip = ip.split(",")[0].strip()

            endpoint = request.endpoint or f.__name__
            now = time.time()
            cutoff = now - window_seconds

            # Filter out timestamps outside the sliding window
            history = [ts for ts in _request_history[endpoint][ip] if ts > cutoff]
            _request_history[endpoint][ip] = history

            # Only check limit on POST / submitting requests
            if request.method == "POST":
                if len(history) >= max_requests:
                    retry_after = int(window_seconds - (now - history[0])) if history else window_seconds
                    flash(
                        f"Too many submission attempts. Please wait {max(1, retry_after)} seconds before trying again.",
                        "danger"
                    )
                    return redirect(request.url)

                # Record current request timestamp
                history.append(now)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
