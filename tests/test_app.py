"""
Backend tests for Mergington High School Activities API.

Uses pytest with the Arrange-Act-Assert (AAA) pattern for structured test cases.
Each test isolates state by resetting the activities database before execution.
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


# Store the initial state of activities for resetting between tests
INITIAL_ACTIVITIES = copy.deepcopy(activities)


@pytest.fixture
def client():
    """Provide a TestClient instance and reset activities state before each test."""
    # Arrange: Reset activities to initial state
    activities.clear()
    activities.update(copy.deepcopy(INITIAL_ACTIVITIES))
    
    yield TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint."""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities with participant data."""
        # Arrange
        expected_activity_names = {
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Soccer Club",
            "Art Club",
            "Drama Club",
            "Math Olympiad",
            "Science Club",
        }
        
        # Act
        response = client.get("/activities")
        data = response.json()
        
        # Assert
        assert response.status_code == 200
        assert set(data.keys()) == expected_activity_names
        
        # Verify each activity has required fields and participants list
        for activity_name, details in data.items():
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)
            assert len(details["participants"]) > 0  # All activities have initial participants


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_new_participant_success(self, client):
        """Test that a new participant can successfully sign up for an activity."""
        # Arrange
        activity_name = "Chess Club"
        email = "new_student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {email} for {activity_name}"
        assert email in activities[activity_name]["participants"]
    
    def test_signup_duplicate_returns_400(self, client):
        """Test that signing up with a duplicate email returns HTTP 400."""
        # Arrange
        activity_name = "Chess Club"
        email = activities[activity_name]["participants"][0]  # Use existing participant
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up"
    
    def test_signup_nonexistent_activity_returns_404(self, client):
        """Test that signing up for a non-existent activity returns HTTP 404."""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"
        
        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/participants endpoint."""
    
    def test_unregister_participant_success(self, client):
        """Test that an existing participant can be successfully unregistered."""
        # Arrange
        activity_name = "Programming Class"
        email = activities[activity_name]["participants"][0]  # Use existing participant
        initial_count = len(activities[activity_name]["participants"])
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Removed {email} from {activity_name}"
        assert email not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count - 1
    
    def test_unregister_nonexistent_participant_returns_400(self, client):
        """Test that unregistering a non-existent participant returns HTTP 400."""
        # Arrange
        activity_name = "Gym Class"
        email = "nonexistent@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Student not signed up"
    
    def test_unregister_from_nonexistent_activity_returns_404(self, client):
        """Test that unregistering from a non-existent activity returns HTTP 404."""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"
        
        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"


class TestIntegration:
    """Integration tests covering signup and unregister workflows."""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test a complete workflow: signup, verify, unregister, verify removal."""
        # Arrange
        activity_name = "Art Club"
        email = "integration_test@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])
        
        # Act: Sign up
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Assert: Signup succeeded
        assert signup_response.status_code == 200
        assert email in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count + 1
        
        # Act: Unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/participants",
            params={"email": email}
        )
        
        # Assert: Unregister succeeded and state restored
        assert unregister_response.status_code == 200
        assert email not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count
    
    def test_get_activities_reflects_signup_changes(self, client):
        """Test that GET /activities reflects participant updates after signup."""
        # Arrange
        activity_name = "Soccer Club"
        email = "test_changes@mergington.edu"
        
        # Act: Get initial state
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity_name]["participants"].copy()
        
        # Sign up
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Get updated state
        updated_response = client.get("/activities")
        updated_participants = updated_response.json()[activity_name]["participants"]
        
        # Assert: Changes reflected in API response
        assert len(updated_participants) == len(initial_participants) + 1
        assert email in updated_participants
