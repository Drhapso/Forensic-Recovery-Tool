"""
Módulo de Gestión de Licencia de Demostración y Temporizador Forense (24 Horas).
Implementa un cerco criptográfico inviolable con doble persistencia (Registro de Windows
y almacenamiento local en %LOCALAPPDATA%), detección de manipulación de reloj (anti-rollback),
vinculación a firma de hardware y mecanismo de autodestrucción/autolimpieza para distribución comercial.

Soporta versionado de compilaciones de prueba (Build IDs): la versión de prueba actual
se limita a 24 horas y se bloquea permanentemente, pero permite la ejecución de futuras
versiones de prueba/beta (con Build ID superior o clave de extensión) antes de la versión comercial estable.
"""

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import subprocess
import platform

# Secreto interno para firma criptográfica HMAC (evita edición manual del token)
_SECRET_SALT = b"F0r3ns1c_R3c0v3ry_D3M0_2026_T1m3_GuaRd_X9!"
TRIAL_DURATION_SECONDS = 24 * 60 * 60  # 24 Horas = 86,400 segundos

# VERSIÓN DE LA COMPILACIÓN DE PRUEBA ACTUAL
# Incrementar este ID (ej: 2, 3...) al generar futuras versiones de prueba previas a la comercial
CURRENT_DEMO_BUILD_ID = 1
CURRENT_DEMO_BUILD_TAG = "DEMO-v1.0"

# Constantes de almacenamiento
REG_PATH = r"Software\ForensicRecoverySuite\TrialGuard"
LOCAL_APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "ForensicRecovery")
LOCAL_TOKEN_FILE = os.path.join(LOCAL_APP_DIR, "lic_cache.dat")


