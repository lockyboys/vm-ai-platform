import os

from web.document_demo_app import create_app


if __name__ == "__main__":
    create_app().run(
        host=os.getenv("SPS_DOCUMENT_DEMO_HOST", "127.0.0.1"),
        port=int(os.getenv("SPS_DOCUMENT_DEMO_PORT", "8010")),
        debug=False,
    )