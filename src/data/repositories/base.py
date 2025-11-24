"""Base repository class for all repositories."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc

from src.data.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """Abstract base repository with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], db_session: Session):
        """
        Initialize repository with model class and database session.
        
        Args:
            model: The SQLAlchemy model class
            db_session: The database session
        """
        self.model = model
        self.db = db_session
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new record.
        
        Args:
            obj_in: Dictionary with field values
            
        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field name to sort by
            order_desc: Whether to sort in descending order
            
        Returns:
            List of model instances
        """
        query = self.db.query(self.model)
        
        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            query = query.order_by(desc(order_column) if order_desc else asc(order_column))
        
        return query.offset(skip).limit(limit).all()
    
    def update(
        self, 
        db_obj: ModelType, 
        obj_in: Union[Dict[str, Any], Any]
    ) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db_obj: Existing model instance
            obj_in: Dictionary with field values to update
            
        Returns:
            Updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: Any) -> Optional[ModelType]:
        """
        Delete a record by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            Deleted model instance or None if not found
        """
        obj = self.get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj
    
    def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """
        Get a record by a specific field value.
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            Model instance or None if not found
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} has no field '{field}'")
        
        return self.db.query(self.model).filter(getattr(self.model, field) == value).first()
    
    def get_by_fields(self, filters: Dict[str, Any]) -> Optional[ModelType]:
        """
        Get a record by multiple field values.
        
        Args:
            filters: Dictionary of field names and values
            
        Returns:
            Model instance or None if not found
        """
        query = self.db.query(self.model)
        
        for field, value in filters.items():
            if not hasattr(self.model, field):
                raise ValueError(f"Model {self.model.__name__} has no field '{field}'")
            query = query.filter(getattr(self.model, field) == value)
        
        return query.first()
    
    def get_multi_by_field(
        self, 
        field: str, 
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records by a specific field value.
        
        Args:
            field: Field name
            value: Field value
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} has no field '{field}'")
        
        return (
            self.db.query(self.model)
            .filter(getattr(self.model, field) == value)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count(self) -> int:
        """
        Count all records.
        
        Returns:
            Total number of records
        """
        return self.db.query(self.model).count()
    
    def count_by_field(self, field: str, value: Any) -> int:
        """
        Count records by a specific field value.
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            Number of matching records
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} has no field '{field}'")
        
        return self.db.query(self.model).filter(getattr(self.model, field) == value).count()
    
    def exists(self, id: Any) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            id: Primary key value
            
        Returns:
            True if record exists, False otherwise
        """
        return self.db.query(self.model).filter(self.model.id == id).first() is not None
    
    def exists_by_field(self, field: str, value: Any) -> bool:
        """
        Check if a record exists by a specific field value.
        
        Args:
            field: Field name
            value: Field value
            
        Returns:
            True if record exists, False otherwise
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Model {self.model.__name__} has no field '{field}'")
        
        return self.db.query(self.model).filter(getattr(self.model, field) == value).first() is not None
