import os
import shutil
import tempfile
import subprocess
import re
from datetime import date
from typing import Optional, List

from pyzerox import zerox
from app.models.invoice import ExtractedInvoice, InvoiceItem
from app.config import OCR_API_KEY

os.environ["OPENAI_API_KEY"] = OCR_API_KEY

async def extract_invoice_data(file_path: str, file_extension: str) -> ExtractedInvoice:
    """
    Extract structured data from an invoice file using Zerox OCR,
    with robust handling for PDF rasterization and parsing errors.
    """
    # Resolve and validate the file path
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Invoice file not found: {file_path}")

    # Ensure Poppler utilities are available
    try:
        subprocess.run(["pdfinfo", "-h"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        raise EnvironmentError(
            "Poppler utilities not found. Please install poppler-utils (Linux), "
            "brew install poppler (macOS), or download Poppler for Windows and add to PATH."
        )

    # Create a temporary directory for Zerox output
    output_dir = tempfile.mkdtemp()
    try:
        # Call Zerox to perform OCR and conversion to markdown
        result = await zerox(
            file_path=file_path,
            model="gpt-4o-mini",
            output_dir=output_dir,
            custom_system_prompt=(
                "You are an AI assistant specialized in extracting structured information from invoices.\n"
                "First, detect the language in which this invoice is written and include it as “Invoice Language”.\n"
                "Then extract the following information in a structured format:\n"
                "- Invoice Language\n"
                "- Invoice number\n"
                "- Supplier name\n"
                "- Issue date\n"
                "- Due date (if available)\n"
                "- Line items with description, quantity, unit price, and total\n"
                "- Total amount\n\n"
                "Format your response as key–value pairs for the header fields (including Invoice Language), "
                "and present the line items as a Markdown table."
            )
        )

        # Defensive check: ensure pages were returned
        if not getattr(result, "pages", None):
            raise RuntimeError(
                "Zerox returned no pages. Check that the file is a valid PDF and Poppler is installed."
            )

        # Concatenate all page contents
        raw_text = "\n\n".join(page.content for page in result.pages)

        # Parse the raw markdown-like text into structured data
        return parse_zerox_output(raw_text)

    except Exception as e:
        # Surface the error for debugging
        raise RuntimeError(f"Error in Zerox OCR processing: {e}") from e

    finally:
        # Clean up temporary directory
        shutil.rmtree(output_dir, ignore_errors=True)


def parse_zerox_output(raw_text: str) -> ExtractedInvoice:
    """
    Parse the Zerox-generated markdown text to extract:
      - Invoice number
      - Supplier name
      - Issue date
      - Due date
      - Line items
      - Total amount
    """
    # Defaults
    invoice_number: str = "Unknown"
    supplier_name: str = "Unknown"
    issue_date: date = date.today()
    due_date: Optional[date] = None
    items: List[InvoiceItem] = []
    total: float = 0.0

    # Invoice number
    m = re.search(
        r"Invoice\s*(?:#|Number|No\.?|ID)?\s*[:;]?\s*([A-Za-z0-9\-]+)",
        raw_text, re.IGNORECASE
    )
    if m:
        invoice_number = m.group(1).strip()

    # Supplier name
    m = re.search(
        r"(?:From|Supplier|Vendor|Company|Billed\s+from)\s*[:;]?\s*([A-Za-z0-9\s\.,&\-]+?)(?:\n|$|\s{2,})",
        raw_text, re.IGNORECASE
    )
    if m:
        supplier_name = m.group(1).strip()

    # Issue date
    m = re.search(
        r"(?:Date|Issue Date|Invoice Date)\s*[:;]?\s*(\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|\d{4}[-./]\d{1,2}[-./]\d{1,2})",
        raw_text, re.IGNORECASE
    )
    if m:
        issue_date = _parse_date_string(m.group(1))

    # Due date
    m = re.search(
        r"(?:Due Date|Payment Due)\s*[:;]?\s*(\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|\d{4}[-./]\d{1,2}[-./]\d{1,2})",
        raw_text, re.IGNORECASE
    )
    if m:
        due_date = _parse_date_string(m.group(1))

    # Line items: first try markdown table rows
    table_row_pattern = re.compile(r"\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|")
    for row in table_row_pattern.finditer(raw_text):
        text = row.group(0).lower()
        # Skip header-like rows
        if any(col in text for col in ("description", "quantity", "unit", "price", "amount", "total")):
            continue
        try:
            desc = row.group(1).strip()
            nums = []
            for col in row.groups()[1:]:
                nm = re.search(r"(\d+(?:\.\d+)?)", col)
                if nm:
                    nums.append(float(nm.group(1)))
            if len(nums) >= 2:
                qty, unit_price = nums[0], nums[1]
                line_total = nums[2] if len(nums) >= 3 else qty * unit_price
                items.append(InvoiceItem(
                    description=desc,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=line_total
                ))
        except Exception:
            continue

    # Fallback: plain-text line matching if no items found
    if not items:
        for line in raw_text.splitlines():
            m = re.search(
                r"([A-Za-z][A-Za-z0-9\s\-&,\.]+?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)",
                line
            )
            if m:
                try:
                    desc = m.group(1).strip()
                    qty = float(m.group(2))
                    unit_price = float(m.group(3))
                    line_total = float(m.group(4))
                    items.append(InvoiceItem(
                        description=desc,
                        quantity=qty,
                        unit_price=unit_price,
                        total_price=line_total
                    ))
                except ValueError:
                    continue

    # Total amount
    m = re.search(
        r"Total\s*[:;]?\s*(?:[A-Za-z]{3})?\s*(\d+(?:\.\d+)?)",
        raw_text, re.IGNORECASE
    )
    if m:
        try:
            total = float(m.group(1))
        except ValueError:
            total = 0.0

    # If we have items but no total, sum item totals
    if items and total == 0.0:
        total = sum(item.total_price for item in items)

    return ExtractedInvoice(
        invoice_number=invoice_number,
        supplier_name=supplier_name,
        issue_date=issue_date,
        due_date=due_date,
        items=items,
        total=total,
        raw_text=raw_text
    )


def _parse_date_string(date_str: str) -> date:
    """
    Helper to parse strings like '2023-12-01' or '01/12/2023' into datetime.date.
    """
    parts = re.split(r"[-./]", date_str)
    try:
        # YYYY-MM-DD
        if len(parts[0]) == 4:
            y, m, d = map(int, parts)
        else:
            # assume DD-MM-YYYY or similar
            d, m, y = map(int, parts)
        return date(y, m, d)
    except Exception:
        # Fallback to today on error
        return date.today()
