from __future__ import annotations

import copy
import json
import unittest

import httpx

from html_css_to_image import (
    ApiErrorResponse,
    CoordinatesScrollTarget,
    CreateHtmlCssRecordingRequest,
    CreateRecordingSuccessResponse,
    CreateUrlRecordingRequest,
    HtmlCssToImageClient,
    PositionScrollTarget,
    RecordingClickAction,
    RecordingElementVisibleTrigger,
    RecordingErrorAction,
    RecordingExecuteJavaScriptAction,
    RecordingFunctionCallTrigger,
    RecordingImmediateTrigger,
    RecordingLocateSelectorAction,
    RecordingOutputOptions,
    RecordingScrollAction,
    RecordingSimpleScrollAction,
    RecordingStallAction,
    RequestOverride,
    RequestOverrideResourceType,
    ScrollStep,
    SelectorScrollTarget,
    UnexpectedResponseError,
)

CREATED = {
    "id": "recording-id",
    "status_url": "https://hcti.io/v1/recordings/recording-id/status",
    "recording_url": "https://hcti.io/v1/recording/recording-id.mp4",
}


class RecordingTests(unittest.TestCase):
    def client(self, handler):
        http = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(http.close)
        return HtmlCssToImageClient("id", "key", http_client=http)

    def test_html_creation_maps_fonts_and_preserves_input(self):
        request = CreateHtmlCssRecordingRequest(
            html="<h1>Hello</h1>",
            duration_ms=1000,
            google_fonts=[" Roboto ", "Open Sans", "Open Sans"],
        )
        before = copy.deepcopy(request)

        def handler(req):
            self.assertEqual(req.method, "POST")
            self.assertEqual(req.url.path, "/v1/recording")
            self.assertEqual(req.headers["authorization"], "Basic aWQ6a2V5")
            self.assertEqual(req.headers["content-type"], "application/json")
            self.assertEqual(
                json.loads(req.content),
                {
                    "html": "<h1>Hello</h1>",
                    "duration_ms": 1000,
                    "google_fonts": "Roboto|Open+Sans",
                },
            )
            return httpx.Response(200, json=CREATED)

        result = self.client(handler).create_recording(request)
        self.assertIsInstance(result, CreateRecordingSuccessResponse)
        self.assertEqual(result.id, "recording-id")
        self.assertEqual(result.recording_url, CREATED["recording_url"])
        self.assertEqual(result.status_url, CREATED["status_url"])
        self.assertEqual(request, before)

    def test_url_options_and_all_nested_action_types(self):
        request = CreateUrlRecordingRequest(
            url="https://example.com",
            duration_ms=5000,
            css="body { color: red; }",
            device_scale=2,
            viewport_width=1280,
            viewport_height=720,
            disable_twemoji=False,
            dedupe_duration_s=0,
            color_scheme="dark",
            timezone="America/New_York",
            viewport_mobile=False,
            viewport_landscape=True,
            viewport_touch=False,
            media_type="screen",
            proxy_id="proxy",
            storage_destination_id="store",
            headers={"Authorization": "Bearer test"},
            additional_header_origins=["https://assets.example.com"],
            include_headers_on_subrequests=False,
            identify_as_hcti=True,
            block_consent_banners=True,
            request_overrides=[
                RequestOverride(
                    resource_types=[RequestOverrideResourceType.SCRIPT],
                )
            ],
            trigger=RecordingElementVisibleTrigger(selector="#ready"),
            duration_mode="at_least",
            defer_render=False,
            skip_scroll_preload=True,
            output=RecordingOutputOptions(format="webm", fps=60, scale=0.5),
            actions=[
                RecordingLocateSelectorAction(
                    selector="#modal",
                    if_not_found=[],
                    if_found=[
                        RecordingClickAction(
                            selector="#close",
                            button="right",
                            count=2,
                            offset_x=0,
                            offset_y=-1,
                            delay_ms=0,
                            if_not_found=[RecordingErrorAction()],
                        )
                    ],
                ),
                RecordingExecuteJavaScriptAction(script="await Promise.resolve();"),
                RecordingExecuteJavaScriptAction(script="throw Error();", if_error=[]),
                RecordingScrollAction(
                    steps=[
                        ScrollStep(
                            to=PositionScrollTarget(position="bottom"), duration_ms=500
                        ),
                        ScrollStep(
                            to=CoordinatesScrollTarget(x=0, y=200),
                            duration_ms=800,
                            easing="ease_in_out_cubic",
                        ),
                        ScrollStep(
                            to=SelectorScrollTarget(
                                selector="#footer",
                                offset_y=-40,
                                if_not_found=[],
                            ),
                            duration_ms=750,
                        ),
                    ],
                    if_not_found=[RecordingStallAction(duration_ms=0)],
                ),
                RecordingSimpleScrollAction(scroll_distance="90vh"),
                RecordingSimpleScrollAction(scroll_distance=900),
            ],
        )
        before = copy.deepcopy(request)

        def handler(req):
            data = json.loads(req.content)
            for key, expected in {
                "viewport_width": 1280,
                "viewport_height": 720,
                "device_scale": 2,
                "dedupe_duration_s": 0,
                "disable_twemoji": False,
                "color_scheme": "dark",
                "timezone": "America/New_York",
                "viewport_mobile": False,
                "viewport_landscape": True,
                "viewport_touch": False,
                "media_type": "screen",
                "proxy_id": "proxy",
                "storage_destination_id": "store",
                "defer_render": False,
                "skip_scroll_preload": True,
                "duration_mode": "at_least",
                "headers": {"Authorization": "Bearer test"},
                "include_headers_on_subrequests": False,
                "identify_as_hcti": True,
                "block_consent_banners": True,
            }.items():
                self.assertEqual(data[key], expected)
            self.assertEqual(
                data["output"],
                {
                    "format": "webm",
                    "fps": 60,
                    "scale": 0.5,
                },
            )
            self.assertEqual(data["trigger"]["type"], "element_visible")
            self.assertEqual(
                data["request_overrides"],
                [
                    {
                        "action": "block",
                        "resource_types": ["script"],
                    }
                ],
            )
            actions = data["actions"]
            self.assertEqual(actions[0]["if_not_found"], [])
            self.assertEqual(actions[0]["if_found"][0]["type"], "click")
            self.assertEqual(
                actions[0]["if_found"][0]["if_not_found"],
                [
                    {
                        "type": "error",
                    }
                ],
            )
            self.assertNotIn("if_error", actions[1])
            self.assertEqual(actions[2]["if_error"], [])
            self.assertEqual(
                [step["to"]["type"] for step in actions[3]["steps"]],
                [
                    "position",
                    "coordinates",
                    "selector",
                ],
            )
            self.assertEqual(
                [step["duration_ms"] for step in actions[3]["steps"]], [500, 800, 750]
            )
            self.assertEqual(actions[4]["scroll_distance"], "90vh")
            self.assertEqual(actions[5]["scroll_distance"], 900)
            return httpx.Response(200, json=CREATED)

        self.assertTrue(self.client(handler).create_recording(request).success)
        self.assertEqual(request, before)

    def test_optional_settings_and_triggers_use_api_defaults(self):
        for trigger in [
            None,
            RecordingImmediateTrigger(),
            RecordingFunctionCallTrigger(timeout_ms=1000),
        ]:
            with self.subTest(trigger=trigger):

                def handler(req):
                    data = json.loads(req.content)
                    self.assertEqual(data["duration_ms"], 0)
                    self.assertNotIn("output", data)
                    if trigger is None:
                        self.assertNotIn("trigger", data)
                    else:
                        self.assertEqual(data["trigger"]["type"], trigger.type)
                    return httpx.Response(400, json={"error": "Bad Request"})

                result = self.client(handler).create_recording(
                    CreateHtmlCssRecordingRequest(
                        html="", duration_ms=0, trigger=trigger
                    ),
                )
                self.assertFalse(result.success)

    def test_status_accepts_200_and_202_and_preserves_attempt_error(self):
        for status in [
            "awaiting_render",
            "processing",
            "pending_retry",
            "ready",
            "failed",
            "cancelled",
        ]:
            with self.subTest(status=status):
                data = {
                    "id": "recording-id",
                    "recording_url": CREATED["recording_url"],
                    "status": status,
                    "status_entered_at": "2026-11-16T10:00:00Z",
                    "attempt_count": 2,
                    "stored_duration_ms": None,
                    "storage_destination_hcti_storage_disabled": None,
                    "error": {
                        "code": "action_error",
                        "message": "Missing element",
                        "occurred_at": "2026-11-16T09:59:00Z",
                        "retryable": True,
                        "action_path": "actions[1]",
                    },
                }

                def handler(req):
                    self.assertEqual(req.method, "GET")
                    self.assertEqual(req.url.path, "/v1/recordings/recording-id/status")
                    self.assertEqual(req.content, b"")
                    return httpx.Response(
                        202
                        if status in ("processing", "pending_retry", "awaiting_render")
                        else 200,
                        json=data,
                    )

                result = self.client(handler).fetch_recording_status("recording-id")
                self.assertTrue(result.success)
                self.assertEqual(result.status, status)
                self.assertEqual(result.attempt_count, 2)
                self.assertIsNone(result.stored_duration_ms)
                self.assertEqual(result.error.action_path, "actions[1]")
                self.assertTrue(result.error.retryable)

    def test_status_maps_unrecognized_value_to_unknown(self):
        data = {
            "id": "recording-id",
            "recording_url": CREATED["recording_url"],
            "status": "some_future_status",
            "status_entered_at": "2026-11-16T10:00:00Z",
            "attempt_count": 1,
        }

        result = self.client(
            lambda req: httpx.Response(202, json=data)
        ).fetch_recording_status("recording-id")
        self.assertTrue(result.success)
        self.assertEqual(result.status, "unknown")

    def test_scroll_step_requires_duration_ms(self):
        with self.assertRaises(TypeError):
            ScrollStep(to=PositionScrollTarget(position="bottom"))

    def test_deletes_accept_empty_success_bodies(self):
        calls = []

        def handler(req):
            self.assertEqual(req.method, "DELETE")
            self.assertEqual(req.headers["authorization"], "Basic aWQ6a2V5")
            calls.append((req.url.path, req.content))
            return httpx.Response(202)

        client = self.client(handler)
        self.assertTrue(client.delete_recording("recording-id").success)
        self.assertTrue(client.delete_recording_batch(("one", "two")).success)
        self.assertEqual(calls[0], ("/v1/recordings/recording-id", b""))
        self.assertEqual(json.loads(calls[1][1]), {"ids": ["one", "two"]})

    def test_empty_delete_batch_does_not_send_request(self):
        def handler(req):
            self.fail("An empty batch must not send an HTTP request")

        client = self.client(handler)
        self.assertTrue(client.delete_recording_batch([]).success)
        self.assertTrue(client.delete_recording_batch(()).success)

    def test_delete_batch_rejects_non_list_or_non_string_ids(self):
        def handler(req):
            self.fail("Invalid input must not send an HTTP request")

        client = self.client(handler)
        for recording_ids in ["recording-id", {"recording-id"}, ["one", 2]]:
            with self.subTest(recording_ids=recording_ids):
                with self.assertRaisesRegex(TypeError, "recording_ids"):
                    client.delete_recording_batch(recording_ids)

    def operations(self, client):
        return [
            lambda: client.create_recording(
                CreateUrlRecordingRequest(
                    url="https://example.com",
                    duration_ms=1000,
                )
            ),
            lambda: client.fetch_recording_status("recording-id"),
            lambda: client.delete_recording("recording-id"),
            lambda: client.delete_recording_batch(["recording-id"]),
        ]

    def test_all_methods_reuse_api_error_and_transport_contracts(self):
        for json_body in [
            {"error": "Forbidden", "message": "Missing permission"},
            None,
        ]:

            def handler(req):
                return (
                    httpx.Response(403, json=json_body)
                    if json_body
                    else httpx.Response(502, text="Unavailable")
                )

            for call in self.operations(self.client(handler)):
                result = call()
                self.assertIsInstance(result, ApiErrorResponse)
                self.assertFalse(result.success)
                self.assertEqual(result.status_code, 403 if json_body else 502)

        def failing(req):
            raise httpx.ReadTimeout("timeout", request=req)

        for call in self.operations(self.client(failing)):
            with self.assertRaises(httpx.ReadTimeout):
                call()

    def test_malformed_success_uses_existing_exception(self):
        client = self.client(lambda req: httpx.Response(200, json={}))
        with self.assertRaises(UnexpectedResponseError):
            client.create_recording(
                CreateUrlRecordingRequest(
                    url="https://example.com",
                    duration_ms=1000,
                )
            )
        with self.assertRaises(UnexpectedResponseError):
            client.fetch_recording_status("recording-id")
