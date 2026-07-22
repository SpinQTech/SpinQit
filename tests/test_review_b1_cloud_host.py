import importlib
import unittest
from unittest.mock import patch

from spinqit.backend.backend import check_backend_and_config


class CloudHostRegressionTest(unittest.TestCase):
    def test_cloud_factory_passes_configured_host(self):
        backend_module = importlib.import_module('spinqit.backend.backend')
        with patch.object(backend_module, 'SpinQCloudBackend') as backend_class:
            backend, _ = check_backend_and_config(
                'cloud',
                username='offline',
                keyfile='/unused',
                host='https://example.invalid',
            )

        backend_class.assert_called_once_with('offline', '/unused', 'https://example.invalid')
        self.assertIs(backend, backend_class.return_value)


if __name__ == '__main__':
    unittest.main()
