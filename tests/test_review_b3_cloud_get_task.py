import json
import unittest

from spinqit.backend.spinq_cloud_backend import SpinQCloudBackend


class CloudGetTaskRegressionTest(unittest.TestCase):
    def test_get_task_reconstructs_task_fields(self):
        class Response:
            status_code = 200
            content = json.dumps({
                'task': {
                    'tname': 'demo',
                    'platformCode': 'offline',
                    'bitNum': 2,
                    'clbitNum': 1,
                    'calcMatrix': True,
                    'shots': 100,
                    'description': 'offline fixture',
                    'tcode': 'T-1',
                    'tstatus': 'S',
                    'createdTime': None,
                }
            }).encode()

            def __bool__(self):
                return True

        class Client:
            @staticmethod
            def get_task_by_code(_task_code):
                return Response()

        backend = object.__new__(SpinQCloudBackend)
        backend._api_client = Client()

        task = backend.get_task('T-1')
        values = task.to_dict()

        self.assertEqual(values['bitNum'], 2)
        self.assertEqual(values['clbitNum'], 1)
        self.assertEqual(values['shots'], 100)
        self.assertIs(values['calc_matrix'], True)
        self.assertEqual(task.task_code, 'T-1')
        self.assertEqual(task.status, 'S')


if __name__ == '__main__':
    unittest.main()
