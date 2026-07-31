from typing import List

def format_garmin_workout(
    name: str,
    warm_up: List[str],
    main_set: List[str],
    cool_down: List[str],
    target_pace_range: str = "N/A",
    target_hr_zone: str = "N/A",
    target_rpe: int = 5
) -> str:
    """
    Format workout steps into manual Garmin Connect app steps.
    """
    steps = []
    steps.append(f"Manual Garmin Connect Workout Setup for '{name}':")
    steps.append("")
    
    step_num = 1
    if warm_up:
        steps.append(f"{step_num}. Warm Up:")
        for step in warm_up:
            steps.append(f"   - {step}")
        steps.append("")
        step_num += 1
        
    if main_set:
        steps.append(f"{step_num}. Run (Main Set):")
        for step in main_set:
            steps.append(f"   - {step}")
        if target_pace_range and target_pace_range != "N/A":
            steps.append(f"   - Target Pace: {target_pace_range} min/mile")
        if target_hr_zone and target_hr_zone != "N/A":
            steps.append(f"   - Target Heart Rate: {target_hr_zone}")
        if target_rpe:
            steps.append(f"   - Target Effort (RPE): {target_rpe}/10")
        steps.append("")
        step_num += 1
    else:
        steps.append(f"{step_num}. Run: Steady pace.")
        steps.append("")
        step_num += 1
        
    if cool_down:
        steps.append(f"{step_num}. Cool Down:")
        for step in cool_down:
            steps.append(f"   - {step}")
        steps.append("")
        
    return "\n".join(steps).strip()
