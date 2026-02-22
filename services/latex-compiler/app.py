from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import tempfile, subprocess, pathlib

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/compile", response_class=Response)
def compile_pdf(payload: dict):
    latex = payload.get("latex")
    if not latex:
        raise HTTPException(400, "Missing 'latex' field")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        tex_file = tmp_path / "main.tex"
        tex_file.write_text(latex, encoding="utf-8")

        try:
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "main.tex"],
                cwd=tmpdir,
                check=True,
                timeout=30
            )
        except subprocess.CalledProcessError:
            raise HTTPException(400, "LaTeX compilation failed")
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "Compilation timeout")

        pdf_file = tmp_path / "main.pdf"
        if not pdf_file.exists():
            raise HTTPException(500, "PDF not generated")

        return Response(
            content=pdf_file.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"}
        )