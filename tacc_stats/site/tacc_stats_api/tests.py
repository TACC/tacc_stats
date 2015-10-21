from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

import json

class TokenTests(APITestCase):

	def setUp(self):
		"""
		Set up resources needed for this token tests
		"""
		UserModel = get_user_model()
		self.user = UserModel.objects.create_user(username='test', first_name='First', last_name='Last', email='')
	
	def test_get_token_unauthorized(self):
	    """
	    Ensure get token throws 401 w/o authentication.
	    """
	    response = self.client.get('/api/token/')
	    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_post_token_unauthorized(self):
	    """
	    Ensure post token throws 401 w/o authentication.
	    """
	    response = self.client.post('/api/token/', {}, format='json')
	    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_delete_token_unauthorized(self):
	    """
	    Ensure delete token throws 401 w/o authentication.
	    """
	    response = self.client.delete('/api/token/some_random_key/')
	    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_get_token(self):
	    """
	    Ensure get token requires authentication.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/token/')
	    self.assertEqual(response.status_code, status.HTTP_200_OK)
	    result = response.data.get('result', None)
	    self.assertTrue(result is not None)
	    key = result.get('key', None)
	    self.assertTrue(key is not None)

	def test_post_token(self):
	    """
	    Ensure post token requires authentication.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.post('/api/token/refresh/', {}, format='json')
	    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
	    result = response.data.get('result', None)
	    self.assertTrue(result is not None)
	    key = result.get('key', None)
	    self.assertTrue(key is not None)

	def test_delete_token(self):
	    """
	    Ensure delete token requires authentication.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/token/')
	    result = response.data.get('result', None)
	    key = result.get('key', None)
	    response = self.client.delete('/api/token/%s/' % key)
	    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
	    self.assertTrue(response.data.get('result', None) is None)


class ThresholdTests(APITestCase):
	fixtures = ['machine_testdata.json']
	def setUp(self):
		"""
		Set up resources needed for this threshold tests
		"""
		UserModel = get_user_model()
		self.user = UserModel.objects.create_user(username='test', first_name='First', last_name='Last', email='')
	
	def test_get_thresholds(self):
	    """
	    Ensure get thresholds for a default resource.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/thresholds/wrangler')
	    self.assertEqual(response.status_code, status.HTTP_200_OK)
	    result = response.data.get('result')
	    self.assertTrue(result is not None)
	    self.assertTrue(len(result) > 0)

	def test_post_threshold_non_staff(self):
	    """
	    Ensure create threshold throws 403 w/a staff user.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.post('/api/thresholds/stampede', { "test_name": "TestThreshold", "field_name": "test_threshold", "threshold": 1, "comparator": ">" }, format='json')
	    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_post_threshold(self):
	    """
	    Ensure create threshold for a default resource.
	    """
	    self.user.is_staff = True
	    self.client.force_authenticate(user=self.user)
	    response = self.client.post('/api/thresholds/stampede', { "test_name": "TestThreshold", "field_name": "test_threshold", "threshold": 1, "comparator": ">" }, format='json')
	    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
	    result = response.data.get('result', None)
	    self.assertTrue(result is not None)

class JobTests(APITestCase):
	fixtures = ['machine_testdata.json']
	def setUp(self):
		"""
		Set up resources needed for this job tests
		"""
		UserModel = get_user_model()
		self.user = UserModel.objects.create_user(username='ericni', first_name='First', last_name='Last', email='')
	
	def test_get_jobs(self):
	    """
	    Ensure we get jobs for a resource applying user filter.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/jobs/wrangler?user=ericni')
	    self.assertEqual(response.status_code, status.HTTP_200_OK)
	    result = response.data.get('results')
	    self.assertTrue(result is not None)
	    #returns 100 jobs per page
	    self.assertTrue(len(result) == 100)
	
	def test_get_job(self):
	    """
	    Ensure get job for a job id.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/jobs/1942/wrangler')
	    self.assertEqual(response.status_code, status.HTTP_200_OK)
	    result = response.data.get('result')
	    self.assertTrue(result is not None)
	    self.assertTrue(result.get('id', None) == 1942)

	def test_get_flagged_jobs(self):
	    """
	    Ensure get flagged jobs for a resource applying user filter.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/flagged-jobs/wrangler?user=ericni')
	    self.assertEqual(response.status_code, status.HTTP_200_OK)
	    result = response.data.get('result')
	    self.assertTrue(result is not None)
	    self.assertTrue(len(result.get('load_llc_hits')) > 1)

	def test_get_characteristics_plot(self):
	    """
	    Ensure we get characteristics plot for a resource applying user filter.
	    """
	    self.client.force_authenticate(user=self.user)
	    response = self.client.get('/api/characteristics-plot/wrangler?user=ericni')
	    self.assertEqual(response.status_code, status.HTTP_200_OK)
	    api_status = response.data.get('status')
	    self.assertEqual(api_status, 'success')
	    result = response.data.get('result', None)
	    self.assertTrue(result is not None)
