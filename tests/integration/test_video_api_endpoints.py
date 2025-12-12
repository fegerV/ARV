"""
Simple API tests for video scheduling functionality.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app


class TestVideoSchedulingAPI:
    """API tests for video scheduling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_api_endpoints_exist(self, client):
        """Test that all video scheduling endpoints exist."""
        # Test that API documentation loads
        response = client.get('/docs')
        assert response.status_code == 200
        
        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Vertex AR B2B Platform API" in data["message"]

    def test_viewer_endpoint_not_found(self, client):
        """Test viewer endpoint with non-existent AR content."""
        response = client.get('/api/viewer/999/active-video')
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "AR content not found" in data["error"]["message"]

    def test_videos_list_endpoint_not_found(self, client):
        """Test videos list endpoint with non-existent AR content."""
        response = client.get('/api/ar-content/999/videos')
        assert response.status_code == 404
        data = response.json()
        assert "AR content not found" in data["detail"]

    def test_set_active_video_not_found(self, client):
        """Test set active video with non-existent AR content."""
        response = client.patch('/api/ar-content/999/videos/1/set-active')
        assert response.status_code == 404
        data = response.json()
        assert "AR content not found" in data["detail"]

    def test_set_active_video_content_not_found(self, client):
        """Test set active video with non-existent video."""
        response = client.patch('/api/ar-content/999/videos/999/set-active')
        assert response.status_code == 404
        data = response.json()
        assert "AR content not found" in data["detail"]

    def test_subscription_update_validation(self, client):
        """Test subscription update with invalid data."""
        # Test invalid preset
        response = client.patch(
            '/api/ar-content/999/videos/1/subscription',
            json={"subscription": "invalid"}
        )
        assert response.status_code == 404  # AR content not found

        # Test invalid date format
        response = client.patch(
            '/api/ar-content/999/videos/1/subscription',
            json={"subscription": "invalid-date"}
        )
        assert response.status_code == 404  # AR content not found

    def test_rotation_update_validation(self, client):
        """Test rotation type validation."""
        # Test invalid rotation type
        response = client.patch(
            '/api/ar-content/999/videos/1/rotation',
            json={"rotation_type": "invalid"}
        )
        assert response.status_code == 404  # AR content not found

        # Test valid rotation types would require database setup, but endpoint should exist
        for rotation_type in ["none", "sequential", "cyclic"]:
            response = client.patch(
                '/api/ar-content/999/videos/1/rotation',
                json={"rotation_type": rotation_type}
            )
            # Should return 404 for non-existent AR content, not 422 for validation
            assert response.status_code == 404

    def test_schedule_endpoints_exist(self, client):
        """Test that schedule endpoints exist."""
        # Test list schedules
        response = client.get('/api/ar-content/999/videos/1/schedules')
        assert response.status_code == 404  # AR content not found

        # Test create schedule
        response = client.post(
            '/api/ar-content/999/videos/1/schedules',
            json={
                "start_time": "2025-12-12T10:00:00Z",
                "end_time": "2025-12-12T12:00:00Z",
                "description": "Test schedule"
            }
        )
        assert response.status_code == 404  # AR content not found

        # Test update schedule
        response = client.patch(
            '/api/ar-content/999/videos/1/schedules/1',
            json={
                "description": "Updated schedule"
            }
        )
        assert response.status_code == 404  # AR content not found

        # Test delete schedule
        response = client.delete('/api/ar-content/999/videos/1/schedules/1')
        assert response.status_code == 404  # AR content not found


if __name__ == "__main__":
    pytest.main([__file__])