# Video Asset Creation End-to-End Summary

## Scope
This document summarizes how a `video` asset is created in this project, from user input to final outputs (payload, audio, and MP4), including both:

- Video Builder tab flow (direct UI path)
- Agent Dashboard workflow flow (DAG + stage orchestration path)

## Primary Entry Points
- UI runtime: `app.py`, `main_app/app/runtime.py`
- Video tab UI: `main_app/ui/tabs/video_tab.py`
- Core video generation service: `main_app/services/video_asset_service.py`
- Audio synthesis service: `main_app/services/audio_overview_service.py`
- MP4 rendering service: `main_app/services/video_export_service.py`
- Agent executor plugin: `main_app/services/agent_dashboard/executor_plugins/video.py`
- Agent stage orchestration: `main_app/services/agent_dashboard/tool_stage_service.py`

## Dependency Wiring
`main_app/app/dependency_container.py` composes the video stack:

1. `SlideShowService` for slide generation
2. `AudioOverviewParser` for script parsing/repair
3. `AudioOverviewService` for MP3 synthesis
4. `VideoAssetService` that orchestrates slideshow + script generation + audio prep
5. `VideoExportService` for final MP4 rendering

## A) Video Builder Tab Flow (Direct UI Path)
Defined in `main_app/ui/tabs/video_tab.py`.

### 1. Input collection
The tab collects:

- Topic, constraints
- Subtopic/slide counts
- Code mode and representation mode
- Speaker count and conversation style
- Audio language + slow mode
- Video template + animation style
- YouTube-style narration prompt toggle

### 2. Background job submission
When user clicks `Generate Video Asset`:

- A background job is submitted via `BackgroundJobManager`.
- Worker stages:
  1. `video_service.generate(...)`
  2. `video_service.synthesize_audio(...)` if payload generation succeeds
  3. `video_exporter.build_video_mp4(...)` if audio exists

This keeps the UI responsive and supports progress updates/cancel flow.

### 3. Video payload generation (`VideoAssetService.generate`)
`main_app/services/video_asset_service.py`

#### 3.1 Slideshow stage
Calls `SlideShowService.generate(...)` first:

- Builds slideshow outline via LLM
- Builds section slides via LLM
- Normalizes slide representations/layout payload
- Adds intro + summary slides
- Returns `slides` or parse error

If slideshow fails, video generation exits early with:
- `parse_error = "Slideshow stage failed: ..."`

#### 3.2 Per-slide narration script stage
For each slide:

- Calls LLM task `video_slide_script` with strict JSON schema
- Parses with `AudioOverviewParser.parse(...)`
  - direct JSON parse
  - local JSON repair fallback
  - optional LLM JSON repair fallback
- Normalizes dialogue:
  - speaker canonicalization to roster
  - removes prefixes like `Ava:`
  - sanitizes/truncates overly long turns
  - estimates duration per slide

If any slide script fails parse/normalization, generation exits with a slide-specific error.

#### 3.3 Payload assembly
On success, returns `VideoGenerationResult.video_payload` with:

- `topic`, `title`
- `slides`
- `speaker_roster`
- `slide_scripts`
- `conversation_style`
- `video_template`, `animation_style`, `representation_mode`
- metadata (`total_slides`, `speaker_count`, `code_mode`, etc.)

History is recorded through `AssetHistoryService` when enabled.

### 4. Audio synthesis (`VideoAssetService.synthesize_audio`)
`main_app/services/video_asset_service.py`

- Flattens all slide dialogue turns into one ordered dialogue stream.
- Delegates to `AudioOverviewService.synthesize_mp3(...)`.

`main_app/services/audio_overview_service.py` synthesis strategy:

1. Try multi-voice `edge_tts` by speaker-to-voice mapping (language-aware voice pools).
2. If unavailable/fails, fallback to `gTTS` single-voice MP3.

Returns:
- `audio_bytes` (if successful)
- optional warning/error string

### 5. MP4 rendering (`VideoExportService.build_video_mp4`)
`main_app/services/video_export_service.py`

Preconditions:

- `audio_bytes` must exist
- `video_payload.slides` must be non-empty
- `moviepy` and `Pillow` must be installed

Render flow:

1. Resolve template (`standard` / `youtube`) and animation style (`none` / `smooth` / `youtube_dynamic`).
2. Create temp render workspace.
3. Write narration MP3 and load audio duration.
4. Compute per-slide durations (using script hints, scaled to total audio duration).
5. Render slide images (gradient theme, title/body/code blocks, representation-aware layouts).
6. Build visual clips:
   - Progressive reveal only for supported representations when `youtube_dynamic`.
   - Motion effects (Ken Burns style zoom/crop) for non-`none` animation.
7. Concatenate clips, apply crossfade transitions, attach audio.
8. Export `libx264` + `aac` MP4 and return bytes.
9. Close clips and cleanup temp workspace.

## B) Agent Dashboard Workflow Flow (DAG Path)

## 1. Tool and workflow registration
`main_app/services/agent_dashboard/tool_registry.py` and `workflow_registry.py`:

- `video` tool default dependency:
  - requires: `artifact.slideshow.slides`
  - produces: `artifact.video.payload`, `artifact.video.audio`

Default media workflow includes explicit dependency `slideshow -> video`.

## 2. Executor behavior
`main_app/services/agent_dashboard/executor_plugins/video.py`:

1. Calls `video_service.generate(...)`
2. Calls `video_service.synthesize_audio(...)`
3. Returns media asset result with payload + audio bytes/error

## 3. Stage orchestration and gating
`main_app/services/agent_dashboard/tool_stage_service.py`

Stage sequence:

1. `validate_tool_registration`
2. `validate_stage_requirements`
3. `resolve_dependencies`
4. `execute_tool`
5. `normalize_artifact`
6. `validate_schema`
7. `verify_result`
8. `policy_gate_result`
9. `finalize_result`

Dependency enforcement:

- `resolve_dependencies` fails with `Missing required dependency artifacts: ...` when required artifacts are absent.

For video, this means slideshow artifacts must exist and be publishable.

## 4. Verification checks for video
`main_app/services/agent_dashboard/verification_service.py` verifies:

- `artifact.video.payload` exists
- payload has non-empty `slides`
- payload has non-empty `slide_scripts`
- audio artifact exists (attachment or `audio_bytes`/`audio_error`)

If verification fails for upstream slideshow, video dependency can be blocked in the same run.

## Outputs and Artifacts

## Direct tab/session outputs
- `video_payload` dict in session state
- `video_audio_bytes` / `video_audio_error`
- `video_full_video_bytes` / `video_full_video_error`

User can download:
- script markdown
- payload JSON
- MP3
- MP4

## Agent artifact outputs
- `artifact.video.payload`
- `artifact.video.audio`

Schema contract:
- `main_app/schemas/assets/video.v1.json` requires `artifact.video.payload` as object.

## Known Failure Modes

- Missing API key/model in UI settings
- Slideshow parse failure (video generation stops)
- Slide narration parse failure on any slide
- No dialogue extracted for audio synthesis
- Missing TTS dependencies (`edge_tts`/`gTTS`)
- Missing rendering dependencies (`moviepy`/`Pillow`)
- Missing required dependency artifacts in agent DAG flow
- Verification/policy/schema failures preventing artifact publication

## Test Coverage Pointers
- Video generation + normalization + youtube prompt behavior:
  - `tests/test_video_asset_service.py`
- MP4 export guardrails and duration/template logic:
  - `tests/test_video_export_service.py`
- Dependency chain blocking when slideshow verification fails:
  - `tests/test_integration_full_flows.py` (`test_verify_failure_blocks_dependency_chain`)
