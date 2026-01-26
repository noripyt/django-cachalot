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
        # Support both old (store_id) and new (request_id) debug toolbar APIs
        if 'data-request-id' in toolbar.attrs:
            # django-debug-toolbar 6.x
            request_id = toolbar.attrs['data-request-id']
            UUID(request_id)
            render_panel_url = toolbar.attrs['data-render-panel-url']
            panel_id = soup.find(title='Cachalot')['class'][0]
            panel_url = f'{render_panel_url}?request_id={request_id}&panel_id={panel_id}'
        else:
            # django-debug-toolbar < 6.0
            store_id = toolbar.attrs['data-store-id']
            UUID(store_id)
            render_panel_url = toolbar.attrs['data-render-panel-url']
            panel_id = soup.find(title='Cachalot')['class'][0]
            panel_url = f'{render_panel_url}?store_id={store_id}&panel_id={panel_id}'

        #
        # Rendering panel
        #
        panel_response = self.client.get(panel_url)
        self.assertEqual(panel_response.status_code, 200)
        # TODO: Check that the displayed data is correct.
