"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".
"""

from django.test import TestCase
from django.core.urlresolvers import reverse

import views
import re

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

    def test_score_equation_is_not_negative(self):
        """
        Tests that the score equation doesn't return a value smaller than zero even if inputs are negative.
        """
        self.assertTrue(views.score_equation(0, -10, -30) >= 0)
        
    def test_only_GET_for_api(self):
        """
        Tests that a POST request doesn't go through our GET API calls
        """
        response = self.client.post(reverse(views.api_user_timeline))
        self.assertNotEqual(response.status_code, 200)

        response = self.client.post(reverse(views.api_user_score))
        self.assertNotEqual(response.status_code, 200)
        
    def test_homepage_has_no_error(self):
        """
        Tests that the HTML page doesn't contain the word 'error' (before API calls)
        and status code was 200 (ie. normal)
        """
        response = self.client.get(reverse(views.home))
        self.assertNotContains(response, "error", status_code=200)
        
    def test_sorted_timeline(self):
        """
        Tests that the timeline is well sorted when using the argument sorting=byRetweet (using screen_name=dbinay)
        """
        response = self.client.get('/api/user_timeline.json?screen_name=dbinay&sorting=byRetweet')
        count_list = re.findall(r'"retweet_count": (\d+),', str(response))
        
        self.assertTrue(all(count_list[i] >= count_list[i+1] for i in xrange(len(count_list)-1)))