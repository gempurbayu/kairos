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
    parser.add_argument("--discover", action="store_true", help="Preview candidates without rendering")
    parser.add_argument("--mode", choices=("auto", "conversation", "instruction", "gaming"), default="auto")
    parser.add_argument("--goal", default="", help="Editorial goal, such as useful tips or funny reactions")
    parser.add_argument("--no-media-analysis", action="store_true", help="Skip audio/frame preview sampling")
    parser.add_argument("--candidate-plan", help="Path to candidates.json from discovery")
    parser.add_argument("--select", nargs="+", help="Candidate IDs to render from the plan")
    parser.add_argument("--review", action="store_true", help="Open a local review page for --candidate-plan")
    parser.add_argument("--port", type=int, default=0, help="Local review port; 0 chooses a free port")
    parser.add_argument("--layout", choices=("portrait", "fit", "landscape"), default=None)
    parser.add_argument("--preset", choices=("tiktok", "reels", "shorts"), help="Vertical platform export target")
    parser.add_argument("--resolution", choices=("auto", "720p", "1080p"), default="auto", help="Output quality; auto uses 1080p")
    args = parser.parse_args()
    if args.review:
        if not args.candidate_plan or args.discover or args.select:
            parser.error("Review requires --candidate-plan and cannot combine with --discover or --select")
        from .review import serve_review
        serve_review(args.source, args.candidate_plan, port=args.port,
                     resolution=args.resolution, preset=args.preset, layout=args.layout)
        return
    if args.discover:
        from .discovery import discover_candidates
        if args.candidate_plan or args.select:
            parser.error("Discovery cannot be combined with candidate selection")
        result = discover_candidates(args.source, args.output, args.count,
                                    args.min_duration, args.max_duration, args.mode,
                                    args.goal, not args.offline, args.model,
                                    not args.no_media_analysis, args.allow_download)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(json.dumps(process(args.source, args.output, args.count, args.min_duration,
                             args.max_duration, args.allow_download, args.model,
                             not args.offline, not args.no_face_tracking,
                             args.candidate_plan, args.select, args.layout or "portrait",
                             args.resolution, args.preset), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
