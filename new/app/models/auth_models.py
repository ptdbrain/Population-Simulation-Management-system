from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from app.models.base import Base

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)
    description = Column(String(255))
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", back_populates="role")

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, index=True) # e.g., 'household:split'
    description = Column(String(255))
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    role_id = Column(Integer, ForeignKey('roles.id'))
    resident_id = Column(Integer, ForeignKey('residents.id', name='fk_user_resident', use_alter=True), nullable=True) # Links to logical resident if applicable
    is_active = Column(Boolean, default=True)

    role = relationship("Role", back_populates="users")
    # resident relationship will be defined in residence_models or via string to avoid circular import if needed.
    # We can rely on basic FK for now.
