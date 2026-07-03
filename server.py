"""DiskDuran – Windows 10/11 backend."""

import os, sys, time, json, subprocess, threading, ctypes, shutil, winreg
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import psutil

app = FastAPI()
_base = os.environ.get("DISKDURAN_BASE", str(Path(__file__).parent))
static_dir = Path(_base) / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

scan_state = {"status": "idle", "progress": "", "pct": 0, "data": None}

# ── Helpers ──────────────────────────────────────────────────────────────

def fmt(b):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} PB"


def get_home():
    return str(Path.home())


def get_all_disks():
    disks = []
    seen = set()
    for part in psutil.disk_partitions(all=False):
        if part.mountpoint in seen:
            continue
        seen.add(part.mountpoint)
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        letter = part.mountpoint.rstrip("\\")
        name = f"Disco ({letter})"
        if part.mountpoint.upper().startswith("C:"):
            name = f"Sistema ({letter})"
        disks.append({
            "name": name,
            "mountpoint": part.mountpoint,
            "device": part.device,
            "fstype": part.fstype,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent": usage.percent,
        })
    disks.sort(key=lambda x: (0 if x["mountpoint"].upper().startswith("C:") else 1, x["mountpoint"]))
    return disks


def get_disk_info():
    disks = get_all_disks()
    return disks[0] if disks else {"total": 0, "used": 0, "free": 0, "percent": 0}


def get_folder_sizes(home):
    folders = []
    try:
        for entry in os.scandir(home):
            if entry.is_dir(follow_symlinks=False):
                size = dir_size(entry.path, max_depth=3)
                if size > 0:
                    folders.append({
                        "name": entry.name,
                        "path": entry.path,
                        "size": size,
                        "type": "dir",
                    })
    except PermissionError:
        pass
    folders.sort(key=lambda x: x["size"], reverse=True)
    return folders


def dir_size(path, max_depth=5, _depth=0):
    total = 0
    if _depth > max_depth:
        return total
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += dir_size(entry.path, max_depth, _depth + 1)
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass
    return total


