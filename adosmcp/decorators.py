import logging
from functools import wraps
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