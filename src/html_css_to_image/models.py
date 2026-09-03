"""Typed request and response models for the HTML/CSS to Image API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

ColorSchemeType: TypeAlias = Literal["light", "dark"]
MediaType: TypeAlias = Literal["print", "screen"]
PDFUnit: TypeAlias = Literal["px", "in", "cm", "mm"]
RenderImageCropOrigin: TypeAlias = Literal["start", "center", "end"]
ImageFormat: TypeAlias = Literal["png", "jpg", "webp", "pdf"]
RenderImageFormat: TypeAlias = ImageFormat
RenderImageValueUnit: TypeAlias = Literal["px", "%"]


def _validate_string_collection(
    name: str,
    value: list[str] | tuple[str, ...] | None,
) -> None:
    if value is None:
        return
    if not isinstance(value, (list, tuple)) or any(
        not isinstance(item, str) for item in value
    ):
        raise TypeError(f"{name} must be a list or tuple of strings")


@dataclass(slots=True)
class PDFValueWithUnits:
    """A numeric PDF dimension paired with an explicit unit.

    Attributes:
        value: Numeric magnitude of the dimension.
        unit: Unit used by the dimension: ``px``, ``in``, ``cm``, or ``mm``.
    """

    value: int | float
    unit: PDFUnit


PDFValueInput: TypeAlias = int | float | PDFValueWithUnits


@dataclass(slots=True)
class PDFMargins:
    """Margins applied to a generated PDF.

    Plain numbers are interpreted as pixels. Use :class:`PDFValueWithUnits`
    when a margin should use inches, centimeters, or millimeters.

    Attributes:
        top: Top page margin.
        right: Right page margin.
        bottom: Bottom page margin.
        left: Left page margin.
    """

    top: PDFValueInput
    right: PDFValueInput
    bottom: PDFValueInput
    left: PDFValueInput


@dataclass(slots=True)
class PDFOptions:
    """Options that cause the API to render a PDF instead of an image.

    Attributes:
        print_background: Include CSS background graphics in the PDF.
        scale: Scale applied to the rendered page.
        margins: Page margins in top, right, bottom, left order.
        page_height: Page height. Plain numbers are interpreted as pixels.
        page_width: Page width. Plain numbers are interpreted as pixels.
    """

    print_background: bool | None = None
    scale: int | float | None = None
    margins: PDFMargins | None = None
    page_height: PDFValueInput | None = None
    page_width: PDFValueInput | None = None


@dataclass(slots=True, kw_only=True)
class BaseCreateImageRequest:
    """Options shared by HTML/CSS and URL screenshot requests.

    All attributes are optional. Unset values are omitted from the API
    payload.

    Attributes:
        format: File format used in the URL returned by the API.
        selector: CSS selector to crop the image to a specific element.
        device_scale: Browser device scale factor. The API default is ``2``.
        viewport_height: Browser viewport height in pixels.
        viewport_width: Browser viewport width in pixels.
        max_wait_ms: Maximum time the renderer may wait before capture.
        ms_delay: Additional delay before capture, in milliseconds.
        render_when_ready: Wait for ``ScreenshotReady()`` in page JavaScript.
        max_render_once: Ensure that the image is rendered and saved once.
        disable_twemoji: Disable the Twemoji fallback renderer.
        color_scheme: Emulate the ``light`` or ``dark`` color scheme.
        timezone: IANA timezone name used by the browser.
        viewport_mobile: Emulate a mobile viewport.
        viewport_touch: Enable touch interactions in the viewport.
        viewport_landscape: Render the viewport in landscape orientation.
        media_type: Emulate ``print`` or ``screen`` CSS media.
        proxy_id: Organization proxy identifier used for rendering.
        jumbo_max_width: Maximum width for jumbo rendering.
        jumbo_max_height: Maximum height for jumbo rendering.
        dedupe_duration_s: Reuse a matching recently generated image for up
            to this many seconds. Supported only for single POST requests,
            not batches, templates, or signed URLs.
        storage_destination_id: Storage destination configured in HCTI.
        transparent_background: Render the page background as transparent.
        pdf_options: PDF-specific output options.
    """

    format: ImageFormat | None = None
    selector: str | None = None
    device_scale: int | float | None = None
    viewport_height: int | None = None
    viewport_width: int | None = None
    max_wait_ms: int | None = None
    ms_delay: int | None = None
    render_when_ready: bool | None = None
    max_render_once: bool | None = None
    disable_twemoji: bool | None = None
    color_scheme: ColorSchemeType | None = None
    timezone: str | None = None
    viewport_mobile: bool | None = None
    viewport_touch: bool | None = None
    viewport_landscape: bool | None = None
    media_type: MediaType | None = None
    proxy_id: str | None = None
    jumbo_max_width: int | None = None
    jumbo_max_height: int | None = None
    dedupe_duration_s: int | None = None
    storage_destination_id: str | None = None
    transparent_background: bool | None = None
    pdf_options: PDFOptions | None = None


@dataclass(slots=True, kw_only=True)
class CreateHtmlCssImageRequest(BaseCreateImageRequest):
    """Request to render an image from an HTML string and optional CSS.

    ``html`` defaults to an empty string so a batch variation can inherit the
    HTML supplied by its batch defaults.

    Attributes:
        html: Raw HTML content to render.
        css: Optional CSS rules applied to the HTML.
        google_fonts: Google Font family names to load before rendering.

    Raises:
        TypeError: If ``google_fonts`` is not a list or tuple of strings.
    """

    html: str = ""
    css: str | None = None
    google_fonts: list[str] | tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        """Validate collection fields that Python would otherwise treat as strings."""

        _validate_string_collection("google_fonts", self.google_fonts)


@dataclass(slots=True, kw_only=True)
class CreateUrlImageRequest(BaseCreateImageRequest):
    """Request to capture a screenshot of a URL.

    ``url`` defaults to an empty string so a batch variation can inherit the
    URL supplied by its batch defaults.

    Attributes:
        url: Public URL for the renderer to capture.
        css: Optional CSS injected into the target page.
        headers: HTTP headers sent to the target URL. Keep secrets out of
            signed URLs because signed query parameters remain visible.
        additional_header_origins: Exact additional origins that may receive
            ``headers`` on subrequests.
        include_headers_on_subrequests: Also send ``headers`` to same-origin
            subrequests made while the page loads.
        identify_as_hcti: Add HCTI's identifying request header.
        full_screen: Capture the entire scrollable page.
        block_consent_banners: Attempt to hide cookie and consent banners.

    Raises:
        TypeError: If ``additional_header_origins`` is not a list or tuple of
            strings.
    """

    url: str = ""
    css: str | None = None
    headers: Mapping[str, str] | None = None
    additional_header_origins: list[str] | tuple[str, ...] | None = None
    include_headers_on_subrequests: bool | None = None
    identify_as_hcti: bool | None = None
    full_screen: bool | None = None
    block_consent_banners: bool | None = None

    def __post_init__(self) -> None:
        """Validate collection fields that Python would otherwise treat as strings."""

        _validate_string_collection(
            "additional_header_origins",
            self.additional_header_origins,
        )


@dataclass(slots=True, kw_only=True)
class CreateTemplatedImageRequest:
    """Request to render a saved HCTI template.

    Attributes:
        template_id: Identifier of the template to render.
        template_values: Values substituted into the template variables.
        template_version: Optional template version. The latest is used when
            omitted.
        format: File format used in the URL returned by the API.
    """

    template_id: str
    template_values: Mapping[str, Any]
    template_version: int | None = None
    format: ImageFormat | None = None


CreateImageRequest: TypeAlias = (
    CreateHtmlCssImageRequest | CreateUrlImageRequest | CreateTemplatedImageRequest
)
BatchCreateImageRequest: TypeAlias = CreateHtmlCssImageRequest | CreateUrlImageRequest


@dataclass(frozen=True, slots=True)
class ValidationError:
    """A validation error associated with one request field.

    Attributes:
        path: API field path that failed validation.
        message: Human-readable validation message.
    """

    path: str
    message: str


@dataclass(frozen=True, slots=True)
class CreateImageSuccessResponse:
    """Successful image creation response.

    Attributes:
        success: Always ``True`` for this response type.
        id: Identifier assigned to the generated image.
        url: URL from which the generated image can be retrieved.
    """

    id: str
    url: str
    success: Literal[True] = True


@dataclass(frozen=True, slots=True)
class ApiErrorResponse:
    """Unsuccessful API response.

    Network and timeout failures are raised by HTTPX and do not produce this
    response type.

    Attributes:
        status_code: HTTP status code returned by the API.
        error: Short API error name.
        message: Optional human-readable error details.
        validation_errors: Field-level validation failures, when supplied.
        success: Always ``False`` for this response type.
    """

    status_code: int
    error: str
    message: str | None = None
    validation_errors: tuple[ValidationError, ...] | None = None
    success: Literal[False] = False


@dataclass(frozen=True, slots=True)
class CreateImageBatchSuccessResponse:
    """Successful batch image creation response.

    Attributes:
        images: Results returned for each batch variation.
        success: Always ``True`` for this response type.
    """

    images: tuple[CreateImageSuccessResponse, ...]
    success: Literal[True] = True


@dataclass(frozen=True, slots=True)
class DeleteImageSuccessResponse:
    """Successful image deletion response.

    Attributes:
        success: Always ``True`` for this response type.
    """

    success: Literal[True] = True


CreateImageResponse: TypeAlias = CreateImageSuccessResponse | ApiErrorResponse
CreateImageBatchResponse: TypeAlias = (
    CreateImageBatchSuccessResponse | ApiErrorResponse
)
DeleteImageResponse: TypeAlias = DeleteImageSuccessResponse | ApiErrorResponse


@dataclass(frozen=True, slots=True)
class RenderImageCropPosition:
    """A crop boundary expressed in pixels or as a percentage.

    Use :meth:`pixels` or :meth:`percent` to construct a validated value.

    Attributes:
        value: Non-negative pixel position or percentage from 1 through 100.
        unit: ``px`` or ``%``.
    """

    value: int
    unit: RenderImageValueUnit

    def __post_init__(self) -> None:
        if self.unit not in ("px", "%"):
            raise ValueError("A crop position unit must be px or %")
        if self.unit == "px" and self.value < 0:
            raise ValueError("A pixel crop position cannot be negative")
        if self.unit == "%" and not 1 <= self.value <= 100:
            raise ValueError("A percentage crop position must be from 1 to 100")

    @classmethod
    def pixels(cls, value: int) -> RenderImageCropPosition:
        """Create a crop position measured in pixels."""

        return cls(value, "px")

    @classmethod
    def percent(cls, value: int) -> RenderImageCropPosition:
        """Create a crop position measured as a percentage."""

        return cls(value, "%")


@dataclass(frozen=True, slots=True)
class RenderImageCropSize:
    """A crop width or height expressed in pixels or as a percentage.

    Use :meth:`pixels` or :meth:`percent` to construct a validated value.

    Attributes:
        value: Positive size value.
        unit: ``px`` or ``%``.
    """

    value: int
    unit: RenderImageValueUnit

    def __post_init__(self) -> None:
        if self.unit not in ("px", "%"):
            raise ValueError("A crop size unit must be px or %")
        if self.unit == "px" and self.value <= 0:
            raise ValueError("A pixel crop size must be positive")
        if self.unit == "%" and not 1 <= self.value <= 100:
            raise ValueError("A percentage crop size must be from 1 to 100")

    @classmethod
    def pixels(cls, value: int) -> RenderImageCropSize:
        """Create a crop size measured in pixels."""

        return cls(value, "px")

    @classmethod
    def percent(cls, value: int) -> RenderImageCropSize:
        """Create a crop size measured as a percentage."""

        return cls(value, "%")


@dataclass(frozen=True, slots=True)
class RenderImageAspectRatio:
    """Positive width and height components of a crop aspect ratio.

    Attributes:
        width: Positive width component, such as ``16`` in ``16:9``.
        height: Positive height component, such as ``9`` in ``16:9``.
    """

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Aspect ratio width and height must be positive")


@dataclass(frozen=True, slots=True)
class RenderImageCropSpan:
    """Crop instructions for one axis.

    Prefer the named constructors because they describe the intended crop:
    :meth:`from_position`, :meth:`between`, :meth:`sized_from`, or
    :meth:`sized`.

    Attributes:
        start: Optional first crop boundary.
        end: Optional second crop boundary.
        size: Optional crop width or height.
        origin: Origin used when ``size`` is supplied without ``start``.
    """

    start: RenderImageCropPosition | None = None
    end: RenderImageCropPosition | None = None
    size: RenderImageCropSize | None = None
    origin: RenderImageCropOrigin = "start"

    def __post_init__(self) -> None:
        if self.origin not in ("start", "center", "end"):
            raise ValueError("Crop origin must be start, center, or end")
        if self.start is None and self.size is None:
            raise ValueError("A crop span requires a start position or size")
        if self.end is not None and self.start is None:
            raise ValueError("A crop end requires a start position")
        if self.end is not None and self.size is not None:
            raise ValueError("A crop span cannot have both an end and a size")
        if self.end is not None:
            start = self.start
            if start is None:
                raise ValueError("A crop end requires a start position")
            if self.end.unit == start.unit and self.end.value <= start.value:
                raise ValueError("Crop end must be greater than crop start")
        if self.start is not None and self.origin != "start":
            raise ValueError("Crop origin is only used by a size without a start")

    @classmethod
    def from_position(
        cls,
        position: RenderImageCropPosition,
    ) -> RenderImageCropSpan:
        """Crop from ``position`` through the remaining image."""

        return cls(start=position)

    @classmethod
    def between(
        cls,
        start: RenderImageCropPosition,
        end: RenderImageCropPosition,
    ) -> RenderImageCropSpan:
        """Crop between two positions, which may use different units."""

        return cls(start=start, end=end)

    @classmethod
    def sized_from(
        cls,
        start: RenderImageCropPosition,
        size: RenderImageCropSize,
    ) -> RenderImageCropSpan:
        """Crop a fixed size beginning at ``start``."""

        return cls(start=start, size=size)

    @classmethod
    def sized(
        cls,
        size: RenderImageCropSize,
        origin: RenderImageCropOrigin = "start",
    ) -> RenderImageCropSpan:
        """Crop ``size`` from the start, center, or end of an axis."""

        return cls(size=size, origin=origin)


@dataclass(frozen=True, slots=True)
class RenderImageCrop:
    """Rectangle or aspect-ratio crop applied when an image URL is fetched.

    Use :meth:`rectangle`, :meth:`aspect_ratio_from_width`, or
    :meth:`aspect_ratio_from_height` to create a crop.

    Attributes:
        horizontal: Horizontal crop span, when explicitly supplied.
        vertical: Vertical crop span, when explicitly supplied.
        aspect_ratio: Optional output aspect ratio.
        aspect_ratio_axis: Axis whose span determines the aspect-ratio crop.
        computed_origin: Origin on the axis calculated from the aspect ratio.
    """

    horizontal: RenderImageCropSpan | None = None
    vertical: RenderImageCropSpan | None = None
    aspect_ratio: RenderImageAspectRatio | None = None
    aspect_ratio_axis: Literal["width", "height"] | None = None
    computed_origin: RenderImageCropOrigin = "start"

    def __post_init__(self) -> None:
        if self.computed_origin not in ("start", "center", "end"):
            raise ValueError("Crop origin must be start, center, or end")
        if self.aspect_ratio is None:
            if self.horizontal is None and self.vertical is None:
                raise ValueError("A rectangle crop requires at least one axis")
            if self.aspect_ratio_axis is not None:
                raise ValueError("A rectangle crop cannot set an aspect-ratio axis")
            if self.computed_origin != "start":
                raise ValueError("A rectangle crop cannot set a computed origin")
            return

        if self.aspect_ratio_axis == "width":
            if self.horizontal is None or self.vertical is not None:
                raise ValueError("A width-based aspect crop requires a horizontal span")
        elif self.aspect_ratio_axis == "height":
            if self.vertical is None or self.horizontal is not None:
                raise ValueError("A height-based aspect crop requires a vertical span")
        else:
            raise ValueError("An aspect-ratio crop requires a width or height axis")

    @classmethod
    def rectangle(
        cls,
        *,
        horizontal: RenderImageCropSpan | None = None,
        vertical: RenderImageCropSpan | None = None,
    ) -> RenderImageCrop:
        """Create a rectangular crop from one or two axis spans."""

        return cls(horizontal=horizontal, vertical=vertical)

    @classmethod
    def aspect_ratio_from_width(
        cls,
        aspect_ratio: RenderImageAspectRatio,
        horizontal: RenderImageCropSpan,
        *,
        height_origin: RenderImageCropOrigin = "start",
    ) -> RenderImageCrop:
        """Calculate crop height from a ratio and horizontal span."""

        return cls(
            horizontal=horizontal,
            aspect_ratio=aspect_ratio,
            aspect_ratio_axis="width",
            computed_origin=height_origin,
        )

    @classmethod
    def aspect_ratio_from_height(
        cls,
        aspect_ratio: RenderImageAspectRatio,
        vertical: RenderImageCropSpan,
        *,
        width_origin: RenderImageCropOrigin = "start",
    ) -> RenderImageCrop:
        """Calculate crop width from a ratio and vertical span."""

        return cls(
            vertical=vertical,
            aspect_ratio=aspect_ratio,
            aspect_ratio_axis="height",
            computed_origin=width_origin,
        )


@dataclass(frozen=True, slots=True)
class RenderImageOptions:
    """Options applied when an HCTI image URL is retrieved.

    Cropping happens before output resizing. These options also work with
    signed template and create-and-render URLs.

    Attributes:
        format: Optional output format: ``png``, ``jpg``, ``webp``, or ``pdf``.
        dpi: Output DPI from 31 through 599.
        height: Output height from 1 through 5000 pixels.
        width: Output width from 1 through 5000 pixels.
        crop: Optional crop instructions applied before resizing.
    """

    format: ImageFormat | None = None
    dpi: int | None = None
    height: int | None = None
    width: int | None = None
    crop: RenderImageCrop | None = None

    def __post_init__(self) -> None:
        if self.format not in (None, "png", "jpg", "webp", "pdf"):
            raise ValueError("Render format must be png, jpg, webp, or pdf")
        if self.dpi is not None and not 30 < self.dpi < 600:
            raise ValueError("DPI must be greater than 30 and less than 600")
        for name, value in (("height", self.height), ("width", self.width)):
            if value is not None and not 1 <= value <= 5000:
                raise ValueError(f"Render {name} must be from 1 to 5000 pixels")
