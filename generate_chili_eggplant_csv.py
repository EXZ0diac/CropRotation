import csv
import random


SEED = 42
TOTAL_ROWS = 50150
OUTPUT_PATH = "chili_eggplant_balanced_50150.csv"


def sample_uniform(low: float, high: float, decimals: int = 2) -> float:
    return round(random.uniform(low, high), decimals)


def gen_chili_row() -> dict:
    return {
        "Nitrogen": sample_uniform(40, 80, 2),
        "Phosphorus": sample_uniform(30, 60, 2),
        "Potassium": sample_uniform(150, 250, 2),
        "pH": sample_uniform(6.0, 6.8, 2),
        "Humidity": sample_uniform(60, 80, 2),
        "Temperature": sample_uniform(20, 30, 2),
        "Crop": "Chili",
    }


def gen_eggplant_row() -> dict:
    return {
        "Nitrogen": sample_uniform(50, 100, 2),
        "Phosphorus": sample_uniform(40, 70, 2),
        "Potassium": sample_uniform(200, 300, 2),
        "pH": sample_uniform(5.5, 6.8, 2),
        "Humidity": sample_uniform(60, 70, 2),
        "Temperature": sample_uniform(22, 32, 2),
        "Crop": "Eggplant",
    }


def main() -> None:
    random.seed(SEED)

    # Keep classes balanced while including the extra 150 rows.
    per_class = TOTAL_ROWS // 2
    rows = []
    for _ in range(per_class):
        rows.append(gen_chili_row())
        rows.append(gen_eggplant_row())

    random.shuffle(rows)

    fieldnames = ["Nitrogen", "Phosphorus", "Potassium", "pH", "Humidity", "Temperature", "Crop"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created {OUTPUT_PATH}")
    print(f"Total rows: {len(rows)}")
    print(f"Chili rows: {per_class}")
    print(f"Eggplant rows: {per_class}")


if __name__ == "__main__":
    main()