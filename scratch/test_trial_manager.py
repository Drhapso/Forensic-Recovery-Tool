"""
Suite de Pruebas Unitarias para el Módulo de Licenciamiento y Temporizador Demo (TrialManager).
Verifica la inicialización del temporizador de 24h, cálculo de tiempo,
detección anti-rollback, firma HMAC y bloqueo permanente.
"""

import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.trial_manager import TrialManager, TRIAL_DURATION_SECONDS


class TestTrialManager(unittest.TestCase):

    def setUp(self):
        self.original_read_reg = TrialManager._read_from_registry
        self.original_save_reg = TrialManager._save_to_registry
        self.original_read_file = TrialManager._read_from_file
        self.original_save_file = TrialManager._save_to_file

        # Emular almacenes en memoria para pruebas aisladas
        self.mock_store = {}

        def mock_save_reg(payload):
            self.mock_store["reg"] = dict(payload)
            return True

        def mock_read_reg():
            return dict(self.mock_store["reg"]) if "reg" in self.mock_store else None

        def mock_save_file(payload):
            self.mock_store["file"] = dict(payload)
            return True

        def mock_read_file():
            return dict(self.mock_store["file"]) if "file" in self.mock_store else None

        TrialManager._save_to_registry = mock_save_reg
        TrialManager._read_from_registry = mock_read_reg
        TrialManager._save_to_file = mock_save_file
        TrialManager._read_from_file = mock_read_file

    def tearDown(self):
        TrialManager._read_from_registry = self.original_read_reg
        TrialManager._save_to_registry = self.original_save_reg
        TrialManager._read_from_file = self.original_read_file
        TrialManager._save_to_file = self.original_save_file

    def test_01_hwid_and_signature(self):
        """Verifica la generación de HWID y la firma HMAC criptográfica."""
        hwid = TrialManager.get_hardware_fingerprint()
        self.assertTrue(len(hwid) > 10, "El HWID debe ser un hash no vacío")

        payload = {"hwid": hwid, "test": 12345}
        sig = TrialManager._sign_payload(payload)
        self.assertTrue(TrialManager._verify_payload(payload, sig), "La firma debe ser válida")

        # Modificación de carga útil debe invalidar la firma
        tampered_payload = {"hwid": hwid, "test": 99999}
        self.assertFalse(TrialManager._verify_payload(tampered_payload, sig), "La firma alterada debe fallar")

    def test_02_first_run_initialization(self):
        """Verifica que la primera ejecución inicie la prueba con 24 horas completas."""
        status = TrialManager.check_or_init_trial()
        self.assertFalse(status["is_expired"], "No debe estar expirado en la primera ejecución")
        self.assertEqual(status["remaining_seconds"], TRIAL_DURATION_SECONDS)
        self.assertEqual(status["reason"], "OK_FIRST_RUN")
        self.assertIn("reg", self.mock_store)
        self.assertIn("file", self.mock_store)

    def test_03_time_progression(self):
        """Verifica que el tiempo restante disminuya de acuerdo al tiempo transcurrido."""
        now = time.time()
        # Simular que pasaron 2 horas (7,200 segundos)
        two_hours_ago = now - 7200
        hwid = TrialManager.get_hardware_fingerprint()
        self.mock_store["reg"] = {
            "hwid": hwid,
            "first_run": two_hours_ago,
            "last_run": two_hours_ago + 100,
            "status": "ACTIVE"
        }

        status = TrialManager.check_or_init_trial()
        self.assertFalse(status["is_expired"])
        # El tiempo restante debe ser aproximadamente 22 horas
        expected_remaining = TRIAL_DURATION_SECONDS - 7200
        self.assertAlmostEqual(status["remaining_seconds"], expected_remaining, delta=10)

    def test_04_clock_rollback_detection(self):
        """Verifica que si el usuario atrasa el reloj de Windows, se detecte manipulación y se bloquee."""
        now = time.time()
        hwid = TrialManager.get_hardware_fingerprint()
        # Simular que el último run registrado fue mañana o 1 hora en el futuro
        future_run = now + 3600
        self.mock_store["reg"] = {
            "hwid": hwid,
            "first_run": now - 1800,
            "last_run": future_run,
            "status": "ACTIVE"
        }

        status = TrialManager.check_or_init_trial()
        self.assertTrue(status["is_expired"], "Debe marcarse como expirado por manipulación de reloj")
        self.assertTrue(status["is_tampered"], "Debe detectarse como manipulado")
        self.assertEqual(status["reason"], "CLOCK_ROLLBACK_DETECTED")

    def test_05_expiration_after_24_hours(self):
        """Verifica que al transcurrir más de 24 horas, la prueba caduque permanentemente."""
        now = time.time()
        hwid = TrialManager.get_hardware_fingerprint()
        # Simular que la primera ejecución fue hace 25 horas
        twenty_five_hours_ago = now - (25 * 3600)
        self.mock_store["reg"] = {
            "hwid": hwid,
            "first_run": twenty_five_hours_ago,
            "last_run": twenty_five_hours_ago + 3600,
            "status": "ACTIVE"
        }

        status = TrialManager.check_or_init_trial()
        self.assertTrue(status["is_expired"], "Debe expirar tras 24 horas")
        self.assertEqual(status["remaining_seconds"], 0)

    def test_06_format_time(self):
        """Verifica el formateo en texto legible de horas, minutos y segundos."""
        self.assertEqual(TrialManager.format_remaining_time(86400), "24h 00m 00s")
        self.assertEqual(TrialManager.format_remaining_time(3665), "01h 01m 05s")
        self.assertIn("Expirado", TrialManager.format_remaining_time(0))

    def test_07_future_test_version_support(self):
        """
        Verifica que la primera versión de prueba (Build 1) quede bloqueada tras 24h,
        pero que una FUTURA versión de prueba (Build 2) pueda ejecutarse con su propio
        ciclo de 24h en la misma máquina antes de la versión comercial estable.
        """
        now = time.time()
        hwid = TrialManager.get_hardware_fingerprint()

        # 1. Simular que Build 1 ya expiró en esta máquina
        TrialManager.CURRENT_DEMO_BUILD_ID = 1
        TrialManager.CURRENT_DEMO_BUILD_TAG = "DEMO-v1.0"
        self.mock_store["reg"] = {
            "hwid": hwid,
            "current_build_id": 1,
            "build_tag": "DEMO-v1.0",
            "first_run": now - 90000,
            "last_run": now - 1000,
            "status": "EXPIRED",
            "expired_build_ids": [1]
        }

        # Comprobar que Build 1 sigue bloqueado
        status_b1 = TrialManager.check_or_init_trial()
        self.assertTrue(status_b1["is_expired"], "Build 1 debe continuar bloqueado")

        # 2. Ahora el desarrollador lanza una NUEVA versión de prueba (Build 2)
        TrialManager.CURRENT_DEMO_BUILD_ID = 2
        TrialManager.CURRENT_DEMO_BUILD_TAG = "DEMO-v2.0-beta"

        status_b2 = TrialManager.check_or_init_trial()
        self.assertFalse(status_b2["is_expired"], "La nueva versión de prueba Build 2 debe poder ejecutarse")
        self.assertEqual(status_b2["remaining_seconds"], TRIAL_DURATION_SECONDS, "Debe tener 24 horas completas")
        self.assertTrue(status_b2.get("is_new_release"), "Debe marcarse como nueva entrega de prueba")

        # 3. Si el usuario intenta volver a ejecutar la vieja Build 1:
        TrialManager.CURRENT_DEMO_BUILD_ID = 1
        status_old_b1 = TrialManager.check_or_init_trial()
        self.assertTrue(status_old_b1["is_expired"], "La vieja Build 1 debe seguir bloqueada permanentemente")

        # Restaurar configuración original
        TrialManager.CURRENT_DEMO_BUILD_ID = 1
        TrialManager.CURRENT_DEMO_BUILD_TAG = "DEMO-v1.0"

    def test_08_developer_grant_extension(self):
        """Verifica que el desarrollador pueda autorizar una nueva ventana de 24h con su clave."""
        now = time.time()
        hwid = TrialManager.get_hardware_fingerprint()

        # Simular estado expirado
        self.mock_store["reg"] = {
            "hwid": hwid,
            "current_build_id": 1,
            "status": "EXPIRED",
            "expired_build_ids": [1]
        }

        # Clave incorrecta debe ser rechazada
        self.assertFalse(TrialManager.grant_trial_extension("CLAVE_FALSA"))

        # Clave maestra de extensión válida
        success = TrialManager.grant_trial_extension("DEMO-EXTEND-BETA-2026")
        self.assertTrue(success, "La clave maestra debe ser aceptada")

        # El estado debe volver a ACTIVE con 24 horas
        status = TrialManager.check_or_init_trial()
        self.assertFalse(status["is_expired"])
        self.assertAlmostEqual(status["remaining_seconds"], TRIAL_DURATION_SECONDS, delta=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)

