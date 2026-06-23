import unittest
import json
import io
from app import app
import db

class TestEduPortalFlaskAPI(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'
        self.client = app.test_client()
        
        # Ensure default seed data exists
        db.seed_default_users()

    def test_unauthenticated_redirect(self):
        """Verify accessing root redirects to login when not authenticated."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_login_invalid_credentials(self):
        """Verify invalid logins display failure alerts."""
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username or password', response.data)

    def test_login_success_admin(self):
        """Verify successful admin login redirects appropriately."""
        with self.client:
            response = self.client.post('/login', data={
                'username': 'admin',
                'password': 'admin123'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Admin Dashboard', response.data)
            from flask import session
            self.assertIn('user', session)
            self.assertEqual(session.get('user')['username'], 'admin')

    def test_admin_metrics_endpoint_unauthorized(self):
        """Verify unauthorized users are blocked from admin metrics endpoint."""
        response = self.client.get('/api/admin/metrics')
        self.assertEqual(response.status_code, 401)

    def test_admin_create_question_and_delete(self):
        """Verify CRUD questions operations via the Flask API."""
        # 1. Login as Admin
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
        # 2. Add MCQ Question
        response = self.client.post('/api/admin/question/add', data={
            'type': 'Multiple Choice',
            'title': 'Test API Question',
            'text': 'What is the default port for Flask?',
            'opt_a': '5000',
            'opt_b': '8501',
            'opt_c': '8000',
            'opt_d': '27017',
            'correct_option': '["A"]',
            'marks': '5',
            'difficulty': 'Easy',
            'explanation': 'Flask runs on 5000 by default.'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')

        # 3. Retrieve Questions & Find newly added one
        response = self.client.get('/api/admin/questions')
        self.assertEqual(response.status_code, 200)
        questions = json.loads(response.data)
        
        test_q = next((q for q in questions if q['title'] == 'Test API Question'), None)
        self.assertIsNotNone(test_q)
        self.assertEqual(test_q['type'], 'Multiple Choice')
        self.assertEqual(test_q['marks'], 5)
        self.assertEqual(test_q['options']['A'], '5000')

        # 4. Clean up: Delete it
        del_response = self.client.post(f"/api/admin/question/delete/{test_q['id']}")
        self.assertEqual(del_response.status_code, 200)
        del_data = json.loads(del_response.data)
        self.assertEqual(del_data['status'], 'ok')

    def test_student_exam_state_cycle(self):
        """Verify student exam start, autosaving answers, and session deletion."""
        # 1. Login as Student
        self.client.post('/login', data={'username': 'student1', 'password': 'student123'})

        # 2. Get lobby questions
        response = self.client.get('/api/student/questions')
        self.assertEqual(response.status_code, 200)
        questions = json.loads(response.data)
        self.assertTrue(len(questions) > 0)

        # 3. Start Exam
        start_response = self.client.post('/api/student/start_exam', json={
            'student_id': 'TEST-123',
            'student_email': 'test@test.com',
            'student_name': 'Test Student'
        })
        self.assertEqual(start_response.status_code, 200)
        
        # 4. Save state answers
        save_response = self.client.post('/api/student/save_state', json={
            'current_question_index': 1,
            'answers': {
                questions[0]['id']: {
                    'answer_type': 'Text',
                    'answer_text': 'This is a test written response'
                }
            }
        })
        self.assertEqual(save_response.status_code, 200)

        # 5. Fetch state & verify it preserved correctly
        get_response = self.client.get('/api/student/get_state')
        self.assertEqual(get_response.status_code, 200)
        state_data = json.loads(get_response.data)
        self.assertEqual(state_data['state']['current_question_index'], 1)
        self.assertEqual(
            state_data['state']['answers'][questions[0]['id']]['answer_text'], 
            'This is a test written response'
        )

        # 6. Cancel exam (clean up)
        cancel_response = self.client.post('/api/student/cancel_exam')
        self.assertEqual(cancel_response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
