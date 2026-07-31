import os
import json
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from google.genai import types

from src.config import settings
from src.models.activity import ConnectedAccount
from src.models.plan import TrainingSession, TrainingPlan
from src.services.planner_service import get_gemini_client

# Garmin Connect client imports
from garminconnect import Garmin
from garminconnect.workout import (
    RunningWorkout,
    WorkoutSegment,
    ExecutableStep,
    RepeatGroup,
    StepType,
    ConditionType,
    TargetType
)
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# Password Encryption Helpers
# -------------------------------------------------------------

def encrypt_password(password: str) -> str:
    """Encrypt a raw string using Fernet symmetric encryption."""
    f = Fernet(settings.GARMIN_ENCRYPTION_KEY.encode())
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted string using Fernet symmetric encryption."""
    f = Fernet(settings.GARMIN_ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted_password.encode()).decode()

# -------------------------------------------------------------
# Connection Verification
# -------------------------------------------------------------

def test_garmin_login(email: str, password: str) -> bool:
    """Validate Garmin login credentials by attempting to authenticate."""
    try:
        client = Garmin(email, password)
        client.login()
        return True
    except Exception as e:
        raise Exception(f"Garmin Connection Error: {str(e)}")

# -------------------------------------------------------------
# Garmin Session Helper — caches tokens to avoid rate limiting
# -------------------------------------------------------------

def get_garmin_client(account: "ConnectedAccount", db: Session) -> "Garmin":
    """Return an authenticated Garmin client.
    
    Strategy:
    1. If cached garth session tokens exist in DB, try to resume the session.
    2. If resume fails (expired/invalid), fall back to fresh email+password login.
    3. After any successful fresh login, persist the new tokens to DB.
    """
    import logging
    logger = logging.getLogger(__name__)

    garmin_email = account.access_token
    garmin_password = decrypt_password(account.refresh_token)

    # --- Attempt 1: resume from cached tokens ---
    if account.garth_tokens:
        try:
            client = Garmin(garmin_email, garmin_password)
            client.client.loads(account.garth_tokens)
            client._load_profile_and_settings()
            logger.info("[GarminClient] Resumed session from cached tokens — no login needed.")
            return client
        except Exception as resume_err:
            logger.warning(f"[GarminClient] Cached session expired or invalid ({resume_err}), falling back to fresh login.")

    # --- Attempt 2: fresh login ---
    try:
        client = Garmin(garmin_email, garmin_password)
        client.login()
        logger.info("[GarminClient] Fresh login succeeded.")
    except Exception as login_err:
        raise Exception(f"Failed to log in to Garmin Connect. Please verify your credentials: {str(login_err)}")

    # Persist the new tokens so the next request can skip login
    try:
        tokens_val = client.client.dumps()
        if isinstance(tokens_val, str):
            account.garth_tokens = tokens_val
            db.commit()
            logger.info("[GarminClient] Garth session tokens saved to database.")
        else:
            logger.info("[GarminClient] Client dumps did not return a string (mocked in tests?); skipping database save.")
    except Exception as save_err:
        logger.warning(f"[GarminClient] Could not save garth tokens: {save_err}")

    return client


# -------------------------------------------------------------
# Gemini Structured Workout Parser Schema
# -------------------------------------------------------------

class GeminiSubStep(BaseModel):
    step_type: str = Field(default="interval", description="Step type: warmup, cooldown, interval, recovery, rest, other")
    end_condition: str = Field(default="time", description="End condition trigger: time, distance, lap_button")
    end_condition_value: float = Field(default=0.0, description="Duration value: seconds if time, miles if distance, 0.0 if lap_button")
    target_type: str = Field(default="no_target", description="Target type: no_target, pace, heart_rate")
    target_value_low: float = Field(default=0.0, description="Slower velocity in m/s if pace, min HR in BPM if heart_rate, 0.0 otherwise")
    target_value_high: float = Field(default=0.0, description="Faster velocity in m/s if pace, max HR in BPM if heart_rate, 0.0 otherwise")
    description: str = Field(default="", description="Short instruction summary for the step")

class GeminiWorkoutStep(BaseModel):
    is_repeat_group: bool = Field(description="True if this represents a repeat block containing sub-steps, False if a single step.")
    repeat_iterations: int = Field(default=1, description="Number of iterations if is_repeat_group is True.")
    repeat_steps: Optional[List[GeminiSubStep]] = Field(default=None, description="Sub-steps to repeat if is_repeat_group is True.")

    # Fields for normal individual step
    step_type: str = Field(default="interval", description="Step type: warmup, cooldown, interval, recovery, rest, other")
    end_condition: str = Field(default="time", description="End condition trigger: time, distance, lap_button")
    end_condition_value: float = Field(default=0.0, description="Duration value: seconds if time, miles if distance, 0.0 if lap_button")
    target_type: str = Field(default="no_target", description="Target type: no_target, pace, heart_rate")
    target_value_low: float = Field(default=0.0, description="Slower velocity in m/s if pace, min HR in BPM if heart_rate, 0.0 otherwise")
    target_value_high: float = Field(default=0.0, description="Faster velocity in m/s if pace, max HR in BPM if heart_rate, 0.0 otherwise")
    description: str = Field(default="", description="Short instruction summary for the step")

class GeminiGarminWorkout(BaseModel):
    session_id: str = Field(description="The unique database ID of the session")
    workoutName: str = Field(description="A clean, concise name for the watch workout (max 15 characters, letters/numbers only)")
    description: str = Field(description="A brief description of the workout")
    estimatedDurationInSecs: int = Field(description="Total estimated workout duration in seconds")
    steps: List[GeminiWorkoutStep] = Field(description="Ordered list of steps or repeat groups")

class GeminiGarminWorkoutResponse(BaseModel):
    workouts: List[GeminiGarminWorkout] = Field(description="A list of structured workouts")

# -------------------------------------------------------------
# Garmin JSON Mapper
# -------------------------------------------------------------

def map_gemini_step_to_garmin(step: GeminiWorkoutStep, step_order: int) -> Union[ExecutableStep, RepeatGroup]:
    """Map the simplified Gemini step/repeat schema to garminconnect Pydantic models."""
    if step.is_repeat_group:
        sub_steps = []
        for idx, sub in enumerate(step.repeat_steps or []):
            sub_mapped = _map_individual_step(sub, step_order=idx + 1)
            sub_steps.append(sub_mapped)
        
        return RepeatGroup(
            stepOrder=step_order,
            numberOfIterations=step.repeat_iterations,
            workoutSteps=sub_steps,
            stepType={
                "stepTypeId": StepType.REPEAT,
                "stepTypeKey": "repeat",
                "displayOrder": 6
            }
        )
    else:
        return _map_individual_step(step, step_order)

def _map_individual_step(step: Union[GeminiWorkoutStep, GeminiSubStep], step_order: int) -> ExecutableStep:
    """Helper to map a single step's fields to a Garmin ExecutableStep."""
    # Map step type
    st_map = {
        "warmup": (StepType.WARMUP, "warmup", 1),
        "cooldown": (StepType.COOLDOWN, "cooldown", 2),
        "interval": (StepType.INTERVAL, "interval", 3),
        "recovery": (StepType.RECOVERY, "recovery", 4),
        "rest": (StepType.REST, "rest", 5),
        "other": (StepType.OTHER, "other", 7)
    }
    st_id, st_key, st_order = st_map.get(step.step_type.lower(), (StepType.INTERVAL, "interval", 3))
    
    # Map end condition
    ec_map = {
        "lap_button": (ConditionType.LAP_BUTTON, "lap.button", 1),
        "time": (ConditionType.TIME, "time", 2),
        "distance": (ConditionType.DISTANCE, "distance", 3)
    }
    ec_id, ec_key, ec_order = ec_map.get(step.end_condition.lower(), (ConditionType.TIME, "time", 2))
    
    # Calculate condition value
    ec_val = step.end_condition_value
    if step.end_condition.lower() == "distance":
        ec_val = round(step.end_condition_value * 1609.34, 2)  # Miles to meters
    elif step.end_condition.lower() == "lap_button":
        ec_val = 0.0
        
    # Map target type
    tt_map = {
        "no_target": (TargetType.NO_TARGET, "no.target", 1),
        "pace": (TargetType.PACE_ZONE, "pace.zone", 6), # Absolute pace targets
        "heart_rate": (TargetType.HEART_RATE_ZONE, "heart.rate.zone", 4)
    }
    tt_id, tt_key, tt_order = tt_map.get(step.target_type.lower(), (TargetType.NO_TARGET, "no.target", 1))
    
    # Initialize ExecutableStep
    exec_step = ExecutableStep(
        stepOrder=step_order,
        stepType={
            "stepTypeId": st_id,
            "stepTypeKey": st_key,
            "displayOrder": st_order
        },
        endCondition={
            "conditionTypeId": ec_id,
            "conditionTypeKey": ec_key,
            "displayOrder": ec_order,
            "displayable": True
        },
        endConditionValue=ec_val,
        targetType={
            "workoutTargetTypeId": tt_id,
            "workoutTargetTypeKey": tt_key,
            "displayOrder": tt_order
        }
    )
    
    # Add target ranges if configured
    # Garmin's PACE_ZONE (targetType 6) uses m/s for targetValueOne/Two
    if step.target_type.lower() == "pace" and step.target_value_high > 0:
        # targetValueOne = slower speed (slower pace boundary) in m/s
        # targetValueTwo = faster speed (faster pace boundary) in m/s
        exec_step.targetValueOne = round(step.target_value_low, 4)   # Slower velocity in m/s
        exec_step.targetValueTwo = round(step.target_value_high, 4)  # Faster velocity in m/s
    elif step.target_type.lower() == "heart_rate" and step.target_value_high > 0:
        # Set heart rate targets in BPM
        exec_step.targetValueOne = step.target_value_low
        exec_step.targetValueTwo = step.target_value_high
        
    return exec_step

