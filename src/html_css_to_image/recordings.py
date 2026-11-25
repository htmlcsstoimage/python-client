"""
Typed recording sources, timeline actions, triggers, and responses.

See https://docs.htmlcsstoimage.com/getting-started/recordings/.
Optional request settings use the API defaults; options are not validated locally.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

from .models import (
    ApiErrorResponse,
    ColorSchemeType,
    DeleteImageResponse,
    DeleteImageSuccessResponse,
    MediaType,
    RequestOverride,
)

RecordingFormat: TypeAlias = Literal["mp4", "webm", "gif"]

RecordingAudioEndBehavior: TypeAlias = Literal["silence", "loop", "trim_video"]

RecordingDurationMode: TypeAlias = Literal["fixed", "target", "at_least", "at_most"]

RecordingMouseButton: TypeAlias = Literal["left", "right", "middle", "back", "forward"]

RecordingStatus: TypeAlias = Literal[
    "processing",
    "pending_retry",
    "ready",
    "failed",
    "cancelled",
    "awaiting_render",
    "unknown",
]
"""Recording status. ``unknown`` is an unrecognized status from a newer API version."""

ScrollEasing: TypeAlias = Literal[
    "linear",
    "ease_in_cubic",
    "ease_out_cubic",
    "ease_in_out_cubic",
    "ease_in_quad",
    "ease_out_quad",
    "ease_in_out_quad",
    "ease_in_quart",
    "ease_out_quart",
    "ease_in_out_quart",
    "ease_in_quint",
    "ease_out_quint",
    "ease_in_out_quint",
    "ease_in_sine",
    "ease_out_sine",
    "ease_in_out_sine",
    "ease_in_expo",
    "ease_out_expo",
    "ease_in_out_expo",
    "ease_in_circ",
    "ease_out_circ",
    "ease_in_out_circ",
    "ease_in_back",
    "ease_out_back",
    "ease_in_out_back",
    "ease_in_elastic",
    "ease_out_elastic",
    "ease_in_out_elastic",
    "ease_in_bounce",
    "ease_out_bounce",
    "ease_in_out_bounce",
]

ScrollPosition: TypeAlias = Literal["top", "bottom", "left", "right"]


@dataclass(slots=True, kw_only=True)
class RecordingScrollAction:
    """Scroll through an ordered sequence of timed movements in the document or a
    selected container.

    Attributes:
        container_selector: Scrollable container's CSS selector. Omit or use None to
            scroll the document.
        steps: Ordered movements. Supply at least one step.
        if_not_found: Fallback when the container is missing. Omitted, None, or empty
            skips this action.
    """

    type: Literal["scroll"] = field(default="scroll", init=False)
    container_selector: str | None = None
    steps: list[ScrollStep]
    if_not_found: list[RecordingAction] | None = None


@dataclass(slots=True, kw_only=True)
class RecordingStallAction:
    """Wait while recording and page activity continue.

    Attributes:
        duration_ms: Wait in milliseconds. The recording deadline can end it early.
    """

    type: Literal["stall"] = field(default="stall", init=False)
    duration_ms: int | None = None


@dataclass(slots=True, kw_only=True)
class RecordingLocateSelectorAction:
    """Look for a matching element and execute the corresponding branch. Branch actions
    supply their own selectors.

    Attributes:
        selector: CSS selector to find.
        timeout_ms: Maximum wait in milliseconds. Defaults to 0 for a single check.
        if_found: Actions when found. Omitted, None, or empty continues with the parent
            sequence.
        if_not_found: Actions when missing. Include an error action to fail the
            recording.
    """

    type: Literal["locate_selector"] = field(default="locate_selector", init=False)
    selector: str
    timeout_ms: int | None = None
    if_found: list[RecordingAction] | None = None
    if_not_found: list[RecordingAction] | None = None


@dataclass(slots=True, kw_only=True)
class RecordingClickAction:
    """Find and click an element, scrolling it into view when needed.

    Attributes:
        selector: CSS selector of the element to click.
        timeout_ms: Maximum wait in milliseconds. Defaults to 0 for a single check.
        if_not_found: Fallback when missing. Omitted, None, or empty continues; use an
            error action to fail.
        button: Mouse button. Defaults to left.
        count: Event click count, from 1 to 3. Defaults to 1; this does not repeat the
            action.
        delay_ms: Delay between mouse down and up, in milliseconds. Defaults to 0;
            maximum 5000.
        offset_x: CSS pixels from the element's top-left. Supplying either offset makes
            the other default to 0.
        offset_y: CSS pixels from the element's top-left. Omit both offsets to use the
            default clickable point.
    """

    type: Literal["click"] = field(default="click", init=False)
    selector: str
    timeout_ms: int | None = None
    if_not_found: list[RecordingAction] | None = None
    button: RecordingMouseButton | None = None
    count: int | None = None
    delay_ms: int | None = None
    offset_x: float | None = None
    offset_y: float | None = None


@dataclass(slots=True, kw_only=True)
class RecordingErrorAction:
    """Fail the recording and stop executing actions. Must be the last action in its
    array.
    """

    type: Literal["error"] = field(default="error", init=False)


@dataclass(slots=True, kw_only=True)
class RecordingSimpleScrollAction:
    """Scroll down repeatedly until reaching the bottom or the recording deadline. Each
    movement has its own duration and easing, followed by a pause.

    Attributes:
        scroll_duration_ms: Duration of each movement in milliseconds. Defaults to 800.
        ms_between_scrolls: Pause between movements in milliseconds. Defaults to 400; 0
            scrolls continuously.
        scroll_distance: CSS pixels as a number, or a string such as '900px' or '50vh'.
            Omit or use None to use API defaults.
        easing: Movement easing. Omit or use None to use API defaults.
        stall_at_end_ms: Time to hold at the bottom in milliseconds, limited by
            remaining recording time. Defaults to 0.
    """

    type: Literal["simple_scroll"] = field(default="simple_scroll", init=False)
    scroll_duration_ms: int | None = None
    ms_between_scrolls: int | None = None
    scroll_distance: int | float | str | None = None
    easing: ScrollEasing | None = None
    stall_at_end_ms: int | None = None


@dataclass(slots=True, kw_only=True)
class RecordingExecuteJavaScriptAction:
    """Execute JavaScript in the page while recording continues, awaiting any returned
    promise.

    Attributes:
        script: Function body supporting await. Its return value is ignored.
        timeout_ms: Maximum execution time in milliseconds. Zero or omitted uses the
            page timeout; maximum 90000.
        if_error: Omitted or None fails on script errors; [] ignores errors. A timeout
            does not undo side effects.
    """

    type: Literal["execute_javascript"] = field(
        default="execute_javascript", init=False
    )
    script: str
    timeout_ms: int | None = None
    if_error: list[RecordingAction] | None = None


@dataclass(slots=True, kw_only=True)
class RecordingImmediateTrigger:
    """Start recording immediately after page preparation. This is the default trigger.
    """

    type: Literal["immediate"] = field(default="immediate", init=False)


@dataclass(slots=True, kw_only=True)
class RecordingElementVisibleTrigger:
    """Wait for a matching element to become visible before starting recording. Fails
    if the timeout expires.

    Attributes:
        selector: CSS selector for the element to wait for.
        timeout_ms: Maximum wait in milliseconds. Defaults to 1000; minimum 100. Plan
            limits apply.
    """

    type: Literal["element_visible"] = field(default="element_visible", init=False)
    selector: str
    timeout_ms: int | None = None


@dataclass(slots=True, kw_only=True)
class RecordingFunctionCallTrigger:
    """Wait for the page to call window.RecordingReady() before starting recording.
    Fails if the timeout expires.

    Attributes:
        timeout_ms: Maximum wait in milliseconds. Defaults to 1000; minimum 100. Plan
            limits apply.
    """

    type: Literal["function_call"] = field(default="function_call", init=False)
    timeout_ms: int | None = None


@dataclass(slots=True, kw_only=True)
class PositionScrollTarget:
    """Scroll to an edge of the document or selected container.

    Attributes:
        position: Edge to scroll to. Defaults to top.
    """

    type: Literal["position"] = field(default="position", init=False)
    position: ScrollPosition | None = None


@dataclass(slots=True, kw_only=True)
class CoordinatesScrollTarget:
    """Scroll to absolute coordinates within the document or selected container.

    Attributes:
        x: Horizontal position. Defaults to 0.
        y: Vertical position. Defaults to 0.
    """

    type: Literal["coordinates"] = field(default="coordinates", init=False)
    x: float | None = None
    y: float | None = None


@dataclass(slots=True, kw_only=True)
class SelectorScrollTarget:
    """Scroll to an element matching a CSS selector, with optional offsets.

    Attributes:
        selector: CSS selector for the destination element.
        offset_x: Horizontal offset from the element. Defaults to 0.
        offset_y: Vertical offset from the element. Defaults to 0.
        if_not_found: Fallback when missing. Omitted, None, or empty skips this movement
            and continues to the next step.
    """

    type: Literal["selector"] = field(default="selector", init=False)
    selector: str
    offset_x: float | None = None
    offset_y: float | None = None
    if_not_found: list[RecordingAction] | None = None


@dataclass(slots=True, kw_only=True)
class _RecordingAudioOptions:
    """Playback options shared by both audio sources.

    Attributes:
        source_start_ms: Offset into the source file in milliseconds. Defaults to 0.
        delay_ms: Delay from the start of the finished video in milliseconds.
            Defaults to 0.
        when_audio_ends: Keep playing silently (default), loop from the source offset,
            or trim the video when the track ends.
        error_on_source_invalid: Defaults to True. Set False to return the full
            silent video if the track cannot play at render time.
    """

    source_start_ms: int | None = None
    delay_ms: int | None = None
    when_audio_ends: RecordingAudioEndBehavior | None = None
    error_on_source_invalid: bool | None = None


@dataclass(slots=True, kw_only=True)
class RecordingAssetAudio(_RecordingAudioOptions):
    """Use the asset_id of a completed audio upload from the recording organization.

    Private Asset Library uploads are supported.
    """

    asset_id: str


@dataclass(slots=True, kw_only=True)
class RecordingUrlAudio(_RecordingAudioOptions):
    """Use a public HTTP or HTTPS URL serving the audio file at render time."""

    url: str


RecordingAudio: TypeAlias = RecordingAssetAudio | RecordingUrlAudio


@dataclass(slots=True, kw_only=True)
class RecordingOutputOptions:
    """Output format, frame rate, and scaling for a recording.

    Attributes:
        format: Media format. Defaults to mp4.
        fps: Frames per second. Defaults to 15 for GIF and 30 for video. GIF supports
            10–50; video supports 10–120.
        scale: Scales captured pixels without changing page layout. Defaults to 1; 0.5
            halves both dimensions.
    """

    format: RecordingFormat | None = None
    fps: int | None = None
    scale: float | None = None


@dataclass(slots=True, kw_only=True)
class ScrollStep:
    """One timed scroll movement within a scroll action. Steps run in order.

    Attributes:
        to: Destination for this movement. Select position, coordinates, or selector
            using its type discriminator.
        duration_ms: Required movement duration in milliseconds. Must be at least 1.
            The recording deadline can cut it short.
        easing: Movement easing. Defaults to linear.
    """

    to: ScrollTarget
    duration_ms: int
    easing: ScrollEasing | None = None


RecordingAction: TypeAlias = (
    RecordingScrollAction
    | RecordingStallAction
    | RecordingLocateSelectorAction
    | RecordingClickAction
    | RecordingErrorAction
    | RecordingSimpleScrollAction
    | RecordingExecuteJavaScriptAction
)

RecordingTrigger: TypeAlias = (
    RecordingImmediateTrigger
    | RecordingElementVisibleTrigger
    | RecordingFunctionCallTrigger
)

ScrollTarget: TypeAlias = (
    PositionScrollTarget | CoordinatesScrollTarget | SelectorScrollTarget
)


@dataclass(slots=True, kw_only=True)
class BaseCreateRecordingRequest:
    """Browser settings and timeline options shared by both recording sources.

    Attributes:
        css: CSS to style HTML content or inject into a URL page after it loads. See
            https://docs.htmlcsstoimage.com/parameters/css/
        device_scale: Capture pixel density. Defaults to 2 for HTML/CSS and 1 for URL
            recordings. See https://docs.htmlcsstoimage.com/parameters/device_scale/
        viewport_height: Viewport height in CSS pixels. Supply both dimensions to set
            the recording size. See https://docs.htmlcsstoimage.com/parameters/viewport/
        viewport_width: Viewport width in CSS pixels. Supply both dimensions to set the
            recording size. See https://docs.htmlcsstoimage.com/parameters/viewport/
        disable_twemoji: Disable Twemoji for HTML/CSS when true. URL recordings inject
            it only when explicitly false. See
            https://docs.htmlcsstoimage.com/parameters/disable_twemoji/
        dedupe_duration_s: Reuse an identical recording created within this many
            seconds. Set to 0 to disable deduplication. See
            https://docs.htmlcsstoimage.com/parameters/dedupe_duration_s/
        color_scheme: Chrome's preferred light or dark color scheme while recording. See
            https://docs.htmlcsstoimage.com/parameters/color_scheme/
        timezone: Browser timezone as an IANA identifier, such as 'America/New_York'.
            See https://docs.htmlcsstoimage.com/parameters/timezone/
        viewport_mobile: Enable mobile viewport behavior, including the page's viewport
            meta tag. See https://docs.htmlcsstoimage.com/parameters/viewport/
        viewport_landscape: Emulate landscape orientation. See
            https://docs.htmlcsstoimage.com/parameters/viewport/
        viewport_touch: Emulate a viewport that supports touch events. See
            https://docs.htmlcsstoimage.com/parameters/viewport/
        media_type: CSS media type used while recording. See
            https://docs.htmlcsstoimage.com/parameters/media_type/
        proxy_id: Organization proxy to use while recording. See
            https://docs.htmlcsstoimage.com/guides/advanced/proxies/
        storage_destination_id: Storage destination to receive the recording. See
            https://docs.htmlcsstoimage.com/guides/advanced/storage-destinations/
        request_overrides: Block matching browser requests while recording. Available on
            paid plans. See
            https://docs.htmlcsstoimage.com/parameters/request_overrides/
        duration_ms: Requested duration in milliseconds: 500–30000, or up to 90000 in
            target mode. duration_mode controls how actions fit into this duration. See
            https://docs.htmlcsstoimage.com/parameters/duration_ms/
        trigger: When recording and actions start after page preparation. Defaults to
            immediate. See https://docs.htmlcsstoimage.com/parameters/trigger/
        actions: Ordered interactions. Leave None or empty to record the page without
            interactions. See https://docs.htmlcsstoimage.com/parameters/actions/
        audio: Optional MP4 or WebM soundtrack from an asset ID or public URL.
            See https://docs.htmlcsstoimage.com/parameters/audio/
        output: Output format, frame rate, and scale. Defaults to MP4 at 30 fps.
            See https://docs.htmlcsstoimage.com/parameters/output/
        duration_mode: How duration_ms limits the timeline. Defaults to at_most. See
            https://docs.htmlcsstoimage.com/parameters/duration_mode/
        defer_render: Wait to render until media or storage is requested. Defaults to
            false; does not reset deduplicated recordings. See
            https://docs.htmlcsstoimage.com/parameters/defer_render/
        skip_scroll_preload: Skip the preparation scroll that loads lazy content.
            Scrolling actions still run. Defaults to false. See
            https://docs.htmlcsstoimage.com/parameters/skip_scroll_preload/
    """

    css: str | None = None
    device_scale: float | None = None
    viewport_height: int | None = None
    viewport_width: int | None = None
    disable_twemoji: bool | None = None
    dedupe_duration_s: int | None = None
    color_scheme: ColorSchemeType | None = None
    timezone: str | None = None
    viewport_mobile: bool | None = None
    viewport_landscape: bool | None = None
    viewport_touch: bool | None = None
    media_type: MediaType | None = None
    proxy_id: str | None = None
    storage_destination_id: str | None = None
    request_overrides: list[RequestOverride] | None = None
    duration_ms: int
    trigger: RecordingTrigger | None = None
    actions: list[RecordingAction] | None = None
    audio: RecordingAudio | None = None
    output: RecordingOutputOptions | None = None
    duration_mode: RecordingDurationMode | None = None
    defer_render: bool | None = None
    skip_scroll_preload: bool | None = None


@dataclass(slots=True, kw_only=True)
class CreateHtmlCssRecordingRequest(BaseCreateRecordingRequest):
    """Record an HTML document or fragment with optional CSS and Google Fonts.

    Attributes:
        google_fonts: Google Fonts to load. Set font-family in your CSS to use them. See
            https://docs.htmlcsstoimage.com/parameters/google_fonts/
        html: HTML document or fragment to record. Fragments are rendered in a wrapper
            document. See https://docs.htmlcsstoimage.com/parameters/html/
    """

    google_fonts: list[str] | tuple[str, ...] | None = None
    html: str


@dataclass(slots=True, kw_only=True)
class CreateUrlRecordingRequest(BaseCreateRecordingRequest):
    """Record a public HTTP or HTTPS webpage.

    Attributes:
        url: Public HTTP or HTTPS URL to record. See
            https://docs.htmlcsstoimage.com/parameters/url/
        block_consent_banners: Attempt to hide cookie and consent banners before
            recording. See
            https://docs.htmlcsstoimage.com/guides/advanced/blocking-cookie-banners/
        identify_as_hcti: Add X-HCTI-SCREENSHOT: 1 to the top-level navigation. See
            https://docs.htmlcsstoimage.com/parameters/identify_as_hcti/
        headers: Custom headers for top-level navigations to the URL's origin and
            additional_header_origins. See
            https://docs.htmlcsstoimage.com/parameters/headers/
        additional_header_origins: Additional exact HTTP or HTTPS origins allowed to
            receive custom headers. See
            https://docs.htmlcsstoimage.com/parameters/headers/#additional-header-origins
        include_headers_on_subrequests: Send custom headers with subrequests to allowed
            origins. Defaults to false. See
            https://docs.htmlcsstoimage.com/parameters/headers/#include-headers-on-subrequests
    """

    url: str
    block_consent_banners: bool | None = None
    identify_as_hcti: bool | None = None
    headers: Mapping[str, str] | None = None
    additional_header_origins: list[str] | None = None
    include_headers_on_subrequests: bool | None = None


CreateRecordingRequest: TypeAlias = (
    CreateHtmlCssRecordingRequest | CreateUrlRecordingRequest
)


@dataclass(frozen=True, slots=True)
class CreateRecordingSuccessResponse:
    """
    Created or deduplicated recording.

    Attributes:
        id: Recording identifier.
        status_url: Authenticated status endpoint. Checking status is optional.
        recording_url: Media URL. Embed or request it directly; the request waits
            until the recording is ready.
    """

    id: str
    status_url: str
    recording_url: str
    success: Literal[True] = True


@dataclass(frozen=True, slots=True)
class RecordingError:
    """
    Error from an attempt. Check status to distinguish retries from failure.
    """

    code: str
    message: str
    occurred_at: str
    retryable: bool
    action_path: str | None = None


@dataclass(frozen=True, slots=True)
class RecordingStatusSuccessResponse:
    """
    Lifecycle information from HTTP 200 or 202, with ISO 8601 UTC timestamps.

    ready, failed, and cancelled are terminal. A successful fetch can report a
    failed recording; error can also describe an earlier, retryable attempt.
    """

    id: str
    recording_url: str
    status: RecordingStatus
    status_entered_at: str
    attempt_count: int
    stored_duration_ms: int | None = None
    storage_destination_hcti_storage_disabled: bool | None = None
    error: RecordingError | None = None
    success: Literal[True] = True


CreateRecordingResponse: TypeAlias = CreateRecordingSuccessResponse | ApiErrorResponse
RecordingStatusResponse: TypeAlias = RecordingStatusSuccessResponse | ApiErrorResponse
DeleteRecordingSuccessResponse = DeleteImageSuccessResponse
DeleteRecordingResponse: TypeAlias = DeleteImageResponse
