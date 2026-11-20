"""Backward-compatible launcher; prefer the installed youtube-clipper-mcp command."""
from youtube_auto_clipper.mcp_server import main


if __name__ == "__main__":
    main()
