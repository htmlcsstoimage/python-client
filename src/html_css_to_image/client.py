"""Synchronous client for the HTML/CSS to Image API."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar
from urllib.parse import quote

import httpx

from ._request_mapper import RequestMapper
from ._response_mapper import ResponseMapper
from ._transport import HttpTransport
from ._url_builder import UrlBuilder
from .models import (
    BatchCreateImageRequest,
    CreateImageBatchResponse,
    CreateImageBatchSuccessResponse,
    CreateImageRequest,
    CreateImageResponse,
    CreateTemplatedImageRequest,
    CreateUrlImageRequest,
    DeleteImageResponse,
    RenderImageOptions,
)

_ClientT = TypeVar("_ClientT", bound="HtmlCssToImageClient")


class HtmlCssToImageClient:
    """Client for creating images with the HTML/CSS to Image API.

    The client performs no automatic retries. To configure retry behavior,
    proxies, certificates, connection limits, or custom transports, construct
    an :class:`httpx.Client` and pass it through ``http_client``.

    Args:
        api_id: HCTI API ID from the dashboard.
        api_key: HCTI API key from the dashboard.
        http_client: Optional configured HTTPX client. Injected clients remain
            owned by the caller and are never closed by this object.
        base_url: API origin. Override this primarily for testing or proxies.

    Example:
        >>> client = HtmlCssToImageClient("api-id", "api-key")
        >>> request = CreateUrlImageRequest(url="https://example.com")
        >>> result = client.create_image(request)
        >>> if result.success:
        ...     print(result.url)
    """

    def __init__(
        self,
        api_id: str,
        api_key: str,
        *,
        http_client: httpx.Client | None = None,
        base_url: str = "https://hcti.io",
    ) -> None:
        normalized_base_url = base_url.rstrip("/")
        self._transport = HttpTransport(
            api_id,
            api_key,
            http_client=http_client,
            base_url=normalized_base_url,
        )
        self._url_builder = UrlBuilder(api_id, api_key, normalized_base_url)

    @classmethod
    def from_env(
        cls: type[_ClientT],
        *,
        http_client: httpx.Client | None = None,
        base_url: str = "https://hcti.io",
    ) -> _ClientT:
        """Create a client from ``HCTI_API_ID`` and ``HCTI_API_KEY``.

        Args:
            http_client: Optional caller-owned HTTPX client.
            base_url: API origin. Override this primarily for testing.

        Returns:
            A configured :class:`HtmlCssToImageClient`.

        Raises:
            ValueError: If either required environment variable is missing.
        """

        api_id = os.environ.get("HCTI_API_ID")
        api_key = os.environ.get("HCTI_API_KEY")
        if not api_id or not api_key:
            raise ValueError(
                "Missing environment variables HCTI_API_ID or HCTI_API_KEY"
            )
        return cls(
            api_id,
            api_key,
            http_client=http_client,
            base_url=base_url,
        )

    def create_image(self, request: CreateImageRequest) -> CreateImageResponse:
        """Create an image from HTML/CSS, a URL, or a saved template.

        API validation and server errors are returned as
        :class:`ApiErrorResponse`. HTTP transport failures and timeouts are
        raised directly by HTTPX.

        Args:
            request: Typed request describing the content to render.

        Returns:
            A success response containing the image ID and URL, or an API
            error response.

        Raises:
            TypeError: If ``request`` is not a supported request model.
            UnexpectedResponseError: If a successful API response is malformed.
            httpx.HTTPError: If the HTTP request cannot be completed.
        """

        payload = RequestMapper.map_request(request, in_batch=False)
        response = self._transport.post("/v1/image", payload)
        return ResponseMapper.map_image_response(response)

    def create_image_batch(
        self,
        variations: Sequence[BatchCreateImageRequest],
        default_options: BatchCreateImageRequest | None = None,
    ) -> CreateImageBatchResponse:
        """Create several related images in one API call.

        Empty ``html`` or ``url`` values are omitted in batch payloads so a
        variation can inherit that value from ``default_options``. An empty
        variation list returns a successful response without making an HTTP
        request.

        Args:
            variations: HTML/CSS or URL requests containing per-image values.
            default_options: Optional values inherited by every variation.

        Returns:
            A batch success response, or an API error response.

        Raises:
            TypeError: If a template request or unsupported object is passed.
            UnexpectedResponseError: If a successful API response is malformed.
            httpx.HTTPError: If the HTTP request cannot be completed.
        """

        if not variations:
            return CreateImageBatchSuccessResponse(images=())

        payload: dict[str, Any] = {
            "variations": [
                RequestMapper.map_batch_request(variation)
                for variation in variations
            ],
        }
        if default_options is not None:
            payload["default_options"] = RequestMapper.map_batch_request(
                default_options
            )
        response = self._transport.post("/v1/image/batch", payload)
        return ResponseMapper.map_batch_response(response)

    def delete_image(self, image_id: str) -> DeleteImageResponse:
        """Delete one generated image.

        Args:
            image_id: HCTI image identifier. It is safely encoded as one URL
                path segment.

        Returns:
            A deletion success response, or a typed API error response.

        Raises:
            httpx.HTTPError: If the HTTP request cannot be completed.
        """

        response = self._transport.delete(f"/v1/image/{quote(image_id, safe='')}")
        return ResponseMapper.map_delete_response(response)

    def delete_image_batch(
        self,
        image_ids: list[str] | tuple[str, ...],
    ) -> DeleteImageResponse:
        """Delete several generated images in one API call.

        Args:
            image_ids: List or tuple of HCTI image identifiers to delete.

        Returns:
            A deletion success response, or a typed API error response.

        Raises:
            TypeError: If ``image_ids`` is not a list or tuple of strings.
            httpx.HTTPError: If the HTTP request cannot be completed.
        """

        if not isinstance(image_ids, (list, tuple)) or any(
            not isinstance(image_id, str) for image_id in image_ids
        ):
            raise TypeError("image_ids must be a list or tuple of strings")
        response = self._transport.delete("/v1/image/batch", {"ids": list(image_ids)})
        return ResponseMapper.map_delete_response(response)

    def image_url(
        self,
        image_id: str,
        render_options: RenderImageOptions | None = None,
    ) -> str:
        """Build a URL for retrieving an existing image.

        Args:
            image_id: HCTI image identifier.
            render_options: Optional output format, resize, DPI, and crop
                settings. Cropping is applied before resizing.

        Returns:
            The image URL. This method performs no HTTP request.
        """

        return self._url_builder.image_url(image_id, render_options)

    def generate_templated_image_url(
        self,
        request: CreateTemplatedImageRequest,
        render_options: RenderImageOptions | None = None,
    ) -> str:
        """Generate a signed on-demand URL from a template request.

        Args:
            request: Complete saved-template request to sign.
            render_options: Optional output format, resize, DPI, and crop
                settings. Its format takes precedence over ``request.format``.

        Returns:
            Signed HCTI image URL safe to expose to a frontend. This method
            performs no HTTP request.
        """

        return self._url_builder.templated_image_url(request, render_options)

    def generate_templated_image_url_from_values(
        self,
        template_id: str,
        template_values: Mapping[str, Any] | None = None,
        template_version: int | None = None,
        render_options: RenderImageOptions | None = None,
    ) -> str:
        """Generate a signed on-demand URL from separate template values.

        Object and array template values are encoded as compact JSON before
        the query string is signed.

        Args:
            template_id: Identifier of the saved template to render.
            template_values: Values substituted into template variables.
            template_version: Optional saved-template version.
            render_options: Optional output format, resize, DPI, and crop
                settings included in the signed URL.

        Returns:
            Signed HCTI image URL safe to expose to a frontend. This method
            performs no HTTP request.
        """

        request = CreateTemplatedImageRequest(
            template_id=template_id,
            template_values={} if template_values is None else template_values,
            template_version=template_version,
        )
        return self.generate_templated_image_url(request, render_options)

    def generate_create_and_render_url(
        self,
        request: CreateUrlImageRequest,
        render_options: RenderImageOptions | None = None,
    ) -> str:
        """Generate a signed URL that captures another URL on demand.

        This method performs no HTTP request. PDF layout options are not
        supported by the create-and-render endpoint and are omitted. Boolean
        options set to ``False`` are also omitted to match the TypeScript
        client.

        Args:
            request: URL screenshot request to sign.
            render_options: Optional output format, resize, DPI, and crop
                settings. Its format takes precedence over ``request.format``.

        Returns:
            Signed HCTI create-and-render URL safe to expose to a frontend.
        """

        return self._url_builder.create_and_render_url(request, render_options)

    def close(self) -> None:
        """Close the internally-created HTTPX client.

        A client supplied through ``http_client`` is owned by the caller and
        is intentionally left open.
        """

        self._transport.close()

    def __enter__(self) -> HtmlCssToImageClient:
        """Return this client for use as a context manager."""

        return self

    def __exit__(self, *exc_info: object) -> None:
        """Close internally-owned HTTP resources on context exit."""

        self.close()
