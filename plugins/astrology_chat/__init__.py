# Plugin registration for the Outer Skies plugin system
# Use lazy import to avoid Django app registry issues
def get_plugin():
    from .plugin import AstrologyChatPlugin
    return AstrologyChatPlugin

Plugin = get_plugin 