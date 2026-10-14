"""Native system-tool and cursor-loader checks on disposable CI runners."""
from pathlib import Path
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys


def run(args, **kwargs):
    process = subprocess.run([str(x) for x in args], text=True, capture_output=True, timeout=180, **kwargs)
    if process.returncode:
        raise AssertionError((args, process.returncode, process.stdout[-6000:], process.stderr[-6000:]))
    return process.stdout


def linux(package, work):
    assert sys.platform == "linux"
    run(["/bin/sh", "-n", package / "INSTALL.sh"])
    env = os.environ.copy()
    isolated = work / "native-user"
    isolated.mkdir(parents=True)
    env.update(HOME=str(isolated), XDG_DATA_HOME=str(isolated / "data"), XDG_CONFIG_HOME=str(isolated / "config"),
               XDG_STATE_HOME=str(isolated / "state"), XDG_CURRENT_DESKTOP="GNOME", XDG_SESSION_TYPE="x11",
               GSETTINGS_BACKEND="dconf")
    env.pop("SUDO_USER", None)
    schema = "org.gnome.desktop.interface"
    run(["gsettings", "set", schema, "cursor-theme", "'Adwaita'"], env=env)
    run(["gsettings", "set", schema, "cursor-size", "48"], env=env)
    for action, theme in [("static", "'PRTS-Final-Static'"), ("install", "'PRTS-Final'"), ("restore", "'Adwaita'")]:
        output = run(["/bin/sh", package / "INSTALL.sh", action], env=env)
        assert run(["gsettings", "get", schema, "cursor-theme"], env=env).strip() == theme, output
        assert run(["gsettings", "get", schema, "cursor-size"], env=env).strip() == "48"
    xcursor = C.CDLL(ctypes.util.find_library("Xcursor"))
    xlib = C.CDLL(ctypes.util.find_library("X11"))

    class Image(C.Structure):
        _fields_ = [(name, C.c_uint) for name in ("version", "size", "width", "height", "xhot", "yhot", "delay")] + [("pixels", C.POINTER(C.c_uint))]

    class Images(C.Structure):
        _fields_ = [("nimage", C.c_int), ("images", C.POINTER(C.POINTER(Image))), ("name", C.c_char_p)]

    xcursor.XcursorFilenameLoadImages.argtypes = [C.c_char_p, C.c_int]
    xcursor.XcursorFilenameLoadImages.restype = C.POINTER(Images)
    xcursor.XcursorImagesDestroy.argtypes = [C.POINTER(Images)]
    xcursor.XcursorImagesLoadCursor.argtypes = [C.c_void_p, C.POINTER(Images)]
    xcursor.XcursorImagesLoadCursor.restype = C.c_ulong
    xlib.XOpenDisplay.argtypes = [C.c_char_p]
    xlib.XOpenDisplay.restype = C.c_void_p
    xlib.XDefaultRootWindow.argtypes = [C.c_void_p]
    xlib.XDefaultRootWindow.restype = C.c_ulong
    xlib.XCreateSimpleWindow.argtypes = [C.c_void_p, C.c_ulong, C.c_int, C.c_int, C.c_uint, C.c_uint, C.c_uint, C.c_ulong, C.c_ulong]
    xlib.XCreateSimpleWindow.restype = C.c_ulong
    xlib.XDefineCursor.argtypes = [C.c_void_p, C.c_ulong, C.c_ulong]
    xlib.XFreeCursor.argtypes = [C.c_void_p, C.c_ulong]
    xlib.XDestroyWindow.argtypes = [C.c_void_p, C.c_ulong]
    xlib.XSync.argtypes = [C.c_void_p, C.c_int]
    xlib.XCloseDisplay.argtypes = [C.c_void_p]
    display = xlib.XOpenDisplay(None)
    assert display, "X11 test display unavailable"
    window = xlib.XCreateSimpleWindow(display, xlib.XDefaultRootWindow(display), 0, 0, 100, 100, 0, 0, 0)
    seen, loads = set(), 0
    try:
        for file in sorted((package / "files").glob("*/cursors/*")):
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            for size in (24, 32, 48, 64, 96, 128):
                images = xcursor.XcursorFilenameLoadImages(os.fsencode(file), size)
                assert images and images.contents.nimage > 0, (file, size)
                try:
                    for index in range(images.contents.nimage):
                        image = images.contents.images[index].contents
                        assert image.size == size and image.width == image.height == size
                        assert image.xhot < size and image.yhot < size and image.delay > 0
                    cursor = xcursor.XcursorImagesLoadCursor(display, images)
                    assert cursor, (file, size, "X11 cursor creation failed")
                    xlib.XDefineCursor(display, window, cursor)
                    xlib.XSync(display, 0)
                    xlib.XFreeCursor(display, cursor)
                    loads += 1
                finally:
                    xcursor.XcursorImagesDestroy(images)
    finally:
        xlib.XDestroyWindow(display, window)
        xlib.XCloseDisplay(display)
    return {"libXcursor_X11_loads": loads, "unique_resources": len(seen),
            "real_dconf_install_static_animated_restore": True, "system_size_preserved": True,
            "limits": ["X11 runs in Xvfb; application refresh and a live Wayland desktop were not tested."]}


