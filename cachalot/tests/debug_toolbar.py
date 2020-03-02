from uuid import UUID
from bs4 import BeautifulSoup
from django.conf import settings
from django.test import LiveServerTestCase, override_settings


@override_settings(DEBUG=True)
class DebugToolbarTestCase(LiveServerTestCase):
    databases = set(settings.DATABASES.keys())

    def test_rendering(self):
        #
        # Rendering toolbar
        #
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content.decode('utf-8'), 'html.parser')
        toolbar = soup.find(id='djDebug')
        self.assertIsNotNone(toolbar)
        store_id = toolbar.attrs['data-store-id']
        # Checks that store_id is a valid UUID.
        UUID(store_id)
        render_panel_url = toolbar.attrs['data-render-panel-url']
        panel_id = soup.find(title='Cachalot')['class'][0]
        panel_url = ('%s?store_id=%s&panel_id=%s'
                     % (render_panel_url, store_id, panel_id))

        #
        # Rendering panel
        #
        panel_response = self.client.get(panel_url)
        self.assertEqual(panel_response.status_code, 200)
        # TODO: Check that the displayed data is correct.
