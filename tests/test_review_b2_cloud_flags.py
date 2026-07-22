import contextlib
import io
import json
import unittest

from spinqit import Circuit, H, get_compiler
from spinqit.backend.spinq_cloud_backend import SpinQCloudBackend, SpinQCloudConfig
from spinqit.model.spinqCloud.gate import H as CloudH
from spinqit.model.spinqCloud.platform import Platform


class CloudFlagsRegressionTest(unittest.TestCase):
    def test_submit_uses_density_matrix_and_process_flags_from_config(self):
        circuit = Circuit('cloud-flags')
        circuit.allocateQubits(1)
        circuit << (H, 0)
        ir = get_compiler('native').compile(circuit, 0)

        backend = object.__new__(SpinQCloudBackend)
        backend._api_client = None
        backend._platforms = [
            Platform(
                'offline', 'offline', 1, machine_count=0, gate_list=[CloudH],
                coupling_map=[], simu=True, active_qubits=[0],
            )
        ]
        config = SpinQCloudConfig()
        config.configure_platform('offline')
        config.configure_density_matrix(True)
        config.configure_process_now(False)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            backend.submit_task(ir, config, debug=True)
        request = json.loads(output.getvalue().splitlines()[-1])

        self.assertIs(request['calcMatrix'], True)
        self.assertIs(request['proceedNow'], False)


if __name__ == '__main__':
    unittest.main()