def mac(package, work):
    assert sys.platform == "darwin"
    app = package / "PRTS Install.app/Contents"
    script = app / "MacOS/PRTSInstaller"
    for file in [script, package / "Install-PRTS.command"]:
        assert os.access(file, os.X_OK), file
        run(["/bin/bash", "-n", file])
    for file in [app / "Info.plist", *(app / "Resources").glob("*.cape")]:
        run(["/usr/bin/plutil", "-lint", file])
    # Compile dialog source with the actual AppleScript compiler without showing UI.
    dialogs = re.findall(r"<<'APPLE'\n(.*?)\nAPPLE", script.read_text(), re.S)
    assert len(dialogs) == 2
    for index, source in enumerate(dialogs):
        file = work / f"dialog-{index}.applescript"
        file.write_text(source)
        run(["/usr/bin/osacompile", "-o", work / f"dialog-{index}.scpt", file])
    # macOS /bin/bash and BSD mktemp must accept the actual installed templates.
    for template in ("installer.XXXXXX", ".prts-cape.XXXXXX"):
        path = run(["/usr/bin/mktemp", str(work / template)]).strip()
        assert Path(path).is_file()
        Path(path).unlink()
    output = run(["/usr/bin/swift", Path(__file__).with_name("MacCursorCheck.swift"), app / "Resources"])
    assert output.startswith("PASS"), output
    env = os.environ.copy()
    isolated = work / "native-user"
    isolated.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(isolated)
    diagnostic = run(["/bin/bash", package / "Install-PRTS.command", "--diagnose"], env=env)
    assert diagnostic.startswith("Diagnostic log: "), diagnostic
    log = Path(diagnostic.strip().split(": ", 1)[1])
    assert log.is_file() and "PRTS macOS 1.1.5" in log.read_text()
    return {"real_plutil": True, "native_AppleScript_compilation": len(dialogs),
            "native_BSD_mktemp": True, "native_appkit_cursor_check": output.strip(),
            "native_diagnostic_entrypoint": True,
            "limits": ["Mousecape's private system cursor injection, GUI prompts and Gatekeeper approval require end-user testing."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=("macOS", "Linux"))
    parser.add_argument("package", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    data = (mac if args.platform == "macOS" else linux)(args.package.resolve(), args.work.resolve())
    data.update(passed=True, platform=args.platform, os=platform.platform(), machine=platform.machine())
    (args.work / "native-result.json").write_text(json.dumps(data, indent=2))
    print(json.dumps(data, indent=2), flush=True)
