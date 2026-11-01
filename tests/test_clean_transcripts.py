from docx import Document

from clean_transcripts import clean_data, remove_text


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


def test_strip_speaker_labels():
    from clean_transcripts import strip_speaker_labels

    assert strip_speaker_labels("de mayagüez J: -e bien yo LMP: - si E: ¿cómo? A las") == "de mayagüez e bien yo si ¿cómo? A las"


def test_clean_turns_drops_interviewer_line():
    from clean_transcripts import clean_turns

    text = "".join(f"línea {i}\n" for i in range(10)) + "E: ¿y el barrio? ¿cómo era?\nera muy tranquilo\nB: habrá títeres\nG.: hasta luego\n"
    assert clean_turns(text).split("\n")[10:] == ["", "era muy tranquilo", "", "", ""]


def test_clean_turns_inline_keeps_answer_after_question():
    from clean_transcripts import clean_turns

    assert clean_turns("comento? E: ¿cómo será Tunja? difícil, difícil") == "comento?  difícil, difícil"


def test_clean_turns_keeps_participant_label_turns():
    from clean_transcripts import clean_turns

    text = "inicio " + "J: -sí " * 20 + "X: -(tercera voz) susan J: -bueno"
    assert clean_turns(text).split() == ("inicio " + "sí " * 20 + "bueno").split()
    assert clean_turns("sabía. E: ¿Y ya sabía inglés? I: Mi inglés no era muy bueno. E: Ah-ha. I: El clima").split() == "sabía. Mi inglés no era muy bueno. El clima".split()


def test_clean_turns_drops_third_voice_under_participant_label():
    from clean_transcripts import clean_turns

    text = "inicio " + "F: -sí " * 20 + "F: -(tercera voz) sigue F: -yo tengo hermano"
    assert clean_turns(text).split()[-4:] == ["sí", "yo", "tengo", "hermano"]


def test_clean_turns_inline_interviewer_turn_ends_after_questions():
    from clean_transcripts import clean_turns

    text = "los niños E.: a, ¡ve que si!, se nota ¿no? ¿cuántos años llevan juntos?, me decía hace veinte años"
    assert clean_turns(text).split() == "los niños , me decía hace veinte años".split()


def test_clean_turns_line_based_drops_frequent_other_speaker():
    from clean_transcripts import clean_turns

    text = "".join(f"él habla {i}\nA.: ella responde {i}\n" for i in range(25))
    assert "ella" not in clean_turns(text)
    assert clean_turns(text).count("él habla") == 25
