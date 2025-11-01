"""Database query optimization module.

This module provides optimized database queries for evidence retrieval
and verdict storage with batch operations and proper indexing.
"""

from .queries import OptimizedQueries
from .query_builder import QueryBuilder

__all__ = ["OptimizedQueries", "QueryBuilder"]
