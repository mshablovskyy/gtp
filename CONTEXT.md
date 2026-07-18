# Google Takeout Processor

Domain language for restoring original capture times and organizing Google Photos Takeout dumps without modifying the source tree.

## Language

**Takeout**:
An unpacked Google Photos export (Google Takeout) used as input. May be one folder or the merge of several archive extracts.
_Avoid_: backup, dump (in user-facing text prefer Takeout), archive (unless meaning the zip before unpack)

**Source tree**:
The input Takeout directory the tool reads. Never modified, deleted, or rewritten by the tool.

**Media**:
A photo or video file in the Takeout (not a JSON sidecar).

**Sidecar**:
A JSON metadata file exported next to Media, holding at least title and capture time (`photoTakenTime`).
_Avoid_: metadata file (when you mean the Takeout JSON specifically), companion (ambiguous)

**Capture time**:
The original taken time from the Sidecar (`photoTakenTime`), applied to the Media’s filesystem created/modified timestamps in the output copy.
_Avoid_: EXIF time (related but not the same source today), “date fix” as a noun

**Album**:
The parent folder name of Media/Sidecar in the Takeout layout. Default output preserves this layout.
_Avoid_: year folder (a possible layout, not the default product term), category

**Suffix**:
A filename variant Google (or the user) attaches to Media without a separate Sidecar for each variant (e.g. `-edited`, user-supplied stickers). One Sidecar title may match several Media names.
_Avoid_: extension (file type), tag

**Match**:
Successful pairing of a Sidecar to one or more Media files so Capture time can be applied and the file placed under Processed.

**Processed**:
Output area for successfully Matched Media (copied, dates set, under Album layout by default).

**Unprocessed**:
Output area for Media (and orphan Sidecars) that could not be Matched, for manual review.
_Avoid_: failed, error folder (outcome is “not matched,” not always an error)

**Run**:
One execution of the processor over a Source tree into an output tree (Processed + Unprocessed + logs).

**Discover / Parse / Match / Plan / Apply**:
The five stages of a Run, in order. Discover finds Sidecars and Media; Parse reads Sidecar fields; Match pairs them; Plan is the pure intended actions; Apply performs copies, Capture-time updates, and logs. Only Apply has side effects on the output tree.