def find_junk(home):
    junk = []
    candidates = [
        (os.path.join(home, "AppData", "Local", "Temp"), "Archivos temporales del usuario"),
        (os.environ.get("TEMP", ""), "Carpeta TEMP del sistema"),
        (os.path.join(home, "AppData", "Local", "Microsoft", "Windows", "INetCache"), "Caché de Internet"),
        (os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache"), "Caché de Chrome"),
        (os.path.join(home, "AppData", "Local", "Mozilla", "Firefox", "Profiles"), "Caché de Firefox"),
        (os.path.join(home, "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache"), "Caché de Edge"),
        (os.path.join(home, "AppData", "Local", "npm-cache"), "Caché de npm"),
        (os.path.join(home, "AppData", "Local", "pip", "cache"), "Caché de pip"),
        (os.path.join(home, "AppData", "Local", "NuGet", "Cache"), "Caché de NuGet"),
        ("C:\\Windows\\Temp", "Temp de Windows"),
        ("C:\\Windows\\SoftwareDistribution\\Download", "Windows Update cache"),
        (os.path.join(home, "AppData", "Local", "CrashDumps"), "Crash dumps"),
        (os.path.join(home, "Downloads"), "Carpeta de Descargas"),
    ]
    for path, desc in candidates:
        if path and os.path.isdir(path):
            size = dir_size(path, max_depth=2)
            if size > 1_000_000:
                junk.append({
                    "name": os.path.basename(path),
                    "path": path,
                    "size": size,
                    "desc": desc,
                })
    # Recycle Bin
    try:
        rb_path = "C:\\$Recycle.Bin"
        if os.path.exists(rb_path):
            size = dir_size(rb_path, max_depth=2)
            if size > 0:
                junk.append({"name": "Papelera de reciclaje", "path": rb_path, "size": size, "desc": "Archivos en la papelera"})
    except:
        pass

    junk.sort(key=lambda x: x["size"], reverse=True)
    return junk


def find_vms(home):
    vms = []
    vm_extensions = {".vmdk", ".vhdx", ".vdi", ".qcow2", ".vmx", ".vbox"}
    vm_dirs = [
        os.path.join(home, "VirtualBox VMs"),
        os.path.join(home, "Virtual Machines"),
        os.path.join(home, ".VirtualBox"),
        os.path.join(home, "Documents", "Virtual Machines"),
        os.path.join(home, "Documents", "Hyper-V"),
    ]
    seen = set()
    for vdir in vm_dirs:
        if not os.path.isdir(vdir):
            continue
        try:
            for root, dirs, files in os.walk(vdir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in vm_extensions:
                        vm_folder = root
                        if vm_folder in seen:
                            continue
                        seen.add(vm_folder)
                        size = dir_size(vm_folder, max_depth=2)
                        try:
                            mtime = os.path.getmtime(os.path.join(root, f))
                            last_used = datetime.fromtimestamp(mtime)
                            days = (datetime.now() - last_used).days
                        except:
                            last_used = None
                            days = 9999
                        status = "active" if days < 14 else "inactive" if days < 180 else "abandoned"
                        vms.append({
                            "name": os.path.basename(vm_folder),
                            "path": vm_folder,
                            "size": size,
                            "last_used_str": last_used.strftime("%Y-%m-%d") if last_used else "Desconocido",
                            "days_inactive": days,
                            "status": status,
                        })
        except (PermissionError, OSError):
            pass
    # Also check for WSL
    wsl_path = os.path.join(home, "AppData", "Local", "Packages")
    if os.path.isdir(wsl_path):
        try:
            for entry in os.scandir(wsl_path):
                if entry.is_dir() and "linux" in entry.name.lower():
                    size = dir_size(entry.path, max_depth=3)
                    if size > 100_000_000:
                        vms.append({
                            "name": f"WSL: {entry.name}",
                            "path": entry.path,
                            "size": size,
                            "last_used_str": "",
                            "days_inactive": 0,
                            "status": "active",
                        })
        except:
            pass
    vms.sort(key=lambda x: x["size"], reverse=True)
    return vms


EXT_MAP = {
    "Video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"},
    "Imágenes": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic", ".raw"},
    "Documentos": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt", ".csv"},
    "Comprimidos": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab", ".msi"},
    "VMs": {".vmdk", ".vhdx", ".vdi", ".qcow2", ".iso", ".img"},
    "Código": {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".cs", ".rb", ".php", ".swift", ".kt", ".html", ".css", ".scss", ".sql", ".sh", ".bat", ".ps1"},
    "Datos": {".db", ".sqlite", ".sqlite3", ".json", ".xml", ".yaml", ".yml", ".log", ".dat", ".bak"},
}

def categorize_files(home):
    cats = {}
    for cat in EXT_MAP:
        cats[cat] = {"size": 0, "count": 0, "files": []}
    cats["Otros"] = {"size": 0, "count": 0, "files": []}

    scan_dirs = [
        home,
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Desktop"),
        os.path.join(home, "Videos"),
        os.path.join(home, "Music"),
        os.path.join(home, "Pictures"),
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        try:
            for root, dirs, files in os.walk(scan_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", ".git", "__pycache__", "venv", ".venv")]
                depth = root.replace(scan_dir, "").count(os.sep)
                if depth > 4:
                    dirs.clear()
                    continue
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                    except:
                        continue
                    ext = os.path.splitext(f)[1].lower()
                    matched = False
                    for cat, exts in EXT_MAP.items():
                        if ext in exts:
                            cats[cat]["size"] += sz
                            cats[cat]["count"] += 1
                            if sz > 5_000_000:
                                cats[cat]["files"].append({"name": f, "path": fp, "size": sz})
                            matched = True
                            break
                    if not matched:
                        cats["Otros"]["size"] += sz
                        cats["Otros"]["count"] += 1
        except (PermissionError, OSError):
            pass

    for cat in cats.values():
        cat["files"].sort(key=lambda x: x["size"], reverse=True)
        cat["files"] = cat["files"][:30]

    return {k: v for k, v in cats.items() if v["count"] > 0}


def find_apps():
    apps = []
    seen = set()

    program_dirs = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
        os.path.join(get_home(), "AppData", "Local", "Programs"),
    ]

    for pdir in program_dirs:
        if not pdir or not os.path.isdir(pdir):
            continue
        try:
            for entry in os.scandir(pdir):
                if not entry.is_dir():
                    continue
                name = entry.name
                if name.lower() in seen or name.startswith("."):
                    continue
                seen.add(name.lower())
                size = dir_size(entry.path, max_depth=3)
                if size < 1_000_000:
                    continue
                try:
                    mtime = max(
                        os.path.getmtime(os.path.join(entry.path, f))
                        for f in os.listdir(entry.path)
                        if os.path.isfile(os.path.join(entry.path, f))
                    ) if os.listdir(entry.path) else 0
                    last_used = datetime.fromtimestamp(mtime) if mtime else None
                    days = (datetime.now() - last_used).days if last_used else 9999
                except:
                    last_used = None
                    days = 9999

                status = "active" if days < 60 else "inactive" if days < 180 else "abandoned"
                apps.append({
                    "name": name,
                    "path": entry.path,
                    "size": size,
                    "last_used_str": last_used.strftime("%Y-%m-%d") if last_used else "Nunca",
                    "days_inactive": days,
                    "status": status,
                })
        except (PermissionError, OSError):
            pass

    # Also check registry for installed apps
    try:
        reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                            if name.lower() in seen or not install_loc or not os.path.isdir(install_loc):
                                continue
                            seen.add(name.lower())
                            size = dir_size(install_loc, max_depth=2)
                            if size < 5_000_000:
                                continue
                            try:
                                date_str = winreg.QueryValueEx(subkey, "InstallDate")[0]
                                install_date = datetime.strptime(date_str, "%Y%m%d")
                                days = (datetime.now() - install_date).days
                            except:
                                days = 9999
                                install_date = None
                            status = "active" if days < 60 else "inactive" if days < 180 else "abandoned"
                            apps.append({
                                "name": name,
                                "path": install_loc,
                                "size": size,
                                "last_used_str": install_date.strftime("%Y-%m-%d") if install_date else "Desconocido",
                                "days_inactive": days,
                                "status": status,
                            })
                        except (FileNotFoundError, OSError):
                            pass
                except (PermissionError, OSError):
                    pass
    except:
        pass

    apps.sort(key=lambda x: x["size"], reverse=True)
    return apps


def find_largest(home):
    largest = []
    scan_dirs = [home]
    for sd in scan_dirs:
        try:
            for root, dirs, files in os.walk(sd):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", ".git", "__pycache__")]
                depth = root.replace(sd, "").count(os.sep)
                if depth > 5:
                    dirs.clear()
                    continue
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        if sz > 50_000_000:
                            largest.append({"name": f, "path": fp, "size": sz})
                    except:
                        pass
        except (PermissionError, OSError):
            pass
    largest.sort(key=lambda x: x["size"], reverse=True)
    return largest[:50]


# ── Scan pipeline ────────────────────────────────────────────────────────

def do_scan(mountpoint=None):
    global scan_state
    scan_state = {"status": "scanning", "progress": "", "pct": 0, "data": None}
    home = get_home()
    all_disks = get_all_disks()

    if mountpoint:
        disk = next((d for d in all_disks if d["mountpoint"] == mountpoint), None)
        if not disk:
            try:
                usage = psutil.disk_usage(mountpoint)
                disk = {"name": mountpoint, "mountpoint": mountpoint,
                        "total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent}
            except:
                disk = all_disks[0] if all_disks else {"total": 0, "used": 0, "free": 0, "percent": 0}
                mountpoint = "C:\\"
    else:
        disk = all_disks[0] if all_disks else {"total": 0, "used": 0, "free": 0, "percent": 0}
        mountpoint = disk.get("mountpoint", "C:\\")

    is_system = mountpoint.upper().startswith("C:")
    scan_root = home if is_system else mountpoint

    result = {"home": home, "scan_root": scan_root, "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    scan_state["progress"] = "Obteniendo info del disco..."
    scan_state["pct"] = 5
    result["disk"] = disk
    result["disks"] = all_disks

    scan_state["progress"] = "Escaneando carpetas principales..."
    scan_state["pct"] = 10
    result["tree"] = get_folder_sizes(scan_root)

    scan_state["progress"] = "Buscando basura recuperable..."
    scan_state["pct"] = 30
    result["junk"] = find_junk(scan_root) if is_system else find_junk_external(scan_root)
    result["recoverable"] = sum(j["size"] for j in result["junk"])

    scan_state["progress"] = "Detectando máquinas virtuales..."
    scan_state["pct"] = 45
    result["vms"] = find_vms(scan_root)
    result["vm_space"] = sum(v["size"] for v in result["vms"])

    scan_state["progress"] = "Categorizando archivos..."
    scan_state["pct"] = 55
    result["categories"] = categorize_files(scan_root)

    scan_state["progress"] = "Analizando aplicaciones instaladas..."
    scan_state["pct"] = 75
    result["apps"] = find_apps() if is_system else []

    scan_state["progress"] = "Buscando archivos más grandes..."
    scan_state["pct"] = 85
    result["largest"] = find_largest(scan_root)

    scan_state["data"] = result
    scan_state["status"] = "ready"
    scan_state["pct"] = 100


def find_junk_external(root):
    results = []
    junk_names = {"node_modules", "__pycache__", ".cache", "Thumbs.db", "$RECYCLE.BIN"}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        depth = dirpath.replace(root, "").count(os.sep)
        if depth > 5:
            dirnames.clear()
            continue
        for d in list(dirnames):
            if d in junk_names:
                full = os.path.join(dirpath, d)
                size = dir_size(full, max_depth=2)
                if size > 1_000_000:
                    results.append({"name": d, "path": full, "size": size, "desc": f"{d} en {dirpath}"})
    results.sort(key=lambda x: x["size"], reverse=True)
    return results


# ── API routes ───────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/disks")
async def api_disks():
    return {"disks": get_all_disks()}


@app.get("/api/scan")
async def api_scan(disk: str = None):
    threading.Thread(target=do_scan, args=(disk,), daemon=True).start()
    return {"status": "started"}


@app.get("/api/status")
async def api_status():
    return {
        "status": scan_state["status"],
        "progress": scan_state.get("progress", ""),
        "pct": scan_state.get("pct", 0),
    }


@app.get("/api/results")
async def api_results():
    if scan_state["status"] == "ready" and scan_state["data"]:
        return {"status": "ready", "data": scan_state["data"]}
    return {"status": scan_state["status"]}


@app.get("/api/browse")
async def api_browse(path: str):
    items = []
    try:
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                size = dir_size(entry.path, max_depth=2)
                items.append({"name": entry.name, "path": entry.path, "size": size, "type": "dir"})
            elif entry.is_file(follow_symlinks=False):
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                    items.append({"name": entry.name, "path": entry.path, "size": size, "type": "file"})
                except:
                    pass
    except (PermissionError, OSError):
        pass
    items.sort(key=lambda x: x["size"], reverse=True)
    return {"items": items}


@app.get("/api/reveal")
async def api_reveal(path: str):
    home = get_home()
    if not path.startswith(home) and not path.startswith("C:\\Program Files"):
        return {"status": "error", "detail": "Ruta no permitida"}
    try:
        if os.path.isdir(path):
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["explorer", "/select,", path])
    except:
        pass
    return {"status": "ok"}


@app.post("/api/delete")
async def api_delete(path: str, permanent: bool = False):
    home = get_home()
    prog_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    prog_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

    allowed = path.startswith(home) or path.startswith(prog_files) or path.startswith(prog_x86)
    if not allowed:
        return {"status": "error", "detail": "Ruta no permitida"}

    try:
        size = dir_size(path) if os.path.isdir(path) else os.path.getsize(path)
    except:
        size = 0

    try:
        if permanent:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.remove(path)
        else:
            try:
                from send2trash import send2trash
                send2trash(path)
            except ImportError:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
        return {"status": "ok", "freed": size}
    except PermissionError:
        return {"status": "error", "detail": "Se requieren permisos de administrador"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8420))
    print(f"\n  🔍 DiskDuran arrancando en http://localhost:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
