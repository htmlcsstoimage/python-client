"""Installed package version used by public metadata and HTTP requests."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("html-css-to-image")
except PackageNotFoundError:
    __version__ = "0+unknown"
