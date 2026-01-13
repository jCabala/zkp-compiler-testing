#!/usr/bin/env python3
import sys

def count_commas_bytes(b: bytes) -> int:
    return b.count(b',')

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file.csv>")
        sys.exit(1)

    path = sys.argv[1]

    with open(path, "rb") as f:
        header = f.readline()
        if not header:
            print("Empty file")
            return

        header_commas = count_commas_bytes(header.rstrip(b"\r\n"))
        header_cols = header_commas + 1
        if header_cols < 2:
            print(f"Header has {header_cols} column(s); can't estimate rows.")
            return

        data_commas = 0
        data_newlines = 0
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            data_commas += count_commas_bytes(chunk)
            data_newlines += chunk.count(b"\n")

    # Average commas per well-formed row would be (header_cols - 1)
    est_rows = data_commas / (header_cols - 1)

    print(f"file: {path}")
    print(f"header_cols: {header_cols} (commas={header_commas})")
    print(f"data_commas: {data_commas}")
    print(f"physical_data_lines(~): {data_newlines}")  # rough (CRLF still contains \n)
    print(f"estimated_rows_by_commas: {est_rows:.2f}")

if __name__ == "__main__":
    main()
