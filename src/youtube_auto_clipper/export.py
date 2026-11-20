"""Shared export targets for CLI, MCP, and review UI."""
LAYOUTS = ("portrait", "fit", "landscape")
RESOLUTIONS = {"720p": (720, 1280), "1080p": (1080, 1920)}
PRESETS = ("tiktok", "reels", "shorts")


def export_target(layout="portrait", resolution="1080p", preset=None):
    if layout not in LAYOUTS:
        raise ValueError(f"Layout must be one of {LAYOUTS}")
    requested_resolution = resolution
    if resolution == "auto":
        resolution = "1080p"
    if resolution not in RESOLUTIONS:
        raise ValueError(f"Resolution must be auto or one of {tuple(RESOLUTIONS)}")
    if preset is not None and preset not in PRESETS:
        raise ValueError(f"Preset must be one of {PRESETS}, or null for custom layout")
    # Platform shortcuts are deliberately vertical; never silently crop a fit layout.
    if preset and layout == "landscape":
        raise ValueError("Platform presets require portrait or fit layout; omit preset for landscape")
    width, height = RESOLUTIONS[resolution]
    if layout == "landscape":
        width, height = height, width
    return {"preset": preset, "resolution": resolution, "requested_resolution": requested_resolution, "width": width, "height": height,
            "aspect_ratio": "16:9" if layout == "landscape" else "9:16",
            "layout": layout, "video_codec": "h264", "pixel_format": "yuv420p", "audio_codec": "aac"}
