#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alex Zorzi
# SPDX-License-Identifier: Apache-2.0
"""Add a LineageOS OTA zip to the Updater feed (songyuan.json).

Usage:
  make_ota_json.py lineage-24.0-YYYYMMDD-UNOFFICIAL-songyuan.zip \
      [--sf-project alles-roms] [--sf-dir songyuan] [--keep 3]

The feed format is the one packages/apps/Updater parses (see its README):
a JSON list, newest first, one entry per build.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

FEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songyuan.json")
NAME_RE = re.compile(r"^lineage-(?P<version>[\d.]+)-\d{8}-(?P<type>[A-Z]+)-(?P<device>\w+)\.zip$")


def read_metadata(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        text = z.read("META-INF/com/android/metadata").decode()
        otacert = z.read("META-INF/com/android/otacert").decode()
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line), otacert


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--sf-project", default="alles-roms", help="SourceForge project name")
    ap.add_argument("--sf-dir", default="songyuan", help="folder inside the project")
    ap.add_argument("--keep", type=int, default=3, help="builds kept in the feed")
    args = ap.parse_args()

    name = os.path.basename(args.zip)
    m = NAME_RE.match(name)
    if not m:
        sys.exit(f"unexpected zip name: {name}")
    meta, otacert = read_metadata(args.zip)
    if meta.get("pre-device") != m["device"]:
        sys.exit(f"zip is for {meta.get('pre-device')}, name says {m['device']}")
    # post-build carries the spoofed stock fingerprint, so it always says
    # release-keys; the OTA cert embedded in the zip is what matters.
    releasekey = os.path.expanduser("~/.android-certs/releasekey.x509.pem")
    if not os.path.exists(releasekey):
        sys.exit(f"missing {releasekey}; cannot verify the zip's signing key")
    with open(releasekey) as f:
        if f.read().strip() != otacert.strip():
            sys.exit("refusing: this zip is not signed with your release key")

    entry = {
        "datetime": int(meta["post-timestamp"]),
        "files": [{
            "filename": name,
            "os_patch_level": meta["post-security-patch-level"],
            # Required in practice: the Updater hides any build whose
            # os_sdk_level (default 0) is below the device's SDK level.
            "os_sdk_level": int(meta["post-sdk-level"]),
            "ota_property_files": meta["ota-property-files"],
            "sha256": sha256(args.zip),
            "size": os.path.getsize(args.zip),
            # downloads.sourceforge.net 302s straight to a mirror; the
            # Updater and update_engine follow it (the feed URL must not).
            "url": f"https://downloads.sourceforge.net/project/"
                   f"{args.sf_project}/{args.sf_dir}/{name}",
        }],
        "type": m["type"].lower(),
        "version": m["version"],
    }

    feed = []
    if os.path.exists(FEED):
        with open(FEED) as f:
            feed = json.load(f)
    feed = [e for e in feed if e["files"][0]["filename"] != name]
    feed.append(entry)
    feed.sort(key=lambda e: e["datetime"], reverse=True)
    feed = feed[:args.keep]

    with open(FEED, "w") as f:
        json.dump(feed, f, indent=2)
        f.write("\n")
    print(f"added {name} ({entry['datetime']}), feed has {len(feed)} build(s)")
    print(f"upload the zip to: {entry['files'][0]['url']}")


if __name__ == "__main__":
    main()
