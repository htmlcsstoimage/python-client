"""Internal mapping from public request models to API payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import (
    BaseCreateImageRequest,
    BatchCreateImageRequest,
    CreateHtmlCssImageRequest,
    CreateImageRequest,
    CreateTemplatedImageRequest,
    CreateUrlImageRequest,
    PDFOptions,
    PDFValueInput,
    PDFValueWithUnits,
)


class RequestMapper:
    """Serialize typed request models for HCTI API operations."""

    @classmethod
    def map_request(
        cls,
        request: CreateImageRequest,
        *,
        in_batch: bool,
    ) -> dict[str, Any]:
        if isinstance(request, CreateHtmlCssImageRequest):
            return cls._map_html_request(request, in_batch=in_batch)
        if isinstance(request, CreateUrlImageRequest):
            return cls._map_url_request(request, in_batch=in_batch)
        if isinstance(request, CreateTemplatedImageRequest):
            if in_batch:
                raise TypeError("Template requests cannot be used in a batch")
            return cls.without_none(
                {
                    "template_id": request.template_id,
                    "template_version": request.template_version,
                    "template_values": dict(request.template_values),
                    "format": request.format,
                }
            )
        raise TypeError(f"Unsupported request type: {type(request).__name__}")

    @classmethod
    def map_batch_request(
        cls,
        request: BatchCreateImageRequest,
    ) -> dict[str, Any]:
        if not isinstance(
            request,
            (CreateHtmlCssImageRequest, CreateUrlImageRequest),
        ):
            raise TypeError("Batch requests must contain HTML/CSS or URL requests")
        return cls.map_request(request, in_batch=True)

    @classmethod
    def common_payload(
        cls,
        request: BaseCreateImageRequest,
        *,
        include_dedupe: bool = True,
    ) -> dict[str, Any]:
        """Map fields shared by POST and signed-URL operations."""

        return cls.without_none(
            {
                "format": request.format,
                "selector": request.selector,
                "device_scale": request.device_scale,
                "viewport_height": request.viewport_height,
                "viewport_width": request.viewport_width,
                "max_wait_ms": request.max_wait_ms,
                "ms_delay": request.ms_delay,
                "render_when_ready": request.render_when_ready,
                "max_render_once": request.max_render_once,
                "disable_twemoji": request.disable_twemoji,
                "color_scheme": request.color_scheme,
                "timezone": request.timezone,
                "viewport_mobile": request.viewport_mobile,
                "viewport_touch": request.viewport_touch,
                "viewport_landscape": request.viewport_landscape,
                "media_type": request.media_type,
                "proxy_id": request.proxy_id,
                "jumbo_max_width": request.jumbo_max_width,
                "jumbo_max_height": request.jumbo_max_height,
                "dedupe_duration_s": (
                    request.dedupe_duration_s if include_dedupe else None
                ),
                "storage_destination_id": request.storage_destination_id,
                "transparent_background": request.transparent_background,
                "pdf_options": cls._map_pdf_options(request.pdf_options),
            }
        )

    @staticmethod
    def without_none(values: Mapping[str, Any]) -> dict[str, Any]:
        """Remove fields whose values are ``None`` while preserving ``False``."""

        return {key: value for key, value in values.items() if value is not None}

    @classmethod
    def _map_html_request(
        cls,
        request: CreateHtmlCssImageRequest,
        *,
        in_batch: bool,
    ) -> dict[str, Any]:
        payload = cls.common_payload(request, include_dedupe=not in_batch)
        payload["html"] = request.html or None if in_batch else request.html
        payload["css"] = request.css

        if request.google_fonts:
            fonts: list[str] = []
            for font in request.google_fonts:
                processed = font.strip().replace(" ", "+")
                if processed and processed not in fonts:
                    fonts.append(processed)
            if fonts:
                payload["google_fonts"] = "|".join(fonts)

        return cls.without_none(payload)

    @classmethod
    def _map_url_request(
        cls,
        request: CreateUrlImageRequest,
        *,
        in_batch: bool,
    ) -> dict[str, Any]:
        payload = cls.common_payload(request, include_dedupe=not in_batch)
        payload.update(
            {
                "url": request.url or None if in_batch else request.url,
                "css": request.css,
                "headers": (
                    dict(request.headers) if request.headers is not None else None
                ),
                "additional_header_origins": (
                    list(request.additional_header_origins)
                    if request.additional_header_origins is not None
                    else None
                ),
                "include_headers_on_subrequests": (
                    request.include_headers_on_subrequests
                ),
                "identify_as_hcti": request.identify_as_hcti,
                "full_screen": request.full_screen,
                "block_consent_banners": request.block_consent_banners,
            }
        )
        return cls.without_none(payload)

    @classmethod
    def _map_pdf_options(
        cls,
        options: PDFOptions | None,
    ) -> dict[str, Any] | None:
        if options is None:
            return None

        payload: dict[str, Any] = {
            "print_background": options.print_background,
            "scale": options.scale,
            "page_height": (
                cls._pdf_value_to_string(options.page_height)
                if options.page_height is not None
                else None
            ),
            "page_width": (
                cls._pdf_value_to_string(options.page_width)
                if options.page_width is not None
                else None
            ),
        }
        if options.margins is not None:
            payload["margins"] = [
                cls._pdf_value_to_string(options.margins.top),
                cls._pdf_value_to_string(options.margins.right),
                cls._pdf_value_to_string(options.margins.bottom),
                cls._pdf_value_to_string(options.margins.left),
            ]
        return cls.without_none(payload)

    @classmethod
    def _pdf_value_to_string(cls, value: PDFValueInput) -> str:
        if isinstance(value, PDFValueWithUnits):
            return f"{cls._number_to_string(value.value)}{value.unit}"
        return f"{cls._number_to_string(value)}px"

    @staticmethod
    def _number_to_string(value: int | float) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
