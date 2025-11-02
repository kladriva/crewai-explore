"""
Unit tests for Authentication System
Tests login, token validation, and RBAC for different user roles
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import jwt
from passlib.context import CryptContext

from backend.database.models import User, UserRole


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest.mark.unit
class TestUserAuthentication:
    """Test user authentication and password management"""
    
    def test_create_user_with_hashed_password(self, test_db_session):
        """Test creating user with hashed password"""
        plain_password = "SecurePassword123!"
        hashed_password = pwd_context.hash(plain_password)
        
        user = User(
            username="newuser",
            email="newuser@example.com",
            hashed_password=hashed_password,
            role=UserRole.VIEWER,
            is_active=True
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        assert user.id is not None
        assert user.hashed_password != plain_password
        assert pwd_context.verify(plain_password, user.hashed_password)
    
    def test_verify_correct_password(self, test_db_session):
        """Test password verification with correct password"""
        plain_password = "TestPassword456"
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=pwd_context.hash(plain_password),
            role=UserRole.OPERATOR
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        
        assert pwd_context.verify(plain_password, user.hashed_password)
    
    def test_verify_incorrect_password(self, test_db_session):
        """Test password verification with incorrect password"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=pwd_context.hash("CorrectPassword"),
            role=UserRole.OPERATOR
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        
        assert not pwd_context.verify("WrongPassword", user.hashed_password)
    
    def test_user_login_success(self, test_db_session):
        """Test successful user login"""
        plain_password = "LoginPassword123"
        user = User(
            username="loginuser",
            email="login@example.com",
            hashed_password=pwd_context.hash(plain_password),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        
        # Simulate login
        db_user = test_db_session.query(User).filter(User.username == "loginuser").first()
        assert db_user is not None
        assert pwd_context.verify(plain_password, db_user.hashed_password)
        assert db_user.is_active is True
    
    def test_user_login_inactive_account(self, test_db_session):
        """Test login with inactive account"""
        user = User(
            username="inactiveuser",
            email="inactive@example.com",
            hashed_password=pwd_context.hash("Password123"),
            role=UserRole.VIEWER,
            is_active=False
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        
        db_user = test_db_session.query(User).filter(User.username == "inactiveuser").first()
        assert db_user is not None
        assert db_user.is_active is False
    
    def test_user_login_nonexistent(self, test_db_session):
        """Test login with nonexistent username"""
        user = test_db_session.query(User).filter(User.username == "nonexistent").first()
        assert user is None
    
    def test_update_last_login(self, test_db_session, sample_user):
        """Test updating last login timestamp"""
        original_last_login = sample_user.last_login
        
        sample_user.last_login = datetime.utcnow()
        test_db_session.commit()
        test_db_session.refresh(sample_user)
        
        assert sample_user.last_login is not None
        if original_last_login:
            assert sample_user.last_login > original_last_login


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self, test_settings):
        """Test creating JWT access token"""
        data = {"sub": "testuser", "role": "admin"}
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            test_settings.jwt_secret_key,
            algorithm=test_settings.jwt_algorithm
        )
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_decode_valid_token(self, test_settings):
        """Test decoding valid JWT token"""
        data = {"sub": "testuser", "role": "admin"}
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            test_settings.jwt_secret_key,
            algorithm=test_settings.jwt_algorithm
        )
        
        decoded = jwt.decode(
            token,
            test_settings.jwt_secret_key,
            algorithms=[test_settings.jwt_algorithm]
        )
        
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"
    
    def test_decode_expired_token(self, test_settings):
        """Test decoding expired JWT token"""
        data = {"sub": "testuser", "role": "admin"}
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() - timedelta(minutes=1)},  # Expired
            test_settings.jwt_secret_key,
            algorithm=test_settings.jwt_algorithm
        )
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )
    
    def test_decode_invalid_token(self, test_settings):
        """Test decoding invalid JWT token"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(jwt.DecodeError):
            jwt.decode(
                invalid_token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )
    
    def test_decode_token_wrong_secret(self, test_settings):
        """Test decoding token with wrong secret key"""
        data = {"sub": "testuser", "role": "admin"}
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            "wrong_secret_key",
            algorithm=test_settings.jwt_algorithm
        )
        
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )
    
    def test_token_with_custom_claims(self, test_settings):
        """Test token with custom claims"""
        data = {
            "sub": "testuser",
            "role": "operator",
            "permissions": ["read", "write"],
            "node_access": [1, 2, 3]
        }
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            test_settings.jwt_secret_key,
            algorithm=test_settings.jwt_algorithm
        )
        
        decoded = jwt.decode(
            token,
            test_settings.jwt_secret_key,
            algorithms=[test_settings.jwt_algorithm]
        )
        
        assert decoded["permissions"] == ["read", "write"]
        assert decoded["node_access"] == [1, 2, 3]


@pytest.mark.unit
class TestRBAC:
    """Test Role-Based Access Control"""
    
    def test_admin_role_permissions(self, test_db_session):
        """Test admin role has full permissions"""
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=pwd_context.hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        
        test_db_session.add(admin)
        test_db_session.commit()
        
        assert admin.role == UserRole.ADMIN
        # Admin should have all permissions
        assert admin.role.value == "admin"
    
    def test_operator_role_permissions(self, test_db_session):
        """Test operator role has limited permissions"""
        operator = User(
            username="operator",
            email="operator@example.com",
            hashed_password=pwd_context.hash("operator123"),
            role=UserRole.OPERATOR,
            is_active=True
        )
        
        test_db_session.add(operator)
        test_db_session.commit()
        
        assert operator.role == UserRole.OPERATOR
        assert operator.role.value == "operator"
    
    def test_viewer_role_permissions(self, test_db_session):
        """Test viewer role has read-only permissions"""
        viewer = User(
            username="viewer",
            email="viewer@example.com",
            hashed_password=pwd_context.hash("viewer123"),
            role=UserRole.VIEWER,
            is_active=True
        )
        
        test_db_session.add(viewer)
        test_db_session.commit()
        
        assert viewer.role == UserRole.VIEWER
        assert viewer.role.value == "viewer"
    
    def test_check_user_permission_admin(self):
        """Test permission checking for admin user"""
        def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
            role_hierarchy = {
                UserRole.ADMIN: 3,
                UserRole.OPERATOR: 2,
                UserRole.VIEWER: 1
            }
            return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
        
        # Admin should have all permissions
        assert has_permission(UserRole.ADMIN, UserRole.VIEWER)
        assert has_permission(UserRole.ADMIN, UserRole.OPERATOR)
        assert has_permission(UserRole.ADMIN, UserRole.ADMIN)
    
    def test_check_user_permission_operator(self):
        """Test permission checking for operator user"""
        def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
            role_hierarchy = {
                UserRole.ADMIN: 3,
                UserRole.OPERATOR: 2,
                UserRole.VIEWER: 1
            }
            return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
        
        # Operator should have operator and viewer permissions
        assert has_permission(UserRole.OPERATOR, UserRole.VIEWER)
        assert has_permission(UserRole.OPERATOR, UserRole.OPERATOR)
        assert not has_permission(UserRole.OPERATOR, UserRole.ADMIN)
    
    def test_check_user_permission_viewer(self):
        """Test permission checking for viewer user"""
        def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
            role_hierarchy = {
                UserRole.ADMIN: 3,
                UserRole.OPERATOR: 2,
                UserRole.VIEWER: 1
            }
            return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)
        
        # Viewer should only have viewer permissions
        assert has_permission(UserRole.VIEWER, UserRole.VIEWER)
        assert not has_permission(UserRole.VIEWER, UserRole.OPERATOR)
        assert not has_permission(UserRole.VIEWER, UserRole.ADMIN)
    
    def test_role_based_resource_access(self, test_db_session):
        """Test role-based access to resources"""
        users = [
            User(username="admin1", email="admin1@example.com", 
                 hashed_password="hash", role=UserRole.ADMIN),
            User(username="operator1", email="operator1@example.com",
                 hashed_password="hash", role=UserRole.OPERATOR),
            User(username="viewer1", email="viewer1@example.com",
                 hashed_password="hash", role=UserRole.VIEWER),
        ]
        
        test_db_session.add_all(users)
        test_db_session.commit()
        
        # Query users by role
        admins = test_db_session.query(User).filter(User.role == UserRole.ADMIN).all()
        operators = test_db_session.query(User).filter(User.role == UserRole.OPERATOR).all()
        viewers = test_db_session.query(User).filter(User.role == UserRole.VIEWER).all()
        
        assert len(admins) >= 1
        assert len(operators) >= 1
        assert len(viewers) >= 1
    
    def test_update_user_role(self, test_db_session, sample_user):
        """Test updating user role"""
        original_role = sample_user.role
        
        sample_user.role = UserRole.ADMIN
        test_db_session.commit()
        test_db_session.refresh(sample_user)
        
        assert sample_user.role == UserRole.ADMIN
        assert sample_user.role != original_role


@pytest.mark.unit
class TestUserManagement:
    """Test user management operations"""
    
    def test_create_user_unique_username(self, test_db_session, sample_user):
        """Test that username must be unique"""
        from sqlalchemy.exc import IntegrityError
        
        duplicate_user = User(
            username=sample_user.username,  # Same username
            email="different@example.com",
            hashed_password="hash",
            role=UserRole.VIEWER
        )
        
        test_db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    def test_create_user_unique_email(self, test_db_session, sample_user):
        """Test that email must be unique"""
        from sqlalchemy.exc import IntegrityError
        
        duplicate_user = User(
            username="different_user",
            email=sample_user.email,  # Same email
            hashed_password="hash",
            role=UserRole.VIEWER
        )
        
        test_db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    def test_deactivate_user(self, test_db_session, sample_user):
        """Test deactivating user account"""
        sample_user.is_active = False
        test_db_session.commit()
        test_db_session.refresh(sample_user)
        
        assert sample_user.is_active is False
    
    def test_reactivate_user(self, test_db_session):
        """Test reactivating user account"""
        user = User(
            username="reactivate_test",
            email="reactivate@example.com",
            hashed_password="hash",
            role=UserRole.VIEWER,
            is_active=False
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        user.is_active = True
        test_db_session.commit()
        test_db_session.refresh(user)
        
        assert user.is_active is True
    
    def test_delete_user(self, test_db_session):
        """Test deleting user account"""
        user = User(
            username="delete_test",
            email="delete@example.com",
            hashed_password="hash",
            role=UserRole.VIEWER
        )
        test_db_session.add(user)
        test_db_session.commit()
        user_id = user.id
        
        test_db_session.delete(user)
        test_db_session.commit()
        
        deleted_user = test_db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None
    
    def test_get_all_active_users(self, test_db_session):
        """Test retrieving all active users"""
        users = [
            User(username=f"user{i}", email=f"user{i}@example.com",
                 hashed_password="hash", role=UserRole.VIEWER,
                 is_active=(i % 2 == 0))
            for i in range(10)
        ]
        test_db_session.add_all(users)
        test_db_session.commit()
        
        active_users = test_db_session.query(User).filter(User.is_active == True).all()
        
        assert len(active_users) >= 5
    
    def test_user_audit_log_relationship(self, test_db_session, sample_user):
        """Test user-audit log relationship"""
        from backend.database.models import AuditLog
        
        audit = AuditLog(
            user_id=sample_user.id,
            action="login",
            resource_type="auth",
            status="success",
            ip_address="192.168.1.100"
        )
        test_db_session.add(audit)
        test_db_session.commit()
        test_db_session.refresh(audit)
        
        assert audit.user is not None
        assert audit.user_id == sample_user.id
        assert audit in sample_user.audit_logs


@pytest.mark.unit
class TestPasswordSecurity:
    """Test password security features"""
    
    def test_password_hashing_uniqueness(self):
        """Test that same password produces different hashes"""
        password = "TestPassword123"
        
        hash1 = pwd_context.hash(password)
        hash2 = pwd_context.hash(password)
        
        # Different hashes due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert pwd_context.verify(password, hash1)
        assert pwd_context.verify(password, hash2)
    
    def test_password_hash_length(self):
        """Test password hash has appropriate length"""
        password = "TestPassword123"
        hashed = pwd_context.hash(password)
        
        # Bcrypt hashes are typically 60 characters
        assert len(hashed) >= 50
    
    def test_weak_password_detection(self):
        """Test weak password detection (custom implementation)"""
        def is_weak_password(password: str) -> bool:
            if len(password) < 8:
                return True
            if not any(c.isupper() for c in password):
                return True
            if not any(c.islower() for c in password):
                return True
            if not any(c.isdigit() for c in password):
                return True
            return False
        
        assert is_weak_password("weak")
        assert is_weak_password("weakpassword")
        assert is_weak_password("WEAKPASSWORD123")
        assert is_weak_password("weakpassword123")
        assert not is_weak_password("StrongPass123")
    
    def test_password_change_requires_old_password(self, test_db_session):
        """Test password change flow"""
        old_password = "OldPassword123"
        user = User(
            username="pwdchange",
            email="pwdchange@example.com",
            hashed_password=pwd_context.hash(old_password),
            role=UserRole.VIEWER
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        # Verify old password before change
        assert pwd_context.verify(old_password, user.hashed_password)
        
        # Change password
        new_password = "NewPassword456"
        user.hashed_password = pwd_context.hash(new_password)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        # Verify new password works
        assert pwd_context.verify(new_password, user.hashed_password)
        # Verify old password no longer works
        assert not pwd_context.verify(old_password, user.hashed_password)
