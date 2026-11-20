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
    args = parser.parse_args()
    if args.discover:
        from .discovery import discover_candidates
        if args.candidate_plan or args.select:
            parser.error("Discovery cannot be combined with candidate selection")
        result = discover_candidates(args.source, args.output, args.count,
                                    args.min_duration, args.max_duration, args.mode,
                                    args.goal, not args.offline, args.model,
                                    not args.no_media_analysis)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(json.dumps(process(args.source, args.output, args.count, args.min_duration,
                             args.max_duration, args.allow_download, args.model,
                             not args.offline, not args.no_face_tracking,
                             args.candidate_plan, args.select), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
