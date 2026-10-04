#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Alex Zorzi
# SPDX-License-Identifier: Apache-2.0
"""Add an Evolution X OTA zip to the Updater feed (evolution/<device>.json).

Usage:
  make_evox_json.py EvolutionX-17.0-YYYYMMDD-songyuan-12.2-Unofficial.zip \
      [--sf-project alles-roms] [--sf-dir evolution/songyuan] [--keep 3]

The feed format is the one org.evolution.updater parses:
{"response": [{timestamp, filename, md5, size, download, version,
               maintainer, forum, firmware, paypal}, ...]}
An update is offered when its timestamp is newer than ro.build.date.utc.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME_RE = re.compile(
    r"^EvolutionX-[\d.]+-\d{8}-(?P<device>\w+)-(?P<version>[\d.]+)-(?P<type>\w+)\.zip$")

MAINTAINER = "Alex Zorzi"
FORUM = "https://github.com/AlexZorzi/android_device_xiaomi_songyuan"


def read_metadata(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        text = z.read("META-INF/com/android/metadata").decode()
        otacert = z.read("META-INF/com/android/otacert").decode()
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line), otacert


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--sf-project", default="alles-roms", help="SourceForge project name")
    ap.add_argument("--sf-dir", default="evolution/songyuan", help="folder inside the project")
    ap.add_argument("--keep", type=int, default=3, help="builds kept in the feed")
    args = ap.parse_args()

    name = os.path.basename(args.zip)
    m = NAME_RE.match(name)
    if not m:
        sys.exit(f"unexpected zip name: {name}")
    meta, otacert = read_metadata(args.zip)
    if meta.get("pre-device") != m["device"]:
        sys.exit(f"zip is for {meta.get('pre-device')}, name says {m['device']}")
    releasekey = os.path.expanduser("~/.android-certs/releasekey.x509.pem")
    if not os.path.exists(releasekey):
        sys.exit(f"missing {releasekey}; cannot verify the zip's signing key")
    with open(releasekey) as f:
        if f.read().strip() != otacert.strip():
            sys.exit("refusing: this zip is not signed with your release key")

    entry = {
        "timestamp": int(meta["post-timestamp"]),
        "filename": name,
        "md5": md5(args.zip),
        "size": os.path.getsize(args.zip),
        "download": f"https://downloads.sourceforge.net/project/"
                    f"{args.sf_project}/{args.sf_dir}/{name}",
        "version": m["version"],
        "maintainer": MAINTAINER,
        "forum": FORUM,
        "firmware": "",
        "paypal": "",
    }

    feed_path = os.path.join(ROOT, "evolution", f"{m['device']}.json")
    os.makedirs(os.path.dirname(feed_path), exist_ok=True)
    builds = []
    if os.path.exists(feed_path):
        with open(feed_path) as f:
            builds = json.load(f).get("response", [])
    builds = [b for b in builds if b["filename"] != name]
    builds.append(entry)
    builds.sort(key=lambda b: b["timestamp"], reverse=True)
    builds = builds[:args.keep]

    with open(feed_path, "w") as f:
        json.dump({"response": builds}, f, indent=2)
        f.write("\n")
    print(f"added {name} ({entry['timestamp']}), feed has {len(builds)} build(s)")
    print(f"upload the zip to: {entry['download']}")


if __name__ == "__main__":
    main()
