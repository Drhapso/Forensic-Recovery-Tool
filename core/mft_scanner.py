"""
Módulo Forense de Análisis de Registros NTFS MFT (Master File Table).
Detecta entradas marcadas como eliminadas (flags 0x00 / 0x02), extrae nombres de archivo originales,
marcas de tiempo reales y recupera datos residentes directamente del registro de 1024 bytes.
"""

import os
import struct
import datetime
from typing import List, Dict, Any, Optional, Callable
from core.recycle_bin import filetime_to_datetime, get_file_category

class MFTScanner:
    """Analizador forense de registros MFT para sistemas de archivos NTFS."""

    @staticmethod
    def parse_mft_record(record_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Parsea un registro MFT individual de 1024 bytes.
        Retorna la información si corresponde a un archivo o carpeta eliminada.
        """
        if len(record_bytes) < 1024 or not record_bytes.startswith(b"FILE"):
            return None

        try:
            # Flags en offset 0x16 (2 bytes): 0x01 = En uso, 0x00 = Eliminado
            flags = struct.unpack("<H", record_bytes[22:24])[0]
            is_in_use = bool(flags & 0x01)
            is_directory = bool(flags & 0x02)

            # Solo nos interesan los registros eliminados (inactivos)
            if is_in_use:
                return None

            attr_offset = struct.unpack("<H", record_bytes[20:22])[0]
            filename = ""
            file_size = 0
            file_date = None
            resident_data = None

            # Recorrer la cadena de atributos NTFS dentro de los 1024 bytes
            pos = attr_offset
            while pos + 8 <= len(record_bytes):
                attr_type = struct.unpack("<I", record_bytes[pos : pos + 4])[0]
                if attr_type == 0xFFFFFFFF or attr_type == 0:
                    break

                attr_len = struct.unpack("<I", record_bytes[pos + 4 : pos + 8])[0]
                if attr_len == 0 or pos + attr_len > len(record_bytes):
                    break

                is_non_resident = bool(record_bytes[pos + 8])

                # Atributo 0x10: $STANDARD_INFORMATION (Fechas)
                if attr_type == 0x10 and not is_non_resident:
                    content_offset = struct.unpack("<H", record_bytes[pos + 20 : pos + 22])[0]
                    c_pos = pos + content_offset
                    if c_pos + 8 <= len(record_bytes):
                        mtime_filetime = struct.unpack("<Q", record_bytes[c_pos + 8 : c_pos + 16])[0]
                        file_date = filetime_to_datetime(mtime_filetime)

                # Atributo 0x30: $FILE_NAME (Nombre real del archivo)
                elif attr_type == 0x30 and not is_non_resident:
                    content_offset = struct.unpack("<H", record_bytes[pos + 20 : pos + 22])[0]
                    c_pos = pos + content_offset
                    if c_pos + 66 <= len(record_bytes):
                        # Longitud en caracteres del nombre
                        name_len = record_bytes[c_pos + 64]
                        name_raw = record_bytes[c_pos + 66 : c_pos + 66 + name_len * 2]
                        decoded_name = name_raw.decode("utf-16le", errors="ignore")
                        # Priorizar nombres largos sobre nombres cortos 8.3 de DOS
                        if not filename or len(decoded_name) > len(filename):
                            filename = decoded_name

                # Atributo 0x80: $DATA (Contenido del archivo)
                elif attr_type == 0x80:
                    if not is_non_resident:
                        # Datos Residentes: ¡El archivo completo cabe en el registro MFT!
                        content_len = struct.unpack("<I", record_bytes[pos + 16 : pos + 20])[0]
                        content_offset = struct.unpack("<H", record_bytes[pos + 20 : pos + 22])[0]
                        c_pos = pos + content_offset
                        if c_pos + content_len <= len(record_bytes):
                            file_size = content_len
                            resident_data = record_bytes[c_pos : c_pos + content_len]
                    else:
                        # Datos No Residentes: Tamaño real en disco
                        if pos + 56 <= len(record_bytes):
                            real_size = struct.unpack("<Q", record_bytes[pos + 48 : pos + 56])[0]
                            file_size = real_size

                pos += attr_len

            if filename and filename not in {"$MFT", "$LogFile", "$Volume", "$Bitmap"}:
                return {
                    "name": filename,
                    "size": file_size,
                    "date": file_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(file_date, datetime.datetime) else str(file_date or "-"),
                    "raw_date": file_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(file_date, datetime.datetime) else "",
                    "category": get_file_category(filename),
                    "is_directory": is_directory,
                    "has_resident_data": resident_data is not None,
                    "resident_bytes": resident_data
                }

        except Exception:
            pass

        return None

    @classmethod
    def scan_mft_stream(cls, 
                        stream, 
                        total_bytes: int,
                        progress_callback: Optional[Callable[[str, int, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Escanea un flujo de datos buscando registros MFT (cabecera FILE) en bloques de 1024 bytes.
        """
        recovered_items = []
        bytes_scanned = 0
        record_idx = 0
        found_count = 0

        while True:
            record = stream.read(1024)
            if len(record) < 1024:
                break

            bytes_scanned += 1024
            record_idx += 1

            if record.startswith(b"FILE"):
                parsed = cls.parse_mft_record(record)
                if parsed:
                    found_count += 1
                    item_type = "Carpeta Eliminada" if parsed["is_directory"] else "Archivo Eliminado"
                    method_str = "MFT Forense (Datos Residentes)" if parsed["has_resident_data"] else "MFT Forense (Registro Inactivo)"

                    recovered_items.append({
                        "id": f"mft_{record_idx}",
                        "name": parsed["name"],
                        "original_path": f"[Registro MFT #{record_idx}]",
                        "original_dir": "Tabla Maestra de Archivos (NTFS MFT)",
                        "size": parsed["size"],
                        "date": parsed["date"],
                        "category": parsed["category"],
                        "source_method": method_str,
                        "recoverable": parsed["has_resident_data"],
                        "preview_bytes": parsed.get("resident_bytes", b"")[:4096],
                        "is_carved": True
                    })

            if progress_callback and record_idx % 2048 == 0:
                pct = min(100, int((bytes_scanned / max(total_bytes, 1)) * 100))
                progress_callback(
                    f"Analizando tabla MFT (Registro #{record_idx:,}, {found_count} recuperables)...",
                    pct,
                    found_count,
                    f"MFT Record #{record_idx}"
                )

        return recovered_items

    @classmethod
    def scan_drive_mft(cls, 
                       drive_letter: str, 
                       max_records: int = 200000,
                       progress_callback: Optional[Callable[[str, int, int, str], None]] = None) -> List[Dict[str, Any]]:
        """
        Intenta leer la tabla maestra de archivos ($MFT) directamente desde el volumen NTFS.
        Requiere privilegios de Administrador en Windows. Si no se tienen permisos o no es NTFS,
        retorna de forma segura una lista vacía sin interrumpir el flujo.
        """
        import sys
        if sys.platform != "win32":
            return []

        from core.disk_utils import is_admin
        if not is_admin():
            return []

        drive_clean = drive_letter.rstrip("\\/").rstrip(":")
        volume_path = rf"\\.\{drive_clean}:"

        import ctypes
        from ctypes import wintypes

        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        INVALID_HANDLE_VALUE = -1

        handle = ctypes.windll.kernel32.CreateFileW(
            volume_path,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None
        )

        if handle == INVALID_HANDLE_VALUE:
            return []

        recovered_items = []
        try:
            # Leer el VBR (Sector 0, 512 bytes)
            vbr_buf = ctypes.create_string_buffer(512)
            bytes_read = wintypes.DWORD()
            success = ctypes.windll.kernel32.ReadFile(
                handle, vbr_buf, 512, ctypes.byref(bytes_read), None
            )
            if not success or bytes_read.value < 512:
                return []

            vbr = vbr_buf.raw
            if vbr[3:7] != b"NTFS":
                return []

            bytes_per_sector = struct.unpack("<H", vbr[11:13])[0]
            sectors_per_cluster = vbr[13]
            cluster_size = bytes_per_sector * sectors_per_cluster
            if cluster_size <= 0:
                return []

            mft_cluster = struct.unpack("<q", vbr[48:56])[0]
            mft_offset = mft_cluster * cluster_size

            # Mover puntero hacia el inicio de $MFT
            FILE_BEGIN = 0
            new_pos = ctypes.c_int64(0)
            ctypes.windll.kernel32.SetFilePointerEx(
                handle, ctypes.c_int64(mft_offset), ctypes.byref(new_pos), FILE_BEGIN
            )

            record_idx = 0
            block_size = 64 * 1024 # 64 KB por bloque = 64 registros MFT
            buf = ctypes.create_string_buffer(block_size)
            
            while record_idx < max_records:
                success = ctypes.windll.kernel32.ReadFile(
                    handle, buf, block_size, ctypes.byref(bytes_read), None
                )
                if not success or bytes_read.value == 0:
                    break

                raw_bytes = buf.raw[:bytes_read.value]
                offset_in_block = 0
                while offset_in_block + 1024 <= len(raw_bytes):
                    record = raw_bytes[offset_in_block : offset_in_block + 1024]
                    record_idx += 1
                    offset_in_block += 1024

                    if record.startswith(b"FILE"):
                        parsed = cls.parse_mft_record(record)
                        if parsed:
                            method_str = "MFT Forense (Datos Residentes)" if parsed["has_resident_data"] else "MFT Forense (Registro Inactivo)"
                            item = {
                                "id": f"mft_{drive_clean}_{record_idx}",
                                "name": parsed["name"],
                                "original_name": parsed["name"],
                                "original_path": f"{drive_clean}:\\{parsed['name']}",
                                "original_dir": f"{drive_clean}:\\",
                                "size": parsed["size"],
                                "date": parsed["date"],
                                "category": parsed["category"],
                                "source_method": method_str,
                                "recoverable": parsed["has_resident_data"],
                                "preview_bytes": parsed.get("resident_bytes", b"") if parsed.get("has_resident_data") else b"",
                                "drive": f"{drive_clean}:\\",
                                "is_carved": True
                            }
                            recovered_items.append(item)

                if progress_callback and record_idx % 2048 == 0:
                    pct = min(100, int((record_idx / max_records) * 100))
                    progress_callback(
                        f"Analizando MFT en {drive_clean}: (Registro #{record_idx:,}, {len(recovered_items)} eliminados)...",
                        pct,
                        len(recovered_items),
                        f"{drive_clean}:\\ MFT #{record_idx}"
                    )

        except Exception as err:
            print(f"Error escaneando MFT en unidad {drive_letter}: {err}")
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)

        return recovered_items

