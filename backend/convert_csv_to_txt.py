"""
CSV to TXT Converter
Convert CSV files to plain text format for document processing
"""

import pandas as pd
import argparse
from pathlib import Path

def convert_csv_to_txt(csv_path, output_path=None, column=None, delimiter=','):
    """
    Convert CSV file to text format

    Args:
        csv_path: Path to input CSV file
        output_path: Path to output TXT file (optional)
        column: Specific column to extract (optional, default: all columns)
        delimiter: CSV delimiter (default: ',')
    """
    # Read CSV
    df = pd.read_csv(csv_path, delimiter=delimiter)

    print(f"📂 Reading CSV: {csv_path}")
    print(f"   Rows: {len(df)}, Columns: {len(df.columns)}")

    # Extract specific column if specified
    if column:
        if column not in df.columns:
            print(f"❌ Column '{column}' not found")
            print(f"   Available columns: {list(df.columns)}")
            return

        text_content = '\n\n'.join(df[column].astype(str).tolist())
        print(f"✅ Extracted column: {column}")
    else:
        # Convert all columns to text
        text_content = df.to_string(index=False)
        print(f"✅ Converted all columns")

    # Determine output path
    if output_path is None:
        csv_file = Path(csv_path)
        output_path = csv_file.with_suffix('.txt')

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text_content)

    print(f"💾 Saved to: {output_path}")
    print(f"   Size: {len(text_content)} characters")

def main():
    parser = argparse.ArgumentParser(description='Convert CSV to TXT')
    parser.add_argument('csv_file', help='Input CSV file path')
    parser.add_argument('-o', '--output', help='Output TXT file path')
    parser.add_argument('-c', '--column', help='Specific column to extract')
    parser.add_argument('-d', '--delimiter', default=',', help='CSV delimiter (default: comma)')

    args = parser.parse_args()

    print("=" * 60)
    print("CSV to TXT Converter")
    print("=" * 60)

    convert_csv_to_txt(
        csv_path=args.csv_file,
        output_path=args.output,
        column=args.column,
        delimiter=args.delimiter
    )

    print("\n✅ Conversion complete!")

if __name__ == "__main__":
    main()
