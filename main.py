import os
import joblib
import numpy as np
import asyncio
import threading
from flask import Flask, request
from dotenv import load_dotenv
import importlib
import json
import re

# Prefer full TensorFlow when available. On Raspberry Pi it's common to use the
# lightweight `tflite_runtime` interpreter and avoid installing full TF. We try
# to detect supported backends and keep both options available.
TF_AVAILABLE = False
TFLITE_AVAILABLE = False
keras_load_model = None
tf = None
_TFLITE_CLASS = None
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model as keras_load_model
    TF_AVAILABLE = True
except Exception:
    # try the tflite runtime (common on ARM/Pi)
    try:
        from tflite_runtime.interpreter import Interpreter as _TFLITE_CLASS  # type: ignore
        TFLITE_AVAILABLE = True
    except Exception:
        # as a fallback, try to import the TFLite Interpreter from tensorflow if TF exists
        try:
            import tensorflow as tf
            from tensorflow.lite.python.interpreter import Interpreter as _TFLITE_CLASS  # type: ignore
            TFLITE_AVAILABLE = True
            TF_AVAILABLE = True
        except Exception:
            TFLITE_AVAILABLE = False

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from pyngrok import ngrok
import requests

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# Dashboard API settings (used by /status)
DASHBOARD_API_BASE = os.getenv("DASHBOARD_API_BASE", "http://127.0.0.1:8001")
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "dev-token")

# -----------------------------
# Flask app initialization
# -----------------------------
app = Flask(__name__)

# -----------------------------
# Load ANN model, scaler, and label encoder (with TFLite fallback)
# -----------------------------
MODEL_PATH = "model/crop_rotation_model.h5"
MODEL_KERAS_PATH = "model/crop_rotation_model.keras"
MODEL_TFLITE_PATH = "model/crop_rotation_model.tflite"
SCALER_PATH = "model/scaler.save"
LE_PATH = "model/label_encoder.save"

# Runtime objects (one of these will be set)
model = None
_tflite_interpreter = None
scaler = None
label_encoder = None

def _load_artifacts():
    """Attempt to load scaler, label encoder, and either a Keras model or TFLite model.

    Load order:
      1) Full Keras model (.keras or .h5) when TensorFlow is available
      2) TFLite model (.tflite) via tflite_runtime or TF Lite Interpreter
    """
    global model, _tflite_interpreter, scaler, label_encoder
    errors = []
    # Load scaler and label encoder (joblib)
    try:
        scaler = joblib.load(SCALER_PATH)
    except Exception as e:
        errors.append(f"scaler: {e}")
    try:
        label_encoder = joblib.load(LE_PATH)
    except Exception as e:
        errors.append(f"label_encoder: {e}")

    # Try to load Keras model when available
    if TF_AVAILABLE and keras_load_model is not None:
        for p in (MODEL_KERAS_PATH, MODEL_PATH):
            try:
                model = keras_load_model(p)
                print("✅ Loaded Keras model from:", p)
                return
            except Exception as e:
                errors.append(f"keras_load {p}: {e}")

    # Try TFLite model
    try:
        import os
        if os.path.exists(MODEL_TFLITE_PATH):
            # Determine interpreter class
            TFLiteInterpreter = None
            if _TFLITE_CLASS is not None:
                TFLiteInterpreter = _TFLITE_CLASS
            else:
                try:
                    from tflite_runtime.interpreter import Interpreter as TFLiteInterpreter  # type: ignore
                except Exception:
                    try:
                        from tensorflow.lite import Interpreter as TFLiteInterpreter  # type: ignore
                    except Exception:
                        TFLiteInterpreter = None

            if TFLiteInterpreter is not None:
                _tflite_interpreter = TFLiteInterpreter(model_path=MODEL_TFLITE_PATH)
                _tflite_interpreter.allocate_tensors()
                print("✅ Loaded TFLite model from:", MODEL_TFLITE_PATH)
                return
            else:
                errors.append("No TFLite interpreter available")
    except Exception as e:
        errors.append(f"tflite load: {e}")

    print("⚠️ Could not fully load model artifacts. Details:")
    for e in errors:
        print("  -", e)


_load_artifacts()

