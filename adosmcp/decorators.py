import logging
import time
from functools import wraps
from collections import defaultdict, deque
from azure.devops.exceptions import AzureDevOpsServiceError

logging.basicConfig(level=logging.INFO)


def azure_devops_error_handler(func):
    """
    Decorator to handle Azure DevOps API errors consistently across all methods.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        
        # Extract context from class name if this is a method call
        context = ""
        if args and hasattr(args[0], '__class__'):
            class_name = args[0].__class__.__name__
            if class_name.startswith('AzureDevOps'):
                # Convert AzureDevOpsWorkItems -> work items
                context_type = class_name.replace('AzureDevOps', '').lower()
                context = f" in {context_type}"
        
        try:
            return await func(*args, **kwargs)
        except AzureDevOpsServiceError as e:
            logging.error(f"Azure DevOps API error in {func_name}: {e}")
            raise Exception(f"Failed to {func_name.replace('_', ' ')}{context}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in {func_name}: {e}")
            raise Exception(f"Unexpected error in {func_name.replace('_', ' ')}{context}: {str(e)}")
    
    return wrapper


# Rate limiting storage
_rate_limit_storage = defaultdict(lambda: deque())


def rate_limit(requests_per_minute=60):
    """
    Decorator to implement rate limiting per client/function combination.
    
    Args:
        requests_per_minute: Maximum number of requests allowed per minute (default: 60)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            
            # Use function name as key for rate limiting
            # In a production environment, you'd want to use client ID or IP
            key = f"{func_name}"
            
            current_time = time.time()
            window_start = current_time - 60  # 1 minute window
            
            # Clean old entries
            request_times = _rate_limit_storage[key]
            while request_times and request_times[0] < window_start:
                request_times.popleft()
            
            # Check if limit exceeded
            if len(request_times) >= requests_per_minute:
                logging.warning(f"Rate limit exceeded for {func_name}")
                raise Exception(f"Rate limit exceeded. Maximum {requests_per_minute} requests per minute allowed.")
            
            # Add current request
            request_times.append(current_time)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def request_size_limit(max_size_mb=10):
    """
    Decorator to limit request data size to prevent resource exhaustion.
    
    Args:
        max_size_mb: Maximum size in MB for request data (default: 10MB)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check for large string parameters that could cause memory issues
            max_bytes = max_size_mb * 1024 * 1024
            
            for arg in args[1:]:  # Skip 'self' parameter
                if isinstance(arg, str) and len(arg.encode('utf-8')) > max_bytes:
                    logging.warning(f"Request size limit exceeded in {func.__name__}")
                    raise Exception(f"Request data too large. Maximum {max_size_mb}MB allowed.")
            
            for key, value in kwargs.items():
                if isinstance(value, str) and len(value.encode('utf-8')) > max_bytes:
                    logging.warning(f"Request size limit exceeded in {func.__name__} for parameter {key}")
                    raise Exception(f"Request data too large. Maximum {max_size_mb}MB allowed.")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator