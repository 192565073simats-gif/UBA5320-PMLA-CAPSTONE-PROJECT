# Test student CRUD operations using TestClient
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from main import app, _seed_admin
from database import create_tables

create_tables()
_seed_admin()
client = TestClient(app)


class TestStudentAPI:
    def setup_method(self):
        """Login and get token before each test"""
        response = client.post("/api/auth/token",
                               data={"username": "admin", "password": "admin123"})
        self.token = response.json().get("access_token", "")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_create_student(self):
        response = client.post("/api/students/",
                               json={"student_id": "TEST001", "name": "Test Student",
                                     "department": "Computer Science", "year": 3, "semester": 5},
                               headers=self.headers)
        assert response.status_code in [200, 201]

    def test_duplicate_student_rejected(self):
        # Create once
        client.post("/api/students/",
                    json={"student_id": "DUPTEST001", "name": "Dup Test",
                          "department": "CS", "year": 1, "semester": 1},
                    headers=self.headers)
        # Create again with same student_id
        response = client.post("/api/students/",
                               json={"student_id": "DUPTEST001", "name": "Dup Test 2",
                                     "department": "CS", "year": 1, "semester": 1},
                               headers=self.headers)
        assert response.status_code == 400

    def test_list_students(self):
        response = client.get("/api/students/", headers=self.headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_search_student(self):
        response = client.get("/api/students/?search=Test", headers=self.headers)
        assert response.status_code == 200
