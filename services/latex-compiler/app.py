from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import subprocess, tempfile, pathlib

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/compile")
def compile_pdf(payload: dict):
    latex = payload.get("latex")
    if not latex or not isinstance(latex, str) or not latex.strip():
        raise HTTPException(400, "Missing 'latex' field")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = pathlib.Path(tmpdir)
        tex_file = tmp_path / "main.tex"
        tex_file.write_text(latex, encoding="utf-8")

        try:
            # nonstopmode prevents interactive hang
            subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=tmpdir,
                check=True,
                timeout=45,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.TimeoutExpired:
            raise HTTPException(504, "Compilation timeout")
        except subprocess.CalledProcessError as e:
            # Try to return the LaTeX log (best signal)
            log_path = tmp_path / "main.log"
            if log_path.exists():
                log = log_path.read_text(errors="ignore")
                # return last part so payload isn't huge
                tail = log[-4000:]
                raise HTTPException(400, f"LaTeX compilation failed. Log tail:\n{tail}")
            # fallback to stdout
            raise HTTPException(400, f"LaTeX compilation failed. Output:\n{(e.stdout or '')[-4000:]}")

        pdf_file = tmp_path / "main.pdf"
        if not pdf_file.exists():
            raise HTTPException(500, "PDF not generated")

        return Response(
            content=pdf_file.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=resume.pdf"},
        )