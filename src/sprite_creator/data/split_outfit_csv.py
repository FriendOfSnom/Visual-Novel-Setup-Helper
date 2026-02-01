#!/usr/bin/env python3
"""
split_outfit_csv.py

One-time migration script to split outfit_prompts.csv into 36 separate files.
Run this from the data directory or use absolute paths.
"""

import csv
from pathlib import Path
from collections import defaultdict

# Constants (mirror from constants.py)
ARCHETYPES = ["young woman", "adult woman", "motherly woman",
              "young man", "adult man", "fatherly man"]
OUTFIT_KEYS = ["casual", "formal", "uniform", "athletic", "swimsuit", "underwear"]

def split_outfit_csv():
    """
    Read outfit_prompts.csv and split into 36 separate files.
    Creates files named {archetype}_{outfit_key}.csv with single 'prompt' column.
    """
    # Setup paths
    data_dir = Path(__file__).parent
    input_csv = data_dir / "outfit_prompts.csv"
    backup_csv = data_dir / "outfit_prompts.csv.backup"

    # Data structure: {(archetype, outfit_key): [prompts]}
    outfit_data = defaultdict(list)

    # Read existing CSV
    print(f"Reading {input_csv}...")
    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            archetype = row["archetype"].strip()
            outfit_key = row["outfit_key"].strip()
            prompt = row["prompt"].strip()

            if archetype and outfit_key and prompt:
                outfit_data[(archetype, outfit_key)].append(prompt)

    print(f"Loaded {sum(len(v) for v in outfit_data.values())} prompts")

    # Create 36 CSV files
    created_count = 0
    empty_count = 0

    for archetype in ARCHETYPES:
        for outfit_key in OUTFIT_KEYS:
            # Generate filename with underscores
            filename = f"{archetype.replace(' ', '_')}_{outfit_key}.csv"
            output_path = data_dir / filename

            prompts = outfit_data.get((archetype, outfit_key), [])

            # Write CSV with just 'prompt' column
            with output_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["prompt"])  # Header

                for prompt in prompts:
                    writer.writerow([prompt])

            if prompts:
                print(f"  Created {filename}: {len(prompts)} prompts")
                created_count += 1
            else:
                print(f"  Created {filename}: (empty)")
                empty_count += 1

    # Backup original file
    if input_csv.exists():
        input_csv.rename(backup_csv)
        print(f"\nBacked up original to {backup_csv.name}")

    print(f"\nComplete! Created {created_count} files with prompts, {empty_count} empty files.")
    print(f"Total: {created_count + empty_count} files")

if __name__ == "__main__":
    split_outfit_csv()
