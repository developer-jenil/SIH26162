from agnivani.geo.india import point_in_india, india_mask

def test_mainland_and_sri_lanka():
    assert point_in_india(77.2,28.6)
    assert point_in_india(70.02,22.35)
    assert not point_in_india(80.77,7.87)
    assert india_mask([77.2,80.77],[28.6,7.87]).tolist()==[True,False]
