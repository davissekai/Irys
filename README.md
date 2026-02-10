# Irys Project
(Will be updated soon)
Digitization app for paper registers.

## Setup

1. **Install Dependencies**
   ```bash
   pip install "paddleocr[all]" paddlepaddle
   ```

2. **Initialize & Download Models**
   Run the test script once to trigger the automatic model download (~1-2GB).
   ```bash
   python test_ocr.py
   ```

## Usage

### Extract Table from Image
To extract structured data from a register image:

```bash
python extract.py path/to/image.jpg
```

This will output a JSON file named `image_output.json` in the same directory.

## Project Structure
- `extract.py`: Main script for OCR extraction.
- `test_ocr.py`: Setup and verification script.
- `Project_Irys_Spec.md`: Project specification and design document.
