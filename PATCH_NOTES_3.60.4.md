# LadderIQ v3.60.4 — Git Cache Exclusion Fix

## Issue corrected
The scanner creates and replaces files under `market_cache/prices` while Git stages the project. A cache file could disappear between Git's directory scan and file read, causing:

`error: open("market_cache/prices/...pkl"): No such file or directory`

and stopping publication at `git add`.

## Changes
- Added `.gitignore` rules that exclude the entire `market_cache/` runtime folder.
- Added standard exclusions for `__pycache__`, Python bytecode, and temporary files.
- Updated `publish_ladderiq.ps1` to remove any previously tracked `market_cache` content from the Git index without deleting local cache files.
- Git now stages only source, configuration, reports, and other durable project artifacts.

## Installation
Extract this patch into `C:\Development` and allow Windows to replace the existing `publish_ladderiq.ps1` file.

The next run can safely build/update the local scanner cache while Git publishes the durable LadderIQ files.
