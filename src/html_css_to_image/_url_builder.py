"""Internal construction and signing of HCTI image URLs."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote, quote_plus

from ._request_mapper import RequestMapper
from .models import (
    CreateTemplatedImageRequest,
    CreateUrlImageRequest,
    RenderImageCrop,
    RenderImageCropSpan,
    RenderImageOptions,
)


class UrlBuilder:
    """Build unsigned retrieval URLs and HMAC-signed rendering URLs."""

    def __init__(self, api_id: str, api_key: str, base_url: str) -> None:
        self._api_id = api_id
        self._api_key = api_key
        self._base_url = base_url

    def image_url(
        self,
        image_id: str,
        render_options: RenderImageOptions | None,
    ) -> str:
        """Build the retrieval URL for an existing image."""

        options = render_options or RenderImageOptions()
        path = f"{self._base_url}/v1/image/{quote(image_id, safe='')}"
        if options.format is not None:
            path += f".{options.format}"
        query = self._form_encode(self._render_option_pairs(options))
        return f"{path}?{query}" if query else path

    def templated_image_url(
        self,
        request: CreateTemplatedImageRequest,
        render_options: RenderImageOptions | None,
    ) -> str:
        """Build an HMAC-signed saved-template rendering URL."""

        pairs: list[tuple[str, str]] = []
        if request.template_version:
            pairs.append(("template_version", str(request.template_version)))

        for key in sorted(request.template_values):
            value = request.template_values[key]
            if value is None:
                continue
            if isinstance(value, (Mapping, list, tuple)):
                encoded_value = json.dumps(
                    value,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            else:
                encoded_value = self._javascript_string(value)
            pairs.append((key, encoded_value))

        options = render_options or RenderImageOptions()
        pairs.extend(
            self._render_option_pairs(
                options,
                reserved_keys=set(request.template_values),
            )
        )
        query = self._form_encode(pairs)
        token = self._generate_hmac_token(query)
        separator = "?" if query else ""
        format_value = options.format or request.format
        format_path = f"/{format_value}" if format_value is not None else ""
        return (
            f"{self._base_url}/v1/image/{request.template_id}/{token}"
            f"{format_path}{separator}{query}"
        )

    def create_and_render_url(
        self,
        request: CreateUrlImageRequest,
        render_options: RenderImageOptions | None,
    ) -> str:
        """Build an HMAC-signed create-and-render URL."""

        pairs: list[tuple[str, str]] = [("url", request.url)]
        payload = RequestMapper.common_payload(request, include_dedupe=False)
        payload.update(
            {
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
        payload.pop("pdf_options", None)
        payload.pop("format", None)

        for key in sorted(payload):
            value = payload[key]
            if value is None or (value is False and key != "transparent_background"):
                continue
            if key == "headers":
                pairs.extend(
                    ("headers", f"{name}:{header_value}")
                    for name, header_value in value.items()
                )
            elif key == "additional_header_origins":
                pairs.extend((key, origin) for origin in value)
            else:
                pairs.append((key, self._javascript_string(value)))

        options = render_options or RenderImageOptions()
        pairs.extend(self._render_option_pairs(options))
        query = self._form_encode(pairs)
        token = self._generate_hmac_token(query)
        format_value = options.format or request.format
        format_path = f"/{format_value}" if format_value is not None else ""
        return (
            f"{self._base_url}/v1/image/create-and-render/"
            f"{self._api_id}/{token}{format_path}?{query}"
        )

    @staticmethod
    def _javascript_string(value: Any) -> str:
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            return ",".join(UrlBuilder._javascript_string(item) for item in value)
        return str(value)

    @classmethod
    def _form_encode(cls, pairs: Sequence[tuple[str, str]]) -> str:
        return "&".join(
            f"{cls._form_encode_component(key)}={cls._form_encode_component(value)}"
            for key, value in pairs
        )

    @staticmethod
    def _form_encode_component(value: str) -> str:
        # Match WHATWG URLSearchParams rather than urllib's RFC 3986 defaults:
        # spaces become '+', '*' remains literal, and '~' is percent-encoded.
        return quote_plus(value, safe="*-._").replace("~", "%7E")

    def _generate_hmac_token(self, query: str) -> str:
        return hmac.new(
            self._api_key.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def _render_option_pairs(
        cls,
        options: RenderImageOptions,
        *,
        reserved_keys: set[str] | None = None,
    ) -> list[tuple[str, str]]:
        reserved = reserved_keys or set()

        def key(name: str) -> str:
            return f"__ro_{name}" if name in reserved else name

        pairs: list[tuple[str, str]] = []
        if options.dpi is not None:
            pairs.append((key("dpi"), str(options.dpi)))
        if options.height is not None:
            pairs.append((key("height"), str(options.height)))
        if options.width is not None:
            pairs.append((key("width"), str(options.width)))
        if options.crop is not None:
            pairs.extend(cls._crop_option_pairs(options.crop, reserved))
        return pairs

    @classmethod
    def _crop_option_pairs(
        cls,
        crop: RenderImageCrop,
        reserved: set[str],
    ) -> list[tuple[str, str]]:
        def key(name: str) -> str:
            return f"__ro_{name}" if name in reserved else name

        pairs: list[tuple[str, str]] = []
        if crop.aspect_ratio is not None:
            pairs.append(
                (
                    key("aspect_ratio"),
                    f"{crop.aspect_ratio.width}_{crop.aspect_ratio.height}",
                )
            )

        x_origin = cls._crop_origin(crop.horizontal)
        y_origin = cls._crop_origin(crop.vertical)
        if crop.aspect_ratio_axis == "height":
            x_origin = crop.computed_origin
        elif crop.aspect_ratio_axis == "width":
            y_origin = crop.computed_origin
        if x_origin != "start":
            pairs.append((key("x_origin"), x_origin))
        if y_origin != "start":
            pairs.append((key("y_origin"), y_origin))

        cls._append_crop_span(pairs, crop.horizontal, "x", reserved)
        cls._append_crop_span(pairs, crop.vertical, "y", reserved)
        return pairs

    @staticmethod
    def _crop_origin(span: RenderImageCropSpan | None) -> str:
        if span is not None and span.start is None and span.size is not None:
            return span.origin
        return "start"

    @classmethod
    def _append_crop_span(
        cls,
        pairs: list[tuple[str, str]],
        span: RenderImageCropSpan | None,
        axis: str,
        reserved: set[str],
    ) -> None:
        if span is None:
            return

        def key(name: str) -> str:
            return f"__ro_{name}" if name in reserved else name

        if span.start is not None:
            pairs.append((key(f"{axis}_1"), f"{span.start.value}{span.start.unit}"))
        if span.end is not None:
            pairs.append((key(f"{axis}_2"), f"{span.end.value}{span.end.unit}"))
        if span.size is not None:
            long_name = "crop_width" if axis == "x" else "crop_height"
            short_name = "crop_w" if axis == "x" else "crop_h"
            value = f"{span.size.value}{span.size.unit}"
            has_collision = False
            if long_name in reserved:
                pairs.append((f"__ro_{long_name}", value))
                has_collision = True
            if short_name in reserved:
                pairs.append((f"__ro_{short_name}", value))
                has_collision = True
            if not has_collision:
                pairs.append((long_name, value))