# -------------------------------------------------------------
# Plan Synchronization Service
# -------------------------------------------------------------

def clear_garmin_calendar(user_id: str, db: Session) -> Dict[str, Any]:
    """Log in to Garmin Connect and remove all scheduled workouts from tomorrow through plan end date.
    Returns a report of what was found and deleted (for debugging)."""
    import logging
    from datetime import timedelta
    logger = logging.getLogger(__name__)

    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "garmin"
    ).first()
    if not account:
        raise Exception("Garmin account credentials are not configured. Please set them up in profile settings first.")

    garmin_email = account.access_token
    garmin_password = decrypt_password(account.refresh_token)

    active_plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    if not active_plan:
        raise Exception("No active training plan found.")

    try:
        garmin_client = get_garmin_client(account, db)
    except Exception as login_err:
        raise Exception(f"Failed to log in to Garmin Connect. Please verify your credentials: {str(login_err)}")

    today = date.today()
    tomorrow = today + timedelta(days=1)
    clear_from_str = tomorrow.isoformat()
    end_date_str = active_plan.end_date.isoformat() if active_plan.end_date else "2030-12-31"

    months_to_fetch = []
    curr_year = today.year
    curr_month = today.month
    end_year = active_plan.end_date.year if active_plan.end_date else today.year
    end_month = active_plan.end_date.month if active_plan.end_date else today.month
    limit = 0
    while (curr_year, curr_month) <= (end_year, end_month) and limit < 12:
        months_to_fetch.append((curr_year, curr_month))
        curr_month += 1
        if curr_month > 12:
            curr_month = 1
            curr_year += 1
        limit += 1

    removed = []
    skipped = []
    raw_sample = []  # capture first few items for diagnosis

    for y, m in months_to_fetch:
        try:
            scheduled = garmin_client.get_scheduled_workouts(y, m)
            
            if isinstance(scheduled, dict):
                scheduled_items = scheduled.get("calendarItems", [])
            elif isinstance(scheduled, list):
                scheduled_items = scheduled
            else:
                scheduled_items = []
                
            logger.info(f"[ClearGarmin] {y}-{m:02d}: got {len(scheduled_items)} items")
            if scheduled_items:
                # Log the raw keys of the first item per month for diagnosis
                if len(raw_sample) < 3:
                    raw_sample.append({"month": f"{y}-{m:02d}", "keys": list(scheduled_items[0].keys()), "sample": scheduled_items[0]})

                for item in scheduled_items:
                    cal_date = item.get("calendarDate") or item.get("date") or item.get("scheduledDate")
                    # Try multiple possible ID field names
                    schedule_id = (
                        item.get("workoutScheduleId") or
                        item.get("scheduleId") or
                        item.get("id") or
                        item.get("workoutId")
                    )
                    logger.info(f"[ClearGarmin] item date={cal_date} id={schedule_id} keys={list(item.keys())}")

                    if cal_date and clear_from_str <= cal_date <= end_date_str and schedule_id:
                        try:
                            garmin_client.unschedule_workout(schedule_id)
                            removed.append({"date": cal_date, "id": schedule_id})
                            logger.info(f"[ClearGarmin] REMOVED schedule_id={schedule_id} on {cal_date}")
                        except Exception as del_err:
                            skipped.append({"date": cal_date, "id": schedule_id, "error": str(del_err)})
                            logger.warning(f"[ClearGarmin] FAILED to remove {schedule_id}: {del_err}")
                    else:
                        logger.info(f"[ClearGarmin] SKIPPED: date={cal_date} in_range={cal_date is not None and clear_from_str <= cal_date <= end_date_str} id={schedule_id}")
        except Exception as fetch_err:
            logger.warning(f"[ClearGarmin] Failed to fetch {y}-{m}: {fetch_err}")

    return {
        "status": "success",
        "message": f"Removed {len(removed)} scheduled workouts from Garmin calendar ({clear_from_str} to {end_date_str}).",
        "removed_count": len(removed),
        "removed": removed,
        "skipped": skipped,
        "raw_sample": raw_sample,
    }

