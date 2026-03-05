from __future__ import annotations

from pathlib import Path

from main_app.contracts import CartoonCharacterSpec


class CartoonCharacterAssetValidator:
    REQUIRED_EMOTIONS: tuple[str, ...] = ("neutral", "energetic", "tense", "warm", "inspiring")
    REQUIRED_VISEMES: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "X")
    REQUIRED_STATES: tuple[str, ...] = ("idle", "blink", "talk")
    RECOMMENDED_MIN_FRAMES_PER_VARIANT: int = 8

    def __init__(self, *, pack_root: Path, expected_cache_resolution: str | None = None) -> None:
        self._pack_root = pack_root
        self._expected_cache_resolution = _parse_resolution(expected_cache_resolution)
        self._expected_cache_resolution_label = _clean(expected_cache_resolution)

    def validate_roster(
        self,
        *,
        roster: list[CartoonCharacterSpec],
        require_lottie_cache: bool,
        timeline_schema_version: str,
    ) -> list[str]:
        if not require_lottie_cache or _clean(timeline_schema_version).lower() != "v2":
            return []
        errors: list[str] = []
        if not roster:
            return ["Character roster missing; cannot validate v2 lottie cache assets."]
        for character in roster:
            errors.extend(self._validate_character(character))
        return errors

    def audit_roster_motion_quality(
        self,
        *,
        roster: list[CartoonCharacterSpec],
        timeline_schema_version: str,
        recommended_min_frames_per_variant: int | None = None,
    ) -> list[str]:
        if _clean(timeline_schema_version).lower() != "v2":
            return []
        warnings: list[str] = []
        if not roster:
            return ["Character roster missing; motion quality audit skipped."]
        threshold = max(1, int(recommended_min_frames_per_variant or self.RECOMMENDED_MIN_FRAMES_PER_VARIANT))
        for character in roster:
            warnings.extend(self._audit_character_motion_quality(character=character, threshold=threshold))
        return warnings

    def motion_quality_summary(
        self,
        *,
        roster: list[CartoonCharacterSpec],
        timeline_schema_version: str,
        recommended_min_frames_per_variant: int | None = None,
    ) -> dict[str, dict[str, int]]:
        if _clean(timeline_schema_version).lower() != "v2":
            return {}
        if not roster:
            return {}
        threshold = max(1, int(recommended_min_frames_per_variant or self.RECOMMENDED_MIN_FRAMES_PER_VARIANT))
        summary: dict[str, dict[str, int]] = {}
        for character in roster:
            _, character_summary = self._collect_motion_quality(character=character, threshold=threshold)
            for char_id, counts in character_summary.items():
                summary[char_id] = counts
        return summary

    def _validate_character(self, character: CartoonCharacterSpec) -> list[str]:
        errors: list[str] = []
        char_id = _clean(character.get("id")) or "unknown"
        asset_mode = _clean(character.get("asset_mode")).lower()
        if asset_mode != "lottie_cache":
            errors.append(f"Character `{char_id}` asset_mode must be `lottie_cache` for timeline v2.")
            return errors
        lottie_source = _clean(character.get("lottie_source"))
        if not lottie_source:
            errors.append(f"Character `{char_id}` missing `lottie_source`.")
        else:
            lottie_path = self._resolve_path(lottie_source)
            if not lottie_path.exists():
                errors.append(f"Character `{char_id}` lottie_source missing: {lottie_path}")

        cache_root = _clean(character.get("cache_root"))
        if not cache_root:
            errors.append(f"Character `{char_id}` missing `cache_root`.")
            return errors
        cache_path = self._resolve_path(cache_root)
        if not cache_path.exists():
            errors.append(f"Character `{char_id}` cache path missing: {cache_path}")
            return errors

        for state in self.REQUIRED_STATES:
            if state == "talk":
                for emotion in self.REQUIRED_EMOTIONS:
                    for viseme in self.REQUIRED_VISEMES:
                        variant = f"{emotion}_{viseme}"
                        variant_errors, first_frame = self._ensure_variant_has_frames(
                            char_id=char_id,
                            cache_path=cache_path,
                            state=state,
                            variant=variant,
                        )
                        errors.extend(variant_errors)
                        if variant_errors or first_frame is None:
                            continue
                        resolution_error = self._validate_frame_resolution(
                            char_id=char_id,
                            frame_path=first_frame,
                            state=state,
                            variant=variant,
                        )
                        if resolution_error:
                            errors.append(resolution_error)
                continue
            for emotion in self.REQUIRED_EMOTIONS:
                variant_errors, first_frame = self._ensure_variant_has_frames(
                    char_id=char_id,
                    cache_path=cache_path,
                    state=state,
                    variant=emotion,
                )
                errors.extend(variant_errors)
                if variant_errors or first_frame is None:
                    continue
                resolution_error = self._validate_frame_resolution(
                    char_id=char_id,
                    frame_path=first_frame,
                    state=state,
                    variant=emotion,
                )
                if resolution_error:
                    errors.append(resolution_error)
        return errors

    def _audit_character_motion_quality(self, *, character: CartoonCharacterSpec, threshold: int) -> list[str]:
        detail_warnings, summary = self._collect_motion_quality(character=character, threshold=threshold)
        summary_warnings = [
            (
                f"Motion quality summary `{char_id}`: "
                f"idle={counts.get('idle', 0)}, "
                f"blink={counts.get('blink', 0)}, "
                f"talk={counts.get('talk', 0)}, "
                f"total={counts.get('total', 0)} low variants."
            )
            for char_id, counts in sorted(summary.items())
        ]
        return detail_warnings + summary_warnings

    def _collect_motion_quality(
        self,
        *,
        character: CartoonCharacterSpec,
        threshold: int,
    ) -> tuple[list[str], dict[str, dict[str, int]]]:
        warnings: list[str] = []
        summary: dict[str, dict[str, int]] = {}
        char_id = _clean(character.get("id")) or "unknown"
        cache_root = _clean(character.get("cache_root"))
        if not cache_root:
            return [f"Character `{char_id}` motion audit skipped: missing `cache_root`."], summary
        cache_path = self._resolve_path(cache_root)
        if not cache_path.exists():
            return [f"Character `{char_id}` motion audit skipped: cache path missing `{cache_path}`."], summary

        state_counts = {"idle": 0, "blink": 0, "talk": 0, "total": 0}
        for state in self.REQUIRED_STATES:
            if state == "talk":
                for emotion in self.REQUIRED_EMOTIONS:
                    for viseme in self.REQUIRED_VISEMES:
                        variant_warnings, is_low = self._audit_variant_frames(
                            char_id=char_id,
                            cache_path=cache_path,
                            state=state,
                            variant=f"{emotion}_{viseme}",
                            threshold=threshold,
                        )
                        warnings.extend(variant_warnings)
                        if is_low:
                            state_counts["talk"] += 1
                            state_counts["total"] += 1
                continue
            for emotion in self.REQUIRED_EMOTIONS:
                variant_warnings, is_low = self._audit_variant_frames(
                    char_id=char_id,
                    cache_path=cache_path,
                    state=state,
                    variant=emotion,
                    threshold=threshold,
                )
                warnings.extend(variant_warnings)
                if is_low:
                    state_counts[state] += 1
                    state_counts["total"] += 1
        if state_counts["total"] > 0:
            summary[char_id] = state_counts
        return warnings, summary

    def _audit_variant_frames(
        self,
        *,
        char_id: str,
        cache_path: Path,
        state: str,
        variant: str,
        threshold: int,
    ) -> tuple[list[str], bool]:
        state_path = cache_path / state / variant
        frame_paths = self._variant_frames(state_path)
        if not frame_paths:
            return [], False
        if len(frame_paths) < threshold:
            return [
                (
                    f"Character `{char_id}` low-motion variant `{state}/{variant}` has {len(frame_paths)} frame(s). "
                    f"Recommended >= {threshold}."
                )
            ], True
        return [], False

    def _ensure_variant_has_frames(
        self,
        *,
        char_id: str,
        cache_path: Path,
        state: str,
        variant: str,
    ) -> tuple[list[str], Path | None]:
        state_path = cache_path / state / variant
        if not state_path.exists():
            return [f"Character `{char_id}` missing cache directory: {state_path}"], None
        frame_paths = self._variant_frames(state_path)
        if not frame_paths:
            return [f"Character `{char_id}` has no frames in: {state_path}"], None
        return [], frame_paths[0]

    def _validate_frame_resolution(
        self,
        *,
        char_id: str,
        frame_path: Path,
        state: str,
        variant: str,
    ) -> str | None:
        expected = self._expected_cache_resolution
        if expected is None:
            return None
        actual = _png_dimensions(frame_path)
        if actual is None:
            return f"Character `{char_id}` unreadable cache frame for resolution check: {frame_path}"
        if actual != expected:
            return (
                f"Character `{char_id}` cache resolution mismatch for `{state}/{variant}`: "
                f"expected {expected[0]}x{expected[1]} "
                f"(manifest `{self._expected_cache_resolution_label or 'unknown'}`), "
                f"found {actual[0]}x{actual[1]} at {frame_path}"
            )
        return None

    @staticmethod
    def _variant_frames(state_path: Path) -> list[Path]:
        return sorted(state_path.glob("f*.png"))

    def _resolve_path(self, path_hint: str) -> Path:
        raw = Path(path_hint)
        if raw.is_absolute():
            return raw
        return (self._pack_root / raw).resolve()


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _parse_resolution(value: object) -> tuple[int, int] | None:
    raw = _clean(value).lower().replace(" ", "")
    if "x" not in raw:
        return None
    width_raw, height_raw = raw.split("x", 1)
    try:
        width = int(width_raw)
        height = int(height_raw)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    if len(payload) < 24:
        return None
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width = int.from_bytes(payload[16:20], "big", signed=False)
    height = int.from_bytes(payload[20:24], "big", signed=False)
    if width <= 0 or height <= 0:
        return None
    return width, height

