def test_base_question_properties(root_question_1):
    base_question = root_question_1.base_question

    assert str(base_question)
    assert base_question.real_root_question
    assert base_question.name
    assert base_question.type
    assert base_question.get_type_display()
    assert base_question.description
