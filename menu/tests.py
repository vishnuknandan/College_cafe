from django.test import TestCase
from django.urls import reverse

class PasswordResetTests(TestCase):
    def test_password_reset_url_resolves(self):
        url = reverse('password_reset')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/password_reset_form.html')
        # Check if email template exists (by trying to get the view attributes)
        from django.urls import resolve
        resolved_func = resolve(url).func
        self.assertEqual(resolved_func.view_initkwargs['email_template_name'], 'menu/password_reset_email.html')
        self.assertEqual(resolved_func.view_initkwargs['subject_template_name'], 'menu/password_reset_subject.txt')



    def test_password_reset_done_url_resolves(self):
        url = reverse('password_reset_done')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/password_reset_done.html')

    def test_password_reset_complete_url_resolves(self):
        url = reverse('password_reset_complete')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/password_reset_complete.html')
