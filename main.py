"""
Entry point aplikasi FastAPI — backend prediksi harga cabai.

File ini hanya berisi inisialisasi minimal.
Seluruh konfigurasi dan logika ada di modul app/.

Cara menjalankan:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app import create_app

app = create_app()


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Documentation"
    )

    content = html.body.decode()

    custom_css = """
    <style>

    /* 1. Paksa background putih untuk Curl box, Request URL, dan Response body pre.microlight */
    .swagger-ui .opblock-body pre.microlight,
    .swagger-ui .opblock-body pre,
    .swagger-ui .highlight-code,
    .swagger-ui .highlight-code pre,
    .swagger-ui .microlight,
    .swagger-ui textarea.curl,
    .swagger-ui .curl-command,
    .swagger-ui .curl-command pre,
    .swagger-ui .request-url,
    .swagger-ui .request-url pre,
    .swagger-ui .responses-inner,
    .swagger-ui .responses-table,
    .swagger-ui .response-col_description,
    .swagger-ui .model-box,
    .swagger-ui .example-snippet pre {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* 2. Base text color dalam blok kode */
    .swagger-ui .opblock-body pre.microlight *,
    .swagger-ui .opblock-body pre *,
    .swagger-ui .highlight-code *,
    .swagger-ui .microlight *,
    .swagger-ui .request-url *,
    .swagger-ui .curl-command * {
        color: #000000 !important;
    }

    /* 3. Highlighting khusus JSON (Key, String, Number, Boolean) */
    /* JSON Key (misal: "status", "provinsi", "durasi") */
    .swagger-ui .opblock-body pre.microlight .hljs-attr,
    .swagger-ui .opblock-body pre.microlight .attr,
    .swagger-ui .highlight-code .hljs-attr,
    .swagger-ui .microlight .hljs-attr,
    .swagger-ui .highlight-code .key,
    .swagger-ui pre .key {
        color: #005cc5 !important;
    }

    /* JSON String (misal: "success", "DKI Jakarta") */
    .swagger-ui .opblock-body pre.microlight .hljs-string,
    .swagger-ui .opblock-body pre.microlight .string,
    .swagger-ui .highlight-code .hljs-string,
    .swagger-ui .microlight .hljs-string,
    .swagger-ui .highlight-code .str,
    .swagger-ui pre .str {
        color: #22863a !important;
    }

    /* JSON Number (misal: 7, 55400, 55688) */
    .swagger-ui .opblock-body pre.microlight .hljs-number,
    .swagger-ui .opblock-body pre.microlight .number,
    .swagger-ui .highlight-code .hljs-number,
    .swagger-ui .microlight .hljs-number,
    .swagger-ui pre .number {
        color: #d73a49 !important;
    }

    /* JSON Keyword / Boolean / Literal */
    .swagger-ui .opblock-body pre.microlight .hljs-keyword,
    .swagger-ui .opblock-body pre.microlight .hljs-literal,
    .swagger-ui .highlight-code .hljs-keyword,
    .swagger-ui .microlight .hljs-keyword {
        color: #d73a49 !important;
    }

    /* 4. Overrides untuk Dark Mode OS/Browser */
    @media (prefers-color-scheme: dark) {
        html, body, .swagger-ui,
        .swagger-ui .opblock-body pre.microlight,
        .swagger-ui .opblock-body pre,
        .swagger-ui .highlight-code,
        .swagger-ui .highlight-code pre,
        .swagger-ui .microlight,
        .swagger-ui textarea.curl,
        .swagger-ui .curl-command,
        .swagger-ui .request-url,
        .swagger-ui .request-url pre {
            background: #ffffff !important;
            background-color: #ffffff !important;
            color: #000000 !important;
        }
    }

    </style>
    """

    if "</head>" in content:
        content = content.replace("</head>", f"{custom_css}\n</head>")
    elif "</body>" in content:
        content = content.replace("</body>", f"{custom_css}\n</body>")
    else:
        content += custom_css

    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )