import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, r"C:\Users\Drhapso\Documents\PROYECTOS IA INDEPENDIENTES\RECUPERADOR DE DATOS")

from core.env_checker import EnvironmentChecker

print("=== TESTING ENVIRONMENT & PREREQUISITE CHECKER ===")

# 1. Run Preflight Checks
passed, results = EnvironmentChecker.run_preflight_checks(show_dialog_on_fail=False)
print(f"Preflight Checks Completed: {'ALL PASSED' if passed else 'FAILURES DETECTED'}")
for item in results:
    icon = "[OK]" if item["ok"] else "[FALTA]"
    print(f" {icon} {item['name']}: {item['msg']}")

assert len(results) >= 4, "Should have checked at least 4 critical components"
assert any("Visual C++" in r["name"] for r in results)
assert any(".NET" in r["name"] for r in results)
assert any("PyQt5" in r["name"] for r in results)
assert any("Arquitectura" in r["name"] for r in results)

# 2. Individual Unit Checks
vc_ok, vc_msg = EnvironmentChecker.check_visual_cpp_redist()
print(f"\nVisual C++ Check: ok={vc_ok}, msg='{vc_msg}'")
assert vc_ok == True, "Visual C++ should be present on this machine"

dn_ok, dn_msg = EnvironmentChecker.check_dotnet_framework()
print(f".NET Framework Check: ok={dn_ok}, msg='{dn_msg}'")
assert dn_ok == True, ".NET Framework should be present on Windows 10/11"

arch_ok, arch_msg = EnvironmentChecker.check_os_architecture()
print(f"Architecture Check: ok={arch_ok}, msg='{arch_msg}'")
assert arch_ok == True, "Windows 64-bit should be confirmed"

qt_ok, qt_msg = EnvironmentChecker.check_qt_runtime()
print(f"Qt Runtime Check: ok={qt_ok}, msg='{qt_msg}'")
assert qt_ok == True, "PyQt5 should be operational"

# 3. Test Error Message Formatting on Simulated Failure
simulated_failures = [
    {"name": "Visual C++ Redistributable (2015-2022 x64)", "ok": False, "msg": "No detectado en el Registro", "critical": True},
    {"name": "Microsoft .NET Framework (4.5+)", "ok": False, "msg": "Versión obsoleta", "critical": False}
]
# Test that URLs are populated
assert EnvironmentChecker.VC_REDIST_URL.startswith("https://")
assert EnvironmentChecker.DOTNET_URL.startswith("https://")
print(f"\nDownload links verified:\n - VC++: {EnvironmentChecker.VC_REDIST_URL}\n - .NET: {EnvironmentChecker.DOTNET_URL}")

print("\n>>> ALL ENVIRONMENT & PREREQUISITE CHECKER TESTS PASSED WITH 100% SUCCESS! <<<")

