"""Impression facultative; aucune commande n'est executee sans confirmation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class PrintResult:
    printer: str
    pages: int
    executed: bool


def available_printers() -> list[str]:
    if os.name == "nt":
        command = "Get-Printer | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15, check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        return [str(data)] if isinstance(data, str) else [str(item) for item in data]
    lpstat = shutil.which("lpstat")
    if not lpstat:
        return []
    result = subprocess.run([lpstat, "-p"], capture_output=True, text=True, check=False)
    return [line.split()[1] for line in result.stdout.splitlines() if line.startswith("printer ")]


def _choose(name: str) -> str:
    requested = name.strip()
    printers = available_printers()
    if requested:
        match = next((printer for printer in printers if printer.casefold() == requested.casefold()), None)
        if not match:
            raise RuntimeError(f"Imprimante introuvable: {requested}")
        return match
    physical = [printer for printer in printers if printer.casefold() not in {
        "fax", "microsoft print to pdf", "onenote (desktop)",
    }]
    if len(physical) != 1:
        raise RuntimeError("Indique --printer quand zero ou plusieurs imprimantes sont disponibles.")
    return physical[0]


def _pdf_en_images(path: Path, dossier: Path, dpi: int = 180) -> None:
    """Convertit chaque page en PNG (pdftoppm s'il est installe, sinon pypdfium2)."""
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        subprocess.run([pdftoppm, "-png", "-r", str(dpi), str(path), str(dossier / "page")], check=True)
        return
    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise RuntimeError("Installe pypdfium2 (ou pdftoppm) pour l'impression Windows.") from error
    document = pdfium.PdfDocument(str(path))
    try:
        for index in range(len(document)):
            image = document[index].render(scale=dpi / 72).to_pil()
            image.save(dossier / f"page-{index + 1:02d}.png")
    finally:
        document.close()


def print_pdf(
    path: Path, *, printer: str = "", duplex: bool = False, execute: bool = False,
) -> PrintResult:
    path = path.resolve()
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise FileNotFoundError(path)
    pages = len(PdfReader(str(path)).pages)
    selected = _choose(printer)
    if not execute:
        return PrintResult(selected, pages, False)
    if os.name != "nt":
        lp = shutil.which("lp")
        if not lp:
            raise RuntimeError("La commande CUPS 'lp' est introuvable.")
        command = [lp, "-d", selected]
        if duplex:
            command += ["-o", "sides=two-sided-long-edge"]
        command.append(str(path))
        subprocess.run(command, check=True)
        return PrintResult(selected, pages, True)

    script = ROOT / "scripts" / "imprimer_image_windows.ps1"
    with tempfile.TemporaryDirectory(prefix="signal-matin-") as tmp:
        _pdf_en_images(path, Path(tmp))
        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-DossierImages", tmp, "-Imprimante", selected,
        ]
        if duplex:
            command.append("-RectoVerso")
        subprocess.run(command, check=True)
    return PrintResult(selected, pages, True)
