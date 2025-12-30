def test_root_question_duplication(
    root_question_1, sub_question_1, sub_question_2, sub_question_4
):
    assert root_question_1.duplicate()
