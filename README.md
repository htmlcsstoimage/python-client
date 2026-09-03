# HTML/CSS to Image Python Client

The official Python client for the [HTML/CSS to Image API](https://htmlcsstoimage.com). It provides typed request and response models, signed URL helpers, and an injectable HTTPX transport.

This README documents how the client behaves. The central [API documentation](https://docs.htmlcsstoimage.com) is the source of truth for rendering features, parameter meanings, supported values, plan availability, and API limits. See the [parameter reference](https://docs.htmlcsstoimage.com/parameters/) when configuring a request.

## Installation

```bash
pip install html-css-to-image
```

Python 3.10 or newer is required.

## Quick start

```python
from html_css_to_image import (
    CreateHtmlCssImageRequest,
    HtmlCssToImageClient,
)

with HtmlCssToImageClient("your-api-id", "your-api-key") as client:
    result = client.create_image(
        CreateHtmlCssImageRequest(
            html="<h1>Hello, world!</h1>",
            css="h1 { color: royalblue; }",
        )
    )

if result.success:
    print(result.id, result.url)
else:
    print(result.status_code, result.error, result.message)
```

Credentials are available in the [HCTI dashboard](https://htmlcsstoimage.com/dashboard). Keep the API key on a trusted server; never embed it in browser, desktop, or mobile application code.

### Environment credentials

Set `HCTI_API_ID` and `HCTI_API_KEY`, then use:

```python
client = HtmlCssToImageClient.from_env()
```

`from_env()` raises `ValueError` when either variable is missing.

## Requests and responses

Request fields use the API's `snake_case` names and are available as typed keyword arguments. `None` fields are omitted from JSON payloads; an explicit `False` is preserved for normal POST requests. Collection fields such as `google_fonts` and `additional_header_origins` accept lists or tuples of strings and reject a plain string rather than treating it as a sequence of characters.

| Request class | Use |
| --- | --- |
| `CreateHtmlCssImageRequest` | Create an image from HTML and CSS. |
| `CreateUrlImageRequest` | Capture a URL. |
| `CreateTemplatedImageRequest` | Render a saved template with values. |

All supported fields are documented by type hints and class docstrings. Their API behavior is documented in the [parameter reference](https://docs.htmlcsstoimage.com/parameters/), [URL screenshot guide](https://docs.htmlcsstoimage.com/getting-started/url-to-image/), and [template guide](https://docs.htmlcsstoimage.com/getting-started/templates/).

```python
from html_css_to_image import (
    CreateTemplatedImageRequest,
    CreateUrlImageRequest,
)

url_result = client.create_image(
    CreateUrlImageRequest(
        url="https://example.com",
        viewport_width=1200,
        viewport_height=630,
        transparent_background=True,
        format="webp",
    )
)

template_result = client.create_image(
    CreateTemplatedImageRequest(
        template_id="your-template-id",
        template_version=3,
        template_values={"title": "Hello from Python"},
    )
)
```

`create_image()` returns either `CreateImageSuccessResponse` or `ApiErrorResponse`, discriminated by `result.success`. API errors include the HTTP `status_code`. HTTP transport failures are raised by HTTPX rather than converted into API responses, while malformed successful responses raise `UnexpectedResponseError` instead of producing an incomplete success object.

### Batch requests

```python
result = client.create_image_batch(
    variations=[
        CreateHtmlCssImageRequest(css="h1 { color: crimson; }"),
        CreateHtmlCssImageRequest(css="h1 { color: royalblue; }"),
    ],
    default_options=CreateHtmlCssImageRequest(
        html="<h1>Shared HTML</h1>",
        viewport_width=600,
        viewport_height=315,
    ),
)
```

Only HTML/CSS and URL requests can be batched. Empty `html` or `url` values in variations are omitted so they can inherit from `default_options`. An empty variation list returns a successful empty result without sending an HTTP request. Options unsupported by the batch API, such as `dedupe_duration_s`, are not serialized. See the [batch API documentation](https://docs.htmlcsstoimage.com/getting-started/using-the-api/#batch-image-creation).

## Signed URLs

The signed URL helpers perform no network request. They create the exact query string, sign it with HMAC-SHA256 using the API key, and return a URL that can be shared without exposing that key.

```python
template_url = client.generate_templated_image_url_from_values(
    "your-template-id",
    {"title": "Rendered on demand"},
    template_version=2,
)

render_url = client.generate_create_and_render_url(
    CreateUrlImageRequest(
        url="https://example.com/card/42",
        viewport_width=1200,
        viewport_height=630,
    )
)
```

Use `generate_templated_image_url()` with a complete `CreateTemplatedImageRequest`, or `generate_templated_image_url_from_values()` when starting with separate values. Both methods accept `render_options`.

```python
from html_css_to_image import CreateTemplatedImageRequest, RenderImageOptions

options = RenderImageOptions(format="webp", width=1200, height=630)

template_url = client.generate_templated_image_url(
    CreateTemplatedImageRequest(
        template_id="your-template-id",
        template_values={"title": "Rendered on demand"},
    ),
    render_options=options,
)
```

Client behavior worth knowing:

- Render options are added before signing, so the signature covers the final query string.
- Template fields that collide with render-option query names are assigned the API's reserved `__ro_` names automatically.
- PDF layout options and deduplication options are omitted from create-and-render URLs because that endpoint does not support them.
- Custom URL headers become visible query parameters in a signed URL. Do not put secrets in them.

See the [signed URL documentation](https://docs.htmlcsstoimage.com/getting-started/create-and-render/) for endpoint behavior and security considerations.

## Image URLs and render options

`format` accepts `"png"`, `"jpg"`, `"webp"`, or `"pdf"` on creation requests and render options. `image_url()` builds a URL for an existing image without making a request:

```python
url = client.image_url(
    "image-id",
    RenderImageOptions(format="jpg", dpi=96, width=1200),
)
```

Cropping uses immutable value objects and explicit factory methods:

```python
from html_css_to_image import (
    RenderImageCrop,
    RenderImageCropPosition,
    RenderImageCropSpan,
)

crop = RenderImageCrop.rectangle(
    horizontal=RenderImageCropSpan.between(
        RenderImageCropPosition.percent(10),
        RenderImageCropPosition.percent(90),
    )
)

url = client.image_url("image-id", RenderImageOptions(crop=crop))
```

The crop factories validate their inputs before generating a URL. Refer to the [image URL and cropping documentation](https://docs.htmlcsstoimage.com/getting-started/using-the-api/#cropping-parameters) for transformation semantics and limits.

## Deleting images

```python
single = client.delete_image("image-id")
batch = client.delete_image_batch(["image-id-1", "image-id-2"])
```

Every successful `2xx` response maps to `DeleteImageSuccessResponse`. API errors use `ApiErrorResponse`, while network failures remain HTTPX exceptions.

## HTTP configuration

The default transport is a persistent `httpx.Client` with a 30-second timeout and no automatic retries. Inject a client to configure timeouts, retries, proxies, certificates, connection limits, or test transports:

```python
import httpx

http_client = httpx.Client(
    transport=httpx.HTTPTransport(retries=2),
    timeout=httpx.Timeout(90),
)

client = HtmlCssToImageClient(
    "your-api-id",
    "your-api-key",
    http_client=http_client,
)
```

An injected HTTP client remains caller-owned and is never closed or reconfigured by this package. Every API request includes `HCTIPython/<version>` as its `User-Agent`, including requests sent through an injected client. When the SDK creates the HTTP client, call `close()` or use `HtmlCssToImageClient` as a context manager.

Retry policy intentionally belongs to the application. HTTPX transport retries cover connection failures; status-code retries and backoff can be implemented around the injected transport or client call.

## Error handling

```python
import httpx

from html_css_to_image import UnexpectedResponseError

try:
    result = client.create_image(request)
except httpx.TimeoutException:
    # Apply application-specific policy.
    ...
except httpx.NetworkError:
    ...
except UnexpectedResponseError as error:
    # A 2xx response did not match the documented API shape.
    print(error.status_code, error)
else:
    if not result.success:
        print(result.status_code, result.error, result.message)
        for error in result.validation_errors or ():
            print(error.path, error.message)
```

## Client API

| Method | Returns | Interaction |
| --- | --- | --- |
| `from_env(...)` | `HtmlCssToImageClient` | Reads credentials from the environment. |
| `create_image(request)` | `CreateImageResponse` | Sends `POST /v1/image`. |
| `create_image_batch(variations, default_options=None)` | `CreateImageBatchResponse` | Sends `POST /v1/image/batch`, unless the list is empty. |
| `delete_image(image_id)` | `DeleteImageResponse` | Sends `DELETE /v1/image/{id}`. |
| `delete_image_batch(image_ids)` | `DeleteImageResponse` | Sends `DELETE /v1/image/batch`. |
| `image_url(image_id, render_options=None)` | `str` | Builds an existing-image URL locally. |
| `generate_templated_image_url(request, render_options=None)` | `str` | Builds and signs a template URL from a request locally. |
| `generate_templated_image_url_from_values(...)` | `str` | Builds and signs a template URL from separate values locally. |
| `generate_create_and_render_url(...)` | `str` | Builds and signs a URL screenshot locally. |
| `close()` | `None` | Closes only an SDK-owned HTTP client. |

The package exports typed request, response, PDF, and render/crop models from `html_css_to_image`. Public classes, constructor parameters, attributes, and methods include docstrings for IDE help and generated API documentation.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
mypy
python -m unittest discover -s tests
python -m build
```

## License

MIT
