#!/usr/bin/env python3
"""Convert a Keras model (.keras or .h5) to a TFLite model.

Usage:
    python tools/convert_to_tflite.py \
        --input model/crop_rotation_model.keras \
        --output model/crop_rotation_model.tflite \
        [--quantize]

Notes:
- If you enable --quantize, the script uses `tf.lite.Optimize.DEFAULT`. Full integer
  quantization requires a representative dataset; this script does not provide one,
  so results may be float or dynamic-range quantized depending on TF version.
- Run this on a machine that has full TensorFlow installed (training machine), not
  on a Raspberry Pi unless you have TF there.
"""
from __future__ import annotations
import argparse
import os


def find_existing_model(path: str) -> str | None:
    """Return existing path among a set of common names, or None."""
    candidates = [path, os.path.splitext(path)[0] + ".keras", os.path.splitext(path)[0] + ".h5"]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def convert_to_tflite(keras_path: str, out_path: str, quantize: bool = False) -> None:
    import tensorflow as tf

    print(f"Loading Keras model from: {keras_path}")
    model = tf.keras.models.load_model(keras_path)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    if quantize:
        print("Enabling default optimizations for TFLite converter (may produce dynamic-range quantized model).")
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        # NOTE: full integer quantization requires a representative dataset function.

    tflite_model = converter.convert()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(tflite_model)
    print(f"Wrote TFLite model to: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Keras model to TFLite")
    parser.add_argument("--input", "-i", default="model/crop_rotation_model.keras", help="Input Keras model path (.keras or .h5)")
    parser.add_argument("--output", "-o", default="model/crop_rotation_model.tflite", help="Output TFLite path")
    parser.add_argument("--quantize", action="store_true", help="Enable default converter optimizations (may reduce size)")
    args = parser.parse_args()

    src = find_existing_model(args.input)
    if src is None:
        print("Could not find model at", args.input)
        return

    convert_to_tflite(src, args.output, args.quantize)


if __name__ == "__main__":
    main()
