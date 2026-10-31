"""Build an Ubuntu/Debian package from the shared udev rule."""

import hashlib
import io
import tarfile
import time
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UBUNTU = ROOT / "ubuntu"
PACKAGE = "usbrelay-hidraw"
VERSION = "1.0.0"
ARCH = "all"
OUT = ROOT / f"{PACKAGE}_{VERSION}_{ARCH}.deb"
RULE_PATH = "etc/udev/rules.d/99-usbrelay.rules"


def lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def tar_gz(members: list[tuple[tarfile.TarInfo, bytes | None]]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for info, data in members:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return compressed.getvalue()


def file_info(name: str, data: bytes, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = int(time.time())
    info.type = tarfile.REGTYPE
    return info


def dir_info(name: str) -> tarfile.TarInfo:
    if not name.endswith("/"):
        name += "/"
    info = tarfile.TarInfo(name=name)
    info.mode = 0o755
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = int(time.time())
    info.type = tarfile.DIRTYPE
    return info


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
    control = lf((UBUNTU / "control").read_bytes())
    if not control.endswith(b"\n"):
        control += b"\n"
    postinst = lf((UBUNTU / "postinst").read_bytes())
    postrm = lf((UBUNTU / "postrm").read_bytes())
    rule = lf((ROOT / "data" / RULE_PATH).read_bytes())
    if not rule.endswith(b"\n"):
        rule += b"\n"
    debian = b"2.0\n"
    md5sums = (
        hashlib.md5(rule).hexdigest() + "  " + RULE_PATH + "\n"
    ).encode("ascii")

    control_tar = tar_gz(
        [
            (file_info("./control", control, 0o644), control),
            (file_info("./postinst", postinst, 0o755), postinst),
            (file_info("./postrm", postrm, 0o755), postrm),
            (file_info("./md5sums", md5sums, 0o644), md5sums),
        ]
    )
    data_tar = tar_gz(
        [
            (dir_info("./"), None),
            (dir_info("./etc"), None),
            (dir_info("./etc/udev"), None),
            (dir_info("./etc/udev/rules.d"), None),
            (file_info("./" + RULE_PATH, rule, 0o644), rule),
        ]
    )
    deb = b"!<arch>\n" + ar_member("debian-binary", debian) + ar_member(
        "control.tar.gz", control_tar
    ) + ar_member("data.tar.gz", data_tar)
    OUT.write_bytes(deb)
    print(OUT)


if __name__ == "__main__":
    main()
