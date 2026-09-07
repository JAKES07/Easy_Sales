"""Easy_Sales ESC/POS receipt command builder.

This module only builds standard ESC/POS byte commands. It does not open a
Bluetooth socket itself. A native Android printing bridge can consume these
bytes and send them to a paired Bluetooth Classic SPP ESC/POS printer.
"""

ESC = b"\x1b"
GS = b"\x1d"
LF = b"\x0a"


def _cmd(*values):
    return bytes(values)


def text(value=""):
    return str(value).encode("cp437", errors="replace")


def build_receipt_commands(receipt, paper_width=58):
    """Return ESC/POS bytes for a simple receipt.

    paper_width is the physical paper width in millimetres (58 or 80).
    """
    width = 32 if int(paper_width) == 58 else 48
    out = bytearray()

    # Initialize, center, bold store name.
    out += ESC + b"@"
    out += ESC + b"a" + _cmd(1)
    out += ESC + b"E" + _cmd(1)
    out += text(receipt.get("store_name", "Easy Sales")) + LF
    out += ESC + b"E" + _cmd(0)
    out += text("Receipt") + LF
    out += ESC + b"a" + _cmd(0)
    out += text("-" * width) + LF

    for item in receipt.get("items", []):
        name = str(item.get("name", ""))[:width]
        qty = int(item.get("quantity", 0))
        line_total = float(item.get("line_total", 0))
        out += text(name) + LF
        line = f"  {qty} x {float(item.get('unit_price', 0)):.2f}".ljust(width - 12) + f"{line_total:>10.2f}"
        out += text(line[:width]) + LF

    out += text("-" * width) + LF
    out += text(f"Subtotal: {float(receipt.get('subtotal', 0)):.2f}".rjust(width)) + LF
    out += text(f"Fee: {float(receipt.get('sale_fee', 0)):.2f}".rjust(width)) + LF
    out += ESC + b"E" + _cmd(1)
    out += text(f"TOTAL: {float(receipt.get('total', 0)):.2f}".rjust(width)) + LF
    out += ESC + b"E" + _cmd(0)
    out += text(f"Payment: {receipt.get('payment_method', 'cash').upper()}") + LF
    if receipt.get("cash_received") is not None:
        out += text(f"Cash: {float(receipt.get('cash_received', 0)):.2f}".rjust(width)) + LF
        out += text(f"Change: {float(receipt.get('change', 0)):.2f}".rjust(width)) + LF
    out += LF + text("Thank you!") + LF + LF

    # Full cut where supported.
    out += GS + b"V" + _cmd(0)
    return bytes(out)