def push_plan_to_garmin(user_id: str, db: Session, force_clear: bool = False) -> Dict[str, Any]:
    """Fetch user's upcoming active plan sessions, parse them with Gemini, and push to GarminConnect calendar."""
    # Retrieve credentials
    account = db.query(ConnectedAccount).filter(
        ConnectedAccount.user_id == user_id,
        ConnectedAccount.provider == "garmin"
    ).first()
    
    if not account:
        raise Exception("Garmin account credentials are not configured. Please set them up in profile settings first.")
        
    garmin_email = account.access_token
    garmin_password = decrypt_password(account.refresh_token)
    
    # Fetch active plan and its future sessions
    active_plan = db.query(TrainingPlan).filter(
        TrainingPlan.user_id == user_id,
        TrainingPlan.status == "active"
    ).first()
    
    if not active_plan:
        raise Exception("No active training plan found. Please generate a training plan first.")
        
    # Find the easy pace range from the plan sessions
    easy_pace_range = "9:00-10:00"  # default fallback
    all_sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == active_plan.id
    ).all()
    for s in all_sessions:
        if s.type.lower() == "easy" and s.target_pace_range and s.target_pace_range != "N/A":
            easy_pace_range = s.target_pace_range
            break

    today = date.today()
    future_sessions = db.query(TrainingSession).filter(
        TrainingSession.plan_id == active_plan.id,
        TrainingSession.date >= today,
        TrainingSession.type != "Rest"  # Skip Rest Days
    ).order_by(TrainingSession.date).all()
    
    if not future_sessions:
        return {
            "status": "success",
            "message": "No upcoming training sessions to sync (rest days or completed plans skipped)."
        }
        
    # Generate structured workout list using Gemini in a single batch call
    session_list_text = []
    for s in future_sessions:
        # Safely parse DB JSON fields for step instructions
        warm_up_steps = []
        main_set_steps = []
        cool_down_steps = []
        try:
            if s.warm_up_json:
                warm_up_steps = json.loads(s.warm_up_json)
        except:
            pass
        try:
            if s.main_set_json:
                main_set_steps = json.loads(s.main_set_json)
        except:
            pass
        try:
            if s.cool_down_json:
                cool_down_steps = json.loads(s.cool_down_json)
        except:
            pass

        session_list_text.append({
            "id": s.id,
            "date": s.date.isoformat(),
            "type": s.type,
            "name": s.name,
            "description": s.description,
            "warm_up_instructions": warm_up_steps,
            "main_set_instructions": main_set_steps,
            "cool_down_instructions": cool_down_steps,
            "garmin_instructions": s.garmin_instructions_text,
            "duration_minutes": s.duration_minutes,
            "distance_miles": s.distance_miles,
            "target_pace_range": s.target_pace_range,
            "target_hr_zone": s.target_hr_zone,
            "target_rpe": s.target_rpe
        })
        
    prompt = (
        "You are an expert running coach parsing calendar training runs into Garmin watch structured workouts.\n\n"
        "Input Sessions:\n"
        f"{json.dumps(session_list_text, indent=2)}\n\n"
        "For each input session:\n"
        "1. Create a structured workout matching the instructions in warm_up_instructions, main_set_instructions, cool_down_instructions, and garmin_instructions.\n"
        "2. SESSION TYPE & STEP RULES:\n"
        "   - For Easy, Recovery, and Long Run sessions (or any session where warm_up_instructions and cool_down_instructions are empty): generate ONLY a single run step (step_type='interval') covering the main set distance or duration. Do NOT create separate warmup or cooldown steps for Easy, Recovery, or Long runs.\n"
        "   - For Quality sessions (Tempo, Intervals, Fartlek, Hill Repeats, Speedwork): generate the warmup step (step_type='warmup'), main set repeat group or interval steps (step_type='interval'), and cooldown step (step_type='cooldown').\n"
        "3. Parse intervals/repeats if described. For example, if main_set_instructions or garmin_instructions says 'Run 3 x 0.5-mile intervals with 2-minute recovery jogs', generate a repeat group with 3 iterations containing a distance-based run step of 0.5 miles and a time-based recovery step of 120 seconds.\n"
        "4. For Quality sessions, do NOT omit the cool-down step if specified! Generate the final cooldown step (with step_type='cooldown') after the main set.\n"
        "5. Set end conditions correctly: time (value in seconds) or distance (value in miles) or lap_button (value 0.0).\n"
        "   - Warmup and cooldown steps can be distance-based if a distance is specified (e.g. 'Warm up 1.0 mile' -> distance=1.0), or time-based or lap_button if not specified.\n"
        "6. Calculate target values for speed (meters per second) if target_type is 'pace':\n"
        "   - Formula: speed (m/s) = 1609.34 / (pace in seconds per mile).\n"
        "   - Slower pace velocity (slower speed) goes to target_value_low. Faster pace velocity (faster speed) goes to target_value_high.\n"
        "   - Example: 8:00 min/mile pace is 480 seconds per mile -> speed = 1609.34 / 480 = 3.35 m/s.\n"
        "7. Set target_type to 'pace' for all main set run/interval steps using the session's 'target_pace_range'.\n"
        f"8. For Quality workout warmup and cooldown steps (step_type='warmup' or 'cooldown'): if easy jogging, set target_type to 'pace' using the Easy Pace Range: '{easy_pace_range}'. If walking or stretching, set target_type to 'no_target'.\n"
        "9. Ensure the estimatedDurationInSecs is the sum of all steps' durations (for lap_button steps, assume a reasonable estimate like 600 seconds for warmups/cooldowns).\n"
    )
    
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiGarminWorkoutResponse
            )
        )
        parsed_response = GeminiGarminWorkoutResponse.model_validate_json(response.text)
        # Log the raw response to diagnose pace target issues
        import logging as _logging
        _log = _logging.getLogger(__name__)
        _log.info(f"[GarminSync] Raw Gemini response: {response.text[:3000]}")
    except Exception as gemini_err:
        raise Exception(f"Failed to generate structured watch workouts using AI: {str(gemini_err)}")
        
    # Connect to Garmin
    try:
        garmin_client = get_garmin_client(account, db)
    except Exception as login_err:
        raise Exception(f"Failed to log in to Garmin Connect. Please verify your credentials: {str(login_err)}")
        
    # Clear existing scheduled workouts from the calendar within the plan date range
    # Start from tomorrow so today's workout is never touched (it may not be done yet)
    from datetime import timedelta
    tomorrow = today + timedelta(days=1)
    clear_from_str = tomorrow.isoformat()
    end_date_str = active_plan.end_date.isoformat() if active_plan.end_date else "2030-12-31"
    
    months_to_fetch = []
    curr_year = today.year
    curr_month = today.month
    end_year = active_plan.end_date.year if active_plan.end_date else today.year
    end_month = active_plan.end_date.month if active_plan.end_date else today.month
    
    limit = 0
    while (curr_year, curr_month) <= (end_year, end_month) and limit < 12:
        months_to_fetch.append((curr_year, curr_month))
        curr_month += 1
        if curr_month > 12:
            curr_month = 1
            curr_year += 1
        limit += 1
        
    # Collect all workout names generated in this batch (both raw and prefixed)
    aurarun_names = set()
    for w in parsed_response.workouts:
        name = w.workoutName
        aurarun_names.add(name.lower())
        if not name.lower().startswith("aura"):
            aurarun_names.add(f"aura{name}".lower()[:15])
            
    known_aurarun_names = {
        "activerecovery", "actrecoveasy", "aerobicmaint", "endurance8k", 
        "midweekeasy", "aerobicintintro", "aerintintro", "speedplay", 
        "pacingfeel", "pacefeelrun", "pacingfeelrun", "build9k", 
        "builddist9k", "builddist93k", "steadymidweek", "fartlekplay", 
        "earlytempo", "tempointro", "postfartlekrec", "posttemporec", 
        "endurance10k", "endur10k", "endmilestone", "endurance103k", 
        "aerobicbuild", "aerfoundbuild", "aerofoundbuild", "susttempointro", 
        "sustainedtempo", "weekendwarmup", "endurance11k", "endurstepup11k", 
        "endstepup112k", "stepup112k", "recweekopener", "speedsharpener", 
        "gentlespeed"
    }
    
    for y, m in months_to_fetch:
        try:
            scheduled = garmin_client.get_scheduled_workouts(y, m)
            
            if isinstance(scheduled, dict):
                scheduled_items = scheduled.get("calendarItems", [])
            elif isinstance(scheduled, list):
                scheduled_items = scheduled
            else:
                scheduled_items = []
                
            if scheduled_items:
                for item in scheduled_items:
                    cal_date = item.get("calendarDate") or item.get("date") or item.get("scheduledDate")
                    schedule_id = (
                        item.get("workoutScheduleId") or
                        item.get("scheduleId") or
                        item.get("id") or
                        item.get("workoutId")
                    )
                    
                    if cal_date and clear_from_str <= cal_date <= end_date_str and schedule_id:
                        if force_clear:
                            # Nuclear option: remove ALL scheduled workouts in the date range
                            garmin_client.unschedule_workout(schedule_id)
                        else:
                            # Standard: only remove workouts matching our plan names
                            title = item.get("title") or item.get("workoutName") or ""
                            title_lower = title.strip().lower()
                            
                            desc = item.get("description") or ""
                            workout_obj = item.get("workout") or {}
                            w_desc = workout_obj.get("description") or ""
                            w_name = workout_obj.get("workoutName") or ""
                            w_name_root = item.get("workoutName") or ""
                            
                            is_aurarun = (
                                title_lower.startswith("aura") or
                                title_lower in aurarun_names or
                                title_lower in known_aurarun_names or
                                "aurarun" in desc.lower() or
                                "aurarun" in w_desc.lower() or
                                "aurarun" in w_name.lower() or
                                "aurarun" in w_name_root.lower()
                            )
                            
                            if is_aurarun:
                                garmin_client.unschedule_workout(schedule_id)
        except Exception as fetch_err:
            import logging
            logging.getLogger(__name__).warning(f"Failed to clear existing calendar workouts for {y}-{m}: {fetch_err}")
            
    synced_count = 0
    # Process and upload each structured workout
    for workout in parsed_response.workouts:
        # Find corresponding session from database to get date
        db_session = next((s for s in future_sessions if s.id == workout.session_id), None)
        if not db_session:
            continue
            
        # Map steps to GarminConnect schema
        workout_steps = []
        for index, step in enumerate(workout.steps):
            workout_steps.append(map_gemini_step_to_garmin(step, step_order=index + 1))
            
        # Create workout segment
        segment = WorkoutSegment(
            segmentOrder=1,
            sportType={"sportTypeId": 1, "sportTypeKey": "running", "displayOrder": 1},
            workoutSteps=workout_steps
        )
        
        # Build Garmin running workout name (letters/numbers only, max 15 chars, prefixed with Aura)
        w_name = workout.workoutName
        if not w_name.lower().startswith("aura"):
            w_name = f"Aura{w_name}"
        w_name = w_name[:15]

        # Build Garmin running workout model
        running_workout = RunningWorkout(
            workoutName=w_name,
            description=f"AuraRun: {workout.description}",
            estimatedDurationInSecs=workout.estimatedDurationInSecs,
            workoutSegments=[segment]
        )
        
        try:
            # Upload workout using the official typed method to exclude None values
            res = garmin_client.upload_running_workout(running_workout)
            workout_id = res["workoutId"]
            
            # Schedule workout on calendar
            date_str = db_session.date.isoformat()
            garmin_client.schedule_workout(workout_id, date_str)
            synced_count += 1
        except Exception as upload_err:
            # Continue trying others even if one fails
            import logging
            logging.getLogger(__name__).error(f"Error syncing session {workout.workoutName} on {db_session.date}: {upload_err}")
            
    return {
        "status": "success",
        "message": f"Successfully pushed {synced_count} structured running workouts to your Garmin calendar!",
        "synced_count": synced_count
    }
