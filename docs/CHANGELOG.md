# 📜 Registro Histórico de Cambios (Changelog)

Todos los cambios notables realizados en el proyecto **Recuperador de Datos Forense** se encuentran documentados cronológicamente en este archivo. El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y sigue el estándar de versionado semántico [SemVer](https://semver.org/lang/es/).

---

## [2.5.0] - 2026-09-07
### Añadido
- **Edición Comercial de Demostración: `Forensic_Recovery_DEMO.exe`**:
  - Creada una edición portable de evaluación de 24 horas independiente de la versión comercial completa (`RecuperadorDeDatos.exe`).
  - **Módulo de Licenciamiento Temporal (`TrialManager`)**:
    - Temporizador inviolable de 24 horas (86,400 segundos) que se activa a partir del primer segundo de ejecución en cada máquina.
    - **Doble Persistencia con Firma HMAC-SHA256**: Almacena el token de estado de forma redundante en el Registro de Windows (`HKCU\Software\ForensicRecoverySuite\TrialGuard`) y en almacenamiento local protegido (`%LOCALAPPDATA%\ForensicRecovery\lic_cache.dat`).
    - **Vinculación a Firma de Hardware (HWID)**: Integra MachineGuid y hashes de procesador/nodo para prevenir la clonación de tokens entre equipos.
    - **Protección Anti-Rollback de Reloj**: Detecta retrocesos en la fecha/hora del sistema operativo o BIOS para burlar el temporizador, bloqueando inmediatamente la prueba como manipulada.
    - **Soporte de Futuras Versiones de Prueba Pre-Comerciales (`CURRENT_DEMO_BUILD_ID`)**:
      - La compilación actual (Build 1) queda bloqueada permanentemente a las 24 horas y no puede reutilizarse ni resetearse.
      - Al distribuir una **futura versión de prueba (Beta / Preview)** con un identificador de compilación superior (`Build ID > 1`), el sistema detecta la nueva versión en la misma máquina y le otorga de forma automática su propio ciclo de 24 horas.
      - Si el usuario intenta ejecutar nuevamente la versión anterior caducada, el bloqueo permanente persiste.
    - **Clave Maestra y Extensión para Desarrollador**:
      - Soporte de parámetro por línea de comandos (`--grant-trial-extension=<KEY>`) e ingreso interactivo en el diálogo comercial para autorizar ventanas de prueba adicionales a evaluadores o soporte técnico.
  - **Banner de Telemetría y Cuenta Regresiva en Tiempo Real (`DemoBanner`)**:
    - Indicador en la parte superior de la ventana con barra de progreso, horas:minutos:segundos restantes y cambio de alerta a color rojo crítico en la última hora.
  - **Bloqueo Definitivo y Autodestrucción Segura (`trigger_self_destruction`)**:
    - Al vencer las 24 horas (o detectarse manipulación), muestra un diálogo explicativo de fin de período de prueba.
    - Inutiliza de forma irreversible la suite en esa máquina registrando el estado `EXPIRED`.
    - Programa la eliminación forzada desacoplada del binario `.exe` (`cmd.exe /c timeout /t 2 /nobreak >nul & del /f /q ...`) tras el cierre del proceso.
  - **Compilación Automatizada (`build_demo.py` & `build.bat`)**:
    - Script `build_demo.py` para generar directamente `dist/Forensic_Recovery_DEMO.exe`.
    - Menú interactivo en `build.bat` para compilar la versión Completa, Demo o Ambas con un solo clic.

---

## [2.4.0] - 2026-09-07
### Añadido
- **Aislamiento Estricto de Alcance por Unidad (Zero Cross-Drive Leaks)**:
  - **Papelera Forense Dirigida (`RecycleBinScanner`)**: El escaneo de `$Recycle.Bin` ahora recibe explícitamente la lista de unidades seleccionadas por el usuario (`drives_for_rb`), evitando el barrido indiscriminado de todas las unidades conectadas al sistema (`C:`, `D:`, `E:`, `H:`, etc.).
  - **Condicionamiento de Caché Gráfica y Temporales a la Unidad de Sistema (`C:`)**: Las fases de extracción de `ThumbcacheExtractor` (fotos en miniatura cacheadas por Windows) y `TempScanner` (borradores de Office y `%TEMP%`) se omiten automáticamente si la unidad de sistema `C:` no forma parte activa del alcance de escaneo.
  - **Coincidencia Exacta de Sesiones Previas (`SessionManager.find_matching_session`)**: Se reemplazó la validación de subconjunto permisiva (`issubset`) por una comprobación de igualdad estricta (`norm_targets == s_targets`). Esto evita que un escaneo previo multiconector o de otra unidad contamine con sus resultados la sesión de una unidad específica.
  - **Barrera de Filtrado por Letra de Unidad (`ScanWorker._filter_out_existing_data`)**: Inspecciona exhaustivamente la letra de unidad asignada a través de `drive`, `original_path`, `data_source_path` y `container_file`. Cualquier elemento perteneciente a una unidad ajena al alcance es descartado al 100%.
  - **Herramienta `[🎯 Solo Esta]` y Aislamiento por Doble Clic en `DirectorySelector`**:
    - Nuevo botón en la barra de herramientas del selector de carpetas que desmarca cualquier otra carpeta/unidad y deja marcada únicamente la unidad seleccionada.
    - Doble clic en cualquier elemento del árbol para aislarlo instantáneamente.
    - Alerta visual en tiempo real en la barra de resumen si el usuario mantiene seleccionadas ubicaciones pertenecientes a discos físicos o letras de unidad distintas.

---

## [2.3.0] - 2026-09-07
### Añadido
- **Omisión Total de Archivos Existentes en Unidades**:
  - Implementado filtro forense estricto `ScanWorker._filter_out_existing_data`: Descarta sistemáticamente cualquier archivo cuyo original se encuentre activo y accesible en el sistema de archivos, coincida en firma `(nombre, tamaño)` con elementos de las carpetas analizadas o haya sido tallado de archivos de usuario activos.
  - Los resultados solo indexan y muestran elementos genuinamente en estado de recuperación (Papelera de reciclaje `$Recycle.Bin`, registros inactivos/eliminados en NTFS `$MFT`, borradores huérfanos de auto-recuperación, archivos tallados de imágenes de disco o instantáneas VSS).
- **Restricción de File Carving a Contenedores Forenses**:
  - `FileCarver.scan_path()` ya no recorre ni abre archivos de usuario activos (`.docx`, `.xlsx`, `.pdf`, `.jpg`, etc.) dentro de las carpetas de alcance.
  - El tallado de flujo se ejecuta exclusivamente sobre imágenes de disco forenses (`.raw`, `.dd`, `.img`, `.vhd`, `.vhdx`, `.dmp`, `.bin`, `.iso`, `.vmdk`, `.dmg`), volcados de memoria y dispositivos en bruto (`\\.\` / `/dev/`).
- **Integración de Escaneo Directo NTFS `$MFT` en Protocolo Profundo**:
  - Nuevo método `MFTScanner.scan_drive_mft()` para consultar directamente la Tabla Maestra de Archivos (NTFS) en busca de entradas con bandera de borrado (`is_in_use == False`) y extraer datos residentes cuando se dispone de permisos de Administrador.
  - Integrado como Fase 4/5 en el Protocolo Forense Profundo Multicapa.
- **Depuración de Escaneo de Temporales y Borradores**:
  - `TempScanner` ahora filtra rigurosamente `%TEMP%` para extraer únicamente borradores huérfanos (`~WRL*.tmp`, `~*.tmp`, `.asd`, `.wbk`, `.xar`, `.bak`), ignorando logs o ficheros activos de instaladores.
  - Corregida la importación de `re` en `core/temp_scanner.py`.

---

## [2.2.0] - 2026-09-07
### Añadido
- **Acción "Nueva Sesión" (`Ctrl+N`)**: Botón dedicado `[➕ Nueva Sesión]` en la barra superior de la ventana principal para cerrar escaneos en ejecución y reiniciar el espacio de trabajo.
- **Limpieza Integral de Estado**: Vacía la memoria de resultados, limpia y reinicia la tabla, desmarca todos los elementos, restablece los filtros de búsqueda/categoría/extensión/calidad, reinicia la vista previa y restablece el HUD de telemetría a "EN ESPERA".
- **Cierre Seguro de Escaneos Activos**: Si el usuario pulsa *Nueva Sesión* durante un escaneo en marcha, el hilo en segundo plano es cancelado y detenido de forma segura antes de limpiar.
- **Protección de Datos No Guardados**: Diálogo interactivo preventivo que ofrece guardar los resultados de la sesión actual en disco antes de descartarlos.
- **Purga Total de Historial en Disco (`SessionManager.clear_all_sessions`)**: Nuevo método y botón `[🧹 Purgar Todo...]` en el gestor de sesiones para eliminar en bloque sesiones obsoletas tanto en archivos JSON como en la base de datos SQLite.
- **Precisión Temporal en Microsegundos**: Generación de identificadores de sesión con resolución a microsegundos (`%Y%m%d_%H%M%S_%f`), previniendo colisiones de sesiones creadas en el mismo segundo.

---

## [2.1.0] - 2026-09-07
### Añadido
- **Listado Embebido Directo en Alcance (`DirectorySelector`)**: Se eliminó el menú desplegable (`QComboBox`) de selección de modo y las ventanas modales emergentes para mostrar directamente en el panel un listado scrolleable e interactivo con casillas de verificación (`[✔]`), íconos, rutas y estado de recomendación.
- **Barra de Herramientas de Alcance**: Botones de acción inmediata `[➕ Añadir...]`, `[➖ Quitar]`, `[🎯 Recomendadas]`, `[✔ Todas]` y `[✖ Ninguna]` integrados directamente en el panel.
- **Sincronización Dinámica de Recomendaciones**: Al alternar los tipos de archivo en el paso 2, el listado actualiza al instante las insignias de recomendación (`🎯`) y las carpetas marcadas.
- **Integración de Unidades del Sistema**: Muestra de forma directa las particiones y discos detectados en el mismo listado para selección inmediata.

---

## [2.0.0] - 2026-09-07
### Añadido
- **Identificadores Criptográficos Únicos en Carving**: Implementado hashing MD5 compuesto (`carved_{hash_md5}`) basado en ruta del contenedor, offset absoluto y posición, eliminando cualquier colisión de identificadores.
- **Rutas de Contenedor Descriptivas**: Cuando un archivo tallado proviene de un formato contenedor (como `.ai`, `.dotx`, `.dotm`, etc.) a partir del byte 0, la ruta muestra claramente el nombre del contenedor y el desplazamiento (ej. `folleto.ai [Offset 0x0]`) en lugar de la confusa etiqueta genérica `[Sector Offset 0x0]`.
- **Aislamiento Exclusivo en Botón `Solo Visibles`**: Ahora reemplaza el conjunto de selección en lugar de acumularlo (`self.checked_item_ids = set(visible_keys)`), desmarcando al instante cualquier archivo de gran tamaño que haya quedado oculto fuera de los filtros activos.
- **Medidor Inteligente Transparente**: Desglose explícito en la barra inferior de la tabla (`X visibles marcados (Y KB) | Total lote: Z (W GB)`) para advertir al usuario cuando existen archivos marcados en otras categorías.
- **Diálogo Interceptor de Seguridad al Exportar**: Si el usuario pulsa *Recuperar Seleccionados* con un filtro activo habiendo archivos pesados marcados en segundo plano, la aplicación despliega una ventana interactiva preventiva para decidir si recuperar únicamente los visibles o el lote completo.

### Corregido
- Corregido el defecto por el cual al filtrar documentos menores a 500 KB, el medidor mostraba más de 8 GB debido a archivos de video y comprimidos ocultos marcados en segundo plano.
- Corregida la colisión masiva donde 162 archivos compartían el mismo identificador `carved_1`.
- Eliminado método duplicado `_on_header_section_clicked` en `ui/results_table.py`.

---

## [1.9.0] - 2026-09-06
### Añadido
- **Soporte Multiplataforma para Linux**: Adaptación para distribuciones Linux, con foco en **Linux Bazzite**, Debian, Ubuntu, Fedora y SteamOS.
- **Lanzadores y Compiladores para Linux**:
  - `build_linux.sh`: Script de compilación desatendida para generar el binario ejecutable nativo ELF `dist/RecuperadorDeDatos`.
  - `run_linux.sh`: Lanzador directo con auto-configuración de entorno virtual Python.
  - `RecuperadorDeDatos.desktop`: Fichero de integración con escritorios KDE Plasma y GNOME.
- **Abstracción de Rutas y Servicios Linux**:
  - Detección de unidades y particiones leyendo `/proc/mounts` y `/run/media/$USER`.
  - Escaneo de papelera de reciclaje estándar FreeDesktop en `~/.local/share/Trash`.
  - Mapeo de directorios de usuario según el estándar XDG (`Documentos`, `Descargas`, etc.).

---

## [1.8.0] - 2026-09-06
### Añadido
- **Catálogo Exhaustivo de 82 Formatos Categorizados**:
  - **40 Formatos de Documentos**: Suites Microsoft Office (Word, Excel, PowerPoint, Access, Publisher, OneNote), LibreOffice / OpenDocument (ODT, ODS, ODP, ODG), Adobe PDF, EPUB, MOBI, RTF y texto estructurado.
  - **16 Formatos de Imágenes**: JPEG, PNG, GIF, BMP, WebP, TIFF, SVG, RAW fotográficos (CR2, NEF, ARW, DNG), PSD de Photoshop, etc.
  - **18 Formatos de Audio y Video**: MP4, MOV, AVI, MKV, WebM, MP3, WAV, FLAC, OGG, M4A, etc.
  - **8 Formatos de Comprimidos**: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ, ISO.
- **Filtrado Granular en Escaneo y Carving**: Parámetro `selected_extensions` en `ScanWorker` y `FileCarver` para restringir la búsqueda en crudo exclusivamente a los formatos elegidos por el usuario, acelerando la velocidad de escaneo.

---

## [1.7.0] - 2026-09-06
### Añadido
- **Interfaz Gráfica Limpia con Diálogos Emergentes**:
  - Reemplazo de checklists invasivos en el panel principal por ventanas modales desplegables compactas (`ui/popups.py`).
  - **`FileTypesDialog`**: Diálogo con 4 pestañas por categoría, barra de búsqueda en tiempo real, contadores de formatos activos y botones de preset rápido de un clic (`Solo Office`, `Solo PDF`, `Solo Texto`, `Todos`, `Ninguno`).
  - **`FolderChecklistDialog`**: Selector interactivo de carpetas con casillas de verificación, cálculo de tamaño libre y botones de selección rápida.
  - **`DirectorySelector`**: Selector de alcance con 3 modos (Indexación Dirigida, Selector Manual y Unidad Completa).

### Corregido
- Corregido error de indentación (`IndentationError: unexpected indent`) en `ui/results_table.py` línea 328 en el ejecutable compilado.

---

## [1.6.0] - 2026-09-05
### Añadido
- **Restauración con Nombres Originales**: Algoritmo en `RecoveryExporter` que recupera el nombre real del archivo a partir de metadatos de papelera (`$I`), metadatos MFT, metadatos EXIF fotográficos o propiedades internas de documentos Office (`dc:title`, `word/document.xml`).
- **Reconstrucción Jerárquica del Árbol de Carpetas**: Opción para recrear en el directorio destino la estructura exacta de subdirectorios donde residía el archivo antes de eliminarse (ejemplo: `Carpeta_Destino/Disco_C/Users/Usuario/Documentos/...`).

---

## [1.5.0] - 2026-09-05
### Añadido
- **Compilación a Ejecutable Autónomo para Windows (`build_exe.py`)**:
  - Empaquetado completo con PyInstaller generando `dist/RecuperadorDeDatos.exe` (100% portable, sin necesidad de instalar Python ni librerías).
  - Manejo automático de bloqueos de archivo mediante respaldo temporal si el binario anterior está en uso.
  - Script por lotes `build.bat` para compilar con un solo doble clic.
- **Base de Datos Local SQLite Autoconstruida (`core/local_db.py`)**:
  - Creación automática de `data/recovery_vault.db` en la primera ejecución con 5 tablas relacionales e índices para almacenamiento local 100% offline.
- **Verificador Preventivo de Requisitos de Sistema (`core/env_checker.py`)**:
  - Chequeo al arranque de Visual C++ Redistributable, .NET Framework y arquitectura de 64 bits con diálogo nativo Win32 en caso de discrepancias.

---

## [1.4.0] - 2026-09-05
### Añadido
- **Analizador de Integridad y Usabilidad Forense (`core/integrity_analyzer.py`)**:
  - Medición de ratio de bytes nulos (`0x00`) para descarte de sectores vacíos y bloques borrados.
  - Medición de entropía de información de Shannon para descarte de patrones sin estructura.
  - Clasificación en 4 niveles de usabilidad: 🌟 Alta Calidad, 🟡 Media, 🟠 Baja y 🔴 Inútil.
  - Botón `🌟 Solo Alta Calidad` en la tabla de resultados para desmarcar basura con un solo clic.
  - Asistente de seguridad al exportar para prevenir la recuperación accidental de archivos inservibles.
- **Parsers Binarios Estructurales en `core/file_carver.py`**:
  - JPEG: Recorrido formal de marcadores con salto de miniaturas incrustadas EXIF para evitar el truncamiento prematuro.
  - PNG: Validación matemática de integridad mediante sumas de verificación CRC32 por chunk.
  - MP4 / MOV: Navegación de átomos ATOM (`ftyp`, `moov`, `mdat`) y extracción de resolución y duración.
  - RIFF: Extracción de audio WAV PCM y video AVI.
  - OOXML: Extracción de texto y párrafos de documentos Word, Excel y PowerPoint.

---

## [1.3.0] - 2026-09-04
### Corregido
- Solucionado error de escaneo: `TypeError: Object of type datetime is not JSON serializable` mediante codificador de fecha ISO-8601 en `core/session_manager.py`.

---

## [1.2.0] - 2026-09-04
### Añadido
- **Sistema de Sesiones Persistentes (`core/session_manager.py`)**:
  - Almacenamiento de sesiones en ficheros JSON dentro del directorio `sessions/`.
  - Serialización y deserialización de muestras binarias de previsualización en Base64.
  - **Escaneo Diferencial e Incremental**: Matriz de huellas digitales (*fingerprints*) para saltar archivos sin cambios y fusionar únicamente novedades en reescaneos.
  - Diálogo visual de administración de sesiones (`ui/session_dialog.py`).

---

## [1.1.0] - 2026-09-03
### Añadido
- **Analizador MFT NTFS (`core/mft_scanner.py`)**: Búsqueda de registros eliminados en la Master File Table con extracción de atributos y datos residentes.
- **Explorador de Copias de Sombra VSS (`core/shadow_explorer.py`)**: Consulta y rescate de versiones anteriores de archivos mediante Volume Shadow Copies de Windows.
- **Filtro Inteligente de Software y Juegos (`core/software_filter.py`)**: Detección automática en Registro y carpetas de juegos para excluir miles de archivos irrelevantes del sistema, reduciendo el tiempo de escaneo en un 85%.
- **Enrutador Contextual (`core/context_router.py`)**: Mapeo inteligente de carpetas según el tipo de archivo buscado.

---

## [1.0.0] - 2026-09-01
### Añadido
- **Lanzamiento Inicial de la Suite Forense**:
  - Arquitectura multi-hilo basada en PyQt5 y `QThread`.
  - Escáner de Papelera de Reciclaje (`$Recycle.Bin`) con rescate de huérfanos `$R`.
  - Extractor de imágenes en caché gráfica (`thumbcache_*.db`).
  - Escáner de borradores de Office y temporales (`%TEMP%`, `.asd`, `.xar`).
  - Motor básico de tallado por firmas (*File Carving*).
  - Barra de telemetría HUD en tiempo real con cronómetro, velocímetro y volumen analizado.
  - Visor interactivo multi-pestaña (gráfico, multimedia, texto, volcado hexadecimal y metadatos).
  - Tema oscuro profesional inspirado en herramientas periciales.

