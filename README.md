# songyuan OTA feed

OTA update feed for unofficial LineageOS builds for the POCO F9 Ultra /
Redmi K100 Pro Max (`songyuan`). The built-in Updater app reads
`songyuan.json` from this repo:

    https://raw.githubusercontent.com/AlexZorzi/songyuan-ota/main/songyuan.json

The zips are hosted on SourceForge:
https://sourceforge.net/projects/alles-roms/files/lineage/songyuan/

## Publishing a build

1. Build a signed zip (`release-keys`).
2. Add it to the feed:

       ./make_ota_json.py lineage-24.0-YYYYMMDD-UNOFFICIAL-songyuan.zip

3. Upload the zip to the SourceForge path the script prints, and wait until
   it is downloadable.
4. Commit and push `songyuan.json`.

Only builds signed with the same keys can be installed over each other.
