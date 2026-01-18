"""
Query Logging Middleware for monitoring API performance.
"""
import time
import json
import logging

logger = logging.getLogger(__name__)


class QueryLoggingMiddleware:
    """
    Middleware to log API query performance.
    
    Captures:
    - Request timing (duration in milliseconds)
    - HTTP method and endpoint
    - Query parameters
    - Response status code
    - Result count (if available)
    - Error messages (if failed)
    
    Excludes:
    - /api/stats/ endpoints (avoid recursion)
    - /health/ endpoints
    - /admin/ endpoints
    - Static file requests
    """
    
    EXCLUDED_PATHS = ['/api/stats/', '/health/', '/admin/', '/static/', '/media/']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if we should log this request
        if not self.should_log(request.path):
            return self.get_response(request)
        
        # Record start time
        start_time = time.time()
        
        # Process the request
        response = self.get_response(request)
        
        # Record end time and calculate duration
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)
        
        # Log the query (non-blocking - failure won't fail the request)
        try:
            self._log_query(request, response, duration_ms)
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Failed to log query: {e}")
        
        # Log warning for very slow queries
        if duration_ms > 2000:
            logger.warning(
                f"Very slow query detected: {request.method} {request.path} "
                f"took {duration_ms}ms"
            )
        
        return response
    
    def should_log(self, path):
        """
        Determine if the request should be logged.
        
        Args:
            path: The request path
            
        Returns:
            bool: True if the request should be logged
        """
        return not any(path.startswith(p) for p in self.EXCLUDED_PATHS)
    
    def _log_query(self, request, response, duration_ms):
        """
        Create a QueryLog entry for the request.
        
        Args:
            request: The Django request object
            response: The Django response object
            duration_ms: Request duration in milliseconds
        """
        # Import here to avoid circular imports
        from .models import QueryLog
        
        # Extract query parameters
        query_params = dict(request.GET.items())
        
        # Extract result count if available
        result_count = self._extract_result_count(response)
        
        # Extract error message if failed
        error_message = None
        if response.status_code >= 400:
            error_message = self._extract_error_message(response)
        
        # Get client information
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255] if request.META.get('HTTP_USER_AGENT') else None
        ip_address = self._get_client_ip(request)
        
        # Create the log entry
        QueryLog.objects.create(
            endpoint=request.path,
            method=request.method,
            query_params=query_params,
            duration_ms=duration_ms,
            status_code=response.status_code,
            result_count=result_count,
            error_message=error_message,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    
    def _extract_result_count(self, response):
        """
        Extract result count from response if available.
        
        Returns:
            int: Number of results, or -1 if not applicable
        """
        if not hasattr(response, 'data'):
            return -1
        
        data = response.data
        
        # Paginated response with count
        if isinstance(data, dict):
            if 'count' in data:
                return data['count']
            if 'results' in data:
                return len(data['results'])
        
        # Direct list response
        if isinstance(data, list):
            return len(data)
        
        return -1
    
    def _extract_error_message(self, response):
        """
        Extract error message from failed response.
        
        Returns:
            str: Error message or None
        """
        if not hasattr(response, 'data'):
            return None
        
        data = response.data
        
        if isinstance(data, dict):
            # Common error formats
            if 'error' in data:
                return str(data['error'])
            if 'detail' in data:
                return str(data['detail'])
            if 'message' in data:
                return str(data['message'])
        
        # Try to serialize the response data
        try:
            return json.dumps(data)[:500]  # Limit error message length
        except (TypeError, ValueError):
            return None
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request.
        
        Handles proxy headers (X-Forwarded-For) appropriately.
        
        Returns:
            str: Client IP address or None
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Take the first IP in the chain
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return ip if ip else None
