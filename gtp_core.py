"""
Adapter wrapping gtp.py functions for GUI use.

Reimplements only the orchestration loop from gtp.main() to add:
- Structured return values (ProcessingResult)
- Progress callbacks (ProgressInfo)
- Cancellation support (cancel_flag)
- ZIP extraction for raw Takeout archives
- Full pipeline: extract → process → dedup → similarity

All actual work is delegated to gtp.* functions unchanged.
"""

import os
import time
import zipfile
from dataclasses import dataclass, field
from typing import Callable, Optional

import gtp
import duplicate_detector
import similarity_detector
import quality_detector


@dataclass
class ProgressInfo:
    phase: str
    current: int
    total: int
    message: str


@dataclass
class ProcessingResult:
    processed: list = field(default_factory=list)
    unprocessed: list = field(default_factory=list)
    unprocessed_jsons: list = field(default_factory=list)
    output_dir: str = ""
    elapsed_seconds: float = 0.0


ProgressCallback = Callable[[ProgressInfo], None]


def process_takeout(
    path: str,
    suffixes: list[str] | None = None,
    destination: str | None = None,
    on_progress: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> ProcessingResult:
    """
    Process a Google Takeout folder. Wraps gtp.py functions with
    progress callbacks and structured return values.
    """
    if suffixes is None:
        suffixes = ["", "-edited"]

    def _progress(phase, current, total, message=""):
        if on_progress:
            on_progress(ProgressInfo(phase, current, total, message))

    def _cancelled():
        return cancel_flag() if cancel_flag else False

    start_time = time.time()

    # Validate input
    if not gtp.exists(path):
        raise FileNotFoundError(f"Input path does not exist: {path}")

    # Setup output directory
    if not destination:
        saveto = gtp.checkout_dir(
            os.path.join(os.path.dirname(path), "gtpOutput"), onlynew=True
        )
    else:
        if not gtp.exists(destination):
            gtp.checkout_dir(destination)
        saveto = gtp.checkout_dir(
            os.path.join(destination, "gtpOutput"), onlynew=True
        )

    # Scan files
    _progress("scanning", 0, 0, f"Scanning {path}...")
    jsons, files = gtp.get_file_names(path)
    _progress("scanning", 1, 1, f"Found {len(jsons)} JSON files, {len(files)} media files")

    # Init logging
    gtp.log_detail(saveto, f"Started processing directory: {path}\n")

    processed = []
    unprocessed_jsons = []
    total_jsons = len(jsons)

    # Main processing loop
    for i, jsonpath in enumerate(jsons):
        if _cancelled():
            _progress("cancelled", i, total_jsons, "Processing cancelled by user")
            break

        _progress("processing", i, total_jsons, f"Processing: {os.path.basename(jsonpath)}")

        jsondata = gtp.unpack_json(jsonpath, saveto)

        if not jsondata:
            unprocessed_jsons.append({
                "filename": os.path.basename(jsonpath),
                "filepath": jsonpath,
                "title": "Title is missing",
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            gtp.log_detail(saveto, f"Skipping JSON file in the main loop: {jsonpath}\n")
            continue

        gtp.log_detail(saveto, f'Searching for file pairs based on "title" from JSON: {jsondata["title"]}')
        exist, files_ = gtp.find_file(jsondata, files, suffixes)

        for file in files_:
            if exist:
                gtp.log_detail(saveto, f"Copying and modifying file: {file['filepath']}")
                procpath = gtp.copy_modify(
                    file, jsondata["date"], gtp.checkout_dir(os.path.join(saveto, "Processed"))
                )
                file["procpath"] = procpath
                file["jsonpath"] = jsonpath
                file["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                gtp.log_detail(saveto, f"Successfully processed file: {file['filename']}\n")
                processed.append(file)
            else:
                gtp.log_detail(saveto, f"Unprocessed JSON file, no pair found for: {file['jsonpath']}\n")
                unprocessed_jsons.append({
                    "filename": os.path.basename(file["jsonpath"]),
                    "filepath": file["jsonpath"],
                    "title": file["title"],
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                })

    _progress("processing", total_jsons, total_jsons, "JSON processing complete")

    # Handle unprocessed files
    _progress("copying_unprocessed", 0, 0, "Identifying unprocessed files...")
    gtp.log_detail(saveto, "Processing unprocessed files...\n")

    processed_paths = {file["filepath"] for file in processed}
    unprocessed = [
        {"filename": os.path.basename(f["filepath"]), "filepath": f["filepath"]}
        for f in files
        if f["filepath"] not in processed_paths
    ]

    total_unproc = len(unprocessed) + len(unprocessed_jsons)
    _progress("copying_unprocessed", 0, total_unproc, f"Copying {total_unproc} unprocessed files...")

    if unprocessed_jsons:
        unprocessed_jsons = gtp.copy_unprocessed(unprocessed_jsons, saveto)
    if unprocessed:
        unprocessed = gtp.copy_unprocessed(unprocessed, saveto)

    _progress("copying_unprocessed", total_unproc, total_unproc, "Unprocessed files copied")

    # Save logs
    elapsed = round(time.time() - start_time, 3)
    start_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start_time))
    end_date = time.strftime("%Y-%m-%d %H:%M:%S")

    gtp.log_detail(saveto, f"Finished processing directory: {path}")
    gtp.savelogs(saveto, processed, unprocessed, unprocessed_jsons, elapsed, start_date, end_date)

    _progress("done", 1, 1, f"Done! {len(processed)} processed, {len(unprocessed)} unprocessed")

    return ProcessingResult(
        processed=processed,
        unprocessed=unprocessed,
        unprocessed_jsons=unprocessed_jsons,
        output_dir=saveto,
        elapsed_seconds=elapsed,
    )


@dataclass
class PipelineResult:
    processing: ProcessingResult
    duplicates: list | None = None
    similar: list | None = None
    quality_issues: list | None = None
    activity_log: str = ""


def extract_zips(
    path: str,
    extract_to: str,
    on_progress: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> str:
    """
    Find and extract all .zip files in `path` into `extract_to`.
    Returns the path to use for processing:
      - `extract_to` if zips were found and extracted
      - `path` unchanged if no zips were found (already extracted)
    """

    def _progress(current, total, message=""):
        if on_progress:
            on_progress(ProgressInfo("extracting_zips", current, total, message))

    def _cancelled():
        return cancel_flag() if cancel_flag else False

    # Find all zip files
    zip_files = []
    for root, _, filenames in os.walk(path):
        for name in filenames:
            if name.lower().endswith(".zip"):
                zip_files.append(os.path.join(root, name))

    if not zip_files:
        _progress(0, 0, "No ZIP files found — using folder as-is")
        return path

    os.makedirs(extract_to, exist_ok=True)

    # Count total files across all zips for granular progress
    total_files = 0
    zip_members: list[tuple[str, list[str]]] = []
    for zf_path in zip_files:
        try:
            with zipfile.ZipFile(zf_path, "r") as zf:
                members = zf.namelist()
                zip_members.append((zf_path, members))
                total_files += len(members)
        except (zipfile.BadZipFile, OSError):
            zip_members.append((zf_path, []))

    extracted_count = 0
    for zf_path, members in zip_members:
        if _cancelled():
            _progress(extracted_count, total_files, "Extraction cancelled")
            break

        zip_name = os.path.basename(zf_path)
        if not members:
            _progress(extracted_count, total_files, f"Skipping corrupt zip: {zip_name}")
            continue

        try:
            with zipfile.ZipFile(zf_path, "r") as zf:
                for member in members:
                    if _cancelled():
                        break
                    zf.extract(member, extract_to)
                    extracted_count += 1
                    if extracted_count % 50 == 0 or extracted_count == total_files:
                        _progress(extracted_count, total_files, f"Extracting {zip_name}: {member}")
        except (zipfile.BadZipFile, OSError) as e:
            _progress(extracted_count, total_files, f"Error in {zip_name}: {e}")
            continue

    _progress(total_files, total_files, f"Extracted {total_files} files from {len(zip_files)} ZIPs")
    return extract_to


def run_full_pipeline(
    path: str,
    suffixes: list[str] | None = None,
    destination: str | None = None,
    scan_duplicates: bool = True,
    scan_similar: bool = True,
    scan_quality: bool = True,
    similar_threshold: int = 8,
    similar_hash_func: str = "phash",
    on_progress: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> PipelineResult:
    """
    Full end-to-end pipeline:
      1. Extract ZIP files (if any)
      2. Process Takeout metadata
      3. Scan for exact duplicates
      4. Scan for similar photos
      5. Scan for quality issues (blurry, dark, screenshots, etc.)
    """
    pipeline_start = time.time()
    log_lines: list[str] = []
    log_lines.append(f"Pipeline started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append(f"Input: {path}")

    def _cancelled():
        return cancel_flag() if cancel_flag else False

    # Step 1: Extract ZIPs
    if destination:
        extract_dir = os.path.join(destination, "_extracted")
    else:
        extract_dir = os.path.join(os.path.dirname(path), "_extracted")

    actual_path = extract_zips(
        path, extract_dir,
        on_progress=on_progress,
        cancel_flag=cancel_flag,
    )

    if actual_path != path:
        log_lines.append(f"Extracted ZIP files to: {actual_path}")
    else:
        log_lines.append("No ZIP files found, using folder as-is")

    if _cancelled():
        log_lines.append("Cancelled during extraction")
        return PipelineResult(
            processing=ProcessingResult(output_dir=""),
            activity_log="\n".join(log_lines),
        )

    # Step 2: Process Takeout
    result = process_takeout(
        path=actual_path,
        suffixes=suffixes,
        destination=destination,
        on_progress=on_progress,
        cancel_flag=cancel_flag,
    )

    log_lines.append(f"Output: {result.output_dir}")
    log_lines.append(f"Processed: {len(result.processed)} files")
    log_lines.append(f"Unprocessed: {len(result.unprocessed)} files, {len(result.unprocessed_jsons)} jsons")
    log_lines.append(f"Processing time: {result.elapsed_seconds}s")

    if _cancelled():
        log_lines.append("Cancelled during processing")
        return PipelineResult(processing=result, activity_log="\n".join(log_lines))

    # Scan the Processed subfolder
    scan_dir = os.path.join(result.output_dir, "Processed")
    if not os.path.isdir(scan_dir):
        scan_dir = result.output_dir

    # Step 3: Duplicate detection
    dup_groups = None
    if scan_duplicates and not _cancelled():
        def _dup_progress(current, total, msg):
            if on_progress:
                on_progress(ProgressInfo("scanning_duplicates", current, total, msg))

        dup_groups = duplicate_detector.find_exact_duplicates(
            scan_dir,
            on_progress=_dup_progress,
            cancel_flag=cancel_flag,
        )
        if dup_groups:
            total_dup_files = sum(len(g.paths) for g in dup_groups)
            reclaimable = sum(g.file_size * (len(g.paths) - 1) for g in dup_groups)
            log_lines.append(f"Duplicates: {len(dup_groups)} groups, {total_dup_files} files, {reclaimable} bytes reclaimable")
        else:
            log_lines.append("Duplicates: none found")

    # Step 4: Similar photo detection
    sim_groups = None
    if scan_similar and not _cancelled():
        def _sim_progress(current, total, msg):
            if on_progress:
                on_progress(ProgressInfo("scanning_similar", current, total, msg))

        sim_groups = similarity_detector.find_similar_photos(
            scan_dir,
            threshold=similar_threshold,
            hash_func=similar_hash_func,
            on_progress=_sim_progress,
            cancel_flag=cancel_flag,
        )
        if sim_groups:
            total_sim = sum(len(g.members) for g in sim_groups)
            log_lines.append(f"Similar photos: {len(sim_groups)} groups, {total_sim} images")
        else:
            log_lines.append("Similar photos: none found")

    # Step 5: Quality scan
    quality_issues = None
    if scan_quality and not _cancelled():
        def _qual_progress(current, total, msg):
            if on_progress:
                on_progress(ProgressInfo("scanning_quality", current, total, msg))

        quality_issues = quality_detector.find_quality_issues(
            scan_dir,
            on_progress=_qual_progress,
            cancel_flag=cancel_flag,
        )
        if quality_issues:
            by_type: dict[str, int] = {}
            for issue in quality_issues:
                by_type[issue.issue.value] = by_type.get(issue.issue.value, 0) + 1
            breakdown = ", ".join(f"{v} {k}" for k, v in by_type.items())
            log_lines.append(f"Quality issues: {len(quality_issues)} ({breakdown})")
        else:
            log_lines.append("Quality issues: none found")

    pipeline_elapsed = round(time.time() - pipeline_start, 1)
    log_lines.append(f"Total pipeline time: {pipeline_elapsed}s")
    log_lines.append(f"Pipeline finished: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    activity_log = "\n".join(log_lines)

    # Save activity log to output directory
    if result.output_dir:
        try:
            log_path = os.path.join(result.output_dir, "pipeline_log.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(activity_log)
        except OSError:
            pass

    if on_progress:
        on_progress(ProgressInfo("pipeline_done", 1, 1, "Pipeline complete!"))

    return PipelineResult(
        processing=result,
        duplicates=dup_groups,
        similar=sim_groups,
        quality_issues=quality_issues,
        activity_log=activity_log,
    )