# -----------------------------
# Crop prediction function (supports Keras and TFLite)
# -----------------------------
def predict_crop(soil_data):
    """Return (predicted_label, probs_array).

    Supports Keras model (if loaded) or TFLite interpreter (if loaded).
    """
    data = np.array([soil_data])
    if scaler is None or label_encoder is None:
        raise RuntimeError("Preprocessors (scaler/label_encoder) are not loaded")

    scaled = scaler.transform(data)

    # Keras path
    if model is not None:
        prediction = model.predict(scaled)
        crop_index = int(np.argmax(prediction[0]))
        return label_encoder.classes_[crop_index], prediction[0]

    # TFLite path
    if _tflite_interpreter is not None:
        input_details = _tflite_interpreter.get_input_details()
        output_details = _tflite_interpreter.get_output_details()
        input_dtype = input_details[0]["dtype"]
        inp = scaled.astype(input_dtype)
        try:
            _tflite_interpreter.set_tensor(input_details[0]["index"], inp)
        except Exception:
            # Try reshaping to the expected input shape
            _tflite_interpreter.set_tensor(input_details[0]["index"], np.reshape(inp, input_details[0]["shape"]))
        _tflite_interpreter.invoke()
        out = _tflite_interpreter.get_tensor(output_details[0]["index"])
        crop_index = int(np.argmax(out[0]))
        return label_encoder.classes_[crop_index], out[0]

    raise RuntimeError("No model is loaded (neither Keras nor TFLite interpreter available)")

# -----------------------------
# MarkdownV2 escape helper
# -----------------------------
def escape_md(text: str) -> str:
    """Escape text for Telegram MarkdownV2.

    Returns a safe string where all MarkdownV2 special characters are escaped.
    """
    if text is None:
        return ""
    # Characters that must be escaped in MarkdownV2
    escape_chars = r"_*[]()~`>#+\-\=\|{}.!\\"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))


def unescape_md(text: str) -> str:
    """Remove MarkdownV2 escape backslashes previously added by escape_md.

    This restores readable plain text for fallback sends.
    """
    if text is None:
        return ""
    # Use the same escape chars set and remove a single backslash before any of them
    escape_chars = r"_*[]()~`>#+\-\=\|{}.!\\"
    pattern = re.compile(r"\\([" + re.escape(escape_chars) + r"])" )
    return pattern.sub(r"\1", str(text))

# -----------------------------
# Telegram bot setup
# -----------------------------
application = Application.builder().token(BOT_TOKEN).build()

# In-memory per-user soil value storage: chat_id -> [N,P,K,pH,Moisture,Temperature]
user_soil = {}
USER_SOIL_FILE = "user_soil.json"
import time
# Pending interactive selections: chat_id -> {"crop": str}
pending_selection = {}
# Pending deletions: chat_id -> {"type": 'all'|'index'|'label', 'target': key}
pending_deletion = {}
USER_PLANTS_FILE = "user_plants.json"
user_plants = {}

