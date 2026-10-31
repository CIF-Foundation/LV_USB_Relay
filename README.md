# USB Relay Control

LabVIEW library for dcttech USB HID relay boards. It discovers the boards that are plugged in, reads and writes each relay, and reads and writes the 40-bit id stored in the board's non-volatile memory.

The library is `usb_relay_control/USB Relay Control.lvlib`, opened from `Relay Board Test.lvproj` (LabVIEW 2021). The LabVIEW code calls native OS functions. On Linux, including Ubuntu and NI Linux RT, the VIs use `libc` `open`, `ioctl`, and `close`. On Windows they use `hid.dll`, `cfgmgr32.dll`, and `kernel32.dll`.

The installer is only needed on Linux, and only to set permissions on the hidraw device node. No installer is needed for Windows.

| VI | What it does |
| --- | --- |
| Get Device List | Finds boards currently plugged in |
| Read Relays | Reads the on/off state of the relays |
| Write Relay | Turns one relay on or off |
| Write Relay All Off | Turns every relay off |
| Read Device ID | Reads the 40-bit id from non-volatile memory |
| Write Device ID | Writes the 40-bit id to non-volatile memory |
| Encode Relay ID / Decode Relay ID | Packs and unpacks that id |

Each call opens the board, does the work, and closes it. A `/dev/hidrawN` node or a Windows device path is not a stable name across unplug, so discovery matches the id stored on the board.

Relay on/off is not written to the non-volatile id. The id remains across unplug and power loss. The USB descriptor serial stays empty; the id lives in the board's own memory and is read back from the HID feature report.

## Board id

The id is 40 bits, stored as five bytes, most significant bit first. The last four bits are the sub-module id.

| Field | Bits | Width | Range |
| --- | --- | --- | --- |
| Vendor ID | 39–34 | 6 | 0–63 (64 values) |
| Product ID | 33–28 | 6 | 0–63 (64 values) |
| Serial number | 27–4 | 24 | `000000`–`FFFFFF` (6 hex digits) |
| Sub-module ID | 3–0 | 4 | 0–15 (16 values) |

These vendor and product fields are values you assign in the 40-bit id. They are separate from the USB vendor id `16C0` and product id `05DF`, which identify the hardware itself.

`Write Device ID` stores the packed five bytes. `Read Device ID` returns them. `Encode Relay ID` and `Decode Relay ID` convert between the fields and those bytes.

Example: vendor 1, product 2, serial `0000AB`, sub-module 3.

```text
000001 000010 000000000000000010101011 0011
bytes: 04 20 00 2A CC
```

Give each physical board its own vendor, product, and serial. Use the sub-module field when one serial needs to name more than one module (up to 16). If two boards are programmed with the same 40-bit id, a write that selects by id cannot tell them apart. Program one board at a time, selecting it by its current device path, then read the id back to confirm.

## Supported boards

Supported boards are the dcttech USB HID relays documented at <https://sigrok.org/wiki/Dcttech_usbrelay>. The same boards are sold on Amazon, eBay, and AliExpress, usually under a title like "5V USB Relay Programmable Computer Control For Smart Home" or "HID driverless USB relay". Listings come in 1, 2, 4, and 8 channel versions. The product string reports which one you have: `USBRelay1`, `USBRelay2`, `USBRelay4`, or `USBRelay8`. Relay numbers in this library are 1 through 8; a 2-channel board only has relays 1 and 2.

A board is supported when it enumerates as USB HID with this identity:

| Field | Value |
| --- | --- |
| Vendor ID | `16C0` |
| Product ID | `05DF` |
| Manufacturer | `www.dcttech.com` |
| Product | `USBRelay1`, `USBRelay2`, `USBRelay4`, or `USBRelay8` |

On Ubuntu:

```sh
lsusb -d 16c0:05df -v
```

`iManufacturer` and `iProduct` must match the table. On Windows, Device Manager shows a HID device whose hardware id contains `VID_16C0` and `PID_05DF`.

Before buying, prefer a listing that says the board is HID or driverless and that it comes with a small Windows app or C++ library for a serial number. After it arrives, the `lsusb` check above is the test that matters. A title that only says "USB relay" covers a lot of other hardware. Boards that appear as a COM port (CH340, CP2102, FTDI, LCUS, and similar) use a different command set, and this library does not control them. Boards with vendor `0519` and product `2018` are a different HID relay and are not covered by the udev rule or this library.

Contact ratings are printed on the board. The dcttech modules sigrok lists are commonly 10 A at 250 VAC or 10 A at 30 VDC. Trust the rating on the relay you received.

## Ubuntu installer

`installer/usbrelay-hidraw_1.0.0_all.deb` installs one udev rule:

```text
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="16c0", ATTRS{idProduct}=="05df", MODE="0666"
```

That makes the matching hidraw node readable and writable by any local user, which is the account LabVIEW runs as on Ubuntu. The rule runs on every later plug-in, so boards can be added and removed after the package is installed without installing it again. The package does not install LabVIEW or the VIs. It depends only on `udev` and is architecture `all`.

Install:

```sh
sudo dpkg -i usbrelay-hidraw_1.0.0_all.deb
```

A board that was already plugged in is updated by the package's post-install script. Confirm with `ls -l /dev/hidraw*`; the relay node is mode `crw-rw-rw-`. Unplug and plug the board once more and the same mode should come back from udev alone.

Remove:

```sh
sudo dpkg -r usbrelay-hidraw
```

Rebuild the package from this tree with Python 3:

```sh
python installer/build_deb.py
```

The rule text is `installer/data/etc/udev/rules.d/99-usbrelay.rules`. The Debian control scripts are in `installer/ubuntu/`.

NI Linux RT cannot install this `.deb`. That target uses the opkg package `installer/usbrelay-hidraw_1.0.0_core2-64.ipk`, which installs the same rule:

```sh
opkg install usbrelay-hidraw_1.0.0_core2-64.ipk
```
