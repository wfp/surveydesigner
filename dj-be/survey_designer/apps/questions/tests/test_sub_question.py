def test_sub_question_properties(sub_question_4, sub_question_1, sub_question_2):
    assert str(sub_question_4) == sub_question_4.name
    assert sub_question_4.get_type_display()
    assert sub_question_1.get_type_display()
    assert sub_question_2.get_type_display()
