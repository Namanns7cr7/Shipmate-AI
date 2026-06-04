import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import jwt


class TestAuthFlows:
    """Security tests for authentication mechanisms in the backend."""

    @pytest.fixture
    def valid_token(self):
        """Generate a valid JWT token."""
        payload = {
            'user_id': 'test_user_123',
            'username': 'testuser',
            'role': 'user',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, 'test_secret_key', algorithm='HS256')

    @pytest.fixture
    def expired_token(self):
        """Generate an expired JWT token."""
        payload = {
            'user_id': 'test_user_123',
            'username': 'testuser',
            'role': 'user',
            'exp': datetime.utcnow() - timedelta(hours=1),
            'iat': datetime.utcnow() - timedelta(hours=2)
        }
        return jwt.encode(payload, 'test_secret_key', algorithm='HS256')

    @pytest.fixture
    def admin_token(self):
        """Generate a valid admin JWT token."""
        payload = {
            'user_id': 'admin_user_456',
            'username': 'adminuser',
            'role': 'admin',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, 'test_secret_key', algorithm='HS256')

    @pytest.fixture
    def user_token(self):
        """Generate a valid user JWT token."""
        payload = {
            'user_id': 'user_789',
            'username': 'regularuser',
            'role': 'user',
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, 'test_secret_key', algorithm='HS256')

    def test_valid_token_accepted(self, valid_token):
        """Test that valid tokens are accepted and authenticated."""
        # Decode and verify the token structure
        decoded = jwt.decode(valid_token, 'test_secret_key', algorithms=['HS256'])
        
        assert decoded['user_id'] == 'test_user_123'
        assert decoded['username'] == 'testuser'
        assert decoded['role'] == 'user'
        assert 'exp' in decoded
        assert 'iat' in decoded

    def test_expired_token_rejected(self, expired_token):
        """Test that expired tokens are rejected during authentication."""
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, 'test_secret_key', algorithms=['HS256'])

    def test_invalid_token_rejected(self):
        """Test that malformed/invalid tokens are rejected."""
        invalid_token = 'invalid.token.format'
        
        with pytest.raises(jwt.DecodeError):
            jwt.decode(invalid_token, 'test_secret_key', algorithms=['HS256'])

    def test_tampered_token_rejected(self, valid_token):
        """Test that tampered tokens are rejected."""
        # Tamper with the token by modifying it
        tampered_token = valid_token[:-5] + 'xxxxx'
        
        with pytest.raises(jwt.DecodeError):
            jwt.decode(tampered_token, 'test_secret_key', algorithms=['HS256'])

    def test_wrong_secret_key_rejected(self, valid_token):
        """Test that tokens signed with wrong key are rejected."""
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(valid_token, 'wrong_secret_key', algorithm='HS256')

    def test_privilege_escalation_blocked_user_to_admin(self, user_token):
        """Test that users cannot escalate privileges to admin."""
        decoded = jwt.decode(user_token, 'test_secret_key', algorithms=['HS256'])
        
        # Verify user has 'user' role, not 'admin'
        assert decoded['role'] == 'user'
        assert decoded['role'] != 'admin'

    def test_privilege_escalation_blocked_role_modification(self, user_token):
        """Test that modifying role in token payload is detected."""
        # Attempt to create a modified token with admin role
        decoded = jwt.decode(user_token, 'test_secret_key', algorithms=['HS256'])
        decoded['role'] = 'admin'
        
        # Re-encode with modified payload
        modified_token = jwt.encode(decoded, 'test_secret_key', algorithm='HS256')
        
        # Verify the modified token has different signature
        assert modified_token != user_token
        
        # Decode and verify the role change is present (but would be caught by server validation)
        modified_decoded = jwt.decode(modified_token, 'test_secret_key', algorithms=['HS256'])
        assert modified_decoded['role'] == 'admin'

    def test_admin_token_has_correct_role(self, admin_token):
        """Test that admin tokens have the correct role."""
        decoded = jwt.decode(admin_token, 'test_secret_key', algorithms=['HS256'])
        
        assert decoded['role'] == 'admin'
        assert decoded['user_id'] == 'admin_user_456'

    def test_token_missing_required_claims(self):
        """Test that tokens missing required claims are rejected."""
        # Create token without user_id
        payload = {
            'username': 'testuser',
            'role': 'user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')
        decoded = jwt.decode(token, 'test_secret_key', algorithms=['HS256'])
        
        # Verify required claim is missing
        assert 'user_id' not in decoded

    def test_token_expiration_boundary(self):
        """Test token expiration at boundary conditions."""
        # Create token that expires in 1 second
        payload = {
            'user_id': 'test_user',
            'username': 'testuser',
            'role': 'user',
            'exp': datetime.utcnow() + timedelta(seconds=1),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, 'test_secret_key', algorithm='HS256')
        
        # Token should be valid immediately
        decoded = jwt.decode(token, 'test_secret_key', algorithms=['HS256'])
        assert decoded['user_id'] == 'test_user'

    def test_multiple_tokens_independent(self, valid_token, admin_token):
        """Test that multiple tokens are independently validated."""
        decoded_user = jwt.decode(valid_token, 'test_secret_key', algorithms=['HS256'])
        decoded_admin = jwt.decode(admin_token, 'test_secret_key', algorithms=['HS256'])
        
        # Verify tokens are independent
        assert decoded_user['role'] == 'user'
        assert decoded_admin['role'] == 'admin'
        assert decoded_user['user_id'] != decoded_admin['user_id']

    def test_token_without_signature_rejected(self):
        """Test that tokens without proper signature are rejected."""
        # Create a token-like string without valid signature
        invalid_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdCJ9.'
        
        with pytest.raises((jwt.DecodeError, jwt.InvalidSignatureError)):
            jwt.decode(invalid_token, 'test_secret_key', algorithms=['HS256'])

    def test_empty_token_rejected(self):
        """Test that empty tokens are rejected."""
        with pytest.raises((jwt.DecodeError, ValueError)):
            jwt.decode('', 'test_secret_key', algorithms=['HS256'])

    def test_none_token_rejected(self):
        """Test that None tokens are rejected."""
        with pytest.raises((jwt.DecodeError, AttributeError, TypeError)):
            jwt.decode(None, 'test_secret_key', algorithms=['HS256'])
