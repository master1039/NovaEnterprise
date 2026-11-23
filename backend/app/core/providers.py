"""Shared provider errors kept independent of any optional SDK."""


class ProviderConfigurationError(RuntimeError):
    """A configured provider cannot be constructed safely."""
