import json
import sys
from pathlib import Path


def convert_records(data):
    """
    Convert records from:
    [
      {
        "title": "",
        "media_list_data": [],
        "string_list_data": [
          {
            "href": "https://www.instagram.com/exampleuser",
            "value": "exampleuser",
            "timestamp": 1234567890
          }
        ]
      }
    ]

    to:
    [
      {
        "username": "exampleuser",
        "id": "1234567890"
      }
    ]
    """
    output = []

    for item in data:
        string_list = item.get("string_list_data", [])
        if not string_list:
            continue

        first_entry = string_list[0]
        username = first_entry.get("value", "")
        timestamp = first_entry.get("timestamp", "")

        if username == "":
            continue

        output.append({
            "username": str(username),
            "id": str(timestamp)
        })

    return output


def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_followers.py input.json output.json")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    converted = convert_records(data)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)

    print(f"Converted {len(converted)} records")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()