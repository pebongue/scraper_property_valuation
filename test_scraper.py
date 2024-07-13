import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from scrap_properties import (
    scrape_data, clean_data, store_data, Property, run_scraper, send_alert
)

class TestScraperFunctions(unittest.TestCase):

    def test_scrape_data_success(self):
        with patch('requests.Session.post') as mock_post:
            mock_response = MagicMock()
            mock_response.text = '<html><div class="property"><span class="description">Test Property</span><span class="address">123 Test St</span><span class="extent">100.5</span><span class="value">500000</span></div></html>'
            mock_post.return_value = mock_response

            result = scrape_data('Full Title Property', '1')
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['property_description'], 'Test Property')

    def test_scrape_data_network_error(self):
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.RequestException("Network error")
            with patch('scrap_properties.logger.error') as mock_logger:
                result = scrape_data('Full Title Property', '1')
                self.assertIsNone(result)
                mock_logger.assert_called_once()

    def test_clean_data(self):
        test_data = [
            {
                'property_type': ' Full Title Property ',
                'volume_no': ' 1 ',
                'property_description': ' Test Property ',
                'street_address': ' 123 Test St ',
                'extent': 100.5555,
                'market_value': 500000.7777,
            }
        ]
        result = clean_data(test_data)
        self.assertEqual(result[0]['property_type'], 'Full Title Property')
        self.assertEqual(result[0]['extent'], 100.56)
        self.assertEqual(result[0]['market_value'], 500000.78)

    @patch('scrap_properties.Session')
    def test_store_data_success(self, mock_session):
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        test_data = [
            {
                'property_type': 'Full Title Property',
                'volume_no': '1',
                'property_description': 'Test Property',
                'street_address': '123 Test St',
                'extent': 100.56,
                'market_value': 500000.78,
            }
        ]

        store_data(test_data)
        mock_session_instance.add.assert_called_once()
        mock_session_instance.commit.assert_called_once()

    @patch('scrap_properties.Session')
    def test_store_data_error(self, mock_session):
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.commit.side_effect = Exception("Database error")

        with patch('scrap_properties.logger.error') as mock_logger:
            store_data([{}])
            mock_session_instance.rollback.assert_called_once()
            mock_logger.assert_called_once()

    @patch('scrap_properties.scrape_data')
    @patch('scrap_properties.clean_data')
    @patch('scrap_properties.store_data')
    def test_run_scraper(self, mock_store, mock_clean, mock_scrape):
        mock_scrape.return_value = [{'test': 'data'}]
        mock_clean.return_value = [{'cleaned': 'data'}]

        run_scraper()

        self.assertEqual(mock_scrape.call_count, 20)
        self.assertEqual(mock_clean.call_count, 20)
        self.assertEqual(mock_store.call_count, 20)

    @patch('smtplib.SMTP')
    def test_send_alert(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        send_alert("Test Subject", "Test Message")

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

if __name__ == '__main__':
    unittest.main()