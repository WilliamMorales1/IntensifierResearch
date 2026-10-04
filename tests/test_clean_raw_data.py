from docx import Document

from step_5_clean_raw_data import clean_data, remove_text


def write_docx(path, paragraphs):
    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    doc.save(path)


def test_clean_data_keeps_interviewee_turns(tmp_path):
    src, out = tmp_path / "original", tmp_path / "text"
    src.mkdir()
    write_docx(src / "05_speaker.docx", [
        "A: era muy bonito (risas) el barrio",
        "B: ¿y ahora?",
        "A: ahora está • bien",
        "B: fin",
    ])

    clean_data(str(src), str(out))

    assert (out / "05_speaker.txt").read_text(encoding="utf-8") == "era muy bonito el barrio\nahora está  bien"


def test_clean_data_reads_b_turns_for_listed_files(tmp_path):
    src, out = tmp_path / "original", tmp_path / "text"
    src.mkdir()
    write_docx(src / "21_speaker.docx", ["A: pregunta", "B: respuesta", "A: fin"])

    clean_data(str(src), str(out))

    assert (out / "21_speaker.txt").read_text(encoding="utf-8") == "respuesta"


def test_remove_text_drops_leading_words(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("uno dos tres\ncuatro cinco\nseis\n", encoding="utf-8")

    remove_text(str(tmp_path), 4)

    assert f.read_text(encoding="utf-8") == "cinco\nseis\n"
