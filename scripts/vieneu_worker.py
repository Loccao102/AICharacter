from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AICharacter VieNeu local TTS worker")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--backend", default="onnx")
    parser.add_argument("--ref-audio", default="")
    parser.add_argument("--ref-text-file", default="")
    parser.add_argument("--preset", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("TTS text is empty")

    from vieneu import Vieneu

    engine = Vieneu(backend=args.backend)
    try:
        kwargs = {}
        mode = "default"
        if args.ref_audio:
            if not args.ref_text_file:
                raise ValueError("ref-text-file is required when ref-audio is supplied")
            ref_text = Path(args.ref_text_file).read_text(encoding="utf-8").strip()
            if not ref_text:
                raise ValueError("Reference transcript is empty")
            kwargs = {
                "ref_audio": str(Path(args.ref_audio).resolve()),
                "ref_text": ref_text,
            }
            mode = "clone"
        elif args.preset:
            kwargs = {"voice": engine.get_preset_voice(args.preset)}
            mode = f"preset:{args.preset}"

        audio = engine.infer(text=text, **kwargs)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        engine.save(audio, output)
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": mode,
                    "output": str(output.resolve()),
                    "sample_rate": int(getattr(engine, "sample_rate", 48000)),
                    "samples": int(len(audio)),
                },
                ensure_ascii=False,
            )
        )
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