def load_user_plants():
    global user_plants
    try:
        if os.path.exists(USER_PLANTS_FILE):
            with open(USER_PLANTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # keys to int
                user_plants = {int(k): v for k, v in data.items()}
                print(f"Loaded plant data for {len(user_plants)} chats from {USER_PLANTS_FILE}.")
    except Exception as e:
        print(f"Could not load user plants file: {e}")

def save_user_plants():
    try:
        with open(USER_PLANTS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in user_plants.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Could not save user plants file: {e}")

async def previous_plant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/previousPlant"):
        body = text[len("/previousPlant"):].strip()
    else:
        body = text

    chat_id = update.effective_chat.id
    if body:
        # set value
        user_plants.setdefault(chat_id, {})["previous"] = body
        save_user_plants()
        await update.message.reply_text(escape_md(f"Set previous plant to: {body}"), parse_mode="MarkdownV2")
        return

    # show value
    entry = user_plants.get(chat_id, {})
    prev = entry.get("previous")
    if prev:
        await update.message.reply_text(escape_md(f"Previous plant: {prev}"), parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(escape_md("No previous plant set."), parse_mode="MarkdownV2")

async def next_plant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/nextPlant"):
        body = text[len("/nextPlant"):].strip()
    else:
        body = text

    chat_id = update.effective_chat.id
    # If a body is provided, set the next plant for this chat and persist
    if body:
        user_plants.setdefault(chat_id, {})["next"] = body
        save_user_plants()
        await update.message.reply_text(escape_md(f"Set next plant to: {body}"), parse_mode="MarkdownV2")
        return

    # Otherwise, show the currently set next plant (if any)
    entry = user_plants.get(chat_id, {})
    nxt = entry.get("next")
    if nxt:
        await update.message.reply_text(escape_md(f"Next plant: {nxt}"), parse_mode="MarkdownV2")
    else:
        await update.message.reply_text(escape_md("No next plant set."), parse_mode="MarkdownV2")

async def get_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    entry = user_plants.get(chat_id, {})
    prev = entry.get("previous")
    nxt = entry.get("next")
    resp = []
    resp.append(f"Previous: {prev}" if prev else "Previous: (not set)")
    resp.append(f"Next: {nxt}" if nxt else "Next: (not set)")
    await update.message.reply_text(escape_md("\n".join(resp)), parse_mode="MarkdownV2")

def load_user_soil():
    global user_soil
    try:
        if os.path.exists(USER_SOIL_FILE):
            with open(USER_SOIL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # keys are strings in JSON; convert to int
                raw = {int(k): v for k, v in data.items()}
                # Normalize old format: if a chat maps to a single soil list (len==6), convert to list of entries
                normalized = {}
                for chat_id, val in raw.items():
                    if isinstance(val, list) and len(val) == 6 and (not val or isinstance(val[0], (int, float))):
                        # old single-entry format
                        normalized[chat_id] = [{"id": 1, "label": None, "values": val, "ts": time.time()}]
                    elif isinstance(val, list):
                        # assume list of entries already
                        normalized[chat_id] = val
                    else:
                        # unexpected format: skip
                        normalized[chat_id] = []
                user_soil = normalized
                print(f"Loaded soil data for {len(user_soil)} chats from {USER_SOIL_FILE}.")
    except Exception as e:
        print(f"Could not load user soil file: {e}")

def save_user_soil():
    try:
        with open(USER_SOIL_FILE, "w", encoding="utf-8") as f:
            # convert keys to strings for JSON
            json.dump({str(k): v for k, v in user_soil.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Could not save user soil file: {e}")

# Typical ideal ranges for a few crops (N,P,K in arbitrary units, pH, moisture %, temperature °C)
# These are illustrative; adjust to your domain knowledge as needed.
ideal_ranges = {
    "Chili":    {"N": (70, 120), "P": (30, 60), "K": (30, 60), "pH": (5.5, 7.0), "Moisture": (50, 80), "Temperature": (20, 32)},
    "Cucumber": {"N": (60, 120), "P": (20, 50), "K": (30, 80), "pH": (6.0, 7.0), "Moisture": (60, 90), "Temperature": (18, 30)},
    "Groundnut":{"N": (40, 80),  "P": (20, 40), "K": (20, 60), "pH": (5.5, 6.5), "Moisture": (40, 70), "Temperature": (20, 30)},
    "Maize":    {"N": (80, 140), "P": (30, 80), "K": (30, 80), "pH": (5.5, 7.5), "Moisture": (40, 70), "Temperature": (18, 32)},
    "Paddy":    {"N": (80, 150), "P": (40, 80), "K": (40, 100),"pH": (5.0, 6.8), "Moisture": (70, 100),"Temperature": (20, 32)},
    "Spinach":  {"N": (40, 100), "P": (20, 60), "K": (30, 70), "pH": (6.0, 7.5), "Moisture": (50, 80), "Temperature": (10, 24)},
}

def suitability_check(desired_crop: str, soil_values):
    """Return suitability boolean and recommendations.

    - desired_crop: string (case-insensitive)
    - soil_values: list [N,P,K,pH,Moisture,Temperature]

    Returns: dict with keys: suitable(bool), top_prob(float), predicted(str), alternatives(list), procedures(list)
    """
    result = {"suitable": False, "top_prob": 0.0, "predicted": None, "alternatives": [], "procedures": []}

    # Run model prediction
    _, probs = predict_crop(soil_values)
    # Ensure label lookup is case-sensitive as label_encoder.classes_
    classes = list(label_encoder.classes_)
    # Map desired crop to the exact class name if possible
    desired_match = None
    for c in classes:
        if c.lower() == desired_crop.lower():
            desired_match = c
            break

    # predicted top crop
    top_idx = int(np.argmax(probs))
    top_crop = classes[top_idx]
    top_prob = float(probs[top_idx])
    result.update({"top_prob": top_prob, "predicted": top_crop})

    # Determine suitability: we require both predicted crop matches desired AND prob >= 0.6
    if desired_match and top_crop.lower() == desired_match.lower() and top_prob >= 0.6:
        result["suitable"] = True
        return result

    # Not straightforwardly suitable: prepare alternatives (top 3)
    sorted_idx = np.argsort(probs)[::-1]
    alts = [classes[int(i)] for i in sorted_idx if classes[int(i)].lower() != desired_crop.lower()]
    result["alternatives"] = alts[:3]

    # Procedures: compare to ideal ranges if we have data
    procedures = []
    if desired_match and desired_match in ideal_ranges:
        labels = ["N","P","K","pH","Moisture","Temperature"]
        ideals = ideal_ranges[desired_match]
        for i, lab in enumerate(labels):
            val = soil_values[i]
            if lab in ideals:
                lo, hi = ideals[lab]
                if val < lo:
                    if lab in ("N","P","K"):
                        procedures.append(f"Increase {lab}: apply suitable fertilizer to raise {lab} from {val} to at least {lo}.")
                    elif lab == "pH":
                        procedures.append(f"Increase pH: apply agricultural lime to raise soil pH towards {lo}.")
                    elif lab == "Moisture":
                        procedures.append(f"Increase moisture: irrigate or improve water retention (mulch, organic matter).")
                    elif lab == "Temperature":
                        procedures.append(f"Temperature is low: consider using greenhouse or planting later when warmer.")
                elif val > hi:
                    if lab in ("N","P","K"):
                        procedures.append(f"Reduce {lab}: avoid excessive fertilization; consider crops that tolerate higher {lab}.")
                    elif lab == "pH":
                        procedures.append(f"Lower pH: apply elemental sulfur to reduce soil pH towards {hi}.")
                    elif lab == "Moisture":
                        procedures.append(f"Reduce moisture: improve drainage or avoid waterlogging.")
                    elif lab == "Temperature":
                        procedures.append(f"Temperature is high: consider shade nets or choose heat-tolerant varieties.")
        if not procedures:
            procedures.append("Soil matches the typical ideal ranges but model still doesn't recommend this crop — consider soil biology or other factors.")
    else:
        procedures.append("No crop-specific ideal ranges available; consider testing soil and improving general fertility and drainage.")

    result["procedures"] = procedures
    return result


# -----------------------------
# /start command
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🌾 Crop Rotation AI — Commands and usage:\n\n"
        "/start — Show this help text.\n\n"
        "Give value of the soil to check if it suitable for the crop\n"
        "  Example:\n"
        "  With this order N,P,K,pH,Moisture,Temperature. 80,45,40,6.5,60,30 \n\n"
        "/testAllCrops CropName:N,P,K,pH,Moisture,Temperature; ... — Test multiple datasets at once.\n"
        "  Example:\n"
        "  /testAllCrops Paddy:80,45,40,6.5,60,30; Maize:70,35,30,6.2,55,28\n\n"
    "/setSoilValue [label:]N,P,K,pH,Moisture,Temperature[; label2:... ] — Save one or more soil values for this chat.\n"
    "  Examples:\n"
    "    /setSoilValue 80,45,40,6.5,60,30\n"
    "    /setSoilValue plot1:80,45,40,6.5,60,30; plot2:70,35,30,6.2,55,28\n\n"
    "/canPlant CropName [selector] — Check if a saved soil entry is suitable.\n"
    "  Selector can be an index (1-based) or a label used when saving. If omitted, the latest saved soil is used.\n"
    "  Example: /canPlant Chili 2  or  /canPlant Chili plot1\n\n"
        "/getSoil — Show saved soil entries for this chat.\n"
        "  Example: /getSoil\n\n"
        "/deleteSoil selector — Delete saved soil entries by index, label, or 'all'.\n"
        "  Examples:\n"
        "    /deleteSoil 2\n"
        "    /deleteSoil plot1\n"
        "    /deleteSoil all\n\n"
        "/previousPlant [PlantName] — Set or show what was planted last season.\n"
        "  Examples:\n"
        "    /previousPlant  (shows last planted)\n"
        "    /previousPlant Paddy  (sets last planted to Paddy)\n\n"
        "/nextPlant [PlantName] — Set or show what to plant next season.\n"
        "  Examples:\n"
        "    /nextPlant  (shows next recommended)\n"
        "    /nextPlant Maize  (sets next plant to Maize)\n\n"
        "Notes:\n"
        "- Soil values are stored per-chat in memory (lost on bot restart).\n"
        "- Values order: N, P, K, pH, Moisture, Temperature.\n"
    )
    await update.message.reply_text(escape_md(help_text), parse_mode="MarkdownV2")

# -----------------------------
# /setSoilValue command
# Usage: /setSoilValue N,P,K,pH,Moisture,Temperature
# -----------------------------
async def set_soil_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/setSoilValue"):
        body = text[len("/setSoilValue"):].strip()
    else:
        body = text
    try:
        if not body:
            raise ValueError("No soil values provided.")

        # Support multiple entries separated by semicolon: label:vals; label2:vals2
        parts = [p.strip() for p in body.split(";") if p.strip()]
        chat_id = update.effective_chat.id
        entries = user_soil.get(chat_id, [])
        next_id = max([e.get("id", 0) for e in entries], default=0) + 1

        saved_labels = []
        for part in parts:
            label = None
            vals_str = part
            if ":" in part:
                maybe_label, maybe_vals = part.split(":", 1)
                if re.match(r"^[0-9]+(\.[0-9]+)?\s*,", maybe_vals.strip()):
                    # looks like label:values
                    label = maybe_label.strip()
                    vals_str = maybe_vals
                else:
                    # if colon present but the right side doesn't look like numbers, treat whole as values
                    vals_str = part

            values = [float(x.strip()) for x in vals_str.split(",")]
            if len(values) != 6:
                raise ValueError(f"Each soil entry must have 6 numbers. Problem with: {part}")

            entry = {"id": next_id, "label": label, "values": values, "ts": time.time()}
            entries.append(entry)
            saved_labels.append(f"{next_id}{(f' ({label})' if label else '')}")
            next_id += 1

        user_soil[chat_id] = entries
        save_user_soil()
        await update.message.reply_text(escape_md(f"Saved soil entries: {', '.join(saved_labels)}"), parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(escape_md(f"Error saving soil values: {e}"), parse_mode="MarkdownV2")

# -----------------------------
# /canPlant command
# Usage: /canPlant CropName   (uses stored soil for the chat)
# -----------------------------
async def can_plant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/canPlant"):
        body = text[len("/canPlant"):].strip()
    else:
        body = text

    if not body:
        await update.message.reply_text(escape_md("Usage: /canPlant CropName"), parse_mode="MarkdownV2")
        return

    parts = body.split()
    crop_name = parts[0]
    selector = parts[1] if len(parts) > 1 else None
    chat_id = update.effective_chat.id
    if chat_id not in user_soil:
        await update.message.reply_text(escape_md("No soil values set for this chat. Use /setSoilValue N,P,K,pH,Moisture,Temperature"), parse_mode="MarkdownV2")
        return

    entries = user_soil[chat_id]
    if not entries:
        await update.message.reply_text(escape_md("No soil entries saved for this chat."), parse_mode="MarkdownV2")
        return
    # If there are multiple entries and no selector was provided, prompt the user
    if selector is None and len(entries) > 1:
        lines = ["Multiple soil entries found. Reply with the number or label to choose:"]
        for i, e in enumerate(entries, start=1):
            lab = e.get("label")
            vals = e.get("values", [])
            vals_str = ",".join([str(v) for v in vals])
            lines.append(f"{i}{(f' ({lab})' if lab else '')}: {vals_str}")
        await update.message.reply_text(escape_md("\n".join(lines)), parse_mode="MarkdownV2")
        # save pending selection for this chat
        pending_selection[chat_id] = {"crop": crop_name}
        return

    # Select entry by selector: index (1-based) or label. Default = latest (last appended)
    chosen = None
    if selector:
        # try index
        try:
            idx = int(selector)
            # convert 1-based to 0-based
            if 1 <= idx <= len(entries):
                chosen = entries[idx - 1]
        except Exception:
            # try label match
            for e in entries:
                if e.get("label") and e.get("label").lower() == selector.lower():
                    chosen = e
                    break

    if chosen is None:
        chosen = entries[-1]

    soil_values = chosen.get("values")
    res = suitability_check(crop_name, soil_values)

    if res.get("suitable"):
        await update.message.reply_text(escape_md(f"Yes — your soil is suitable for {crop_name}! Predicted: {res.get('predicted')} ({res.get('top_prob'):.2f})"), parse_mode="MarkdownV2")
        return

    # Not suitable: provide alternatives and procedures
    alt_text = ", ".join(res.get("alternatives", [])) or "None"
    proc_text = "\n".join([f"- {p}" for p in res.get("procedures", [])])
    msg = (
        f"Your soil is not suitable for {crop_name}.\n"
        f"Model predicted: {res.get('predicted')} ({res.get('top_prob'):.2f})\n"
        f"Suggested alternative crops: {alt_text}\n\n"
        f"Recommendations to make {crop_name} possible:\n{proc_text}"
    )
    await update.message.reply_text(escape_md(msg), parse_mode="MarkdownV2")


async def get_soil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_soil:
        await update.message.reply_text(escape_md("No soil values set for this chat. Use /setSoilValue."), parse_mode="MarkdownV2")
        return
    entries = user_soil[chat_id]
    if not entries:
        await update.message.reply_text(escape_md("No soil entries saved for this chat."), parse_mode="MarkdownV2")
        return

    labels = ["N","P","K","pH","Moisture","Temperature"]
    lines = []
    for i, e in enumerate(entries, start=1):
        vals = e.get("values", [])
        lab = e.get("label")
        ts = e.get("ts")
        labeled = ", ".join([f"{labels[j]}: {vals[j]}" for j in range(len(vals))]) if vals else ""
        lines.append(f"{i}{(f' ({lab})' if lab else '')}: {labeled}")

    await update.message.reply_text(escape_md("\n".join(lines)), parse_mode="MarkdownV2")

# -----------------------------
# /testAllCrops command
# -----------------------------
async def test_all_crops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/testAllCrops"):
        text = text[len("/testAllCrops"):].strip()

    if not text:
        await update.message.reply_text(
            "⚠️ Provide soil datasets as `CropName:N,P,K,pH,Moisture,Temperature` separated by `;`",
            parse_mode="MarkdownV2"
        )
        return

    datasets = text.split(";")
    reply_text = "🌱 Test predictions:\n\n"

    def escape_md_v2(text):
        escape_chars = r"_*[]()~`>#+-=|{}.!?"
        return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))
    # use the module-level escape helper to ensure consistent escaping
    escape_md_v2 = escape_md

    for data_str in datasets:
        try:
            if ":" not in data_str:
                raise ValueError("Missing crop label")

            crop_label, values_str = data_str.split(":", 1)
            crop_label = crop_label.strip()
            values = [float(x.strip()) for x in values_str.split(",")]
            if len(values) != 6:
                raise ValueError("Soil values must be 6 numbers")

            predicted_crop, probs = predict_crop(values)

            # Determine icon (initial assignment removed; using escaped-only assignment below)
            # Determine icon/text (escaped) - only Right or Wrong
            if predicted_crop.lower() == crop_label.lower():
                icon = escape_md_v2("✅ Right")
            else:
                icon = escape_md_v2("❌ Wrong")

            # Build labeled values: N, P, K, pH, Moisture, Temperature
            labels = ["N", "P", "K", "pH", "Moisture", "Temperature"]
            labeled_pairs = ", ".join([
                f"{escape_md_v2(labels[i])}: {escape_md_v2(str(values[i]))}"
                for i in range(len(values))
            ])

            reply_text += (
                f"{escape_md_v2(crop_label)} soil \[{labeled_pairs}\] -> "
                f"Predicted: *{escape_md_v2(predicted_crop)}* {icon}\n\n"
            )

        except Exception as e:
            # Avoid using raw backticks or unescaped characters in the message
            reply_text += (
                f"{escape_md_v2('❌ Could not process dataset')} {escape_md_v2(data_str)}: "
                f"{escape_md_v2(str(e))}\n\n"
            )

    try:
        await update.message.reply_text(reply_text, parse_mode="MarkdownV2")
    except Exception as send_err:
        # If MarkdownV2 parsing fails, log the problematic text and resend as plain text
        try:
            import telegram
            if isinstance(send_err, telegram.error.BadRequest):
                print("[WARN] MarkdownV2 BadRequest while sending reply_text. Falling back to plain text.")
                print("[OFFENDING MESSAGE START]")
                print(reply_text)
                print("[OFFENDING MESSAGE END]")
                # Remove MarkdownV2 escape slashes for a clean plain-text resend
                clean_text = unescape_md(reply_text)
                await update.message.reply_text(clean_text)  # fallback to plain text
                return
        except Exception:
            # If we couldn't import telegram or check the type, still try to resend plain text
            print("[ERROR] Failed to send with MarkdownV2 and could not check exception type. Resending as plain text.")
            print(reply_text)
            clean_text = unescape_md(reply_text)
            await update.message.reply_text(clean_text)
            return
        # If it's some other exception, re-raise
        raise

# -----------------------------
# Handle plain messages
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    # Check for pending deletion confirmation first
    if chat_id in pending_deletion:
        ans = text.strip().lower()
        if ans in ("yes", "y"):
            pend = pending_deletion.pop(chat_id)
            entries = user_soil.get(chat_id, [])
            if pend["type"] == "all":
                user_soil[chat_id] = []
                save_user_soil()
                await update.message.reply_text(escape_md("All entries deleted."), parse_mode="MarkdownV2")
                return
            elif pend["type"] == "index":
                idx = pend["target"]
                if 1 <= idx <= len(entries):
                    removed = entries.pop(idx - 1)
                    user_soil[chat_id] = entries
                    save_user_soil()
                    lab = removed.get('label')
                    labtxt = f" ({lab})" if lab else ""
                    await update.message.reply_text(escape_md(f"Deleted entry {idx}{labtxt}."), parse_mode="MarkdownV2")
                    return
                else:
                    await update.message.reply_text(escape_md("Index out of range; nothing deleted."), parse_mode="MarkdownV2")
                    return
            elif pend["type"] == "label":
                label = pend["target"]
                for i, e in enumerate(entries):
                    if e.get("label") and e.get("label").lower() == label.lower():
                        removed = entries.pop(i)
                        user_soil[chat_id] = entries
                        save_user_soil()
                        lab = removed.get('label')
                        labtxt = f" ({lab})" if lab else ""
                        await update.message.reply_text(escape_md(f"Deleted entry {i+1}{labtxt}."), parse_mode="MarkdownV2")
                        return
                await update.message.reply_text(escape_md("Label not found; nothing deleted."), parse_mode="MarkdownV2")
                return
        else:
            pending_deletion.pop(chat_id, None)
            await update.message.reply_text(escape_md("Deletion cancelled."), parse_mode="MarkdownV2")
            return
    # If there's a pending selection for this chat, interpret the message as selection
    if chat_id in pending_selection:
        pending = pending_selection.pop(chat_id)
        crop_name = pending.get("crop")
        # try to match as index
        entries = user_soil.get(chat_id, [])
        chosen = None
        sel = text.strip()
        try:
            idx = int(sel)
            if 1 <= idx <= len(entries):
                chosen = entries[idx - 1]
        except Exception:
            # match label
            for e in entries:
                if e.get("label") and e.get("label").lower() == sel.lower():
                    chosen = e
                    break

        if chosen is None:
            # reply with error and instructions
            await update.message.reply_text(escape_md("Invalid selection. Reply with the number shown or the label."), parse_mode="MarkdownV2")
            return

        soil_values = chosen.get("values")
        res = suitability_check(crop_name, soil_values)
        if res.get("suitable"):
            await update.message.reply_text(escape_md(f"Yes — your soil is suitable for {crop_name}! Predicted: {res.get('predicted')} ({res.get('top_prob'):.2f})"), parse_mode="MarkdownV2")
            return

        alt_text = ", ".join(res.get("alternatives", [])) or "None"
        proc_text = "\n".join([f"- {p}" for p in res.get("procedures", [])])
        msg = (
            f"Your soil is not suitable for {crop_name}.\n"
            f"Model predicted: {res.get('predicted')} ({res.get('top_prob'):.2f})\n"
            f"Suggested alternative crops: {alt_text}\n\n"
            f"Recommendations to make {crop_name} possible:\n{proc_text}"
        )
        await update.message.reply_text(escape_md(msg), parse_mode="MarkdownV2")
        return
    try:
        values = [float(x.strip()) for x in text.split(",")]
        if len(values) != 6:
            raise ValueError("Invalid number of values.")
        predicted_crop, _ = predict_crop(values)
        await update.message.reply_text(
            f"🌱 Recommended crop: *{escape_md(predicted_crop)}*",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        await update.message.reply_text(
            "⚠️ Invalid input format. Use: `N,P,K,pH,Moisture,Temperature`",
            parse_mode="MarkdownV2"
        )

# -----------------------------
# Register handlers
# -----------------------------
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("testAllCrops", test_all_crops))
application.add_handler(CommandHandler("setSoilValue", set_soil_value))
application.add_handler(CommandHandler("canPlant", can_plant))
application.add_handler(CommandHandler("getSoil", get_soil))
application.add_handler(CommandHandler("previousPlant", previous_plant))
application.add_handler(CommandHandler("nextPlant", next_plant))
application.add_handler(CommandHandler("getPlants", get_plants))
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch latest soil reading from the dashboard API and show to the user."""
    try:
        url = f"{DASHBOARD_API_BASE.rstrip('/')}/api/readings/latest"
        # Run blocking requests in a thread to avoid blocking the event loop
        resp = await asyncio.to_thread(requests.get, url, headers={"x-api-key": DASHBOARD_API_KEY})
        if resp.status_code != 200:
            await update.message.reply_text(escape_md(f"Could not fetch latest reading: {resp.status_code}"))
            return
        data = resp.json()
        # Build message
        ts = data.get("timestamp")
        msg = (
            f"📡 Latest reading (timestamp: {ts})\n"
            f"N: {data.get('np_n')}\n"
            f"P: {data.get('np_p')}\n"
            f"K: {data.get('np_k')}\n"
            f"EC: {data.get('ec')}\n"
            f"pH: {data.get('ph')}\n"
            f"Humidity: {data.get('humidity')}\n"
            f"Temperature: {data.get('temperature')}\n"
        )
        await update.message.reply_text(escape_md(msg), parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(escape_md(f"Error retrieving status: {e}"))

application.add_handler(CommandHandler("status", status))

async def delete_soil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/deleteSoil"):
        body = text[len("/deleteSoil"):].strip()
    else:
        body = text

    if not body:
        await update.message.reply_text(escape_md("Usage: /deleteSoil <index|label|all>"), parse_mode="MarkdownV2")
        return

    chat_id = update.effective_chat.id
    if chat_id not in user_soil or not user_soil.get(chat_id):
        await update.message.reply_text(escape_md("No saved soil entries for this chat."), parse_mode="MarkdownV2")
        return

    entries = user_soil[chat_id]
    key = body.strip()
    # Ask for confirmation before deleting
    pending = None
    if key.lower() == "all":
        pending = {"type": "all", "target": None}
    else:
        # try index
        try:
            idx = int(key)
            if 1 <= idx <= len(entries):
                pending = {"type": "index", "target": idx}
        except Exception:
            pass

        # try label
        if pending is None:
            for i, e in enumerate(entries):
                if e.get("label") and e.get("label").lower() == key.lower():
                    pending = {"type": "label", "target": e.get("label")}
                    break

    if pending is None:
        await update.message.reply_text(escape_md("Could not find an entry with that index or label."), parse_mode="MarkdownV2")
        return

    # Save pending deletion and ask for confirmation
    pending_deletion[chat_id] = pending
    await update.message.reply_text(escape_md("Please confirm deletion by replying 'yes' or cancel with 'no'."), parse_mode="MarkdownV2")

application.add_handler(CommandHandler("deleteSoil", delete_soil))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# -----------------------------
# Background asyncio loop
# -----------------------------
bg_loop = asyncio.new_event_loop()
def start_bg_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
threading.Thread(target=start_bg_loop, args=(bg_loop,), daemon=True).start()

# -----------------------------
# Flask webhook route
# -----------------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return "No data received", 400

        update = Update.de_json(data, application.bot)
        asyncio.run_coroutine_threadsafe(application.process_update(update), bg_loop)
        return "OK", 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "Error", 500

# -----------------------------
# Ngrok webhook setup
# -----------------------------
def setup_webhook():
    public_url = ngrok.connect(5000).public_url
    webhook_url = f"{public_url}/webhook"
    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
    )
    print(f"🌐 Ngrok URL: {public_url}")
    print(f"🤖 Webhook set response: {response.json()}")
    return public_url

# -----------------------------
# Main entry
# -----------------------------
if __name__ == "__main__":
    load_user_soil()
    load_user_plants()
    # Defer webhook setup until after the Application is initialized so we can
    # choose between webhook (server) or polling (local/dev) modes via env var.
    use_webhook = os.getenv('USE_WEBHOOK', '0')

    def is_raspberry_pi() -> bool:
        """Best-effort detection of Raspberry Pi environment.

        Checks common Pi indicators in order:
          - /proc/device-tree/model containing 'raspberry'
          - /proc/cpuinfo containing 'raspberry' or 'bcm'
          - platform.machine() starting with arm/aarch

        Returns True if it appears to be a Pi, False otherwise.
        """
        try:
            # Most reliable on Linux/Pi
            if os.path.exists('/proc/device-tree/model'):
                try:
                    with open('/proc/device-tree/model', 'r', encoding='utf-8', errors='ignore') as f:
                        return 'raspberry' in f.read().lower()
                except Exception:
                    pass
            if os.path.exists('/proc/cpuinfo'):
                try:
                    with open('/proc/cpuinfo', 'r', encoding='utf-8', errors='ignore') as f:
                        txt = f.read().lower()
                        if 'raspberry' in txt or 'bcm' in txt:
                            return True
                except Exception:
                    pass
            # Fallback to architecture check
            import platform
            m = platform.machine() or ''
            m = m.lower()
            if m.startswith('arm') or m.startswith('aarch'):
                return True
        except Exception:
            pass
        return False

    # If running on a Raspberry Pi, prefer local polling mode (no webhook/ngrok).
    if is_raspberry_pi():
        # Allow an explicit override if the operator wants to force webhook usage on the Pi
        force_on_pi = os.getenv('FORCE_WEBHOOK_ON_PI', '0')
        if force_on_pi == '1':
            print("ℹ️ Detected Raspberry Pi environment but FORCE_WEBHOOK_ON_PI=1 — leaving webhook setting as configured by USE_WEBHOOK.")
        else:
            print("ℹ️ Detected Raspberry Pi environment — disabling webhook (forcing USE_WEBHOOK=0). The bot will use local polling and the dashboard should be reachable via the Pi's IP.")
            use_webhook = '0'

    future = asyncio.run_coroutine_threadsafe(application.initialize(), bg_loop)
    future.result()

    try:
        if use_webhook == '1':
            # Only set a webhook when explicitly requested (e.g., on the Pi).
            setup_webhook()
        else:
            # Ensure no webhook is active so polling (getUpdates) can be used
            # when running the bot locally on a laptop.
            try:
                asyncio.run_coroutine_threadsafe(application.bot.delete_webhook(drop_pending_updates=True), bg_loop).result()
                print("🤖 Existing webhook (if any) deleted; using polling mode.")
            except Exception as e:
                print(f"[WARN] Could not delete existing webhook: {e}")
    except Exception as e:
        print(f"[ERROR] Webhook setup/delete failed: {e}")

    print("🤖 Telegram bot initialized and ready.")
    app.run(host="0.0.0.0", port=5000)
