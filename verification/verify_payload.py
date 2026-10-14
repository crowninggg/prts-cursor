"""Checks the distributed themes, using no desktop settings or cursor changes."""
from pathlib import Path
import argparse
import base64
import hashlib
import io
import json
import plistlib
import stat
import struct
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from PIL import Image

SIZES = (24, 32, 48, 64, 96, 128)


def png(raw):
    image = Image.open(io.BytesIO(raw))
    image.load()
    assert image.format == "PNG" and image.mode == "RGBA"
    return image


def linux(folder):
    counts = {"themes": 0, "xcursor_names": 0, "unique_xcursor_files": 0, "image_chunks": 0, "svg_frames": 0}
    seen_binary, seen_svg = set(), set()
    for theme in sorted((folder / "files").iterdir()):
        if not theme.is_dir():
            continue
        counts["themes"] += 1
        assert "PRTS 1.1.5" in (theme / "index.theme").read_text()
        manifest = theme / "checksums.sha256"
        entries = {}
        for line in manifest.read_text().splitlines():
            digest, name = line.split("  ", 1)
            assert name not in entries and not name.startswith("/") and ".." not in Path(name).parts
            entries[name] = digest
            assert hashlib.sha256((theme / name).read_bytes()).hexdigest() == digest, name
        assert set(entries) == {p.relative_to(theme).as_posix() for p in theme.rglob("*") if p.is_file() and p != manifest}
        names = {p.name for p in (theme / "cursors").iterdir()}
        assert len(names) == 104 and names == {p.name for p in (theme / "cursors_scalable").iterdir()}
        counts["xcursor_names"] += len(names)
        for name in sorted(names):
            data = (theme / "cursors" / name).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            magic, header, version, frames = struct.unpack_from("<4I", data)
            assert magic == 0x72756358 and header == 16 and version == 1 and frames % len(SIZES) == 0
            if digest not in seen_binary:
                seen_binary.add(digest)
                counts["unique_xcursor_files"] += 1
                seen_sizes, cadence = set(), {}
                position = header + frames * 12
                for index in range(frames):
                    typ, nominal, offset = struct.unpack_from("<3I", data, header + index * 12)
                    head, chunk_type, size, ver, width, height, x, y, delay = struct.unpack_from("<9I", data, offset)
                    assert typ == chunk_type == 0xfffd0002 and offset == position and head == 36 and ver == 1
                    assert nominal == size == width == height and size in SIZES
                    assert 0 <= x < width and 0 <= y < height and delay > 0
                    position = offset + head + width * height * 4
                    pixels = data[offset + head:position]
                    assert len(pixels) == width * height * 4 and any(pixels[3::4])
                    assert all(max(b, g, r) <= a for b, g, r, a in struct.iter_unpack("4B", pixels))
                    seen_sizes.add(size)
                    cadence.setdefault(size, []).append(delay)
                    counts["image_chunks"] += 1
                assert position == len(data) and seen_sizes == set(SIZES)
                assert len({tuple(x) for x in cadence.values()}) == 1
                if theme.name.endswith("-Static"):
                    assert all(len(x) == 1 for x in cadence.values())
            scalable = theme / "cursors_scalable" / name
            frames_meta = json.loads((scalable / "metadata.json").read_text())
            assert len(frames_meta) == frames // len(SIZES)
            for frame in frames_meta:
                assert frame["nominal_size"] == 256 and frame["delay"] > 0
                assert 0 <= frame["hotspot_x"] < 256 and 0 <= frame["hotspot_y"] < 256
                assert Path(frame["filename"]).name == frame["filename"]
                svg = (scalable / frame["filename"]).read_bytes()
                digest = hashlib.sha256(svg).hexdigest()
                if digest not in seen_svg:
                    seen_svg.add(digest)
                    xml = ET.fromstring(svg)
                    image = xml.find("{http://www.w3.org/2000/svg}image")
                    source = image.attrib["{http://www.w3.org/1999/xlink}href"]
                    assert source.startswith("data:image/png;base64,") and png(base64.b64decode(source.split(",", 1)[1])).size == (256, 256)
                counts["svg_frames"] += 1
    assert counts["themes"] == 2
    return counts


def mac(folder):
    app = folder / "PRTS Install.app/Contents"
    info = plistlib.loads((app / "Info.plist").read_bytes())
    assert info["CFBundleShortVersionString"] == "1.1.5" and info["CFBundleVersion"] == "25"
    assert info["CFBundleExecutable"] == "PRTSInstaller" and (app / "MacOS/PRTSInstaller").is_file()
    counts = {"themes": 0, "role_mappings": 0, "png_representations": 0}
    unique_pngs = set()
    for file in (app / "Resources").glob("*.cape"):
        cape = plistlib.loads(file.read_bytes())
        counts["themes"] += 1
        assert cape["CapeVersion"] == 25.0 and cape["CapeName"].startswith("PRTS 1.1.5 ")
        assert cape["Identifier"] in ("local.prts.final.Animated", "local.prts.final.Static")
        assert cape["HiDPI"] and len(cape["Cursors"]) == 40
        for cursor in cape["Cursors"].values():
            counts["role_mappings"] += 1
            count = cursor["FrameCount"]
            assert 1 <= count <= 24 and cursor["FrameDuration"] > 0
            assert cursor["PointsWide"] == cursor["PointsHigh"] == 32
            assert 0 <= cursor["HotSpotX"] < 32 and 0 <= cursor["HotSpotY"] < 32
            assert len(cursor["Representations"]) == 3
            if file.stem.endswith("-Static"):
                assert count == 1
            for size, data in zip((32, 64, 96), cursor["Representations"]):
                counts["png_representations"] += 1
                key = (hashlib.sha256(data).hexdigest(), size, count)
                if key not in unique_pngs:
                    unique_pngs.add(key)
                    assert png(data).size == (size, size * count)
    assert counts["themes"] == 2
    return counts


def extract(archive, destination):
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for entry in z.infolist():
                assert not entry.filename.startswith("/") and ".." not in Path(entry.filename).parts
                if entry.filename.endswith((".command", "/PRTSInstaller")) or entry.is_dir():
                    assert (entry.external_attr >> 16) & 0o111
                assert not stat.S_ISLNK(entry.external_attr >> 16)
            z.extractall(destination)
            for entry in z.infolist():
                if not entry.is_dir():
                    (destination / entry.filename).chmod((entry.external_attr >> 16) & 0o777)
        return destination
    with tarfile.open(archive) as t:
        for entry in t:
            assert not entry.name.startswith("/") and ".." not in Path(entry.name).parts
            assert entry.isfile() or entry.isdir()
            if entry.name.endswith("/INSTALL.sh"):
                assert entry.mode & 0o111
        t.extractall(destination, filter="data")
    return destination / "PRTS-Linux"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=("macOS", "Linux"))
    parser.add_argument("package", type=Path)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    folder = args.package
    if args.package.is_file():
        if args.manifest:
            entries = json.loads(args.manifest.read_text(encoding="utf-8"))["assets"]
            entry = entries[args.package.name]
            assert args.package.stat().st_size == entry["bytes"]
            assert hashlib.sha256(args.package.read_bytes()).hexdigest() == entry["sha256"]
        folder = extract(args.package, args.work / "extracted")
    counts = (mac if args.platform == "macOS" else linux)(folder)
    result = {"passed": True, "platform": args.platform, "version": "1.1.5", "folder": str(folder.resolve()), "counts": counts}
    (args.work / "payload-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
