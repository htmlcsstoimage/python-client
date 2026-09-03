"""Internal mapping from HTTP responses to public response models."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .exceptions import UnexpectedResponseError
from .models import (
    ApiErrorResponse,
    CreateImageBatchResponse,
    CreateImageBatchSuccessResponse,
    CreateImageResponse,
    CreateImageSuccessResponse,
    DeleteImageResponse,
    DeleteImageSuccessResponse,
    ValidationError,
)


class ResponseMapper:
    """Create typed response models and reject malformed successful bodies."""

    @classmethod
    def map_image_response(cls, response: httpx.Response) -> CreateImageResponse:
        """Map one image-creation response."""

        if not response.is_success:
            return cls._map_error_response(response)
        data = cls._decode_success_object(response, "image creation")
        return cls._map_success_image(data, response, "image creation response")

    @classmethod
    def map_batch_response(
        cls,
        response: httpx.Response,
    ) -> CreateImageBatchResponse:
        """Map a batch image-creation response."""

        if not response.is_success:
            return cls._map_error_response(response)
        data = cls._decode_success_object(response, "batch image creation")
        raw_images = data.get("images")
        if not isinstance(raw_images, list):
            raise cls._unexpected(
                response,
                "Batch image creation response must contain an images array.",
            )

        images = tuple(
            cls._map_batch_image(item, index, response)
            for index, item in enumerate(raw_images)
        )
        return CreateImageBatchSuccessResponse(images=images)

    @classmethod
    def map_delete_response(cls, response: httpx.Response) -> DeleteImageResponse:
        """Map an image-deletion response."""

        if response.is_success:
            return DeleteImageSuccessResponse()
        return cls._map_error_response(response)

    @classmethod
    def _map_batch_image(
        cls,
        item: object,
        index: int,
        response: httpx.Response,
    ) -> CreateImageSuccessResponse:
        if not isinstance(item, dict):
            raise cls._unexpected(
                response,
                f"Batch image result at index {index} must be an object.",
            )
        return cls._map_success_image(
            item,
            response,
            f"batch image result at index {index}",
        )

    @classmethod
    def _map_success_image(
        cls,
        data: Mapping[str, Any],
        response: httpx.Response,
        description: str,
    ) -> CreateImageSuccessResponse:
        image_id = data.get("id")
        url = data.get("url")
        if not isinstance(image_id, str) or not image_id:
            raise cls._unexpected(
                response,
                f"The {description} must contain a non-empty string id.",
            )
        if not isinstance(url, str) or not url:
            raise cls._unexpected(
                response,
                f"The {description} must contain a non-empty string url.",
            )
        return CreateImageSuccessResponse(id=image_id, url=url)

    @classmethod
    def _decode_success_object(
        cls,
        response: httpx.Response,
        operation: str,
    ) -> dict[str, Any]:
        try:
            decoded = response.json()
        except ValueError as error:
            raise cls._unexpected(
                response,
                f"Successful {operation} response was not valid JSON.",
            ) from error
        if not isinstance(decoded, dict):
            raise cls._unexpected(
                response,
                f"Successful {operation} response must be a JSON object.",
            )
        return decoded

    @classmethod
    def _map_error_response(cls, response: httpx.Response) -> ApiErrorResponse:
        data = cls._decode_error_object(response)
        raw_validation_errors = data.get("validation_errors")
        validation_errors: tuple[ValidationError, ...] | None = None
        if isinstance(raw_validation_errors, list):
            validation_errors = tuple(
                ValidationError(
                    path=str(item.get("path", "")),
                    message=str(item.get("message", "")),
                )
                for item in raw_validation_errors
                if isinstance(item, dict)
            )
        message = data.get("message")
        return ApiErrorResponse(
            status_code=response.status_code,
            error=str(data.get("error", "Unknown error")),
            message=str(message) if message is not None else None,
            validation_errors=validation_errors,
        )

    @staticmethod
    def _decode_error_object(response: httpx.Response) -> dict[str, Any]:
        try:
            decoded = response.json()
            if isinstance(decoded, dict):
                return decoded
        except ValueError:
            pass
        return {
            "error": "Internal Server Error",
            "message": (
                "The server returned an unexpected response "
                f"(Status: {response.status_code})."
            ),
        }

    @staticmethod
    def _unexpected(
        response: httpx.Response,
        message: str,
    ) -> UnexpectedResponseError:
        return UnexpectedResponseError(message, status_code=response.status_code)
