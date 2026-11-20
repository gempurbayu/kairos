import argparse
import json
from .pipeline import process


def main():
    parser = argparse.ArgumentParser(description="Turn authorized videos into portrait short clips")
    parser.add_argument("source", help="Local video path or YouTube URL")
    parser.add_argument("--output", default="output")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--min-duration", type=float, default=20)
    parser.add_argument("--max-duration", type=float, default=60)
    parser.add_argument("--model", default=None, help="faster-whisper model, e.g. base or small")
    parser.add_argument("--allow-download", action="store_true", help="Confirm rights to download YouTube video")
    parser.add_argument("--offline", action="store_true", help="Disable Gemini highlight selection")
    parser.add_argument("--no-face-tracking", action="store_true", help="Use a centered crop instead of face tracking")
    args = parser.parse_args()
    print(json.dumps(process(args.source, args.output, args.count, args.min_duration,
                             args.max_duration, args.allow_download, args.model,
                             not args.offline, not args.no_face_tracking), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
