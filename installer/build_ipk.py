"""Build an opkg package for NI Linux RT from the installer/ tree."""

import io
import tarfile
import time
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = "usbrelay-hidraw"
VERSION = "1.0.0"
ARCH = "core2-64"
OUT = ROOT / f"{PACKAGE}_{VERSION}_{ARCH}.ipk"


def lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def tar_gz(members: list[tuple[str, bytes, int]]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data, mode in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = mode
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            info.mtime = int(time.time())
            info.type = tarfile.REGTYPE
            tar.addfile(info, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return compressed.getvalue()


def ar_member(name: str, data: bytes) -> bytes:
    name_field = (name + "/").ljust(16).encode("ascii")
    if len(name_field) != 16:
        raise SystemExit(f"ar name too long: {name}")
    header = b"".join(
        [
            name_field,
            f"{int(time.time()):<12d}".encode("ascii"),
            b"0     ",
            b"0     ",
            b"100644  ",
            f"{len(data):<10d}".encode("ascii"),
            b"`\n",
        ]
    )
    if len(header) != 60:
        raise SystemExit(f"bad ar header length {len(header)} for {name}")
    blob = header + data
    if len(data) % 2:
        blob += b"\n"
    return blob


def main() -> None:
    control = lf((ROOT / "control" / "control").read_bytes())
    if not control.endswith(b"\n"):
        control += b"\n"
    postinst = lf((ROOT / "control" / "postinst").read_bytes())
    postrm = lf((ROOT / "control" / "postrm").read_bytes())
    rule = lf((ROOT / "data" / "etc" / "udev" / "rules.d" / "99-usbrelay.rules").read_bytes())
    if not rule.endswith(b"\n"):
        rule += b"\n"
    debian = lf((ROOT / "debian-binary").read_bytes())
    if not debian.endswith(b"\n"):
        debian += b"\n"

    control_tar = tar_gz(
        [
            ("control", control, 0o644),
            ("postinst", postinst, 0o755),
            ("postrm", postrm, 0o755),
        ]
    )
    data_tar = tar_gz(
        [
            ("etc/udev/rules.d/99-usbrelay.rules", rule, 0o644),
        ]
    )
    ipk = b"!<arch>\n" + ar_member("debian-binary", debian) + ar_member(
        "control.tar.gz", control_tar
    ) + ar_member("data.tar.gz", data_tar)
    OUT.write_bytes(ipk)
    print(OUT)


if __name__ == "__main__":
    main()
