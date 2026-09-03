from __future__ import annotations

import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx

from html_css_to_image import (
    ApiErrorResponse,
    CreateHtmlCssImageRequest,
    CreateTemplatedImageRequest,
    CreateUrlImageRequest,
    DeleteImageSuccessResponse,
    HtmlCssToImageClient,
    PDFMargins,
    PDFOptions,
    PDFValueWithUnits,
    RenderImageAspectRatio,
    RenderImageCrop,
    RenderImageCropPosition,
    RenderImageCropSize,
    RenderImageCropSpan,
    RenderImageOptions,
    UnexpectedResponseError,
    __version__,
)


class HtmlCssToImageClientTests(unittest.TestCase):
    api_id = "user_id"
    api_key = "api_key"

    def make_client(self, handler):
        transport = httpx.MockTransport(handler)
        http_client = httpx.Client(transport=transport)
        self.addCleanup(http_client.close)
        return HtmlCssToImageClient(
            self.api_id,
            self.api_key,
            http_client=http_client,
        )

    def test_create_image_maps_html_css_fonts_pdf_and_auth(self):
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url, "https://hcti.io/v1/image")
            self.assertEqual(
                request.headers["Authorization"],
                "Basic dXNlcl9pZDphcGlfa2V5",
            )
            self.assertEqual(
                request.headers["User-Agent"],
                f"HCTIPython/{__version__}",
            )
            payload = __import__("json").loads(request.content)
            self.assertEqual(payload["html"], "<h1>Test</h1>")
            self.assertEqual(payload["google_fonts"], "Roboto|Open+Sans")
            self.assertEqual(payload["format"], "webp")
            self.assertEqual(
                payload["pdf_options"]["margins"],
                ["10px", "20px", "5mm", "20in"],
            )
            return httpx.Response(
                200,
                json={"id": "123", "url": "https://hcti.io/v1/image/123"},
            )

        client = self.make_client(handler)
        result = client.create_image(
            CreateHtmlCssImageRequest(
                html="<h1>Test</h1>",
                format="webp",
                google_fonts=["Roboto", "Open Sans", "Open Sans"],
                pdf_options=PDFOptions(
                    margins=PDFMargins(
                        top=10,
                        right=20,
                        bottom=PDFValueWithUnits(5, "mm"),
                        left=PDFValueWithUnits(20, "in"),
                    )
                ),
            )
        )

        self.assertTrue(result.success)
        if result.success:
            self.assertEqual(result.id, "123")

    def test_create_image_maps_template_without_internal_fields(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = __import__("json").loads(request.content)
            self.assertEqual(
                payload,
                {
                    "template_id": "template-id",
                    "template_values": {"title": "Hello"},
                    "format": "pdf",
                },
            )
            return httpx.Response(200, json={"id": "123", "url": "image-url"})

        client = self.make_client(handler)
        result = client.create_image(
            CreateTemplatedImageRequest(
                template_id="template-id",
                template_values={"title": "Hello"},
                format="pdf",
            )
        )
        self.assertTrue(result.success)

    def test_create_image_maps_url_css_and_false_values(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = __import__("json").loads(request.content)
            self.assertEqual(payload["url"], "https://example.com")
            self.assertEqual(payload["css"], "body { background: black; }")
            self.assertFalse(payload["full_screen"])
            return httpx.Response(200, json={"id": "123", "url": "image-url"})

        client = self.make_client(handler)
        result = client.create_image(
            CreateUrlImageRequest(
                url="https://example.com",
                css="body { background: black; }",
                full_screen=False,
            )
        )
        self.assertTrue(result.success)

    def test_create_image_maps_new_render_and_header_options(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(payload["dedupe_duration_s"], 300)
            self.assertEqual(payload["storage_destination_id"], "storage-1")
            self.assertFalse(payload["transparent_background"])
            self.assertEqual(
                payload["headers"],
                {"Authorization": "Bearer secret", "X-Card": "42"},
            )
            self.assertEqual(
                payload["additional_header_origins"],
                ["https://assets.example.com"],
            )
            self.assertTrue(payload["include_headers_on_subrequests"])
            self.assertTrue(payload["identify_as_hcti"])
            return httpx.Response(200, json={"id": "123", "url": "image-url"})

        client = self.make_client(handler)
        result = client.create_image(
            CreateUrlImageRequest(
                url="https://example.com/private",
                headers={
                    "Authorization": "Bearer secret",
                    "X-Card": "42",
                },
                additional_header_origins=["https://assets.example.com"],
                include_headers_on_subrequests=True,
                identify_as_hcti=True,
                dedupe_duration_s=300,
                storage_destination_id="storage-1",
                transparent_background=False,
            )
        )
        self.assertTrue(result.success)

    def test_batch_omits_empty_inherited_content(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = __import__("json").loads(request.content)
            self.assertEqual(request.url, "https://hcti.io/v1/image/batch")
            self.assertNotIn("html", payload["variations"][1])
            self.assertEqual(payload["variations"][1]["format"], "jpg")
            self.assertEqual(
                payload["default_options"]["html"],
                "<h1>BASE</h1>",
            )
            self.assertEqual(payload["default_options"]["format"], "webp")
            return httpx.Response(
                200,
                json={
                    "images": [
                        {"id": "1", "url": "u1"},
                        {"id": "2", "url": "u2"},
                    ]
                },
            )

        client = self.make_client(handler)
        result = client.create_image_batch(
            [
                CreateHtmlCssImageRequest(html="<h1>V1</h1>"),
                CreateHtmlCssImageRequest(viewport_width=600, format="jpg"),
            ],
            CreateHtmlCssImageRequest(
                html="<h1>BASE</h1>",
                viewport_width=1280,
                format="webp",
            ),
        )
        self.assertTrue(result.success)
        if result.success:
            self.assertEqual(len(result.images), 2)

    def test_batch_omits_post_only_dedupe_option(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertNotIn("dedupe_duration_s", payload["variations"][0])
            self.assertNotIn("dedupe_duration_s", payload["default_options"])
            self.assertTrue(payload["variations"][0]["transparent_background"])
            return httpx.Response(200, json={"images": []})

        client = self.make_client(handler)
        result = client.create_image_batch(
            [
                CreateHtmlCssImageRequest(
                    html="<h1>V1</h1>",
                    dedupe_duration_s=300,
                    transparent_background=True,
                )
            ],
            CreateHtmlCssImageRequest(
                html="<h1>BASE</h1>",
                dedupe_duration_s=300,
            ),
        )
        self.assertTrue(result.success)

    def test_empty_batch_does_not_send_request(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            self.fail("An empty batch must not send an HTTP request")

        client = self.make_client(handler)
        result = client.create_image_batch([])
        self.assertTrue(result.success)
        if result.success:
            self.assertEqual(result.images, ())

    def test_batch_without_defaults_omits_default_options(self):
        def handler(request: httpx.Request) -> httpx.Response:
            payload = __import__("json").loads(request.content)
            self.assertNotIn("default_options", payload)
            return httpx.Response(200, json={"images": []})

        client = self.make_client(handler)
        result = client.create_image_batch(
            [CreateHtmlCssImageRequest(html="<h1>Only</h1>")]
        )
        self.assertTrue(result.success)

    def test_templated_url_uses_whatwg_encoding_and_valid_hmac(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)
        url = client.generate_templated_image_url_from_values(
            "my-template",
            {
                "title": "Hello world~*",
                "data": {"enabled": True},
                "ignored": None,
            },
            2,
        )
        parsed = urlparse(url)
        query = parsed.query
        token = parsed.path.rsplit("/", 1)[-1]

        self.assertIn(
            "title=Hello+world%7E*",
            query,
        )
        self.assertEqual(
            token,
            hmac.new(
                self.api_key.encode(),
                query.encode(),
                hashlib.sha256,
            ).hexdigest(),
        )

    def test_create_and_render_url_matches_typescript_boolean_behavior(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)
        url = client.generate_create_and_render_url(
            CreateUrlImageRequest(
                url="https://example.com/a path",
                css="body { color: red; }",
                full_screen=True,
                block_consent_banners=False,
                pdf_options=PDFOptions(print_background=True),
                format="pdf",
            )
        )
        parsed = urlparse(url)
        values = parse_qs(parsed.query)

        self.assertEqual(values["url"], ["https://example.com/a path"])
        self.assertEqual(values["full_screen"], ["true"])
        self.assertNotIn("block_consent_banners", values)
        self.assertNotIn("pdf_options", values)
        self.assertNotIn("format", values)
        self.assertTrue(parsed.path.endswith("/pdf"))

    def test_create_and_render_supports_headers_transparency_and_render_options(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)
        url = client.generate_create_and_render_url(
            CreateUrlImageRequest(
                url="https://example.com/private",
                headers={"Authorization": "Bearer secret", "X-Test": "yes"},
                additional_header_origins=[
                    "https://assets.example.com",
                    "https://fonts.example.com",
                ],
                include_headers_on_subrequests=True,
                identify_as_hcti=True,
                transparent_background=False,
                dedupe_duration_s=300,
                format="pdf",
            ),
            RenderImageOptions(format="webp", width=1200, height=630),
        )
        parsed = urlparse(url)
        values = parse_qs(parsed.query)
        token = parsed.path.split("/")[-2]

        self.assertEqual(
            values["headers"],
            ["Authorization:Bearer secret", "X-Test:yes"],
        )
        self.assertEqual(
            values["additional_header_origins"],
            ["https://assets.example.com", "https://fonts.example.com"],
        )
        self.assertEqual(values["transparent_background"], ["false"])
        self.assertEqual(values["width"], ["1200"])
        self.assertEqual(values["height"], ["630"])
        self.assertNotIn("dedupe_duration_s", values)
        self.assertTrue(parsed.path.endswith("/webp"))
        self.assertEqual(
            token,
            hmac.new(
                self.api_key.encode(),
                parsed.query.encode(),
                hashlib.sha256,
            ).hexdigest(),
        )

    def test_image_url_supports_resize_dpi_and_crop(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)
        crop = RenderImageCrop.aspect_ratio_from_width(
            RenderImageAspectRatio(16, 9),
            RenderImageCropSpan.between(
                RenderImageCropPosition.percent(10),
                RenderImageCropPosition.percent(90),
            ),
            height_origin="center",
        )

        url = client.image_url(
            "folder/image id",
            RenderImageOptions(
                format="jpg",
                dpi=96,
                width=600,
                crop=crop,
            ),
        )

        self.assertEqual(
            url,
            "https://hcti.io/v1/image/folder%2Fimage%20id.jpg?"
            "dpi=96&width=600&aspect_ratio=16_9&y_origin=center&"
            "x_1=10%25&x_2=90%25",
        )

    def test_pdf_render_format_is_supported(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)

        self.assertEqual(
            client.image_url("image-id", RenderImageOptions(format="pdf")),
            "https://hcti.io/v1/image/image-id.pdf",
        )

    def test_template_request_format_controls_signed_url(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)

        url = client.generate_templated_image_url(
            CreateTemplatedImageRequest(
                template_id="template-id",
                template_values={"title": "Hello"},
                format="pdf",
            )
        )

        self.assertTrue(urlparse(url).path.endswith("/pdf"))

    def test_template_render_options_avoid_template_value_collisions(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)
        url = client.generate_templated_image_url_from_values(
            "template-id",
            {
                "width": "template width",
                "crop_width": "template long crop",
                "crop_w": "template short crop",
            },
            render_options=RenderImageOptions(
                format="png",
                width=1200,
                crop=RenderImageCrop.rectangle(
                    horizontal=RenderImageCropSpan.sized(
                        RenderImageCropSize.pixels(100),
                        "end",
                    )
                ),
            ),
        )
        parsed = urlparse(url)
        values = parse_qs(parsed.query)

        self.assertEqual(values["width"], ["template width"])
        self.assertEqual(values["__ro_width"], ["1200"])
        self.assertEqual(values["__ro_crop_width"], ["100px"])
        self.assertEqual(values["__ro_crop_w"], ["100px"])
        self.assertEqual(values["x_origin"], ["end"])
        self.assertTrue(parsed.path.endswith("/png"))

    def test_render_options_validate_ranges(self):
        with self.assertRaisesRegex(ValueError, "DPI"):
            RenderImageOptions(dpi=30)
        with self.assertRaisesRegex(ValueError, "width"):
            RenderImageOptions(width=5001)
        with self.assertRaisesRegex(ValueError, "greater than"):
            RenderImageCropSpan.between(
                RenderImageCropPosition.pixels(20),
                RenderImageCropPosition.pixels(10),
            )

    def test_string_collection_fields_reject_plain_strings(self):
        with self.assertRaisesRegex(TypeError, "google_fonts"):
            CreateHtmlCssImageRequest(html="<h1>Test</h1>", google_fonts="Roboto")

        with self.assertRaisesRegex(TypeError, "additional_header_origins"):
            CreateUrlImageRequest(
                url="https://example.com",
                additional_header_origins="https://assets.example.com",
            )

    def test_delete_batch_rejects_a_plain_string(self):
        client = HtmlCssToImageClient(self.api_id, self.api_key)
        self.addCleanup(client.close)

        with self.assertRaisesRegex(TypeError, "image_ids"):
            client.delete_image_batch("image-id")

    def test_delete_image_and_batch(self):
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(204)

        client = self.make_client(handler)
        single = client.delete_image("folder/image id")
        batch = client.delete_image_batch(["one", "two"])

        self.assertIsInstance(single, DeleteImageSuccessResponse)
        self.assertTrue(batch.success)
        self.assertEqual(requests[0].method, "DELETE")
        self.assertEqual(
            str(requests[0].url),
            "https://hcti.io/v1/image/folder%2Fimage%20id",
        )
        self.assertEqual(requests[0].headers["User-Agent"], f"HCTIPython/{__version__}")
        self.assertEqual(
            requests[1].headers["User-Agent"],
            requests[0].headers["User-Agent"],
        )
        self.assertEqual(json.loads(requests[1].content), {"ids": ["one", "two"]})

    def test_delete_error_is_typed(self):
        client = self.make_client(
            lambda _request: httpx.Response(
                404,
                json={"error": "Not Found", "message": "No image"},
            )
        )
        result = client.delete_image("missing")

        self.assertFalse(result.success)
        if not result.success:
            self.assertEqual(result.error, "Not Found")
            self.assertEqual(result.status_code, 404)

    def test_validation_error_is_typed(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={
                    "error": "Validation Failed",
                    "message": "Invalid input",
                    "validation_errors": [{"path": "html", "message": "is required"}],
                },
            )

        client = self.make_client(handler)
        result = client.create_image(CreateHtmlCssImageRequest())
        self.assertIsInstance(result, ApiErrorResponse)
        self.assertFalse(result.success)
        if not result.success:
            self.assertEqual(result.error, "Validation Failed")
            self.assertEqual(result.status_code, 400)
            self.assertEqual(result.validation_errors[0].path, "html")

    def test_non_json_error_has_fallback_details(self):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="<html>edge error</html>")

        client = self.make_client(handler)
        result = client.create_image(CreateUrlImageRequest(url="https://example.com"))
        self.assertFalse(result.success)
        if not result.success:
            self.assertEqual(result.error, "Internal Server Error")
            self.assertEqual(result.status_code, 500)
            self.assertIn("Status: 500", result.message)

    def test_non_json_success_raises_unexpected_response(self):
        client = self.make_client(
            lambda _request: httpx.Response(200, text="<html>unexpected</html>")
        )

        with self.assertRaises(UnexpectedResponseError) as raised:
            client.create_image(CreateHtmlCssImageRequest(html="<h1>Test</h1>"))

        self.assertEqual(raised.exception.status_code, 200)
        self.assertIn("not valid JSON", str(raised.exception))

    def test_incomplete_image_success_raises_unexpected_response(self):
        client = self.make_client(
            lambda _request: httpx.Response(200, json={"id": "image-id"})
        )

        with self.assertRaisesRegex(UnexpectedResponseError, "non-empty string url"):
            client.create_image(CreateUrlImageRequest(url="https://example.com"))

    def test_malformed_batch_success_raises_unexpected_response(self):
        client = self.make_client(
            lambda _request: httpx.Response(
                200,
                json={"images": [{"id": "one", "url": "u1"}, None]},
            )
        )

        with self.assertRaisesRegex(UnexpectedResponseError, "index 1"):
            client.create_image_batch(
                [CreateHtmlCssImageRequest(html="<h1>Test</h1>")]
            )

    def test_from_env(self):
        transport = httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"id": "1", "url": "u1"},
            )
        )
        http_client = httpx.Client(transport=transport)
        self.addCleanup(http_client.close)
        with patch.dict(
            os.environ,
            {"HCTI_API_ID": "env-id", "HCTI_API_KEY": "env-key"},
            clear=True,
        ):
            client = HtmlCssToImageClient.from_env(http_client=http_client)
            result = client.create_image(CreateHtmlCssImageRequest(html="ok"))
        self.assertTrue(result.success)

    def test_from_env_requires_both_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "HCTI_API_ID"):
                HtmlCssToImageClient.from_env()


if __name__ == "__main__":
    unittest.main()
