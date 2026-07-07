from src.services.garmin_formatter import format_garmin_workout

def test_format_garmin_workout_success():
    name = "Tempo Threshold Intervals"
    warm_up = ["Jog 10 minutes slowly", "Execute 3x100m strides"]
    main_set = ["Repeat 3 times: Run 6 mins at tempo, recovery 2 mins jog"]
    cool_down = ["Jog 5 minutes slowly"]
    
    result = format_garmin_workout(
        name=name,
        warm_up=warm_up,
        main_set=main_set,
        cool_down=cool_down,
        target_pace_range="7:25-7:40",
        target_hr_zone="Zone 3",
        target_rpe=7
    )
    
    assert "Tempo Threshold Intervals" in result
    assert "Jog 10 minutes slowly" in result
    assert "Repeat 3 times: Run 6 mins at tempo" in result
    assert "7:25-7:40" in result
    assert "Zone 3" in result
    assert "RPE" in result

def test_format_garmin_workout_empty_sets():
    result = format_garmin_workout(
        name="Easy Run",
        warm_up=[],
        main_set=[],
        cool_down=[]
    )
    assert "Warm Up: 5-10 minutes easy jogging." in result
    assert "Run: Steady pace." in result
    assert "Cool Down: 5-10 minutes easy recovery jog." in result