class TrialManager:
    """Gestiona el ciclo de vida de la versión de prueba de 24 horas con soporte para futuras versiones."""

    CURRENT_DEMO_BUILD_ID = CURRENT_DEMO_BUILD_ID
    CURRENT_DEMO_BUILD_TAG = CURRENT_DEMO_BUILD_TAG

    @staticmethod
    def get_hardware_fingerprint() -> str:
        """Obtiene una firma criptográfica única del hardware de la máquina."""
        raw_ids = []

        # 1. MachineGuid de Windows
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                    guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                    raw_ids.append(str(guid).strip())
            except Exception:
                pass

        # 2. Nombre del nodo y procesador
        raw_ids.append(platform.node())
        raw_ids.append(platform.processor())
        raw_ids.append(platform.machine())

        combo = "_".join(raw_ids).encode("utf-8", errors="ignore")
        return hashlib.sha256(combo).hexdigest()[:32]

    @classmethod
    def _sign_payload(cls, payload: dict) -> str:
        """Genera una firma HMAC-SHA256 del contenido del estado."""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(_SECRET_SALT, canonical, hashlib.sha256).hexdigest()

    @classmethod
    def _verify_payload(cls, payload: dict, signature: str) -> bool:
        """Verifica la validez de la firma HMAC."""
        expected = cls._sign_payload(payload)
        return hmac.compare_digest(expected, signature)

    @classmethod
    def _read_from_registry(cls) -> dict or None:
        """Lee el estado del token desde el Registro de Windows."""
        if sys.platform != "win32":
            return None
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                enc_data, _ = winreg.QueryValueEx(key, "Token")
                raw = base64.b64decode(enc_data).decode("utf-8")
                envelope = json.loads(raw)
                payload = envelope.get("payload", {})
                sig = envelope.get("signature", "")
                if cls._verify_payload(payload, sig):
                    return payload
        except Exception:
            pass
        return None

    @classmethod
    def _save_to_registry(cls, payload: dict) -> bool:
        """Escribe el estado del token en el Registro de Windows."""
        if sys.platform != "win32":
            return False
        try:
            import winreg
            sig = cls._sign_payload(payload)
            envelope = {"payload": payload, "signature": sig}
            enc_data = base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                winreg.SetValueEx(key, "Token", 0, winreg.REG_SZ, enc_data)
                winreg.SetValueEx(key, "HWID", 0, winreg.REG_SZ, payload.get("hwid", ""))
                winreg.SetValueEx(key, "BuildID", 0, winreg.REG_DWORD, payload.get("current_build_id", 1))
            return True
        except Exception:
            return False

    @classmethod
    def _read_from_file(cls) -> dict or None:
        """Lee el estado del token desde el archivo protegido en %LOCALAPPDATA%."""
        if not os.path.exists(LOCAL_TOKEN_FILE):
            return None
        try:
            with open(LOCAL_TOKEN_FILE, "r", encoding="utf-8") as f:
                enc_data = f.read().strip()
            raw = base64.b64decode(enc_data).decode("utf-8")
            envelope = json.loads(raw)
            payload = envelope.get("payload", {})
            sig = envelope.get("signature", "")
            if cls._verify_payload(payload, sig):
                return payload
        except Exception:
            pass
        return None

    @classmethod
    def _save_to_file(cls, payload: dict) -> bool:
        """Escribe el estado del token en el archivo protegido en %LOCALAPPDATA%."""
        try:
            os.makedirs(LOCAL_APP_DIR, exist_ok=True)
            sig = cls._sign_payload(payload)
            envelope = {"payload": payload, "signature": sig}
            enc_data = base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")
            with open(LOCAL_TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(enc_data)
            return True
        except Exception:
            return False

    @classmethod
    def check_or_init_trial(cls) -> dict:
        """
        Inspecciona el estado de la prueba.
        - Para la primera versión (Build ID 1), se limita a 24 horas y se bloquea permanentemente.
        - Si en el futuro se ejecuta una NUEVA versión de prueba (Build ID superior), se le otorga
          un nuevo ciclo de evaluación de 24 horas de forma automática.
        - Si el Build ID actual ya caducó previamente en esta máquina, permanece bloqueado.
        """
        now = time.time()
        hwid = cls.get_hardware_fingerprint()

        # Recuperar estado de ambos almacenes (redundancia dual)
        reg_state = cls._read_from_registry()
        file_state = cls._read_from_file()

        state = None
        if reg_state and file_state:
            # Combinar lista histórica de compilaciones expiradas
            expired_reg = set(reg_state.get("expired_build_ids", []))
            expired_file = set(file_state.get("expired_build_ids", []))
            all_expired = sorted(list(expired_reg.union(expired_file)))

            # Tomar la versión más reciente registrada
            rec_build = max(reg_state.get("current_build_id", 1), file_state.get("current_build_id", 1))

            state = dict(reg_state if reg_state.get("current_build_id", 1) >= file_state.get("current_build_id", 1) else file_state)
            state["expired_build_ids"] = all_expired
            state["current_build_id"] = rec_build
        elif reg_state:
            state = reg_state
        elif file_state:
            state = file_state

        # CASO 1: PRIMERA EJECUCIÓN ABSOLUTA EN ESTE EQUIPO
        if not state:
            state = {
                "hwid": hwid,
                "current_build_id": cls.CURRENT_DEMO_BUILD_ID,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "first_run": now,
                "last_run": now,
                "status": "ACTIVE",
                "expired_build_ids": []
            }
            cls._save_to_registry(state)
            cls._save_to_file(state)

            return {
                "is_expired": False,
                "remaining_seconds": TRIAL_DURATION_SECONDS,
                "is_tampered": False,
                "reason": "OK_FIRST_RUN",
                "first_run": now,
                "elapsed_seconds": 0,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "is_new_release": False
            }

        # CASO 2: COMPROBACIÓN DE FIRMA DE HARDWARE
        if state.get("hwid") != hwid:
            cls.mark_expired("HWID_MISMATCH")
            return {
                "is_expired": True,
                "remaining_seconds": 0,
                "is_tampered": True,
                "reason": "TOKEN_CLONED_FROM_ANOTHER_MACHINE",
                "first_run": state.get("first_run", now),
                "elapsed_seconds": TRIAL_DURATION_SECONDS,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "is_new_release": False
            }

        recorded_build = state.get("current_build_id", 1)
        expired_builds = state.get("expired_build_ids", [])

        # CASO 3: DETECCIÓN DE NUEVA VERSIÓN DE PRUEBA FUTURA (BUILD_ID SUPERIOR)
        # Si el desarrollador compila una nueva versión beta/demo con un Build ID mayor,
        # se autoriza un nuevo ciclo de 24 horas para probar las novedades.
        if cls.CURRENT_DEMO_BUILD_ID > recorded_build:
            # Archivar la versión anterior en la lista de expiradas
            new_expired = list(set(expired_builds + [recorded_build]))
            state = {
                "hwid": hwid,
                "current_build_id": cls.CURRENT_DEMO_BUILD_ID,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "first_run": now,
                "last_run": now,
                "status": "ACTIVE",
                "expired_build_ids": new_expired
            }
            cls._save_to_registry(state)
            cls._save_to_file(state)

            return {
                "is_expired": False,
                "remaining_seconds": TRIAL_DURATION_SECONDS,
                "is_tampered": False,
                "reason": "NEW_TEST_RELEASE_ACTIVATED",
                "first_run": now,
                "elapsed_seconds": 0,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "is_new_release": True
            }

        # CASO 4: ESTA VERSIÓN DE PRUEBA ESPECÍFICA YA EXPIRÓ PREVIAMENTE EN ESTE EQUIPO
        if cls.CURRENT_DEMO_BUILD_ID in expired_builds or (state.get("status") == "EXPIRED" and recorded_build == cls.CURRENT_DEMO_BUILD_ID):
            return {
                "is_expired": True,
                "remaining_seconds": 0,
                "is_tampered": False,
                "reason": f"BUILD_{cls.CURRENT_DEMO_BUILD_ID}_EXPIRED",
                "first_run": state.get("first_run", now),
                "elapsed_seconds": TRIAL_DURATION_SECONDS,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "is_new_release": False
            }

        first_run = state.get("first_run", now)
        last_run = state.get("last_run", now)

        # CASO 5: DETECCIÓN DE MANIPULACIÓN DE RELOJ (ANTI-CLOCK ROLLBACK)
        if now < (last_run - 300):
            cls.mark_expired("CLOCK_ROLLBACK_DETECTED")
            return {
                "is_expired": True,
                "remaining_seconds": 0,
                "is_tampered": True,
                "reason": "CLOCK_ROLLBACK_DETECTED",
                "first_run": first_run,
                "elapsed_seconds": TRIAL_DURATION_SECONDS,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "is_new_release": False
            }

        # CASO 6: CÁLCULO DE TIEMPO TRANSCURRIDO PARA LA COMPILACIÓN ACTUAL
        elapsed = int(now - first_run)
        remaining = max(0, TRIAL_DURATION_SECONDS - elapsed)

        if remaining <= 0 or elapsed >= TRIAL_DURATION_SECONDS:
            cls.mark_expired("TIME_LIMIT_EXCEEDED")
            return {
                "is_expired": True,
                "remaining_seconds": 0,
                "is_tampered": False,
                "reason": "TIME_LIMIT_EXCEEDED",
                "first_run": first_run,
                "elapsed_seconds": elapsed,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "is_new_release": False
            }

        # Actualizar last_run hacia adelante de forma monótona
        if now > last_run:
            state["last_run"] = now
            cls._save_to_registry(state)
            cls._save_to_file(state)

        return {
            "is_expired": False,
            "remaining_seconds": remaining,
            "is_tampered": False,
            "reason": "ACTIVE",
            "first_run": first_run,
            "elapsed_seconds": elapsed,
            "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
            "is_new_release": False
        }

    @classmethod
    def heartbeat(cls):
        """Actualiza el último timestamp registrado en segundo plano para evitar rollbacks."""
        state = cls._read_from_registry() or cls._read_from_file()
        if state and state.get("status") == "ACTIVE":
            now = time.time()
            if now > state.get("last_run", 0):
                state["last_run"] = now
                cls._save_to_registry(state)
                cls._save_to_file(state)

    @classmethod
    def mark_expired(cls, reason: str = "EXPIRED", build_id: int = None):
        """Registra el bloqueo permanente para la compilación actual o especificada."""
        state = cls._read_from_registry() or cls._read_from_file() or {}
        target_build = build_id if build_id is not None else cls.CURRENT_DEMO_BUILD_ID
        expired_list = list(set(state.get("expired_build_ids", []) + [target_build]))

        payload = {
            "hwid": cls.get_hardware_fingerprint(),
            "current_build_id": target_build,
            "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
            "first_run": state.get("first_run", 0),
            "last_run": time.time(),
            "status": "EXPIRED",
            "expire_reason": reason,
            "expired_build_ids": expired_list
        }
        cls._save_to_registry(payload)
        cls._save_to_file(payload)

    @classmethod
    def grant_trial_extension(cls, auth_key: str) -> bool:
        """
        Permite al desarrollador o técnico autorizar una nueva ventana de evaluación
        de 24 horas para pruebas pre-comerciales mediante una clave de desbloqueo.
        """
        valid_keys = {"DEMO-EXTEND-BETA-2026", "FORENSIC-DEV-TEST-PASS"}
        hwid = cls.get_hardware_fingerprint()
        dev_hash = hashlib.sha256(hwid.encode() + _SECRET_SALT).hexdigest()[:12].upper()
        if auth_key in valid_keys or auth_key.upper() == dev_hash:
            now = time.time()
            state = cls._read_from_registry() or cls._read_from_file() or {}
            expired_list = [b for b in state.get("expired_build_ids", []) if b != cls.CURRENT_DEMO_BUILD_ID]
            payload = {
                "hwid": hwid,
                "current_build_id": cls.CURRENT_DEMO_BUILD_ID,
                "build_tag": cls.CURRENT_DEMO_BUILD_TAG,
                "first_run": now,
                "last_run": now,
                "status": "ACTIVE",
                "expired_build_ids": expired_list,
                "authorized_by": "DEVELOPER_OVERRIDE"
            }
            cls._save_to_registry(payload)
            cls._save_to_file(payload)
            return True
        return False

    @staticmethod
    def format_remaining_time(seconds: int) -> str:
        """Formatea segundos en formato 'HHh MMm SSs'."""
        if seconds <= 0:
            return "00h 00m 00s (Expirado)"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}h {minutes:02d}m {secs:02d}s"

    @classmethod
    def trigger_self_destruction(cls):
        """
        Ejecuta la autodestrucción física o autolimpieza del ejecutable en disco.
        En Windows, un proceso en ejecución no puede borrarse a sí mismo directamente
        debido al bloqueo de kernel (IMAGE_FILE). Se dispara un subproceso desacoplado
        que aguarda 2 segundos a la finalización de este proceso y luego elimina el archivo
        portable .exe de forma permanente.
        """
        # Asegurar que la compilación actual quede marcada en el historial de expiradas
        cls.mark_expired("SELF_DESTRUCT_TRIGGERED")

        exe_path = sys.executable
        is_frozen = getattr(sys, "frozen", False)

        if is_frozen and exe_path and os.path.exists(exe_path):
            try:
                cmd = f'cmd.exe /c timeout /t 2 /nobreak >nul & del /f /q "{exe_path}"'
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                subprocess.Popen(cmd, shell=True, creationflags=creation_flags)
            except Exception as e:
                print(f"[TrialManager] Error al programar autodestrucción: {e}", file=sys.stderr)
